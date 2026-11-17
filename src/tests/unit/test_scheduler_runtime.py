"""Scheduler capacity, execution windows, PID cleanup, and worker failures."""
from datetime import datetime, timedelta
import errno
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import lockfile
import psutil
import pytest

from sboa.scheduler import boa_scheduler as scheduler
from sboa.scheduler import boa_scheduler_functions as functions
from sboa.scheduler import boa_execute_triggering as worker


@pytest.fixture
def scheduler_io(monkeypatch):
    query, engine = Mock(), Mock()
    query.get_triggerings.return_value = []
    query.get_tasks.return_value = []
    pool = Mock()
    pool_factory = Mock(return_value=pool)
    monkeypatch.setattr(scheduler, "Query", Mock(return_value=query))
    monkeypatch.setattr(scheduler, "Engine", Mock(return_value=engine))
    monkeypatch.setattr(scheduler, "Pool", pool_factory)
    monkeypatch.setattr(scheduler, "maximum_parallel_tasks", 2)
    return SimpleNamespace(query=query, engine=engine, pool=pool, pool_factory=pool_factory)


def scheduled_task(index):
    return SimpleNamespace(
        task_uuid=uuid4(), triggering_time=datetime(2026, 11, 16, 10) + timedelta(days=index),
        rule=SimpleNamespace(window_delay=0.5, window_size=2, periodicity=7),
    )


def test_idle_scheduler_closes_sessions_without_starting_workers(scheduler_io):
    scheduler.query_and_execute_tasks()
    scheduler_io.pool_factory.assert_not_called()
    scheduler_io.query.close_session.assert_called_once()
    scheduler_io.engine.close_session.assert_called_once()


def test_saturated_scheduler_preserves_limit_and_closes_sessions(scheduler_io):
    scheduler_io.query.get_triggerings.return_value = [Mock(), Mock()]
    logger = Mock()
    scheduler.query_and_execute_tasks(logger)
    logger.error.assert_called_once()
    scheduler_io.query.get_tasks.assert_not_called()
    scheduler_io.pool_factory.assert_not_called()
    scheduler_io.query.close_session.assert_called_once()
    scheduler_io.engine.close_session.assert_called_once()


@pytest.mark.parametrize("capacity_limited", [True, False])
def test_available_tasks_use_correct_windows_and_next_triggering_time(scheduler_io, capacity_limited):
    tasks = [scheduled_task(index) for index in range(3 if capacity_limited else 1)]
    scheduler_io.query.get_tasks.return_value = tasks
    scheduler_io.query.get_triggerings.return_value = [Mock()] if capacity_limited else []
    triggering_id = uuid4()
    scheduler_io.engine.insert_triggering.return_value = {"status": 0, "triggering_uuid": triggering_id}
    scheduler.query_and_execute_tasks(Mock())
    scheduler_io.pool_factory.assert_called_once_with(1)
    scheduler_io.engine.set_triggering_time.assert_called_once_with(tasks[0].task_uuid, tasks[0].triggering_time + timedelta(days=7))
    expected = {"triggering_uuid": str(triggering_id), "start": "2026-11-13T22:00:00", "stop": "2026-11-15T22:00:00"}
    scheduler_io.pool.map.assert_called_once_with(scheduler.execute_triggering, [expected])
    scheduler_io.pool.close.assert_called_once()
    scheduler_io.pool.join.assert_called_once()
    filters = scheduler_io.query.get_triggerings.call_args.kwargs["date_filters"]
    assert datetime.fromisoformat(filters[1]["date"]) - datetime.fromisoformat(filters[0]["date"]) == timedelta(minutes=30)


def test_failed_triggering_is_not_rescheduled(scheduler_io):
    scheduler_io.query.get_tasks.return_value = [scheduled_task(0)]
    scheduler_io.engine.insert_triggering.return_value = {"status": 7, "triggering_uuid": ""}
    scheduler.query_and_execute_tasks(Mock())
    scheduler_io.engine.set_triggering_time.assert_not_called()
    scheduler_io.pool.map.assert_called_once_with(scheduler.execute_triggering, [])


def test_worker_pool_errors_still_release_pool_and_database_sessions(scheduler_io):
    scheduler_io.query.get_tasks.return_value = [scheduled_task(0)]
    scheduler_io.engine.insert_triggering.return_value = {"status": 0, "triggering_uuid": uuid4()}
    scheduler_io.pool.map.side_effect = RuntimeError("worker pool failed")
    with pytest.raises(RuntimeError, match="worker pool failed"):
        scheduler.query_and_execute_tasks(Mock())
    scheduler_io.pool.close.assert_called_once()
    scheduler_io.pool.join.assert_called_once()
    scheduler_io.query.close_session.assert_called_once()
    scheduler_io.engine.close_session.assert_called_once()


def test_scheduler_launches_trigger_command_with_window_arguments(monkeypatch):
    launch = Mock()
    monkeypatch.setattr(scheduler, "Popen", launch)
    scheduler.execute_triggering({"triggering_uuid": "uuid", "start": "2026-11-16T10:00:00", "stop": "2026-11-17T10:00:00"})
    assert launch.call_args.args[0] == ["boa_execute_triggering.py", "-u", "uuid", "-b", "2026-11-16T10:00:00", "-e", "2026-11-17T10:00:00"]


def test_pid_directory_creation_is_idempotent_and_propagates_other_errors(tmp_path, monkeypatch):
    folder = tmp_path / "triggerings"
    monkeypatch.setattr(scheduler, "pid_files_folder", str(folder))
    scheduler.create_pid_files_folder()
    scheduler.create_pid_files_folder()
    assert folder.is_dir()
    monkeypatch.setattr(scheduler, "os", SimpleNamespace(makedirs=Mock(side_effect=OSError(errno.EACCES, "permission denied"))))
    with pytest.raises(OSError, match="permission denied"):
        scheduler.create_pid_files_folder()


def test_scheduler_main_loop_polls_and_wrappers_delegate(monkeypatch, tmp_path):
    stop = RuntimeError("stop the test loop")
    sleep = Mock(side_effect=[None, stop])
    poll = Mock()
    monkeypatch.setattr(scheduler, "time", SimpleNamespace(sleep=sleep))
    monkeypatch.setattr(scheduler, "query_and_execute_tasks", poll)
    monkeypatch.setattr(scheduler, "pid_files_folder", str(tmp_path / "state"))
    with pytest.raises(RuntimeError, match="stop the test loop"):
        scheduler.start_scheduler()
    poll.assert_called_once()
    shutdown = Mock()
    status = Mock(return_value={"status": "off"})
    monkeypatch.setattr(functions, "stop_scheduler", shutdown)
    monkeypatch.setattr(functions, "status_scheduler", status)
    scheduler.stop_scheduler()
    assert scheduler.status_scheduler() == {"status": "off"}
    shutdown.assert_called_once()


@pytest.fixture
def pid_environment(monkeypatch, tmp_path):
    query, lock, process = Mock(), Mock(), Mock()
    lock.is_locked.return_value = True
    lock.read_pid.return_value = 12345
    lock_factory = Mock(return_value=lock)
    process_factory = Mock(return_value=process)
    monkeypatch.setattr(functions, "Query", Mock(return_value=query))
    monkeypatch.setattr(functions.pidfile, "TimeoutPIDLockFile", lock_factory)
    monkeypatch.setattr(functions.psutil, "Process", process_factory)
    main = tmp_path / "scheduler.pid"
    folder = tmp_path / "triggerings"
    main.touch()
    folder.mkdir()
    monkeypatch.setattr(functions, "pid_file", str(main))
    monkeypatch.setattr(functions, "pid_files_folder", str(folder))
    return SimpleNamespace(query=query, lock=lock, lock_factory=lock_factory, process=process, process_factory=process_factory, main=main, folder=folder)


def test_shutdown_when_scheduler_is_off_leaves_files_alone(pid_environment):
    state = pid_environment
    state.lock.is_locked.return_value = False
    assert functions.status_scheduler()["status"] == "off"
    functions.stop_scheduler()
    assert state.main.is_file()
    state.process_factory.assert_not_called()
    state.query.close_session.assert_called_once()


@pytest.mark.parametrize("stale", [False, True])
@pytest.mark.parametrize("workers", [False, True])
def test_shutdown_cleans_running_and_stale_pid_files(pid_environment, stale, workers):
    state = pid_environment
    if workers:
        (state.folder / "worker.pid").touch()
    if stale:
        state.process_factory.side_effect = psutil.NoSuchProcess(12345)
    assert functions.status_scheduler()["status"] == "on"
    functions.stop_scheduler()
    assert not state.main.exists()
    assert list(state.folder.iterdir()) == []
    if not stale:
        assert state.process.terminate.call_count == 1 + int(workers)
    state.query.close_session.assert_called_once()


def test_shutdown_tolerates_pid_files_removed_by_another_process(pid_environment, monkeypatch):
    state = pid_environment
    remove = Mock(side_effect=FileNotFoundError())
    monkeypatch.setattr(functions, "os", SimpleNamespace(remove=remove, listdir=Mock(return_value=["worker.pid"])))
    functions.stop_scheduler()
    assert remove.call_count == 2
    state.query.close_session.assert_called_once()


@pytest.mark.parametrize("missing", [False, True])
def test_start_command_captures_output_or_reports_missing_binary(monkeypatch, missing):
    process = Mock(returncode=0)
    process.communicate.return_value = (b"started", b"diagnostic")
    launch = Mock(side_effect=FileNotFoundError()) if missing else Mock(return_value=process)
    monkeypatch.setattr(functions, "Popen", launch)
    result = functions.command_start_scheduler()
    assert launch.call_args.args[0] == ["boa_scheduler.py", "-c", "start", "-o"]
    assert result["return_code"] == (-1 if missing else 0)
    assert result["output"] == ("" if missing else "started")
    assert ("not found" in result["error"]) if missing else result["error"] == "diagnostic"


@pytest.fixture
def worker_io(monkeypatch, tmp_path):
    query, engine, lock = Mock(), Mock(), Mock()
    task = SimpleNamespace(command='echo "a task"', add_window_arguments=True, triggering_time=datetime(2026, 11, 16))
    query.get_triggerings.return_value = [SimpleNamespace(task=task)]
    process = Mock(returncode=0)
    process.communicate.return_value = (b"done", b"")
    launch = Mock(return_value=process)
    monkeypatch.setattr(worker, "Query", Mock(return_value=query))
    monkeypatch.setattr(worker, "Engine", Mock(return_value=engine))
    monkeypatch.setattr(worker.pidfile, "TimeoutPIDLockFile", Mock(return_value=lock))
    monkeypatch.setattr(worker, "Popen", launch)
    monkeypatch.setattr(worker, "pid_files_folder", str(tmp_path))
    return SimpleNamespace(query=query, engine=engine, lock=lock, task=task, launch=launch)


@pytest.mark.parametrize("window", [True, False])
def test_triggering_runs_command_and_releases_lock_and_sessions(worker_io, window):
    state = worker_io
    state.task.add_window_arguments = window
    worker.execute_triggering("uuid", "begin", "end")
    expected = ["echo", "a task"] + (["-b", "begin", "-e", "end"] if window else [])
    assert state.launch.call_args.args[0] == expected
    state.engine.triggering_done.assert_called_once_with("uuid")
    state.lock.acquire.assert_called_once()
    state.lock.release.assert_called_once()
    state.engine.close_session.assert_called_once()
    state.query.close_session.assert_called_once()


def test_missing_triggering_does_not_execute_a_command(worker_io):
    state = worker_io
    state.query.get_triggerings.return_value = []
    worker.execute_triggering("missing", "begin", "end")
    state.launch.assert_not_called()
    state.lock.acquire.assert_not_called()
    state.engine.close_session.assert_called_once()
    state.query.close_session.assert_called_once()


def test_lock_failure_aborts_execution_and_closes_database_sessions(worker_io, capsys):
    state = worker_io
    state.lock.acquire.side_effect = lockfile.LockFailed("locked")
    worker.execute_triggering("uuid", "begin", "end")
    state.launch.assert_not_called()
    state.lock.release.assert_not_called()
    assert "locked" in capsys.readouterr().out
    state.engine.close_session.assert_called_once()
    state.query.close_session.assert_called_once()


def test_command_failure_releases_lock_without_marking_triggering_complete(worker_io, capsys):
    state = worker_io
    state.launch.side_effect = FileNotFoundError("missing command")
    worker.execute_triggering("uuid", "begin", "end")
    state.engine.triggering_done.assert_not_called()
    state.lock.release.assert_called_once()
    state.engine.close_session.assert_called_once()
    state.query.close_session.assert_called_once()
    assert "missing command" in capsys.readouterr().out
