"""Runtime helpers for SBOA, part of the BOA suite.

Written by Daniel Brosnan Blázquez.
"""

import json
import os
import uuid

from dateutil import parser

from sboa.datamodel.functions import config_path
from sboa.engine.errors import InputError, SboaLogPathNotAvailable
from sboa.engine.operators import arithmetic_operators, text_operators, regex_operators


def get_log_path():
    """Return SBOA_LOG_PATH, creating the log directory when necessary."""
    directory = os.environ.get("SBOA_LOG_PATH", "/tmp/sboa_log")
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as error:
        raise SboaLogPathNotAvailable("The SBOA log path {} is not available".format(directory)) from error
    return directory


def read_configuration():
    """Read SBOA engine and logging configuration."""
    with open(config_path("engine.json"), encoding="utf-8") as stream:
        return json.load(stream)


def is_datetime(date):
    """
    Function for the parsing of dates inside json files

    :param date: date to be parsed
    :type date: str

    :return: True if date is a correct date, False otherwise
    :rtype: bool
    """
    try:
        parser.parse(date)
    except:
        return False
    else:
        return True

def is_valid_bool_filter(filter):

    if type(filter) != bool:
        raise InputError("The parameter filter must be a boolean value (received filter: {}).".format(filter))
    # end if

    return True

def is_valid_positive_integer(filter):

    try:
        int(filter)
    except ValueError:
        raise InputError("The parameter filter must be an integer (received filter: {}).".format(filter))
    # end try

    if int(filter) < 0:
        raise InputError("The parameter filter must be a positive integer (received filter: {}).".format(filter))
    # end if

    return True

def is_valid_order_by(order_by):

    if type(order_by) != dict:
        raise InputError("The parameter order_by must be a dictionary (received order_by: {}).".format(order_by))
    # end if

    if len(order_by.keys()) != 2 or not "field" in order_by.keys() or not "descending" in order_by.keys():
        raise InputError("Every order_by should be a dictionary with keys field and descending (received keys: {}).".format(order_by.keys()))
    # end if

    if type(order_by["field"]) != str:
        raise InputError("The key field inside the dictionary order_by must be a string (received type: {}).".format(order_by["field"]))
    # end if

    if type(order_by["descending"]) != bool:
        raise InputError("The key descending inside the dictionary order_by must be a boolean (received type: {}).".format(order_by["descending"]))
    # end if

    return True

def is_valid_date_filters(date_filters):

    if type(date_filters) != list:
        raise InputError("The parameter date_filters must be a list of dictionaries (received date_filters: {}).".format(date_filters))
    # end if
    for date_filter in date_filters:
        if type(date_filter) != dict:
            raise InputError("The parameter date_filters must contain dictionaries (received date_filter: {}).".format(date_filter))
        # end if
        if len(date_filter.keys()) != 2 or not "date" in date_filter.keys() or not "op" in date_filter.keys():
            raise InputError("Every date_filter should be a dictionary with keys date and op (received keys: {}).".format(date_filter.keys()))
        # end if
        if not date_filter["op"] in arithmetic_operators:
            raise InputError("The specified op is not a valid operator (received op: {}).".format(date_filter["op"]))
        # end if
        if not is_datetime(date_filter["date"]):
            raise InputError("The specified date is not a valid date (received date: {}).".format(date_filter["date"]))
        # end if
    # end for

    return True

def is_valid_float_filters(float_filters):

    if type(float_filters) != list:
        raise InputError("The parameter float_filters must be a list of dictionaries (received float_filters: {}).".format(float_filters))
    # end if
    for float_filter in float_filters:
        if type(float_filter) != dict:
            raise InputError("The parameter float_filters must contain dictionaries (received float_filter: {}).".format(float_filter))
        # end if
        if len(float_filter.keys()) != 2 or not "float" in float_filter.keys() or not "op" in float_filter.keys():
            raise InputError("Every float_filter should be a dictionary with keys float and op (received keys: {}).".format(float_filter.keys()))
        # end if
        if not float_filter["op"] in arithmetic_operators:
            raise InputError("The specified op is not a valid operator (received op: {}).".format(float_filter["op"]))
        # end if
        try:
            float(float_filter["float"])
        except ValueError:
            raise InputError("The specified float is not a valid float (received float: {}).".format(float_filter["float"]))
        # end try
    # end for

    return True

def is_valid_text_filter(text_filter):

    if type(text_filter) != dict:
        raise InputError("The parameter text_filter must be a dictionary (received text_filter: {}).".format(text_filter))
    # end if
    if len(text_filter.keys()) != 2 or not "op" in text_filter.keys() or not "filter" in text_filter.keys():
        raise InputError("The parameter text_filter should be a dictionary with keys op and filter (received keys: {}).".format(text_filter.keys()))
    # end if
    if type(text_filter["op"]) != str or not (text_filter["op"] in arithmetic_operators.keys() or text_filter["op"] in text_operators.keys() or text_filter["op"] in regex_operators.keys()):
        raise InputError("The specified op must be a string inside these list: {} (received op: {}).".format(list(arithmetic_operators.keys()) + list(text_operators.keys()) + list(regex_operators.keys()), text_filter["op"]))
    # end if
    if (text_filter["op"] in ["like", "notlike", "regex"] or text_filter["op"] in arithmetic_operators.keys()) and type(text_filter["filter"]) != str:
        raise InputError("The specified filter must be a string when the op is in the list {} (received filter has type: {}).".format(list(arithmetic_operators.keys()) + ["like", "notlike"], type(text_filter["filter"])))
    # end if
    if text_filter["op"] in ["in", "notin"] and type(text_filter["filter"]) != list:
        raise InputError("The specified filter must be a list when the op is 'in' or 'notin' (received filter has type: {}).".format(type(text_filter["filter"])))
    # end if
    if text_filter["op"] in ["in", "notin"] and type(text_filter["filter"]) == list:
        not_str_filters = [text_filter for text_filter in text_filter["filter"] if type(text_filter) != str and type(text_filter) != uuid.UUID]
        if len(not_str_filters) > 0:
            raise InputError("The specified filter inside the list must be a string when the op is 'in' or 'notin' (received filters are: {}).".format(not_str_filters))
        # end if
    # end if

    return True
