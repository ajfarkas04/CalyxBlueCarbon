import geemap
import ee
import csv
import PP, Baseline, SLR
import os

# Main tools!
def convert_to_ee(filepath):
    """
    Loads a vector file into earth engine as a feature collection/image.
    Supports .shp and .kml. .kml files are untested.
    """

    filepath = filepath.lower()

    if filepath.endswith('.shp'):
        return geemap.shp_to_ee(filepath)
    elif filepath.endswith('.kml'):
        return geemap.kml_to_ee(filepath)
    else:
        raise ValueError("Unsupported file type - must be .shp or .kml")


def get_csv(filepath, start_year, sedimentation, folder):
    #Make folder if doesn't exist yet
    if not os.path.exists(folder):
        os.makedirs(folder)
    # Parse input data
    aoi = convert_to_ee(filepath)
    eval_year = start_year - 1
    year_string = str(eval_year)

    # Call functions for csv data
    area = round(aoi.geometry().area(1).getInfo() / 10000)

    murray_hectares_dict = Baseline.murray_hectares(aoi, eval_year)
    murray_percent_dict = Baseline.murray_percent(aoi, eval_year)

    gmw_hectares = Baseline.gmw_hectares(aoi, eval_year)
    gmw_percent = Baseline.gmw_percent(aoi, eval_year)

    jaxa_hectares = Baseline.jaxa_hectares(aoi, eval_year)
    jaxa_percentages = Baseline.jaxa_percent(aoi, eval_year)

    slr_dict = SLR.get_slr_dictionary(aoi, eval_year)

    elevation_dict = SLR.get_elevation_data(aoi)

    # Get SLR value from 100 years in future
    ssp370_last_year_SLR = slr_dict["SSP3-7.0"][(((start_year // 10) + 1) * 10) + 100]
    ssp585_last_year_SLR = slr_dict["SSP5-8.5"][(((start_year // 10) + 1) * 10) + 100]

    # No data parsing needed for sedimentation: 1 cm/year = 1 meter/100 years! It took me way too long to realize that.
    inundation_height_ssp370 = SLR.calculate_inundation_height(sedimentation, ssp370_last_year_SLR)
    area_inundated_hectares_ssp370 = SLR.area_inundated_hectares(aoi, inundation_height_ssp370)
    area_inundated_percent_ssp370 = SLR.area_inundated_percent(aoi, inundation_height_ssp370)

    inundation_height_ssp585 = SLR.calculate_inundation_height(sedimentation, ssp585_last_year_SLR)
    area_inundated_hectares_ssp585 = SLR.area_inundated_hectares(aoi, inundation_height_ssp585)
    area_inundated_percent_ssp585 = SLR.area_inundated_percent(aoi, inundation_height_ssp585)

    # Finally, protected planet data.
    protected_planet_hectares = PP.protected_planet_hectares(aoi)
    protected_planet_percent = PP.protected_planet_percent(aoi)

    # CREATE ROWS FROM DATA COLLECTED ABOVE - MOSTLY VISUALS AND AESTHETICS OF SHEET BELOW.

    # BASELINE ROWS - complicated to make it look pretty - don't worry about below unless you want to change the CSV format.
    # includes Murray and GMW
    baseline_rows = [
        ["Baseline Spatial Analysis"],
        ['Project Area:', area, 'ha'],
        ['Murray tree cover loss (' + str(start_year - 10) + '-' + year_string + ')',
         round(murray_hectares_dict['ten_year_loss'], 2),
         'ha', str(murray_percent_dict['ten_year_loss_percent']) + "%", "Note that data cuts off at 2019."],
        ['Murray tree cover loss (1999-2019)', round(murray_hectares_dict['total'], 2),
         'ha', str(murray_percent_dict['total_loss_percent']) + "%"],
        ['Area covered by forest ' + year_string + " GMW", round(gmw_hectares, 2), 'ha', str(gmw_percent) + "%"],
    ]

    # initalize jaxa_rows
    jaxa_rows = None

    # Make jaxa rows - some parsing must be done
    if type(jaxa_hectares) is dict:
        jaxa_rows = [
            ['Area covered by dense forest ' + year_string + ' JAXA', round(jaxa_hectares["Dense"], 2), "ha",
             str(jaxa_percentages["Dense"]) + "%"],
            ['Area covered by sparse forest ' + year_string + ' JAXA', round(jaxa_hectares["Non-dense"], 2), "ha",
             str(jaxa_percentages["Non-dense"]) + "%"],
            ['Area covered by forest total ' + year_string + ' JAXA', round(jaxa_hectares["Total"], 2), "ha",
             str(jaxa_percentages["Total"]) + "%"],
        ]
    else:
        jaxa_rows = [
            ['Area covered by dense forest ' + year_string + ' JAXA', "N/A"],
            ['Area covered by sparse forest ' + year_string + ' JAXA', "N/A"],
            ['Area covered by forest total ' + year_string + ' JAXA', round(jaxa_hectares["Total"], 2), "ha",
             str(jaxa_percentages["Total"]) + "%"],
        ]

    # Make SLR rows

    years = slr_dict["SSP3-7.0"].keys()
    slr_rows = [['SLR DATA', 'IPCC Sea Level Rise SSP3-7.0 (m)', 'IPCC SLR SSP5-8.5 (m)']]
    for year in years:
        row = [year, slr_dict["SSP3-7.0"][year], slr_dict["SSP5-8.5"][year]]
        slr_rows.append(row)

    # Make Elevation rows
    elevation_rows = [
        ["Elevation of area"],
        ["Mean", round(elevation_dict["mean"], 2), "m"],
        ["Min", round(elevation_dict["min"], 2), "m"],
        ["Max", round(elevation_dict["max"], 2), "m"]

    ]

    # Make inundation rows
    submergence_rows = [
        ["Project Area lost to SLR after 100 years calculation"],
        ["IPCC Sea Level Rise SSP3-7.0 in Area"],
        [round(area_inundated_hectares_ssp370, 2), "ha under", inundation_height_ssp370, "m"],
        [round(area_inundated_percent_ssp370, 2), "% inundated"],
        ["IPCC Sea Level Rise SSP5-8.5 in Area"],
        [round(area_inundated_hectares_ssp585, 2), "ha under", inundation_height_ssp585, "m"],
        [round(area_inundated_percent_ssp585, 2), "% inundated"]
    ]

    # Make Protected Planet Rows
    pp_rows = [
        ["Protected Planet Statistics"],
        [round(protected_planet_hectares, 2), "ha"],
        [round(protected_planet_percent, 2), "ha"]
    ]

    with open(folder + '/output.csv', mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([])
        writer.writerows(baseline_rows)
        writer.writerows(jaxa_rows)
        writer.writerow([])
        writer.writerows(slr_rows)
        writer.writerow([])
        writer.writerows(elevation_rows)
        writer.writerow([])
        writer.writerows(submergence_rows)
        writer.writerow([])
        writer.writerows(pp_rows)

def get_area(aoi):
    """
    Gets total area of aoi in hectares using GEOMETRY ONLY calculation
    """
    return aoi.geometry().area(1).getInfo() / 10000