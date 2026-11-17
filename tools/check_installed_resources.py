"""Smoke test an installed SBOA distribution outside its source checkout."""
from importlib.resources import files
from importlib.abc import MetaPathFinder
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_distribution import COMMANDS, RESOURCES, require


class BlockSuiteImports(MetaPathFinder):
    """Verify SBOA runs independently of other BOA suite components."""

    def find_spec(self, fullname, path=None, target=None):
        package = fullname.split(".", 1)[0]
        if package != "sboa" and package.endswith("boa"):
            raise ImportError("SBOA must run independently of other BOA suite components: " + fullname)
        return None


def check():
    package = files("sboa")
    for resource in RESOURCES:
        require(package.joinpath(resource).is_file(), "Missing installed resource: " + resource)
    for command in COMMANDS:
        require(shutil.which(command), "Missing installed command: " + command)

    with TemporaryDirectory(prefix="sboa-installed-") as directory:
        state = Path(directory) / "state"
        state.mkdir()
        for config in package.joinpath("config").iterdir():
            if config.is_file():
                (state / config.name).write_bytes(config.read_bytes())
        log = Path(directory) / "log"
        log.mkdir()
        environment = {
            key: value for key, value in os.environ.items()
            if not key.split("_", 1)[0].endswith("BOA") or key.startswith("SBOA_")
        }
        environment.update({
            "SBOA_LOG_PATH": str(log),
            "SBOA_RESOURCES_PATH": str(state),
            "SBOA_SCHEMAS_PATH": str(package.joinpath("schemas")),
        })
        with patch.dict(os.environ, environment, clear=True), patch.object(sys, "meta_path", [BlockSuiteImports(), *sys.meta_path]):
            import sboa.engine.engine
            from sboa.scheduler import boa_scheduler_functions
            from sboa.scripts import sboa_init

            require(Path(boa_scheduler_functions.pid_file) == state / "boa_scheduler.pid", "Scheduler PID file did not use SBOA_RESOURCES_PATH")
            require(Path(boa_scheduler_functions.pid_files_folder) == state / "on_going_triggerings", "Triggering state did not use SBOA_RESOURCES_PATH")
            with patch.object(sboa_init, "execute_command") as execute:
                sboa_init.init()
            execute.assert_called_once()
            arguments = shlex.split(execute.call_args.args[0])
            model = Path(arguments[arguments.index("-f") + 1])
            require(model.samefile(str(package.joinpath("datamodel/sboa_data_model.sql"))), "Initializer did not select bundled SQL")
            for command in ("sboa_init.py", "boa_scheduler.py", "boa_execute_triggering.py"):
                subprocess.run([command, "--help"], check=True, cwd=directory, capture_output=True, text=True)
    print("Validated installed SBOA resources, initializer, imports, and commands")


if __name__ == "__main__":
    check()
