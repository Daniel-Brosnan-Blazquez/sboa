"""Check relocated initializer defaults without executing database commands."""
from importlib.resources import files
from pathlib import Path
import shlex
from unittest.mock import patch

from sboa.scripts import sboa_init as initializer


def test_initializer_uses_bundled_sql_model():
    with patch.object(initializer, "execute_command") as execute:
        initializer.init()

    execute.assert_called_once()
    arguments = shlex.split(execute.call_args.args[0])
    model = Path(arguments[arguments.index("-f") + 1])
    assert model.is_file()
    assert model.samefile(str(files("sboa.datamodel").joinpath("sboa_data_model.sql")))
