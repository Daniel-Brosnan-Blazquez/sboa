"""Verify SBOA logging configuration."""
import json
import logging
import uuid

import pytest

from sboa.logging import Log, RotatingFileHandlerAllUsers


@pytest.fixture
def logger_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("SBOA_LOG_PATH", str(tmp_path / "logs"))
    for key in ("SBOA_LOG_LEVEL", "SBOA_LOG_MAX_BYTES", "SBOA_LOG_MAX_BACKUP", "SBOA_STREAM_LOG"):
        monkeypatch.delenv(key, raising=False)
    name = "sboa.test." + uuid.uuid4().hex
    yield name, tmp_path
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def test_rotate_sboa_log_configure_by_env(logger_setup, monkeypatch):
    name, directory = logger_setup
    monkeypatch.setenv("SBOA_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SBOA_LOG_MAX_BYTES", "2000")
    monkeypatch.setenv("SBOA_LOG_MAX_BACKUP", "3")
    monkeypatch.setenv("BOA_LOG_LEVEL", "ERROR")
    logger = Log(name=name).logger
    handler, = [handler for handler in logger.handlers if isinstance(handler, RotatingFileHandlerAllUsers)]
    assert logger.level == logging.DEBUG
    assert handler.maxBytes == 2000
    assert handler.backupCount == 3
    for index in range(100):
        logger.debug("TESTING LOG ROTATION %s", index)
    assert (directory / "logs/sboa_engine.log.1").is_file()
    assert not (directory / "logs/sboa_engine.log.4").exists()


def test_rotate_sboa_log_configure_by_json(logger_setup, monkeypatch):
    name, directory = logger_setup
    config = directory / "config"
    config.mkdir()
    (config / "engine.json").write_text(json.dumps({"LOG": {"LEVEL": "INFO", "MAX_BYTES": 512, "MAX_BACKUP": 2}}))
    monkeypatch.setenv("SBOA_RESOURCES_PATH", str(config))
    logger = Log(name=name).logger
    handler, = [handler for handler in logger.handlers if isinstance(handler, RotatingFileHandlerAllUsers)]
    assert logger.level == logging.INFO
    assert handler.maxBytes == 512
    assert handler.backupCount == 2
    for index in range(100):
        logger.info("TESTING JSON LOG ROTATION %s", index)
    assert (directory / "logs/sboa_engine.log.1").is_file()
    assert not (directory / "logs/sboa_engine.log.3").exists()


def test_custom_debug_level_and_stream_logging(logger_setup, monkeypatch, capsys):
    name, _ = logger_setup
    monkeypatch.setenv("SBOA_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SBOA_STREAM_LOG", "1")
    logger = Log(name=name).logger
    logger.debugi("scheduler profiling")
    assert "scheduler profiling" in capsys.readouterr().err
