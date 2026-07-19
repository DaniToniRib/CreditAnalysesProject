import json
import logging
import logging.config
from datetime import datetime, timezone

from app.config import get_settings


class JSONFormatter(logging.Formatter):
    """Uma linha JSON por evento de log — formato padrão para ingestão por
    ferramentas de SIEM (ex.: Cortex XSIAM) que coletam stdout/journald do
    container. Evita depender de uma lib externa (`python-json-logger`) para
    algo simples o bastante para fazer à mão."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    settings = get_settings()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": JSONFormatter},
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "json"},
            },
            "root": {"handlers": ["console"], "level": settings.log_level},
        }
    )
