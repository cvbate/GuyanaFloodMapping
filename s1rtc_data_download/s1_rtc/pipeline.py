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
from .utils import *
###########################################################

def query_and_download(aoi_path, stac_catalog, query_range, download_bands, start_date, end_date, spatial_cover, orbit, save_path_rtc, noData=False, collection = 'sentinel-1-rtc', crs=None, clip_to_aoi=False):
    aoi, bbox = load_aoi(aoi_path)
    items = stac_query(stac_catalog, bbox, collection, query_range)
    tile_df = spatial_coverage_calc(items, aoi)
    filtered_df = query_rtc(tile_df, start_date, end_date, spatial_cover=None, orbit=None)
    if clip_to_aoi:
        clip_aoi = aoi
    else:
        clip_aoi = None
    data_download(filtered_df, download_bands, save_path = save_path_rtc, clip_aoi = clip_aoi, crs=crs, noData=noData)
    