"""
Functions definition for the datamodel component

Written by Daniel Brosnan Blázquez

module sboa
"""
# Import python utilities
from importlib.resources import files
import os
import json
from pathlib import Path

class SboaResourcesPathNotAvailable(FileNotFoundError):
    """The configured SBOA resource directory is unavailable."""


class SboaSchemasPathNotAvailable(FileNotFoundError):
    """The configured SBOA schema directory is unavailable."""


def get_resources_path():
    """Return SBOA_RESOURCES_PATH, defaulting to the bundled config directory."""
    directory = os.environ.get("SBOA_RESOURCES_PATH", str(files("sboa").joinpath("config")))
    if not os.path.isdir(directory):
        raise SboaResourcesPathNotAvailable("The SBOA resources path {} is not available".format(directory))
    return directory


def config_path(filename):
    return str(Path(get_resources_path()) / filename)


def get_schemas_path():
    """Return SBOA_SCHEMAS_PATH, defaulting to the bundled schemas directory."""
    directory = os.environ.get("SBOA_SCHEMAS_PATH", str(files("sboa").joinpath("schemas")))
    if not os.path.isdir(directory):
        raise SboaSchemasPathNotAvailable("The SBOA schemas path {} is not available".format(directory))
    return directory


def schema_path(filename):
    return str(Path(get_schemas_path()) / filename)


def read_configuration():
    # Get configuration
    with open(config_path("sboa_datamodel.json")) as json_data_file:
        config = json.load(json_data_file)
    # end with

    if "SBOA_DDBB_HOST" in os.environ:
        config["DDBB_CONFIGURATION"]["host"] = os.environ["SBOA_DDBB_HOST"]
    # end if

    return config
