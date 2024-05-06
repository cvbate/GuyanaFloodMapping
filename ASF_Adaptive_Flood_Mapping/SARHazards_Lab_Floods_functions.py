# Consolidated functions from SARHazards_Lab_Floods.ipnyb notebooks
# Original notebook: https://mybinder.org/v2/gh/ASFBinderRecipes/
# Binder_SAR_Hazards_Floods/main?labpath=SARHazards_Lab_Floods.ipynb
# André de Oliveira 4/26/2024

#----------------------------------------------ORIGINAL NOTEBOOK IMPORTED MODULE
# asf_notebook_FloodMapping.py
# Alex Lewandowski
# 9-16-2020
# Module of Alaska Satellite Facility OpenSARLab Jupyter Notebook helper 
#functions
# Minimal version of asf_notebook.py containing only the functions needed for 
#FloodMappingFromSARImages.ipynb
# 

import os

class NoHANDLayerException(Exception):
    """
    Raised when expecting path to HAND layer but none found
    """
    pass
    
def input_path(prompt):        
    print(f"Current working directory: {os.getcwd()}") 
    print(prompt)
    return input()


def handle_old_data(data_dir, contents):
    print(f"\n********************** WARNING! **********************")
    print(f"The directory {data_dir} already exists and contains:")
    for item in contents:
        print(f"• {item.split('/')[-1]}")
    print(f"\n\n[1] Delete old data and continue.")
    print(f"[2] Save old data and add the data from this analysis to it.")
    print(f"[3] Save old data and pick a different subdirectory name.")
    while True:
        try:
            selection = int(input("Select option 1, 2, or 3.\n"))
        except ValueError:
             continue
        if selection < 1 or selection > 3:
             continue
        return selection

#---------------------------------------------------------CONSOLIDATED FUNCTIONS
# FUNCTIONS FROM WORKSHOP NOTEBOOK

#@ Function to pad an image, so it may be split into tiles with consistent 
#  dimensions

import subprocess
import numpy as np
from typing import Tuple
import rasterio
from osgeo import gdal
import pyproj

def pad_image(image: np.ndarray, to: int) -> np.ndarray:
    height, width = image.shape

    n_rows, n_cols = get_tile_row_col_count(height, width, to)
    new_height = n_rows * to
    new_width = n_cols * to

    padded = np.zeros((new_height, new_width))
    padded[:image.shape[0], :image.shape[1]] = image
    return padded

## Function to tile an image
#def tile_image(
        #image: np.ndarray, width: int = 200, height: int = 200) -> np.ndarray:
def tile_image(image: np.ndarray, width, height) -> np.ndarray:
    _nrows, _ncols = image.shape
    _strides = image.strides

    nrows, _m = divmod(_nrows, height)
    ncols, _n = divmod(_ncols, width)

    assert _m == 0, "Image must be evenly tileable. Please pad it first"
    assert _n == 0, "Image must be evenly tileable. Please pad it first"

    return np.lib.stride_tricks.as_strided(
        np.ravel(image),
        shape=(nrows, ncols, height, width),
        strides=(height * _strides[0], width * _strides[1], *_strides),
        writeable=False
    ).reshape(nrows * ncols, height, width)

## Function for multi-class Expectation Maximization Thresholding
def EMSeg_opt(image, number_of_classes):
    image_copy = image.copy()
    # needed for valid posterior_lookup keys
    image_copy2 = np.ma.filled(image.astype(float), np.nan) 
    image = image.flatten()
    minimum = np.amin(image)
    image = image - minimum + 1
    maximum = np.amax(image)

    size = image.size
    histogram = make_histogram(image)
    nonzero_indices = np.nonzero(histogram)[0]
    histogram = histogram[nonzero_indices]
    histogram = histogram.flatten()
    class_means = (
            (np.arange(number_of_classes) + 1) * maximum /
            (number_of_classes + 1)
    )
    class_variances = np.ones((number_of_classes)) * maximum
    class_proportions = np.ones((number_of_classes)) * 1 / number_of_classes
    sml = np.mean(np.diff(nonzero_indices)) / 1000
    iteration = 0
    while(True):
        class_likelihood = make_distribution(
            class_means, class_variances, class_proportions, nonzero_indices
        )
        sum_likelihood = np.sum(class_likelihood, 1) + np.finfo(
                class_likelihood[0][0]).eps
        log_likelihood = np.sum(histogram * np.log(sum_likelihood))
        for j in range(0, number_of_classes):
            class_posterior_probability = (
                histogram * class_likelihood[:,j] / sum_likelihood
            )
            class_proportions[j] = np.sum(class_posterior_probability)
            class_means[j] = (
                np.sum(nonzero_indices * class_posterior_probability)
                    / class_proportions[j]
            )
            vr = (nonzero_indices - class_means[j])
            class_variances[j] = (
                np.sum(vr *vr * class_posterior_probability)
                    / class_proportions[j] +sml
            )
            del class_posterior_probability, vr
        class_proportions = class_proportions + 1e-3
        class_proportions = class_proportions / np.sum(class_proportions)
        class_likelihood = make_distribution(
            class_means, class_variances, class_proportions, nonzero_indices
        )
        sum_likelihood = np.sum(class_likelihood, 1) + np.finfo(
                class_likelihood[0,0]).eps
        del class_likelihood
        new_log_likelihood = np.sum(histogram * np.log(sum_likelihood))
        del sum_likelihood
        if((new_log_likelihood - log_likelihood) < 0.000001):
            break
        iteration = iteration + 1
    del log_likelihood, new_log_likelihood
    class_means = class_means + minimum - 1
    s = image_copy.shape
    posterior = np.zeros((s[0], s[1], number_of_classes))
    posterior_lookup = dict()
    for i in range(0, s[0]):
        for j in range(0, s[1]):
            pixel_val = image_copy2[i,j] 
            if pixel_val in posterior_lookup:
                for n in range(0, number_of_classes): 
                    posterior[i,j,n] = posterior_lookup[pixel_val][n]
            else:
                posterior_lookup.update({pixel_val: [0]*number_of_classes})
                for n in range(0, number_of_classes): 
                    x = make_distribution(
                        class_means[n], class_variances[n], 
                        class_proportions[n],
                        image_copy[i,j]
                    )
                    posterior[i,j,n] = x * class_proportions[n]
                    posterior_lookup[pixel_val][n] = posterior[i,j,n]
    return posterior, class_means, class_variances, class_proportions

def make_histogram(image):
    image = image.flatten()
    indices = np.nonzero(np.isnan(image))
    image[indices] = 0
    indices = np.nonzero(np.isinf(image))
    image[indices] = 0
    del indices
    size = image.size
    maximum = int(np.ceil(np.amax(image)) + 1)
    #maximum = (np.ceil(np.amax(image)) + 1)
    histogram = np.zeros((1, maximum))
    for i in range(0,size):
        #floor_value = int(np.floor(image[i]))
        floor_value = np.floor(image[i]).astype(np.uint8)
        #floor_value = (np.floor(image[i]))
        if floor_value > 0 and floor_value < maximum - 1:
            temp1 = image[i] - floor_value
            temp2 = 1 - temp1
            histogram[0,floor_value] = histogram[0,floor_value] + temp1
            histogram[0,floor_value - 1] = histogram[0,floor_value - 1] + temp2
    histogram = np.convolve(histogram[0], [1,2,3,2,1])
    histogram = histogram[2:(histogram.size - 3)]
    histogram = histogram / np.sum(histogram)
    return histogram

def make_distribution(m, v, g, x):
    x = x.flatten()
    m = m.flatten()
    v = v.flatten()
    g = g.flatten()
    y = np.zeros((len(x), m.shape[0]))
    for i in range(0,m.shape[0]):
        d = x - m[i]
        amp = g[i] / np.sqrt(2*np.pi*v[i])
        y[:,i] = amp * np.exp(-0.5 * (d * d) / v[i])
    return y

def get_proj4(filename):
    f=rasterio.open(filename)
    return pyproj.Proj(f.crs, preserve_units=True)  #used in pysheds
    
def gdal_read(filename, ndtype=np.float64):
    '''
    z=readData('/path/to/file')
    '''
    ds = gdal.Open(filename) 
    return np.array(ds.GetRasterBand(1).ReadAsArray()).astype(ndtype);

def gdal_get_geotransform(filename):
    '''
    [top left x, w-e pixel resolution, rotation, top left y, rotation, 
    n-s pixel resolution]=gdal_get_geotransform('/path/to/file')
    '''
    #http://stackoverflow.com/questions/2922532/obtain-latitude-and-longitude-
    #   from-a-geotiff-file
    ds = gdal.Open(filename)
    return ds.GetGeoTransform()

## Function to calculate the number of rows and columns of tiles needed to tile 
# an image to a given size
def get_tile_row_col_count(
    height: int, width: int, tile_size: int) -> Tuple[int, int]:
    return int(np.ceil(height / tile_size)), int(np.ceil(width / tile_size))

## Function to extract the tiff dates from a wildcard path:
def get_dates(paths):
    dates = []
    pths = glob.glob(paths)
    for p in pths:
        date = p.split('/')[-1].split("_")[0]
        dates.append(date)
    dates.sort()
    return dates

## Function to save a mask
def write_mask_to_file(mask: np.ndarray, 
                       file_name: str, 
                       projection: str, 
                       geo_transform: str) -> None:
    (width, height) = mask.shape
    out_image = gdal.GetDriverByName('GTiff').Create(
        file_name, height, width, bands=1
    )
    out_image.SetProjection(projection)
    out_image.SetGeoTransform(geo_transform)
    out_image.GetRasterBand(1).WriteArray(mask)
    out_image.GetRasterBand(1).SetNoDataValue(0)
    out_image.FlushCache()

## Function to load SAR dataset
# def get_tiff_paths(paths: str) -> list:
#     tiff_paths = !ls $paths | sort -t_ -k5,5
#     return tiff_paths
def get_tiff_paths(paths: str) -> list:
    # Construct the shell command to list and sort files
    command = f"ls {paths} | sort -t_ -k5,5"
    # Execute the command and capture the output
    result = subprocess.run(command, shell=True, text=True, 
                            capture_output=True, check=True)
    # Split the output into lines to get a list of paths
    tiff_paths = result.stdout.strip().split('\n')
    return tiff_paths

## Function to create a dictionary containing lists of each vv/vh pair
def group_polarizations(tiff_paths: list) -> dict:
    pths = {}
    for tiff in tiff_paths:
        product_name = tiff.split('.')[0][:-2]
        if product_name in pths:
            pths[product_name].append(tiff)
        else:
            pths.update({product_name: [tiff]})
            pths[product_name].sort()
    return pths

## Function to confirm the presence of both VV and VH images in all image sets
def confirm_dual_polarizations(paths: dict) -> bool:
    for p in paths:
        if len(paths[p]) == 2:
            if ('vv' not in paths[p][1] and 'VV' not in paths[p][1]) or \
            ('vh' not in paths[p][0] and 'VH' not in paths[p][0]):
                return False
    return True   