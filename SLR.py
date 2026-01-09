import geemap
import ee

##############NASA SLR##################
def get_nasa_slr(aoi, year, scenario):
    '''

    Returns SLR at cite in METERS
    '''

    # Default dataset initialization - will throw error if it stays this way due to invalid inputs.
    dataset = None

    # Get year as a string
    year_string = str(year)

    # get dataset
    if scenario.lower() == "ssp5-8.5":
        dataset = ee.Image('IPCC/AR6/SLP/ssp585_' + year_string).select('total_values_quantile_0_5')
    elif scenario.lower() == "ssp3-7.0":
        dataset = ee.Image('IPCC/AR6/SLP/ssp370_' + year_string).select('total_values_quantile_0_5')
    else:
        raise ValueError("Inputs must either be SSP5-8.5 or SSP3-7.0")

    # Reduce region to nearest pixel and extracts value from said pixel
    value_mm = dataset.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=aoi,
        scale=25000,
        maxPixels=1e13
    ).getInfo()['total_values_quantile_0_5']

    # Return METERS value
    return value_mm / 1000

def get_slr_dictionary(aoi, start_year):
    '''
    according to AOI and project start year, returns SLR data in a dictionary with 2 keys: SSP3-7.0 and SSP5-8.5.
    The values of these keys are also dictionaries, with keys referring to the year and values referring to the SLR at that time and scenario
    return this dictionary of dictionaries.

    '''

    first_year = ((start_year // 10) + 1) * 10  # First decade after start year
    last_year = first_year + 100  # century later
    decade_years = list(range(first_year, last_year + 1, 10))

    slr_dict = {}

    for scenario in ["SSP3-7.0", "SSP5-8.5"]:
        scenario_dict = {}
        for year in decade_years:
            slr_value = get_nasa_slr(aoi, year, scenario)
            scenario_dict[year] = slr_value
        slr_dict[scenario] = scenario_dict

    return (slr_dict)

#############COPERNICUS#############

def get_elevation_map(aoi):
    '''
    Takes in AOI, returns DEM masked to aoi.
    '''
    copernicus_dataset = ee.ImageCollection("COPERNICUS/DEM/GLO30")
    DEM = copernicus_dataset.select('DEM')
    DEM_local = DEM.median().toFloat().clip(aoi)

    # returns ee.Image of area of interest with DEM data inside.
    return DEM_local

def get_elevation_data(aoi):
    '''
    Takes in AOI as input, returns a dictionary with keys "mean", "min", and "max"
    '''

    # get DEM clipped to aoi
    dem = get_elevation_map(aoi)

    # Use reduce region with multiple reducers to calculate mean, min, and max.
    stats = dem.reduceRegion(
        reducer=ee.Reducer.mean()
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.max(), sharedInputs=True),
        geometry=aoi,
        scale=30,  # native resolution for GLO-30
        maxPixels=1e13
    )

    # GetInfo to bring values to Python
    stats_dict = stats.getInfo()

    # Return only mean, min, max
    return {
        'mean': stats_dict.get('DEM_mean'),
        'min': stats_dict.get('DEM_min'),
        'max': stats_dict.get('DEM_max')
    }

def export_dem_geotiff(aoi, folder_name):
    '''
    Exports a GeoTIFF of elevation
    File will be named submergence.tif
    '''

    dem_image = get_elevation_map(aoi)

    geemap.ee_export_image(
        dem_image,
        filename=folder_name + "/DEM.tif",
        # FOR USERS: change line below to scale = 50 if the DEM  geotiff fails to download.
        scale=50,
        region=aoi.geometry()
    )

##############SUBMERGED#############

def calculate_inundation_height(sedimentation, SLR):
    '''
    Input: SLR and Sedimentation, inputted as METERS PER HUNDRED YEARS.
    Output: Returns their difference, as inundation
    '''
    return (SLR - sedimentation)

def area_inundated_hectares(aoi, inundation_height_m):
    '''
    Returns area in hectares of area of interest where elevation < inundation height

    Inputs: aoi (ee.image.Image or imageCollection), inundation_height_m
    Output: percent of area inundated, as a float
    '''

    # get DEM
    dem_image = get_elevation_map(aoi)

    # Make a mask where 1 = inundated (dem.lte = less than or equal to)
    inundated = dem_image.lte(inundation_height_m)

    # Calculate pixel area in hectares
    pixel_area_ha = ee.Image.pixelArea().divide(10000)

    #
    area_img_year = pixel_area_ha.updateMask(inundated)

    # Area of inundated pixels:
    inundated_area = area_img_year.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=30,
        maxPixels=1e13
    )

    return inundated_area.getInfo().get('area')

def area_inundated_percent(aoi, inundation_height_m):
    '''
    takes in area of interest and inundation/submergence height and calculates percent of area below this height.
    '''
    hectares = area_inundated_hectares(aoi, inundation_height_m)

    pixel_area_ha = ee.Image.pixelArea().divide(10000)
    total_area = pixel_area_ha.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=30,
        maxPixels=1e13
    ).get('area')

    # return percentage
    return (hectares / total_area.getInfo()) * 100

def export_submergence_geotiff(aoi, inundation_height_m, folder_name):
    '''
    Exports a GeoTIFF of inundated areas to output folder.
    File will be named submergence.tif
    '''

    dem_image = get_elevation_map(aoi)

    # Mask DEM to inundated areas, where 1 = inundated
    inundated = dem_image.lte(inundation_height_m)
    inundated_dem = dem_image.updateMask(inundated)

    geemap.ee_export_image(
        inundated_dem,
        filename=folder_name + "/submergence.tif",
        # FOR USERS: change line below to scale = 50 if the submergence geotiff fails to download.
        scale=30,
        region=aoi.geometry()
    )