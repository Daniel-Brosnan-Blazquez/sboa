"""CLI argument handling with database resets, forks, and daemonization intercepted."""
from contextlib import nullcontext
from importlib.resources import files
import os
from pathlib import Path
import runpy
import shlex
import sys
import time
from unittest.mock import MagicMock, Mock

import daemon
from daemon import pidfile
import pytest

from sboa.common import commands
from sboa.engine import engine as engine_module, query as query_module
from sboa.scheduler import boa_scheduler_functions as functions
from sboa.scripts import sboa_init


ROOT = Path(str(files("sboa")))


def test_initializer_custom_sql_file_is_passed_as_one_argument(tmp_path, monkeypatch):
    model = tmp_path / "custom model.sql"
    model.write_text("-- an alternate model")
    execute = Mock()
    monkeypatch.setattr(sboa_init, "execute_command", execute)
    sboa_init.init(str(model))
    arguments = shlex.split(execute.call_args.args[0])
    assert arguments[arguments.index("-f") + 1:] == [str(model)]


def test_initializer_rejects_missing_sql_before_running_commands(tmp_path, monkeypatch):
    execute = Mock()
    monkeypatch.setattr(sboa_init, "execute_command", execute)
    with pytest.raises(SystemExit) as raised:
        sboa_init.init(str(tmp_path / "missing.sql"))
    assert raised.value.code == -1
    execute.assert_not_called()


@pytest.mark.parametrize("accept,answer,custom", [(True, None, False), (True, None, True), (False, "y", True), (False, "n", False)])
def test_initializer_confirmation_and_cli_arguments(monkeypatch, tmp_path, accept, answer, custom):
    model = tmp_path / "model.sql"
    argv = ["sboa_init.py"] + (["-y"] if accept else []) + (["-f", str(model)] if custom else [])
    init = Mock()
    prompt = Mock(return_value=answer)
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr("builtins.input", prompt)
    monkeypatch.setattr(sboa_init, "init", init)
    with pytest.raises(SystemExit) as raised:
        sboa_init.main()
    assert raised.value.code == 0
    assert prompt.call_count == int(not accept)
    if not accept and answer != "y":
        init.assert_not_called()
    else:
        init.assert_called_once_with(str(model) if custom else None)


def test_initializer_script_entry_point_executes_bundled_model(monkeypatch):
    execute = Mock()
    monkeypatch.setattr(commands, "execute_command", execute)
    monkeypatch.setattr(sys, "argv", ["sboa_init.py", "-y"])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(ROOT / "scripts/sboa_init.py"), run_name="__main__")
    assert raised.value.code == 0
    assert "sboa_data_model.sql" in execute.call_args.args[0]


class StopLoop(Exception):
    """Stop a daemon's infinite test loop without creating a process."""


@pytest.mark.parametrize("command,no_output,locked", [
    ("start", False, False), ("start", True, False), ("start", False, True), ("start", True, True),
    ("stop", False, False), ("status", False, False), ("invalid", False, False),
])
def test_scheduler_cli_never_daemonizes_or_signals_real_processes(monkeypatch, tmp_path, capsys, command, no_output, locked):
    lock = Mock()
    lock.is_locked.return_value = locked
    context = MagicMock()
    shutdown, status = Mock(), Mock(return_value={"status": "off"})
    monkeypatch.setattr(pidfile, "TimeoutPIDLockFile", Mock(return_value=lock))
    monkeypatch.setattr(daemon, "DaemonContext", context)
    monkeypatch.setattr(functions, "pid_file", str(tmp_path / "scheduler.pid"))
    monkeypatch.setattr(functions, "pid_files_folder", str(tmp_path / "triggerings"))
    monkeypatch.setattr(functions, "stop_scheduler", shutdown)
    monkeypatch.setattr(functions, "status_scheduler", status)
    monkeypatch.setattr(time, "sleep", Mock(side_effect=StopLoop))
    monkeypatch.setattr(sys, "argv", ["boa_scheduler.py", "-c", command] + (["-o"] if no_output else []))
    expected = pytest.raises(SystemExit) if command == "start" and locked else pytest.raises(StopLoop) if command == "start" else nullcontext()
    with expected:
        runpy.run_path(str(ROOT / "scheduler/boa_scheduler.py"), run_name="__main__")
    if command == "start" and not locked:
        assert context.call_count == 1
        assert ("stdout" in context.call_args.kwargs) is (not no_output)
        assert (tmp_path / "triggerings").is_dir()
    else:
        context.assert_not_called()
    assert shutdown.call_count == int(command == "stop")
    assert status.call_count == int(command == "status")
    if command == "invalid":
        assert "not a valid argument" in capsys.readouterr().out


@pytest.mark.parametrize("fork_result", [0, 100])
def test_triggering_cli_only_executes_in_child(monkeypatch, fork_result):
    query, engine = Mock(), Mock()
    query.get_triggerings.return_value = []
    fork = Mock(return_value=fork_result)
    monkeypatch.setattr(os, "fork", fork)
    monkeypatch.setattr(query_module, "Query", Mock(return_value=query))
    monkeypatch.setattr(engine_module, "Engine", Mock(return_value=engine))
    monkeypatch.setattr(sys, "argv", ["boa_execute_triggering.py", "-u", "uuid", "-b", "begin", "-e", "end"])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(ROOT / "scheduler/boa_execute_triggering.py"), run_name="__main__")
    assert raised.value.code == 0
    fork.assert_called_once()
    assert query.get_triggerings.call_count == int(fork_result == 0)


def test_database_shell_script_preserves_paths_with_spaces(tmp_path):
    import subprocess

    model = tmp_path / "custom model.sql"
    model.write_text("-- a model for the fake PostgreSQL client")
    client = tmp_path / "psql"
    client.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$PSQL_ARGUMENTS"\nprintf "0\\n"\n')
    client.chmod(0o755)
    arguments = tmp_path / "arguments.txt"
    environment = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"], "PSQL_ARGUMENTS": str(arguments)}
    subprocess.run(["bash", str(ROOT / "scripts/sboa_init_ddbb.sh"), "-f", str(model)], env=environment, check=True, capture_output=True, text=True)
    assert arguments.read_text().splitlines()[-1] == str(model)
