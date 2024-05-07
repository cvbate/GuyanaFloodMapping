from .utils import *

###########################################################

def query_and_download(aoi_path: str, stac_catalog: str, query_range: str, download_bands: list, start_date: str, end_date: str, spatial_cover: int, orbit: str, save_path_rtc: str, noData: bool=False, collection: str = 'sentinel-1-rtc', crs:str =None, clip_to_aoi: bool=False):
    r"""Comprehensive sentinel-1 rtc data query and download function.

    Arguments:
    ----------
    aoi_path (str): Path to the area of interest geojson file.
    stac_catalog (str): Name/link to the STAC-Catalog being queried.
    query_range (str): Detailed date pair of range to query from STAC-Catalog
    download_bands (list): List of bands to be download. Pick from VV and VH, or both together.
    start_date (str): Beginning date of the filtering. Must be within the query_range.
    end_date (str): Ending date of the filtering. Must be within the query_range while be a later date of start_date.
    spatial_cover (int): The amount of spatial coverage filtering based on the ratio of coverage between the queried tiles and AOI. Typical amount in this project
            is ~5%. ~90%, ~95% and 100%. Enter None to disable this filter
    orbit (str): Orbit order picking from ascending or descending (Sentinel-1A or Sentinel-1B). Enter None to disable this filter.
    save_path_rtc (str): Path to save the filtered RTC rasters
    noData: (boolean): Boolean argument of whether apply noData pre-processing. When set to True the noData value in the saved RTC images would be set to zero.
    collection (str): Data collection to query and download images. Default is RTC collection.
    crs (str): When a CRS is provided, all queried rasters will be reporjected into the provided projection before downlading. Enter None to disable this 
            pre-processing step.
    clip_to_aoi (boolean): Boolean argument that weather clipping the rasters to the AOI. 
    

    Returns:
    --------
    None
    """
    aoi, bbox = load_aoi(aoi_path)
    items = stac_query(stac_catalog, bbox, collection, query_range)
    tile_df = spatial_coverage_calc(items, aoi)
    filtered_df = query_rtc(tile_df, start_date, end_date, spatial_cover=None, orbit=None)
    if clip_to_aoi:
        clip_aoi = aoi
    else:
        clip_aoi = None
    data_download(filtered_df, download_bands, save_path = save_path_rtc, clip_aoi = clip_aoi, crs=crs, noData=noData)
    