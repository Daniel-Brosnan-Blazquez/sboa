"""Invalid public query inputs and logging failure paths from the coverage report."""
import logging
from unittest.mock import Mock

import pytest

from sboa import debugging
from sboa.engine import functions
from sboa.engine.errors import InputError, SboaLogPathNotAvailable
from sboa.logging import Log


@pytest.mark.parametrize("validator,value", [
    (functions.is_valid_order_by, []),
    (functions.is_valid_order_by, {"field": 123, "descending": False}),
    (functions.is_valid_order_by, {"field": "name", "unexpected": False}),
    (functions.is_valid_date_filters, {}),
    (functions.is_valid_date_filters, ["2026-11-16"]),
    (functions.is_valid_date_filters, [{"date": "2026-11-16"}]),
    (functions.is_valid_date_filters, [{"other": "2026-11-16", "op": "=="}]),
    (functions.is_valid_float_filters, {}),
    (functions.is_valid_float_filters, [1]),
    (functions.is_valid_float_filters, [{"float": 1}]),
    (functions.is_valid_float_filters, [{"other": 1, "op": "=="}]),
    (functions.is_valid_float_filters, [{"float": 1, "op": "unknown"}]),
    (functions.is_valid_text_filter, "name"),
    (functions.is_valid_text_filter, {"filter": "name"}),
    (functions.is_valid_text_filter, {"other": "name", "op": "=="}),
    (functions.is_valid_text_filter, {"filter": 3, "op": "=="}),
    (functions.is_valid_text_filter, {"filter": "name", "op": "in"}),
])
def test_malformed_filter_structures_raise_input_error(validator, value):
    with pytest.raises(InputError):
        validator(value)


def test_log_directory_cannot_be_a_file(tmp_path, monkeypatch):
    path = tmp_path / "file"
    path.touch()
    monkeypatch.setenv("SBOA_LOG_PATH", str(path))
    with pytest.raises(SboaLogPathNotAvailable) as raised:
        functions.get_log_path()
    assert isinstance(raised.value.__cause__, OSError)


def test_profiling_logs_elapsed_time_in_debug_mode(monkeypatch):
    logger = Mock(level=logging.DEBUG)
    monkeypatch.setattr(debugging, "logger", logger)

    @debugging.debug
    def total(first, second=0):
        return first + second

    assert total(3, second=4) == 7
    assert "lasted" in logger.debug.call_args.args[0]


def test_logger_defaults_stream_reconfiguration_and_disabled_custom_level(tmp_path, monkeypatch):
    monkeypatch.setenv("SBOA_LOG_PATH", str(tmp_path))
    monkeypatch.setenv("SBOA_STREAM_LOG", "1")
    wrapper = Log()
    logger = wrapper.logger
    try:
        wrapper.define_logging_configuration()
        streams = [handler for handler in logger.handlers if type(handler) is logging.StreamHandler]
        assert len(streams) == 1
        monkeypatch.delenv("SBOA_STREAM_LOG")
        wrapper.define_logging_configuration()
        assert not any(type(handler) is logging.StreamHandler for handler in logger.handlers)
        logger.setLevel(logging.CRITICAL)
        logger.debugi("this message is disabled")
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
