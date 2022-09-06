'''collection of useful functions used across workflows'''

import os

import isce3
import logging
from osgeo import gdal

import rtc

logger = logging.getLogger('rtc_s1')

WORKFLOW_SCRIPTS_DIR = os.path.dirname(rtc.__file__)

# get the basename given an input file path
# example: get_module_name(__file__)
get_module_name = lambda x : os.path.basename(x).split('.')[0]


def check_file_path(file_path: str) -> None:
    """Check if file_path exist else raise an error.

    Parameters
    ----------
    file_path : str
        Path to file to be checked
    """
    if not os.path.exists(file_path):
        err_str = f'{file_path} not found'
        logger.error(err_str)
        raise FileNotFoundError(err_str)


def check_directory(file_path: str) -> None:
    """Check if directory in file_path exists else raise an error.

    Parameters
    ----------
    file_path: str
       Path to directory to be checked
    """
    if not os.path.isdir(file_path):
        err_str = f'{file_path} not found'
        logger.error(err_str)
        raise FileNotFoundError(err_str)

def get_file_polarization_mode(file_path: str) -> str:
    '''Check polarization mode from file name

    Taking PP from SAFE file name with following format:
    MMM_BB_TTTR_LFPP_YYYYMMDDTHHMMSS_YYYYMMDDTHHMMSS_OOOOOO_DDDDDD_CCCC.SAFE

    Parameters
    ----------
    file_path : str
        SAFE file name to parse

    Returns
    -------
    original: dict
        Default dictionary updated with user-defined options

    References
    ----------
    https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/naming-conventions
    '''
    # index split tokens from rear to account for R in TTTR being possibly
    # replaced with '_'
    safe_pol_mode = os.path.basename(file_path).split('_')[-6][2:]

    return safe_pol_mode


def deep_update(original, update):
    """Update default runconfig dict with user-supplied dict.

    Parameters
    ----------
    original : dict
        Dict with default options to be updated
    update: dict
        Dict with user-defined options used to update original/default

    Returns
    -------
    original: dict
        Default dictionary updated with user-defined options

    References
    ----------
    https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    """
    for key, val in update.items():
        if isinstance(val, dict):
            original[key] = deep_update(original.get(key, {}), val)
        else:
            original[key] = val

    # return updated original
    return original


def check_write_dir(dst_path: str):
    """Check if given directory is writeable; else raise error.

    Parameters
    ----------
    dst_path : str
        File path to directory for which to check writing permission
    """
    if not dst_path:
        dst_path = '.'

    # check if scratch path exists
    dst_path_ok = os.path.isdir(dst_path)

    if not dst_path_ok:
        try:
            os.makedirs(dst_path, exist_ok=True)
        except OSError:
            err_str = f"Unable to create {dst_path}"
            logger.error(err_str)
            raise OSError(err_str)

    # check if path writeable
    write_ok = os.access(dst_path, os.W_OK)
    if not write_ok:
        err_str = f"{dst_path} scratch directory lacks write permission."
        logger.error(err_str)
        raise PermissionError(err_str)


def check_dem(dem_path: str):
    """Check if given path is a GDAL-compatible file; else raise error

    Parameters
    ----------
    dem_path : str
        File path to DEM for which to check GDAL-compatibility
    """
    try:
        gdal.Open(dem_path, gdal.GA_ReadOnly)
    except:
        err_str = f'{dem_path} cannot be opened by GDAL'
        logger.error(err_str)
        raise ValueError(err_str)

    epsg = isce3.io.Raster(dem_path).get_epsg()
    if not 1024 <= epsg <= 32767:
        err_str = f'DEM epsg of {epsg} out of bounds'
        logger.error(err_str)
        raise ValueError(err_str)
