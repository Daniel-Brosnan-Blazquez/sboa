"""Verify SBOA release metadata, commands, and bundled runtime resources."""
import argparse
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile


RESOURCES = (
    "__init__.py",
    "common/__init__.py",
    "common/commands.py",
    "debugging.py",
    "logging.py",
    "config/engine.json",
    "config/sboa_datamodel.json",
    "config/scheduler.xml",
    "schemas/sboa_schema.xsd",
    "datamodel/__init__.py",
    "datamodel/base.py",
    "datamodel/functions.py",
    "datamodel/rules.py",
    "datamodel/sboa_data_model.dbm",
    "datamodel/sboa_data_model.sql",
    "engine/errors.py",
    "engine/functions.py",
    "engine/operators.py",
    "engine/printing.py",
    "engine/query.py",
    "scripts/__init__.py",
    "scripts/sboa_init.py",
    "scripts/sboa_init_ddbb.sh",
    "scripts/initialize_sboa_ddbb.sh",
    "scripts/start_sboa.sh",
    "scheduler/boa_scheduler.py",
    "scheduler/boa_execute_triggering.py",
    "scheduler/boa_scheduler_functions.py",
)
COMMANDS = (
    "sboa_init.py",
    "sboa_init_ddbb.sh",
    "initialize_sboa_ddbb.sh",
    "start_sboa.sh",
    "boa_scheduler.py",
    "boa_execute_triggering.py",
)
FIGURES = (
    "doc/fig/sboadb.png",
    "doc/fig/sboa_operations_overview_flow.svg",
    "doc/fig/sboa_configuration_activation_flow.svg",
    "doc/fig/sboa_scheduler_dispatch_flow.svg",
    "doc/fig/sboa_triggering_execution_flow.svg",
)


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def check_metadata(data, tag):
    metadata = BytesParser().parsebytes(data)
    require(metadata["Name"] == "sboa", "Unexpected distribution name")
    require(metadata["License-Expression"] == "MIT", "Missing MIT license metadata")
    require(set((metadata["Requires-Python"] or "").split(",")) == {">=3.9", "<3.12"}, "Unexpected Python compatibility")
    require(metadata["Description-Content-Type"] == "text/markdown", "Missing Markdown description")
    for image_url in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", metadata.get_payload()):
        require(image_url.startswith("https://"), "README images must use absolute HTTPS URLs: " + image_url)
    require(metadata.get_all("Requires-Dist"), "Missing runtime dependencies")
    for dependency in metadata.get_all("Requires-Dist", []):
        name = re.match(r"[A-Za-z0-9_.-]+", dependency).group().lower()
        require(not name.endswith("boa"), "SBOA must not depend on other BOA suite components")
    require(metadata.get_all("Project-URL"), "Missing project URLs")
    require(metadata["Version"], "Missing version")
    if tag:
        require(tag == "v" + metadata["Version"], "Release tag must match v" + metadata["Version"])
    return metadata["Version"]


def check_contents(names, prefix):
    for resource in RESOURCES:
        require(prefix + "sboa/" + resource in names, "Missing resource: " + resource)
    for name in names:
        parts = PurePosixPath(name).parts
        require(
            not {"tests", "__pycache__", ".pytest_cache", ".git"}.intersection(parts)
            and PurePosixPath(name).name != ".coverage"
            and not name.endswith((".pyc", ".pyo")),
            "Development artifact in distribution: " + name,
        )
        if name.startswith(prefix):
            package = name[len(prefix):].split("/", 1)[0]
            require(package == "sboa" or not package.endswith("boa"), "Unrelated package in distribution: " + name)


def check(directory, tag=""):
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    require(len(wheels) == len(sdists) == 1, "Expected exactly one wheel and one source distribution")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        require(len(metadata_names) == 1, "Expected one wheel metadata file")
        wheel_version = check_metadata(archive.read(metadata_names[0]), tag)
        check_contents(names, "")
        for command in COMMANDS:
            require(any(name.endswith(".data/scripts/" + command) for name in names), "Missing command: " + command)
        for filename in ("LICENSE", "AUTHORS"):
            require(any(name.endswith(".dist-info/licenses/" + filename) for name in names), "Missing license file: " + filename)
    with tarfile.open(sdists[0]) as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        names = [member.name.split("/", 1)[-1] for member in members]
        metadata_members = [member for member in members if member.name.split("/", 1)[-1] == "PKG-INFO"]
        require(len(metadata_members) == 1, "Expected one source metadata file")
        source_version = check_metadata(archive.extractfile(metadata_members[0]).read(), tag)
        require(wheel_version == source_version, "Wheel and source versions differ")
        check_contents(names, "src/")
        for filename in ("pyproject.toml", "README.md", "LICENSE", "AUTHORS", "doc/publishing.md", "tools/check_distribution.py", "tools/check_installed_resources.py"):
            require(filename in names, "Missing source file: " + filename)
        for figure in FIGURES:
            require(figure in names, "Missing documentation image: " + figure)
    print("Validated SBOA wheel and source distribution")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("dist"))
    parser.add_argument("--tag", default="", help="release tag, such as v1.0.7")
    args = parser.parse_args()
    check(args.directory, args.tag)
