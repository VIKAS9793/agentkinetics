from __future__ import annotations

import json
import logging
import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator


_trace_id: ContextVar[str] = ContextVar("trace_id", default="system")
_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})

_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "password",
        "password_hash",
        "password_salt",
        "secret",
        "token",
        "x-session-token",
    }
)
_MAX_STRING_LENGTH = 256
_MAX_COLLECTION_ITEMS = 12


def _sanitize_for_logs(value: Any, key: str | None = None) -> Any:
    lowered_key = key.lower() if key is not None else ""
    if lowered_key in _SENSITIVE_KEYS:
        return "***"
    if isinstance(value, dict):
        return {
            str(item_key): _sanitize_for_logs(item_value, key=str(item_key))
            for item_key, item_value in list(value.items())[:_MAX_COLLECTION_ITEMS]
        }
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        sanitized = [_sanitize_for_logs(item) for item in items[:_MAX_COLLECTION_ITEMS]]
        if len(items) > _MAX_COLLECTION_ITEMS:
            sanitized.append(f"...(+{len(items) - _MAX_COLLECTION_ITEMS} more)")
        return sanitized
    if isinstance(value, str):
        if len(value) <= _MAX_STRING_LENGTH:
            return value
        return f"{value[:_MAX_STRING_LENGTH]}...(+{len(value) - _MAX_STRING_LENGTH} chars)"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


def _current_context() -> dict[str, Any]:
    current = _log_context.get()
    return dict(current)


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(trace_id)s] [%(name)s] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _get_extra(self) -> dict[str, str]:
        return {"trace_id": _trace_id.get()}

    def _render(self, message: str, **kwargs: Any) -> str:
        merged = _current_context()
        merged.update(kwargs)
        if not merged:
            return message
        safe_payload = {
            key: _sanitize_for_logs(value, key=key)
            for key, value in sorted(merged.items(), key=lambda item: item[0])
        }
        return f"{message} | {json.dumps(safe_payload, sort_keys=True, default=str)}"

    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(self._render(message, **kwargs), extra=self._get_extra())

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(self._render(message, **kwargs), extra=self._get_extra())

    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(self._render(message, **kwargs), extra=self._get_extra())

    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        self.logger.error(self._render(message, **kwargs), extra=self._get_extra(), exc_info=exc_info)


def set_trace_id(trace_id: str | None = None) -> str:
    resolved_trace_id = trace_id or str(uuid.uuid4())[:8]
    _trace_id.set(resolved_trace_id)
    return resolved_trace_id


def bind_log_context(**kwargs: Any) -> Token[dict[str, Any]]:
    current = _current_context()
    current.update(kwargs)
    return _log_context.set(current)


def reset_log_context(token: Token[dict[str, Any]]) -> None:
    _log_context.reset(token)


@contextmanager
def log_context(**kwargs: Any) -> Iterator[None]:
    token = bind_log_context(**kwargs)
    try:
        yield
    finally:
        reset_log_context(token)


def clear_log_context() -> None:
    _log_context.set({})


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
