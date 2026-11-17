"""Scheduling calendar rules, configuration validation, and persisted triggerings."""
import calendar
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from lxml import etree
import pytest

from sboa.datamodel.rules import Rule, Task, Triggering
from sboa.engine import engine as engine_module


pytestmark = pytest.mark.integration


FIXTURE = Path(__file__).parents[1] / "xml_inputs/test_general_scheduler.xml"


@pytest.fixture
def engine(store, monkeypatch):
    monkeypatch.setattr(engine_module.boa_scheduler, "stop_scheduler", Mock())
    return store.engine


@pytest.fixture
def configuration(tmp_path):
    path = tmp_path / "scheduler.xml"
    path.write_bytes(FIXTURE.read_bytes())
    return path


def generate(engine, path, date=datetime(2026, 11, 16)):
    rules, tasks = [], []
    result = engine.generate_rules_and_tasks(rules, tasks, date, str(path))
    return result, rules, tasks


@pytest.mark.parametrize("weekday", list(calendar.day_name))
@pytest.mark.parametrize("start", [datetime(2026, 11, 16), datetime(2026, 11, 22)])
def test_weekday_schedule_rolls_forward_to_next_matching_day(engine, configuration, weekday, start):
    tree = etree.parse(str(configuration))
    tree.find("rule/date/weekday").text = weekday.lower()
    tree.write(str(configuration))
    result, rules, tasks = generate(engine, configuration, start)
    assert result["status"] == engine_module.exit_codes["RULES_AND_TASKS_GENERATED"]["status"]
    expected = start + timedelta(days=(list(calendar.day_name).index(weekday) - start.weekday()) % 7)
    assert tasks[0]["triggering_time"] == expected.strftime("%Y-%m-%dT10:00:00")
    assert len(rules) == 3
    assert tasks[1]["triggering_time"] == start.strftime("%Y-%m-%dT10:00:00")
    assert tasks[2]["triggering_time"] == "2019-12-01T10:00:00"


@pytest.mark.parametrize("window", ["true", "false", "1", "0"])
def test_skip_flags_and_window_arguments(engine, configuration, window):
    tree = etree.parse(str(configuration))
    tree.find("rule").set("skip", "false")
    tree.find("rule/tasks/task").set("add_window_arguments", window)
    tree.findall("rule")[2].find("tasks/task").set("skip", "true")
    tree.write(str(configuration))
    result, rules, tasks = generate(engine, configuration)
    assert result["status"] == 5
    assert len(rules) == 3
    assert len(tasks) == 3
    assert tasks[0]["add_window_arguments"] is (window in ("true", "1"))
    assert "ECHO_3_1" not in {task["name"] for task in tasks}


@pytest.mark.parametrize("kind,code", [
    ("wrong_date", "T0_IS_NOT_DATETIME"),
    ("missing_file", "CONFIG_FILE_DOES_NOT_EXIST"),
    ("malformed_xml", "FILE_NOT_READABLE"),
    ("invalid_schema", "FILE_NOT_VALID"),
    ("duplicate_rules", "DUPLICATED_RULE_NAMES"),
    ("duplicate_tasks", "DUPLICATED_TASK_NAMES"),
])
def test_bad_configuration_reports_error_without_modifying_agenda(engine, configuration, kind, code):
    date = datetime(2026, 11, 16)
    rule = Rule(uuid4(), "existing", 1, 0, 1)
    task = Task(uuid4(), "existing task", "echo existing", date, True, rule.rule_uuid)
    task.rule = rule
    engine.session.add_all([rule, task])
    engine.session.commit()
    if kind == "wrong_date":
        date = "not a date"
    elif kind == "missing_file":
        configuration.unlink()
    elif kind == "malformed_xml":
        configuration.write_text("<rules>")
    elif kind == "invalid_schema":
        configuration.write_text("<unexpected/>")
    else:
        tree = etree.parse(str(configuration))
        if kind == "duplicate_rules":
            tree.findall("rule")[1].set("name", "ECHO_1")
        else:
            tree.findall("rule")[1].find("tasks/task").set("name", "ECHO_1")
        tree.write(str(configuration))
    result, rules, tasks = generate(engine, configuration, date)
    assert result["status"] == engine_module.exit_codes[code]["status"]
    assert result["message"]
    assert rules == tasks == []
    assert engine.session.query(Task).one().name == "existing task"
    assert engine.insert_configuration(date, str(configuration))["status"] == result["status"]
    assert engine.session.query(Task).one().name == "existing task"


@pytest.mark.parametrize("start_scheduler,return_code", [(False, 0), (True, 0), (True, 1)])
def test_configuration_insertion_and_scheduler_start(engine, configuration, monkeypatch, start_scheduler, return_code):
    start = Mock(return_value={"return_code": return_code, "output": "output", "error": "reason"})
    monkeypatch.setattr(engine_module.boa_scheduler, "command_start_scheduler", start)
    result = engine.insert_configuration(datetime(2026, 11, 16), str(configuration), start_scheduler)
    expected = "BOA_SCHEDULER_COULD_NOT_START" if return_code else "OK"
    assert result["status"] == engine_module.exit_codes[expected]["status"]
    assert engine.session.query(Task).count() == 4
    assert start.call_count == int(start_scheduler)


def test_triggering_lifecycle_and_task_rescheduling(engine, configuration):
    engine.insert_configuration(datetime(2026, 11, 16), str(configuration))
    task = engine.session.query(Task).first()
    date = datetime(2026, 11, 16, 11)
    missing = engine.insert_triggering(date, uuid4())
    assert missing == {"triggering_uuid": "", "status": engine_module.exit_codes["TASK_UUID_DOES_NOT_EXIST"]["status"]}
    invalid = engine.insert_triggering("invalid", task.task_uuid)
    assert invalid["status"] == engine_module.exit_codes["DATE_IS_NOT_DATETIME"]["status"]
    result = engine.insert_triggering(date, task.task_uuid)
    triggering = engine.session.query(Triggering).one()
    assert triggering.triggering_uuid == result["triggering_uuid"]
    assert triggering.triggered is False
    assert triggering.date == date
    engine.triggering_done(triggering.triggering_uuid)
    assert triggering.triggered is True
    engine.set_triggering_time(task.task_uuid, date + timedelta(days=1))
    assert task.triggering_time == date + timedelta(days=1)


@pytest.mark.parametrize("skip", ["false", "0", "true", "1"])
def test_all_xml_boolean_skip_values(engine, configuration, skip):
    tree = etree.parse(str(configuration))
    tree.find("rule").set("skip", skip)
    tree.write(str(configuration))
    result, rules, tasks = generate(engine, configuration)
    assert result["status"] == 5
    included = skip in ("false", "0")
    assert ("ECHO_1" in {rule["name"] for rule in rules}) is included
    assert ("ECHO_1" in {task["name"] for task in tasks}) is included


def test_tasks_in_skipped_rules_do_not_create_duplicate_name_errors(engine, configuration):
    tree = etree.parse(str(configuration))
    task = etree.SubElement(tree.findall("rule")[-1].find("tasks"), "task", name="ECHO_1")
    etree.SubElement(task, "command").text = "echo skipped"
    tree.write(str(configuration))
    result, rules, tasks = generate(engine, configuration)
    assert result["status"] == 5
    assert len(tasks) == 4
