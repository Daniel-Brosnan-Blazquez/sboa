"""
Helper module for the Copernicus ingestion management

Written by DEIMOS Space S.L. (dibb)

module siboa
"""
# Import logging
from eboa.logging import Log
import logging

logging_module = Log(name = __name__)
logger = logging_module.logger

###########
# Functions for helping with the ingestion of footprints
###########
def correct_antimeridian_issue_in_footprint(coordinates):
    """Function to generate a list of footprints (cut when affected by the antimeridian issue) from a given string of
    coordinates with the following format:
    'longitude,latitude longitude,latitude longitude,latitude'
    
    Note that the algorithm adds the coordinates to the first point to close the coordinates.
    
    Example of coordinates corrected from negative to positive longitude:
    Input = '-179.99592,-74.16433 162.86178,-64.68046 170.32559,-62.88090 -170.92199,-71.51724 -179.99592,-74.16433'
    Output = ['-179.99592 -74.16433 -180.0 -74.1620727655799 -180.0 -67.33640462603759 -170.92199 -71.51724 -179.99592 -74.16433 -179.99592 -74.16433', '180.0 -74.1620727655799 162.86178 -64.68046 170.32559 -62.8809 180.0 -67.33640462603759 180.0 -74.1620727655799']

    Example of coordinates corrected from positive to negative longitude:
    Input = '177.70168,70.09508 176.21806,71.69579 -176.68693,72.24555 -175.74527,70.61387 177.70168,70.09508'
    Output = ['177.70168 70.09508 176.21806 71.69579 180.0 71.988835300063 180.0 70.27703274456933 177.70168 70.09508 177.70168 70.09508', '-180.0 71.988835300063 -176.68693 72.24555 -175.74527 70.61387 -180.0 70.27703274456933 -180.0 71.988835300063']

    Example of coordinates not corrected
    Input = '46.85375,80.07100 31.46458,74.70960 17.52212,75.89819 25.94555,81.89870 46.85375,80.07100'
    Output = ['46.85375 80.071 31.46458 74.7096 17.52212 75.89819 25.94555 81.8987 46.85375 80.071 46.85375 80.071']

    :param coordinates: string of coordinates with the following format:
    'longitude,latitude longitude,latitude longitude,latitude'
    :type coordinates: str

    :return: list of footprints
    :rtype: list of str
    """

    longitude_latitudes = coordinates.split(" ")

    intersections_with_antimeridian=0
    init_longitudes_after_intersect_antimeridian=[]
    polygon = []
    polygons = [polygon]
    polygon_index = 0
    reverse = False
    for i, longitude_latitude  in enumerate(longitude_latitudes):
        if i == 0:
            j = len(longitude_latitudes) - 1
        else:
            j = i - 1
        # end if
        
        longitude, latitude = longitude_latitude.split(',')
        pre_longitude, pre_latitude = longitude_latitudes[j].split(',')

        longitude = float(longitude)
        latitude = float(latitude)

        pre_longitude = float(pre_longitude)
        pre_latitude = float(pre_latitude)
        # Check if the polygon crosses the antimeridian
        if (pre_longitude * longitude) <0 and (abs(longitude) + abs(pre_longitude)) > 270:
            if pre_longitude > 0:
                # Move the longitude coordinates to be around G meridian to calculate intersection 
                pre_longitude_g_meridian = pre_longitude - 180
                longitude_g_meridian = 180 + longitude
                latitude_med =  pre_latitude - pre_longitude_g_meridian * ((latitude - pre_latitude ) / (longitude_g_meridian - pre_longitude_g_meridian))
            else:
                pre_longitude_g_meridian = 180 + pre_longitude
                longitude_g_meridian = longitude - 180
                latitude_med =  pre_latitude - pre_longitude_g_meridian * ((latitude - pre_latitude ) / (longitude_g_meridian - pre_longitude_g_meridian))
            # end if
            
            new_longitude = 180.0
            if longitude > 0:
                new_longitude = -180.0
            # end if
            polygon.append((new_longitude, latitude_med))
                
            if len(init_longitudes_after_intersect_antimeridian) > 0 and new_longitude == init_longitudes_after_intersect_antimeridian[intersections_with_antimeridian-1]:
                reverse = True
            elif reverse and polygon_index == 0:
                reverse = False
                polygon_index = len(polygons) - 1
            # end if
            
            if reverse:
                polygon_index = polygon_index - 1
            else:
                polygon_index = polygon_index + 1
            # end if
            
            if reverse:
                polygon = polygons[polygon_index]
            else:
                polygon = []
                polygons.append(polygon)
            # end if
            polygon.append((-1 * new_longitude, latitude_med))
            init_longitudes_after_intersect_antimeridian.append(-1 * new_longitude)
            intersections_with_antimeridian = intersections_with_antimeridian + 1
        # end if            

        # Insert the current coordinate
        polygon.append((longitude, latitude))
    # end for

    # Postgis (for at least version 2.5.1) accepts a minimum number of 8 coordinates for a polygon. So, when the number of coordinates is 4 they are just duplicated
    for polygon in polygons:
        if len(polygon) == 2:
            polygon.append(polygon[1])
            polygon.append(polygon[0])
        else:
            polygon.append(polygon[0])
        # end if    
    # end for
    
    footprints = []
    for polygon in polygons:
        footprint = ""
        for i, coordinate in enumerate(polygon):
            if i == len(polygon) - 1:
                footprint = footprint + str(coordinate[0]) + " " + str(coordinate[1])
            else:
                footprint = footprint + str(coordinate[0]) + " " + str(coordinate[1]) + " "
            # end if
        # end for
        footprints.append(footprint)
    # end for

    return footprints

def correct_longitude_in_allowed_range(coordinates):
    """Function to correct the longitudes in the coordinates to be inside the range (-180,180)
    The coordinates have the following format:
    'longitude,latitude longitude,latitude longitude,latitude'
    
    Example of coordinates corrected from below -180:
    Input = '-169.61550,78.96737 -183.78889,72.56051 -186.68091,70.18446 -197.55297,71.14780 -196.07618,73.62399 -188.62089,80.59654 -169.61550,78.96737'
    Output = '-169.6155,78.96737 176.21111,72.56051 173.31909,70.18446 162.44703,71.14780 163.92382,73.62399 171.37911,80.59654 -169.6155,78.96737'

    Example of coordinates corrected from above 180:
    Input = '177.70168,70.09508 176.21806,71.69579 183.31307,72.24555 184.25473,70.61387 177.70168,70.09508'
    Output = '177.70168,70.09508 176.21806,71.69579 -176.68693,72.24555 -175.74527,70.61387 177.70168,70.09508'

    Example of coordinates not corrected
    Input = '151.90466,76.21047 143.36859,68.63463 140.95880,65.03045 135.66232,65.48421 137.23929,69.13027 142.62253,76.89805 151.90466,76.21047'
    Output = '151.90466,76.21047 143.36859,68.63463 140.9588,65.03045 135.66232,65.48421 137.23929,69.13027 142.62253,76.89805 151.90466,76.21047'

    :param coordinates: string of coordinates with the following format:
    'longitude,latitude longitude,latitude longitude,latitude'
    :type coordinates: str

    :return: corrected_coordinates
    :rtype: str
    """
    list_coordinates = coordinates.split(" ")
    # Correct the coordinates due to the antimeridian issue
    list_coordinates_to_correct = []
    for longitude_latitude in list_coordinates:
        longitude = longitude_latitude.split(",")[0]
        latitude = longitude_latitude.split(",")[1]
        if float(longitude) > 180:
            new_longitude = -180 + (float(longitude) - 180)
        elif float(longitude) < -180:
            new_longitude = 180 + (float(longitude) + 180)
        else:
            new_longitude = float(longitude)
        # end if
        list_coordinates_to_correct.append(str(new_longitude) + "," + latitude)
    # end for

    corrected_coordinates = " ".join(list_coordinates_to_correct)

    return corrected_coordinates
