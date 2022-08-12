'''
A module to mosaic Sentinel-1 geobursts from RTC workflow
'''


import os

import numpy as np
from osgeo import gdal


def check_mosaic_eligibility(list_rtc,list_nlooks):
    '''
    Check if the list of the geobursts are eligible to be mosaiced

    Parameters:
    -----------
        list_rtc: list
            path to the RTC geoburst
        list_nlooks: list
            path to the nlooks raster that corresponds to list_rtc

    '''

    # Accepted error in the coordinates.
    maxerr_coord=1.0e-6

    # Check the number of the raster files in list_rtc and list_nlooks
    num_rtc=len(list_rtc)
    num_nlooks=len(list_nlooks)
    if num_rtc != num_nlooks:
        raise ValueError(f'# RTC ({num_rtc}) and # nlooks ({num_nlooks}) does not match.')

    # Check for geotransform, dimension, #bands, and projection
    str_proj_prev = None
    spacing_x_prev = None
    spacing_y_prev = None
    numbands_prev = None
    mod_x_prev = None
    mod_y_prev = None

    flag_rtn=True
    for i, path_rtc in enumerate(list_rtc):
        path_nlooks=list_nlooks[i]

        raster_rtc=gdal.Open(path_rtc,0)
        raster_nlooks=gdal.Open(path_rtc,0)

        geo_transformation_rtc=raster_rtc.GetGeoTransform()
        geo_transformation_nlooks=raster_nlooks.GetGeoTransform()

        # Geotransform - between RTC and corresponding nlooks
        if geo_transformation_rtc != geo_transformation_nlooks:
            print('GeoTransform does not match between '+\
                  f'{os.path.basename(path_rtc)} and {os.path.basename(path_nlooks)}')
            flag_rtn=False

        # dimension - between RTC and corresponding nlooks
        if (raster_rtc.RasterXSize != raster_nlooks.RasterXSize) or (raster_rtc.RasterYSize != raster_nlooks.RasterYSize):
            print('Dimension does not agree between '+\
                   f'{os.path.basename(path_rtc)} and {os.path.basename(path_nlooks)}')
            flag_rtn=False

        # number of bands - for all RTC
        if numbands_prev is None:
            numbands_prev = raster_rtc.RasterCount
        else:
            if numbands_prev != raster_rtc.RasterCount:
                print(f'Band number anomaly detected from {os.path.basename(path_rtc)}')
                flag_rtn=False
            #else:
            #    numbands_prev = raster_rtc.RasterCount


        # projection - for every RTC and nlooks
        if str_proj_prev is None:
            str_proj_prev = raster_rtc.GetProjection()
        else:
            if numbands_prev != raster_rtc.RasterCount:
                print(f'Map projection anomaly detected: {os.path.basename(path_rtc)}')
                flag_rtn=False

            if numbands_prev != raster_nlooks.RasterCount:
                print(f'Map projection anomaly detected: {os.path.basename(path_nlooks)}')
                flag_rtn=False


        #spacing x - for all RTC and nlooks
        if spacing_x_prev is None:
            spacing_x_prev = geo_transformation_rtc[1]
        else:
            if spacing_x_prev != geo_transformation_rtc[1]:
                print(f'spacing_x anomaly detected: {os.path.basename(path_rtc)}')
                flag_rtn=False

            if spacing_x_prev != geo_transformation_nlooks[1]:
                print(f'spacing_y anomaly detected: {os.path.basename(path_nlooks)}')
                flag_rtn=False

        #spacing y - for all RTC and nlooks
        if spacing_y_prev is None:
            spacing_y_prev = geo_transformation_rtc[5]
        else:
            if spacing_y_prev != geo_transformation_rtc[5]:
                print(f'spacing_y anomaly detected: {os.path.basename(path_rtc)}')
                flag_rtn=False

            if spacing_y_prev != geo_transformation_nlooks[5]:
                print(f'spacing_y anomaly detected: {os.path.basename(path_nlooks)}')
                flag_rtn=False

        #snapping_x - by calculating the mod of the corner coords - for all RTC and nlooks
        if mod_x_prev is None:
            mod_x_prev = geo_transformation_rtc[0] % geo_transformation_rtc[1]
        else:
            if abs(mod_x_prev - geo_transformation_rtc[0]%geo_transformation_rtc[1]) > maxerr_coord:
                print(f'snapping_x anomaly detected: {os.path.basename(path_rtc)}')
                flag_rtn=False

            if abs(mod_x_prev - geo_transformation_nlooks[0]%geo_transformation_nlooks[1]) > maxerr_coord:
                print(f'snapping_x anomaly detected: {os.path.basename(path_nlooks)}')
                flag_rtn=False

        #snapping_y - by calculating the mod of the corner coords - for all RTC and nlooks
        if mod_y_prev is None:
            mod_y_prev = geo_transformation_rtc[3] % geo_transformation_rtc[5]
        else:
            if abs(mod_y_prev - geo_transformation_rtc[3]%geo_transformation_rtc[5]) > maxerr_coord:
                print(f'snapping_y anomaly detected: {os.path.basename(path_rtc)}')
                flag_rtn=False

            if abs(mod_y_prev - geo_transformation_nlooks[3]%geo_transformation_nlooks[5]) > maxerr_coord:
                print(f'snapping_y anomaly detected: {os.path.basename(path_nlooks)}')
                flag_rtn=False


        raster_rtc=None
        raster_nlooks=None

    print('Passed the mosaic eligiblity test.')
    return flag_rtn




def weighted_mosaic(list_rtc, list_nlooks, geo_filename, geogrid_in=None):
    '''
    Mosaic the snapped S1 geobursts
    paremeters:
    -----------
        list_rtc: list
            list of the path to the rtc geobursts
        list_nlooks: list
            list of the nlooks raster that corresponds to list_rtc
        geogrid_in: isce3.product.GeoGridParameters, default: None <-- TODO check again the data type
            geogrid information to determine the output mosaic's shape and projection

    '''

    num_raster = len(list_rtc)
    num_bands = None
    posting_x = None
    posting_y = None

    list_geo_transform = np.zeros((num_raster, 6))
    list_dimension = np.zeros((num_raster, 2), dtype=np.int32)

    for i, path_rtc in enumerate(list_rtc):
        print(f'Processing: {i+1} of {num_raster}')
        raster_in = gdal.Open(path_rtc, 0)
        list_geo_transform[i, :] = raster_in.GetGeoTransform()
        list_dimension[i, :] = (raster_in.RasterYSize, raster_in.RasterXSize)

        # Check if the number of bands are consistent over the input RTC rasters
        if num_bands is None:
            num_bands = raster_in.RasterCount
            continue
        elif num_bands != raster_in.RasterCount:
            raise ValueError(f'Anomaly detected on # of bands from RTC file: {os.path.basename(path_rtc)}')

        raster_in = None


    if geogrid_in is None:
        # determine GeoTransformation, posting, dimension, and projection from the input raster
        for i in range(num_raster):
            if list_geo_transform[:, 1].max() == list_geo_transform[:, 1].min():
                posting_x = list_geo_transform[0,1]

            if list_geo_transform[:, 5].max() == list_geo_transform[:, 5].min():
                posting_y = list_geo_transform[0,5]

        # determine the dimension and the upper left corner of the output mosaic
        xmin_mosaic = list_geo_transform[:, 0].min()
        ymax_mosaic = list_geo_transform[:, 3].max()
        xmax_mosaic = (list_geo_transform[:, 0] + list_geo_transform[:, 1]*list_dimension[:, 1]).max()
        ymin_mosaic = (list_geo_transform[:, 3] + list_geo_transform[:, 5]*list_dimension[:, 0]).min()

        dim_mosaic = (int(np.ceil((ymin_mosaic - ymax_mosaic) / posting_y)),
                      int(np.ceil((xmax_mosaic - xmin_mosaic) / posting_x)))

        with gdal.Open(list_rtc[0],0) as raster_in:
            wkt_projection=raster_in.GetProjectionRef()
            epsg_mosaic=None

    else:
        # Directly bring the geogrid information from the input parameter
        xmin_mosaic = geogrid_in.start_x
        ymax_mosaic = geogrid_in.start_y
        posting_x = geogrid_in.spacing_x
        posting_y = geogrid_in.spacing_y

        dim_mosaic = (geogrid_in.length, geogrid_in.width)

        xmax_mosaic = xmin_mosaic + posting_x*dim_mosaic[1]
        ymin_mosaic = ymax_mosaic + posting_y*dim_mosaic[0]
        dim_mosaic = (geogrid_in.length, geogrid_in.width)

        epsg_mosaic=geogrid_in.epsg
        wkt_projection = None

    print('mosaic dimension: ',dim_mosaic)

    if num_bands == 1:
        arr_numerator = np.zeros(dim_mosaic)

    else:
        arr_numerator = np.zeros((num_bands,dim_mosaic[0], dim_mosaic[1]))

    arr_denominator = np.zeros(dim_mosaic)

    for i, path_rtc in enumerate(list_rtc):
        path_nlooks = list_nlooks[i]
        print(f'Mosaicking: {i+1} of {num_raster}: {os.path.basename(path_rtc)}', end=' ')

        # calculate the burst RTC's offset wrt. the output mosaic in the image coordinate
        offset_imgx = int((list_geo_transform[i,0] - xmin_mosaic) / posting_x + 0.5)
        offset_imgy = int((list_geo_transform[i,3] - ymax_mosaic) / posting_y + 0.5)

        print(f'img. offset [x,y]=[{offset_imgx}, {offset_imgy}]')
        raster_rtc = gdal.Open(path_rtc,0)
        arr_rtc = raster_rtc.ReadAsArray()
        # Replace NaN values with 0
        arr_rtc[np.isnan(arr_rtc)] = 0.0

        raster_nlooks = gdal.Open(path_nlooks, 0)
        arr_nlooks = raster_nlooks.ReadAsArray()
        arr_nlooks[np.isnan(arr_nlooks)] = 0.0

        if num_bands == 1:
            arr_numerator[offset_imgy:offset_imgy+list_dimension[i, 0],
                          offset_imgx:offset_imgx+list_dimension[i, 1]] += arr_rtc * arr_nlooks
        else:
            for i_band in range(num_bands):
                arr_numerator[i_band,
                              offset_imgy:offset_imgy+list_dimension[i, 0],
                              offset_imgx:offset_imgx+list_dimension[i, 1]] += arr_rtc[i_band, :, :] * arr_nlooks

        arr_denominator[offset_imgy:offset_imgy + list_dimension[i, 0],
                        offset_imgx:offset_imgx + list_dimension[i, 1]] += arr_nlooks

        raster_rtc = None
        raster_nlooks = None

    if num_bands == 1:
        arr_out = arr_numerator/arr_denominator
    else:
        arr_out = np.zeros(arr_numerator.shape)
        for i_band in range(num_bands):
            arr_out[i_band, :, :]=arr_numerator[i_band, :, :] / arr_denominator


    # write out the array
    drv_out = gdal.GetDriverByName('Gtiff')
    raster_out = drv_out.Create(geo_filename,
                                dim_mosaic[1], dim_mosaic[0], num_bands,
                                gdal.GDT_Float32)

    raster_out.SetGeoTransform((xmin_mosaic, posting_x, 0, ymax_mosaic, 0, posting_y))

    raster_srs_src = gdal.Open(list_rtc[0], 0)
    raster_out.SetProjection(raster_srs_src.GetProjection())
    raster_srs_src = None

    if num_bands == 1:
        raster_out.GetRasterBand(1).WriteArray(arr_out)

    else:
        for i_band in range(num_bands):
            raster_out.GetRasterBand(i_band+1).WriteArray(arr_out[i_band])

'''
# test code below. remove before commit!!!
if __name__=='__main__':
    PATH_HOME=os.getenv('HOME')
    PATH_RTC_BURST=PATH_HOME+'/opera-adt/scratch/COMPASS_RTC_Indonesia_WIP_v15/scratch_dir_all_bursts_with_correction_all_frame'
    list_rtc_vh=glob.glob(f'{PATH_RTC_BURST}/t??_??????_iw?_????????.tif')
    list_nlooks_vh=[rtc.replace('.tif','_VH_nlooks_temp_1660198055.814647.tif') for rtc in list_rtc_vh]

    weighted_mosaic(list_rtc_vh,list_nlooks_vh)
'''