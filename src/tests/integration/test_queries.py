"""Exercise filters, joins, ordering, pagination, and deletion on real SQLAlchemy queries."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from sboa.datamodel.rules import Rule, Task, Triggering
from sboa.engine import query as query_module
from sboa.engine.errors import InputError


pytestmark = pytest.mark.integration


@pytest.fixture
def agenda(store):
    session = store.query.session
    base = datetime(2026, 11, 16, 10)
    rules, tasks, triggerings = [], [], []
    for index in range(3):
        rule = Rule(uuid4(), f"rule{index}", index + 1, 0, index + 1)
        task = Task(uuid4(), f"task{index}", "echo example", base + timedelta(days=index), True, rule.rule_uuid)
        task.rule = rule
        triggering = Triggering(uuid4(), task.triggering_time, index % 2 == 0, task.task_uuid)
        triggering.task = task
        session.add_all([rule, task, triggering])
        rules.append(rule)
        tasks.append(task)
        triggerings.append(triggering)
    session.commit()
    return store.query, rules, tasks, triggerings


@pytest.mark.parametrize("entity,method,id_argument,id_field,name_argument", [
    (Rule, "get_rules", "rule_uuids", "rule_uuid", "names"),
    (Task, "get_tasks", "task_uuids", "task_uuid", "names"),
    (Triggering, "get_triggerings", "triggering_uuids", "triggering_uuid", "task_names"),
])
def test_identifier_and_name_filters(agenda, entity, method, id_argument, id_field, name_argument):
    query, rules, tasks, triggerings = agenda
    rows = {Rule: rules, Task: tasks, Triggering: triggerings}[entity]
    find = getattr(query, method)
    key = getattr(rows[1], id_field)
    assert len(find()) == 3
    assert find(**{id_argument: {"filter": str(key), "op": "=="}})[0] == rows[1]
    assert find(**{id_argument: {"filter": [key], "op": "in"}}) == [rows[1]]
    name = "rule1" if entity is Rule else "task1"
    assert find(**{name_argument: {"filter": name, "op": "=="}}) == [rows[1]]
    assert find(**{name_argument: {"filter": [name], "op": "in"}}) == [rows[1]]
    assert len(find(**{name_argument: {"filter": "%0", "op": "like"}})) == 1


@pytest.mark.parametrize("method,field,expected_field", [
    ("get_rules", "name", "name"), ("get_tasks", "name", "name"), ("get_triggerings", "date", "date"),
])
@pytest.mark.parametrize("descending", [True, False])
def test_order_and_pagination(agenda, method, field, expected_field, descending):
    query, *_ = agenda
    find = getattr(query, method)
    rows = find(order_by={"field": field, "descending": descending})
    assert [getattr(row, expected_field) for row in rows] == sorted([getattr(row, expected_field) for row in rows], reverse=descending)
    assert find(order_by={"field": field, "descending": descending}, limit=1, offset=1) == rows[1:2]


def test_numeric_date_and_boolean_filters(agenda):
    query, rules, tasks, triggerings = agenda
    assert {row.rule_uuid for row in query.get_rules(window_size_filters=[{"float": 2, "op": ">="}])} == {row.rule_uuid for row in rules[1:]}
    date = tasks[1].triggering_time.isoformat()
    assert query.get_tasks(triggering_time_filters=[{"date": date, "op": "=="}]) == [tasks[1]]
    assert {row.triggering_uuid for row in query.get_triggerings(date_filters=[{"date": date, "op": ">="}])} == {row.triggering_uuid for row in triggerings[1:]}
    assert query.get_triggerings(triggered=False) == [triggerings[1]]
    assert {row.triggering_uuid for row in query.get_triggerings(triggered=True)} == {triggerings[0].triggering_uuid, triggerings[2].triggering_uuid}


@pytest.mark.parametrize("method", ["get_rules", "get_tasks", "get_triggerings"])
@pytest.mark.parametrize("argument", ["limit", "offset"])
def test_invalid_pagination_is_rejected(agenda, method, argument):
    query, *_ = agenda
    with pytest.raises(InputError):
        getattr(query, method)(**{argument: -1})


def test_clear_database_removes_all_scheduler_entities(agenda):
    query, *_ = agenda
    query.close_session()
    query.clear_db()
    assert query.get_triggerings() == []
    assert query.get_tasks() == []
    assert query.get_rules() == []


def test_query_logging_tolerates_unsupported_literals(monkeypatch, store):
    def unsupported(statement):
        raise NotImplementedError("unsupported literal")
    monkeypatch.setattr(query_module, "literal_query", unsupported)
    assert store.query.get_rules() == []


def test_caller_supplied_session_keeps_uncommitted_changes_in_its_transaction(store):
    session = store.factory()
    rule = Rule(uuid4(), "uncommitted", 1, 0, 1)
    session.add(rule)
    query = query_module.Query(session=session)
    assert query.get_rules(names={"filter": "uncommitted", "op": "=="}) == [rule]
    session.rollback()
    assert query.get_rules() == []
    query.close_session()
