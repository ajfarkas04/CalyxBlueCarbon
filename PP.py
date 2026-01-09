import geemap
import ee

def ProtectedPlanetHectares(aoi):
    PP_dataset = ee.FeatureCollection("WCMC/WDPA/current/polygons")

    intersection = (
        PP_dataset
        .filterBounds(aoi)
        .geometry()
        .intersection(aoi.geometry(), ee.ErrorMargin(1))
    )

    area_ha = intersection.area().divide(10000)

    return area_ha.getInfo()

def ProtectedPlanetPercent(aoi):
    PPHectares = ProtectedPlanetHectares(aoi)
    return (PPHectares / (aoi.geometry().area(1).getInfo()/10000))*100