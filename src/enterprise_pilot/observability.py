#!/usr/bin/env python3
"""
C-06 结构化日志 / 健康 / 指标（FR-06 / C-06）。

设计（共享知识 §8 衍生）：
  * StructuredLogger：结构化（JSON）日志，便于受控环境留痕。
  * HealthCheck：扩展 /health（独立 v1.5 端点 + CLI）。
  * Metrics：处理数 / 失败数计数（线程安全）。
标准库实现，无新第三方依赖。
"""
import json
import logging
import threading

PILOT_VERSION = "1.5.0"


class StructuredLogger:
    """结构化（JSON 行）日志记录器。"""

    def __init__(self, name="enterprise_pilot", level=logging.INFO):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(level)
            self._logger.propagate = False

    def log(self, level, event, ctx=None):
        lvl = level.upper() if isinstance(level, str) else level
        if isinstance(lvl, str):
            lvl = logging.getLevelName(lvl)
        record = {"event": event, "ctx": ctx or {}}
        self._logger.log(lvl, json.dumps(record, ensure_ascii=False))


class HealthCheck:
    """健康探针（扩展 /health 语义）。"""

    def __init__(self, extra=None):
        self._extra = extra or {}

    def status(self):
        return {
            "status": "ok",
            "component": "enterprise_pilot",
            "version": PILOT_VERSION,
            "pilot_enabled": True,
            **self._extra,
        }


class Metrics:
    """线程安全计数器：处理数 / 失败数。"""

    def __init__(self):
        self._processed = 0
        self._failed = 0
        self._lock = threading.Lock()

    def inc_processed(self):
        with self._lock:
            self._processed += 1

    def inc_failed(self):
        with self._lock:
            self._failed += 1

    def snapshot(self):
        with self._lock:
            return {
                "processed": self._processed,
                "failed": self._failed,
                "version": PILOT_VERSION,
            }


_default_metrics = Metrics()


def health(extra=None):
    """门面函数（§4.2 签名）。"""
    return HealthCheck(extra).status()


def metrics_snapshot():
    """门面函数（§4.2 签名）。"""
    return _default_metrics.snapshot()
