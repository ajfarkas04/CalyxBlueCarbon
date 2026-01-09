import geemap
import ee

def protected_planet_hectares(aoi):
    pp_dataset = ee.FeatureCollection("WCMC/WDPA/current/polygons")

    intersection = (
        pp_dataset
        .filterBounds(aoi)
        .geometry()
        .intersection(aoi.geometry(), ee.ErrorMargin(1))
    )

    area_ha = intersection.area().divide(10000)

    return area_ha.getInfo()

def protected_planet_percent(aoi):
    pp_hectares = protected_planet_hectares(aoi)
    return (pp_hectares / (aoi.geometry().area(1).getInfo()/10000))*100