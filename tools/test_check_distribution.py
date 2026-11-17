"""Regression checks for release metadata and unwanted archive contents."""
import unittest

from check_distribution import RESOURCES, check_contents, check_metadata


METADATA = b'''Metadata-Version: 2.4
Name: sboa
Version: 1.0.7
License-Expression: MIT
Requires-Python: <3.12,>=3.9
Description-Content-Type: text/markdown
Requires-Dist: sqlalchemy==1.3.22
Project-URL: Repository, https://github.com/danielbrosnan/sboa

# SBOA
'''


class DistributionChecks(unittest.TestCase):
    def test_metadata_accepts_normalized_python_specifiers(self):
        self.assertEqual(check_metadata(METADATA, "v1.0.7"), "1.0.7")

    def test_release_tag_must_match_version(self):
        with self.assertRaisesRegex(SystemExit, "Release tag must match"):
            check_metadata(METADATA, "v1.0.8")

    def test_suite_component_dependency_is_rejected(self):
        metadata = METADATA.replace(b"Requires-Dist: sqlalchemy==1.3.22", b"Requires-Dist: otherboa>=1.0.0")
        with self.assertRaisesRegex(SystemExit, "must not depend on other BOA suite components"):
            check_metadata(metadata, "")

    def test_missing_scheduler_resource_is_rejected(self):
        names = ["sboa/" + resource for resource in RESOURCES if resource != "scheduler/boa_scheduler.py"]
        with self.assertRaisesRegex(SystemExit, "Missing resource: scheduler/boa_scheduler.py"):
            check_contents(names, "")

    def test_development_and_sibling_packages_are_rejected(self):
        for prefix in ("", "src/"):
            for extra in ("tests/test_sboa_engine.py", "sboa/__pycache__/engine.pyc", "otherboa/__init__.py"):
                with self.subTest(prefix=prefix, extra=extra):
                    names = [prefix + "sboa/" + resource for resource in RESOURCES]
                    with self.assertRaises(SystemExit):
                        check_contents(names + [prefix + extra], prefix)

    def test_runtime_resources_pass_in_both_distributions(self):
        for prefix in ("", "src/"):
            check_contents([prefix + "sboa/" + resource for resource in RESOURCES], prefix)


if __name__ == "__main__":
    unittest.main()
