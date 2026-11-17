"""Regression coverage for SBOA configuration and scheduler resource locations."""
from importlib.resources import files
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sboa.datamodel.functions import (
    config_path,
    get_resources_path,
    get_schemas_path,
    schema_path,
    SboaResourcesPathNotAvailable,
    SboaSchemasPathNotAvailable,
)


class TestResources(unittest.TestCase):
    def test_default_resource_directory(self):
        with patch.dict(os.environ, {}, clear=True):
            expected = Path(str(files("sboa").joinpath("config")))
            self.assertEqual(Path(get_resources_path()), expected)
            self.assertEqual(Path(config_path("sboa_datamodel.json")), expected / "sboa_datamodel.json")

    def test_shared_configuration_does_not_override_sboa(self):
        with TemporaryDirectory() as legacy, patch.dict(os.environ, {"BOA_RESOURCES_PATH": legacy}, clear=True):
            (Path(legacy) / "sboa_datamodel.json").write_text("unrelated configuration")
            expected = Path(str(files("sboa").joinpath("config", "sboa_datamodel.json")))
            self.assertEqual(Path(config_path("sboa_datamodel.json")), expected)

    def test_component_resource_directory(self):
        from sboa.datamodel.functions import read_configuration
        with TemporaryDirectory() as directory:
            config = {"DDBB_CONFIGURATION": {"host": "sboa-database"}, "MAXIMUM_PARALLEL_TASKS": 3}
            (Path(directory) / "sboa_datamodel.json").write_text(json.dumps(config))
            with patch.dict(os.environ, {"SBOA_RESOURCES_PATH": directory, "BOA_RESOURCES_PATH": "/unrelated"}, clear=True):
                self.assertEqual(get_resources_path(), directory)
                self.assertEqual(read_configuration(), config)
                self.assertEqual(Path(config_path("scheduler.xml")), Path(directory) / "scheduler.xml")

    def test_missing_resource_directory_is_reported(self):
        with TemporaryDirectory() as directory:
            missing = str(Path(directory) / "missing")
            with patch.dict(os.environ, {"SBOA_RESOURCES_PATH": missing}, clear=True):
                with self.assertRaisesRegex(SboaResourcesPathNotAvailable, "SBOA resources path"):
                    get_resources_path()

    def test_resource_path_must_be_directory(self):
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "file"
            file_path.touch()
            with patch.dict(os.environ, {"SBOA_RESOURCES_PATH": str(file_path)}, clear=True):
                with self.assertRaises(SboaResourcesPathNotAvailable):
                    get_resources_path()

    def test_missing_component_config_does_not_fall_back_to_shared_directory(self):
        from sboa.datamodel.functions import read_configuration
        with TemporaryDirectory() as component, TemporaryDirectory() as legacy:
            (Path(legacy) / "sboa_datamodel.json").write_text('{"DDBB_CONFIGURATION": {"host": "unrelated"}}')
            with patch.dict(os.environ, {"SBOA_RESOURCES_PATH": component, "BOA_RESOURCES_PATH": legacy}, clear=True):
                with self.assertRaises(FileNotFoundError):
                    read_configuration()

    def test_database_host_override_uses_bundled_configuration(self):
        from sboa.datamodel.functions import read_configuration
        with patch.dict(os.environ, {"SBOA_DDBB_HOST": "test-database"}, clear=True):
            self.assertEqual(read_configuration()["DDBB_CONFIGURATION"]["host"], "test-database")

    def test_default_schema_directory(self):
        with patch.dict(os.environ, {}, clear=True):
            expected = Path(str(files("sboa").joinpath("schemas")))
            self.assertEqual(Path(get_schemas_path()), expected)
            self.assertEqual(Path(schema_path("sboa_schema.xsd")), expected / "sboa_schema.xsd")
            self.assertTrue(Path(schema_path("sboa_schema.xsd")).is_file())

    def test_shared_schema_does_not_override_sboa(self):
        with TemporaryDirectory() as legacy, patch.dict(os.environ, {"BOA_SCHEMAS_PATH": legacy}, clear=True):
            (Path(legacy) / "sboa_schema.xsd").write_text("unrelated schema")
            expected = Path(str(files("sboa").joinpath("schemas", "sboa_schema.xsd")))
            self.assertEqual(Path(schema_path("sboa_schema.xsd")), expected)

    def test_component_schema_directory(self):
        with TemporaryDirectory() as directory:
            expected = Path(directory) / "sboa_schema.xsd"
            expected.write_text("custom schema")
            with patch.dict(os.environ, {"SBOA_SCHEMAS_PATH": directory, "BOA_SCHEMAS_PATH": "/unrelated"}, clear=True):
                self.assertEqual(get_schemas_path(), directory)
                self.assertEqual(Path(schema_path("sboa_schema.xsd")).read_text(), "custom schema")

    def test_invalid_schema_directories_are_reported(self):
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "file"
            file_path.touch()
            for invalid in (file_path, Path(directory) / "missing"):
                with self.subTest(path=invalid), patch.dict(os.environ, {"SBOA_SCHEMAS_PATH": str(invalid)}, clear=True):
                    with self.assertRaisesRegex(SboaSchemasPathNotAvailable, "SBOA schemas path"):
                        schema_path("sboa_schema.xsd")

    def test_missing_component_schema_does_not_fall_back(self):
        with TemporaryDirectory() as component, TemporaryDirectory() as legacy:
            (Path(legacy) / "sboa_schema.xsd").write_text("unrelated schema")
            with patch.dict(os.environ, {"SBOA_SCHEMAS_PATH": component, "BOA_SCHEMAS_PATH": legacy}, clear=True):
                with self.assertRaises(FileNotFoundError):
                    Path(schema_path("sboa_schema.xsd")).read_text()
