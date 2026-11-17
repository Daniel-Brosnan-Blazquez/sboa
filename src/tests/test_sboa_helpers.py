"""Exercise SBOA runtime helpers without a database."""
import datetime
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import column, select, table

from sboa.common.commands import execute_command
from sboa.debugging import debug
from sboa.engine import functions
from sboa.engine.engine import Engine, exit_codes
from sboa.engine.errors import InputError
from sboa.engine.printing import literal_query


@pytest.mark.parametrize("validator,value", [
    (functions.is_valid_bool_filter, True),
    (functions.is_valid_positive_integer, 0),
    (functions.is_valid_positive_integer, "12"),
    (functions.is_valid_order_by, {"field": "name", "descending": False}),
    (functions.is_valid_date_filters, [{"date": "2026-11-16T12:00:00", "op": ">="}]),
    (functions.is_valid_float_filters, [{"float": "3.5", "op": "<="}]),
    (functions.is_valid_text_filter, {"filter": "ECHO%", "op": "like"}),
    (functions.is_valid_text_filter, {"filter": ["ECHO", uuid.uuid4()], "op": "in"}),
])
def test_copied_validators_accept_supported_filters(validator, value):
    assert validator(value) is True


@pytest.mark.parametrize("validator,value", [
    (functions.is_valid_bool_filter, "true"),
    (functions.is_valid_positive_integer, -1),
    (functions.is_valid_positive_integer, "invalid"),
    (functions.is_valid_order_by, {"field": "name"}),
    (functions.is_valid_order_by, {"field": "name", "descending": "false"}),
    (functions.is_valid_date_filters, [{"date": "invalid", "op": ">="}]),
    (functions.is_valid_date_filters, [{"date": "2026-11-16", "op": "unknown"}]),
    (functions.is_valid_float_filters, [{"float": "invalid", "op": "<="}]),
    (functions.is_valid_text_filter, {"filter": "ECHO", "op": "unknown"}),
    (functions.is_valid_text_filter, {"filter": [123], "op": "in"}),
])
def test_copied_validators_raise_local_input_error(validator, value):
    with pytest.raises(InputError):
        validator(value)


def test_debug_decorator_preserves_results_and_exceptions():
    @debug
    def example(value):
        """A profiled command."""
        if value < 0:
            raise ValueError("invalid value")
        return value * 2

    assert example.__name__ == "example"
    assert example(3) == 6
    with pytest.raises(ValueError, match="invalid value"):
        example(-1)


def test_query_formatter_uses_local_dialect():
    rules = table("rules", column("name"))
    statement = select([rules.c.name]).where(rules.c.name == "ECHO")
    sql = literal_query(statement)
    assert "rules.name" in sql
    assert "ECHO" in sql


def test_execute_command_reports_success_and_failure(capsys):
    execute_command(f'{sys.executable} -c "print(123)"', "completed")
    assert "completed" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        execute_command(f'{sys.executable} -c "raise SystemExit(2)"', "completed")
    assert "ended unexpectedly" in capsys.readouterr().out


def test_execute_command_can_ignore_exit_status(capsys):
    execute_command(f'{sys.executable} -c "raise SystemExit(2)"', "unchecked", check_error=False)
    assert "unchecked" in capsys.readouterr().out


def test_scheduler_configuration_generation_without_database():
    engine = Engine.__new__(Engine)
    rules, tasks = [], []
    fixture = Path(__file__).parent / "xml_inputs/test_general_scheduler.xml"
    result = engine.generate_rules_and_tasks(rules, tasks, datetime.datetime(2019, 12, 9), str(fixture))
    assert result["status"] == exit_codes["RULES_AND_TASKS_GENERATED"]["status"]
    assert len(rules) == 3
    assert len(tasks) == 4
    assert {task["name"] for task in tasks} == {"ECHO_1", "ECHO_2", "ECHO_3_1", "ECHO_3_2"}
