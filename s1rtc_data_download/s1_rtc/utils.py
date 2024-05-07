import os
import dask
import json
import math
import geogif
import shutil
import leafmap
import requests
import tempfile
import rasterio
import stackstac
import pystac_client
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import rioxarray as rio
import planetary_computer as pc
import shapely.geometry as geom

from tqdm import tqdm
from pathlib import Path
from pystac import ItemCollection
from datetime import datetime as dt
from rioxarray.merge import merge_datasets
###########################################################
def load_aoi(aoi_path: str):
    aoi = gpd.read_file(aoi_path).to_crs("EPSG:4326")
    bbox = [coord for coord in aoi.bounds.values[0]]
    return aoi, bbox
###########################################################
def stac_query(stac_catalog, bbox, collection, datetime):
    
    catalog = pystac_client.Client.open(stac_catalog)
    # Sentinel1-rtc is available from 2014/10/10-present
    search = catalog.search(
        collections=[collection],
        datetime = datetime,
        bbox=bbox,
    )
    items = pc.sign(search)
    print(f"There are {len(items)} tiles found")
    return items
###########################################################
def spatial_coverage_calc(items, aoi):
    df = gpd.GeoDataFrame.from_features(items.to_dict(), crs="epsg:4326")
    geom_tiles = []
    for i in range(len(df)):
        geom_tiles.append(df.loc[i].geometry)
    sArea = aoi.geometry[0] # Study Area Geometry
    s_cover = []
    for i, geom_tile in enumerate(geom_tiles):
        # print(i, (sArea.intersection(geom_tile).area/sArea.area)*100)
        s_cover.append((sArea.intersection(geom_tile).area/sArea.area)*100)
    if len(s_cover) == len(items):
        print("Spatial coverage successfully calculated")
    meta_list = []
    for i, item in enumerate(items):
        
        datetime = item.properties["datetime"]
        tile_name = f"S1A_RTC_Guyana_{datetime.split('T')[0].replace('-', '_')}"
        vh_link = item.assets["vh"].href
        vv_link = item.assets["vv"].href
        bounds = item.geometry
        orbit = item.properties["sat:orbit_state"]
        instrument = item.properties["platform"]
        crs = f"EPSG:{item.properties['proj:epsg']}"
        temp_dict = {"tile_name": tile_name, "datetime": datetime, 
                     "vh_band": vh_link, "vv_band": vv_link, 
                     "spatial_cover": s_cover[i], "crs": crs, 
                     "orbit_order": orbit, "instrument": instrument}
    
        meta_list.append(temp_dict)
    
    tile_df = pd.DataFrame(meta_list)
    return tile_df
###########################################################
def query_rtc (df, start_date, end_date, spatial_cover=None, orbit=None):
    
    start = dt.strptime(start_date, "%Y-%m-%d")
    end = dt.strptime(end_date, "%Y-%m-%d")
    passed_list = []
    
    for i in range(len(df)):
        aqu_time = dt.strptime(df.loc[i].datetime.split("T")[0], "%Y-%m-%d")
        if start <= aqu_time and end >= aqu_time:
            if orbit:
                if orbit in df.loc[i].orbit_order:
                    if spatial_cover:
                        if df.loc[i].spatial_cover > spatial_cover:
                            passed_list.append(df.loc[i])
                    else:
                        passed_list.append(df.loc[i])
            else:
                if spatial_cover:
                    if df.loc[i].spatial_cover > spatial_cover:
                        passed_list.append(df.loc[i])
                else:
                    passed_list.append(df.loc[i])
    df = pd.DataFrame(passed_list)
    print(f"Contains images from {df.instrument.unique()} with crs of {df.crs.unique()}")
    return df
###########################################################
def local_save(item, save_path, tile_crs, clip_aoi=None, crs=None):
    if not os.path.isfile(save_path):
            if clip_aoi is not None:
                if crs is not None:
                    # print(f"Source:{tile_crs}|Target:{crs}|{crs==tile_crs}")
                    if not crs == tile_crs :
                        rio.open_rasterio(item, cache = False).rio.clip(clip_aoi.geometry.values, 
                                                                        clip_aoi.crs).rio.reproject(crs, resolution=10).rio.to_raster(save_path, driver="COG")
                    else:
                        rio.open_rasterio(item, cache = False).rio.clip(clip_aoi.geometry.values, clip_aoi.crs).rio.to_raster(save_path, driver="COG")
            else:
                if crs is not None:
                    print(f"Source:{tile_crs}|Target:{crs}|{crs==tile_crs}")
                    if not crs == tile_crs :
                        rio.open_rasterio(item, cache = False).rio.reproject(crs, resolution=10).rio.to_raster(save_path, driver="COG")
                    else:
                        rio.open_rasterio(item, cache = False).rio.to_raster(save_path, driver="COG")
###########################################################
def nodata_convert(file_path, workdir):
    temp_file_path = Path(workdir)
    with rasterio.open(file_path) as src:
        data = src.read(1)  # read the first band into an array
        profile = src.profile
        original_nodata = profile['nodata']

        # Check if the original nodata value is not 0
        if original_nodata is not None and original_nodata != 0:
            # Create a temporary file to write modified data
            with tempfile.NamedTemporaryFile(delete=False, 
                                             suffix='.tif', 
                                             dir=workdir) \
                                            as tmpfile:
                temp_file_path = tmpfile.name

            # Update the profile to specify the new NoData value and 
            #replace existing NoData values
            profile.update(nodata=0)
            mask = data == original_nodata
            if np.any(mask):
                data[mask] = 0

            # Write the modified data to the temporary file
            with rasterio.open(temp_file_path, 'w', **profile) as dst:
                dst.write(data, 1)

            with rasterio.open(temp_file_path) as src:
                nodata = src.nodatavals[0]  # Assuming only one band
                
            if nodata == 0:
                shutil.move(temp_file_path, file_path)
            else: 
                print(f"Failed to set noData value for {file_path.split('/')[-1]}. Removing temporary file...")
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
def data_download(df: pd.DataFrame(), bands: list, save_path: str=None, clip_aoi: geom=None, crs: str=None, noData: bool=False):
    
    if not save_path:
        save_path = os.getcwd()
    if not os.path.exists(save_path):
       os.makedirs(save_path)
    
    bands = [x.lower() for x in bands]
    
    if len(bands) > 2:
        raise ValueError("List cannot contain more than 2 elements")
    if not all(item in ('vh', 'vv') for item in bands):
        raise ValueError("List contains invalid items. Only 'vh' or 'vv' are allowed")

    download_queue = []
    for i in range(len(df)):
        temp = []
        if "vh" in bands:
            vh_link = df.iloc[i].vh_band
            temp.append(vh_link)
        if "vv" in bands:
            vv_link = df.iloc[i].vv_band
            temp.append(vv_link)
        tile_crs = df.iloc[i].crs.lower()
        tile_name = df.iloc[i].tile_name
        download_queue.append([temp, tile_name, tile_crs])
    for item in tqdm(download_queue):

        if "vh" in bands:
            vh_path = Path(save_path) / f"{item[1]}_vh.tif"
            if not os.path.isfile(vh_path):
                local_save(item[0][0], vh_path, tile_crs, clip_aoi, crs)
                if noData:
                    nodata_convert(vh_path, save_path)


        if "vv" in bands:
            vv_path = Path(save_path) / f"{item[1]}_vv.tif"
            if not os.path.isfile(vv_path):
                local_save(item[0][1], vv_path, tile_crs, clip_aoi, crs)
                if noData:
                    nodata_convert(vv_path, save_path)
                
    
    