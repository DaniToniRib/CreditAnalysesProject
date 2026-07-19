import json
import logging

from app.logging_config import JSONFormatter


def _make_record(level=logging.INFO, msg="hello", exc_info=None) -> logging.LogRecord:
    return logging.LogRecord(
        name="app.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )


def test_json_formatter_produces_valid_json_with_expected_fields():
    formatter = JSONFormatter()
    output = formatter.format(_make_record(msg="pedido %s analisado"))

    payload = json.loads(output)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "pedido %s analisado"
    assert "timestamp" in payload
    assert "exception" not in payload


def test_json_formatter_includes_exception_when_present():
    try:
        raise ValueError("falha simulada")
    except ValueError:
        import sys

        record = _make_record(level=logging.ERROR, msg="erro ao processar", exc_info=sys.exc_info())

    formatter = JSONFormatter()
    payload = json.loads(formatter.format(record))

    assert "exception" in payload
    assert "ValueError" in payload["exception"]
    assert "falha simulada" in payload["exception"]
