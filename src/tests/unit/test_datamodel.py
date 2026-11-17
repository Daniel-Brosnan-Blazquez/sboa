"""Model constructors and serialized scheduler state."""
from datetime import datetime
from uuid import uuid4

from sboa.datamodel.rules import Rule, Task, Triggering


def test_models_serialize_identifiers_dates_and_window_options():
    rule_id, task_id, triggering_id = uuid4(), uuid4(), uuid4()
    date = datetime(2026, 11, 16, 10, 30)
    rule = Rule(rule_id, "weekly", 7, 1, 2)
    task = Task(task_id, "task", "echo example", date, False, rule_id)
    task.rule = rule
    triggering = Triggering(triggering_id, date, True, task_id)
    triggering.task = task

    assert rule.jsonify() == {"rule_uuid": rule_id, "name": "weekly", "periodicity": 7, "window_delay": 1, "window_size": 2}
    assert task.jsonify() == {
        "task_uuid": task_id, "name": "task", "command": "echo example",
        "triggering_time": "2026-11-16T10:30:00", "add_window_arguments": False,
        "rule_uuid": rule_id,
    }
    assert triggering.jsonify() == {
        "triggering_uuid": triggering_id, "date": "2026-11-16T10:30:00", "triggered": True, "task_uuid": task_id,
    }
