import geemap
import ee
from datetime import datetime


###########GMW#############

def gmw_hectares(aoi, year):
    '''
    Inputs: aoi (image, imageCollection, featureCollection). Most importantly, NOT a shpfile. That translation must be done outside of this function.
            year - the year you are looking for, as an integer.
    Output: The area of the aoi covered by mangroves in the given year.

    '''
    year_string = str(year)
    extent_raster = ee.ImageCollection(
        "projects/earthengine-legacy/assets/projects/sat-io/open-datasets/GMW/extent/GMW_V3")

    # Filter by year, clip to AOI:
    extent_year_clipped = extent_raster.filterDate(year_string + '-01-01', year_string + '-12-31').first().clip(aoi)

    # Create mask
    mangrove_year = extent_year_clipped.eq(1)

    # Calculate pixel area in hectares
    pixel_area_ha = ee.Image.pixelArea().divide(10000)

    area_img_year = pixel_area_ha.updateMask(mangrove_year)

    # Get total area!
    area = area_img_year.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=30,
        maxPixels=1e12
    )

    # Return
    return area.getInfo().get('area')

def gmw_percent(aoi, year):
    Hectares = gmw_hectares(aoi, year)
    return (Hectares / (aoi.geometry().area(1).getInfo()/10000))*100

def export_gmw_tif(aoi, year, folder):
    year_string = str(year)
    extent_raster = ee.ImageCollection(
        "projects/earthengine-legacy/assets/projects/sat-io/open-datasets/GMW/extent/GMW_V3")

    # Filter by year, clip to AOI:
    extent_year_clipped = extent_raster.filterDate(year_string + '-01-01', year_string + '-12-31').first().clip(aoi)

    # Create mask
    mangrove_year = extent_year_clipped.eq(1)

    geemap.ee_export_image(
        mangrove_year.updateMask(mangrove_year),  # only mangrove pixels
        filename=folder + '/gmw.tif',  # output file in outputs folder
        scale=30,  # 30m resolution
        region=aoi.geometry(),
        file_per_band=False
    )

#############JAXA#############

def jaxa_hectares_fnf3(aoi, year):
    year_str = str(year)

    # Load JAXA FNF dataset
    jaxa = (
        ee.ImageCollection('JAXA/ALOS/PALSAR/YEARLY/FNF')
        .filterDate(year_str + '-01-01', year_str + '-12-31')
        .filterBounds(aoi)
        .select('fnf')
    )

    # Get yearly image and clip
    fnf = jaxa.first().clip(aoi)

    # Forest mask (1 = forest)
    forest = fnf.eq(1)

    # Pixel area in hectares
    pixel_area_ha = ee.Image.pixelArea().divide(10000)

    # Mask to forest pixels only
    forest_area_img = pixel_area_ha.updateMask(forest)

    # Sum area
    area = forest_area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=25,        # JAXA PALSAR resolution (~25 m)
        maxPixels=1e12
    )

    # Return value as Python float
    return area.getInfo().get('area')

def jaxa_hectares_fnf4(aoi, year):
    '''

    Returns DICTIONARY with keys 'Dense', "Non-dense" and "Total"
    '''
    year_string = str(year)

    # Load JAXA FNF4 dataset, since year >=2017
    dataset_jaxa = (
        ee.ImageCollection('JAXA/ALOS/PALSAR/YEARLY/FNF4')
        .filterDate(year_string + '-01-01', year_string + '-12-31')
        .filterBounds(aoi)
        .select('fnf')
    )

    fnf = dataset_jaxa.first().clip(aoi)

    # Pixel area in hectares
    pixel_area_ha = ee.Image.pixelArea().divide(10000)

    # Calculate Dense forest (band 1)
    dense_mask = fnf.eq(1)
    dense_area = pixel_area_ha.updateMask(dense_mask).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=25,
        maxPixels=1e12
    ).get('area').getInfo()

    # Calculate Non-dense forest (band 2)
    nondense_mask = fnf.eq(2)
    nondense_area = pixel_area_ha.updateMask(nondense_mask).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=25,
        maxPixels=1e12
    ).get('area').getInfo()

    total_ha = dense_area + nondense_area

    return {
        "Dense": dense_area,
        "Non-dense": nondense_area,
        "Total": total_ha
    }

#Wrapper function for above fnf3 and fnf4
def jaxa_hectares(aoi, year):
    if year >= 2017:
        return jaxa_hectares_fnf4(aoi,year)
    else:
        return jaxa_hectares_fnf3(aoi,year)

def jaxa_percent(aoi, year):
    retVal = jaxa_hectares(aoi, year)
    # This can either turn an integer or a dictionary - check the type!
    #TODO - aoi.geometry() is going to be SLIGHTLY too large. for 100% accuracy, use pixel size mask.
    if type(retVal) is dict:
        return {
            "Dense": round((retVal['Dense'] / (aoi.geometry().area(1).getInfo() / 10000)) * 100, 2),
            "Non-dense": round((retVal['Non-dense'] / (aoi.geometry().area(1).getInfo() / 10000)) * 100, 2),
            "Total": round((retVal['Total'] / (aoi.geometry().area(1).getInfo() / 10000)) * 100, 2)
        }

    else:
        return round((retVal / (aoi.geometry().area(1).getInfo() / 10000)) * 100, 2)

def export_jaxa_tif_fnf3(aoi, year, folder):
    year_string = str(year)

    # Load JAXA FNF3 dataset
    dataset_jaxa = (
        ee.ImageCollection('JAXA/ALOS/PALSAR/YEARLY/FNF')
        .filterDate(f'{year_string}-01-01', f'{year_string}-12-31')
        .filterBounds(aoi)
        .select('fnf')  # single band FNF3
    )

    # Clip the image to AOI
    fnf_img = dataset_jaxa.first().clip(aoi)

    # Optional: mask to only forest pixels (1 and 2)
    forest_mask = fnf_img.eq(1)

    # Export using geemap
    geemap.ee_export_image(
        fnf_img.updateMask(forest_mask),  # mask non-forest pixels
        filename=folder + '/jaxa_fnf3.tif',  # export path
        scale=25,  # JAXA resolution ~25m
        region=aoi.geometry(),
        file_per_band=False
    )

def export_jaxa_tif_fnf4(aoi, year, folder):
    year_string = str(year)

    #
    dataset_jaxa = (
        ee.ImageCollection('JAXA/ALOS/PALSAR/YEARLY/FNF4')
        .filterDate(f'{year_string}-01-01', f'{year_string}-12-31')
        .filterBounds(aoi)
        .select('fnf')  # single band FNF3
    )

    fnf_img = dataset_jaxa.first().clip(aoi)

    # SOMETHING IS MISSING HERE!
    geemap.ee_export_image(
        fnf_img,  # only mangrove pixels
        filename=folder + '/jaxa_fnf4.tif',  # output file in outputs folder
        scale=25,  # 30m resolution
        region=aoi.geometry(),
        file_per_band=True
    )

#Wrapper function for fnf3 and fnf4 exports
def export_jaxa_tif(aoi, year, folder):
    if year >= 2017:
        export_jaxa_tif_fnf4(aoi,year, folder)
    else:
        export_jaxa_tif_fnf3(aoi,year, folder)

#####################MURRAY#####################

def murray_hectares_year_range(aoi, year_start, year_end):
    # Load dataset
    murray_dataset = ee.Image('JCU/Murray/GIC/global_tidal_wetland_change/2019').clip(aoi)  # Don't clip

    # Select relevant bands
    lossBand = murray_dataset.select('loss');
    lossYear = murray_dataset.select('lossYear');

    # Define mask for range of years we desire
    # Note - 2000 subtracted since the key in Murray counts only the last 2 digits of year - for example,
    year_start_murray = year_start - 2000
    year_end_murray = year_end - 2000
    time_loss_mask = lossYear.gte(year_start_murray).And(lossYear.lte(year_end_murray));

    periodLoss = lossBand.eq(1)
    periodLoss = periodLoss.updateMask(time_loss_mask);

    # simplify for easy calculation

    # Calculation pixel area in hectares
    pixel_area_ha = ee.Image.pixelArea().divide(10000)

    area_img_year = pixel_area_ha.updateMask(periodLoss)

    # Get total area - reduce over geometry

    area = area_img_year.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10,  #
        maxPixels=1e13,
    )

    return ee.Number(area.get('area')).getInfo()

def murray_hectares(aoi, year):
    '''
    Input start year and aoi, and function returns 2 pieces of info in a dictionary
    OUTPUT: a dictionary containing 2 pieces of info: loss overall, and loss over last 10 years.
    '''
    total = murray_hectares_year_range(aoi,1999,2019)
    ten_year = murray_hectares_year_range(aoi,year-9,year)
    return {
        'ten_year_loss' : ten_year,
        'total' : total
    }

def murray_percent(aoi, year):
    Hectares = murray_hectares(aoi, year)
    return {
        'ten_year_loss_percent' : (Hectares['ten_year_loss'] / (aoi.geometry().area(1).getInfo()/10000))*100,
        'total_loss_percent' : (Hectares['total'] / (aoi.geometry().area(1).getInfo()/10000))*100
    }

