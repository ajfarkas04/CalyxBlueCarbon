import geemap
import ee
from datetime import datetime


def GMWhectares(aoi, year):
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