#!/usr/bin/env python3
"""
C-05 幂等 / 重试 / 超时 / 失败可恢复（FR-05 / C-05）。

设计（共享知识 §8.7）：
  * 关键操作带 ``IdempotencyKey``；``RetryPolicy`` / ``Timeout`` 包裹；
  * 失败回滚至操作前快照，绝不写半截结果（红线衍生：无半成品污染）。
标准库实现（concurrent.futures 跨平台超时），无新第三方依赖。
"""
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from src.governance_chain.envelope import canonical_json


class ResilienceError(Exception):
    code = "RESILIENCE"


class TimeoutErrorR(ResilienceError):
    code = "TIMEOUT"


class IdempotencyKey:
    """幂等键：对请求体做确定性 SHA-256。"""

    @staticmethod
    def compute(payload):
        # hashlib_sha256() already returns a hex digest string.
        digest = hashlib_sha256(canonical_json(payload).encode("utf-8"))
        return "idem_" + digest[:24]


class RetryPolicy:
    """简单重试策略（指数退避可选）。"""

    def __init__(self, max_attempts=3, backoff=0.0, swallow=()):
        self.max_attempts = max_attempts
        self.backoff = backoff
        self.swallow = tuple(swallow)

    def run(self, fn, *args, **kwargs):
        last = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last = exc
                if isinstance(exc, self.swallow):
                    raise
                if attempt < self.max_attempts:
                    if self.backoff:
                        time.sleep(self.backoff)
                    continue
        raise last


class Timeout:
    """跨平台超时包裹（线程池实现，避免 Windows 上 signal.SIGALRM 不可用）。"""

    def __init__(self, seconds=5.0):
        self.seconds = seconds

    def run(self, fn, *args, **kwargs):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=self.seconds)
        except FuturesTimeoutError:
            # Executor context-manager exit waits for running work.  That made
            # a nominal timeout block until the slow operation completed.
            future.cancel()
            raise TimeoutErrorR(f"operation exceeded {self.seconds}s")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)


def with_retry(fn, policy, *args, **kwargs):
    return policy.run(fn, *args, **kwargs)


def with_timeout(fn, timeout, *args, **kwargs):
    return timeout.run(fn, *args, **kwargs)


def run_resilient(fn, *, snapshot, rollback, args=None, kwargs=None):
    """执行 ``fn``；异常时回滚到操作前快照，绝不写半截结果；成功返回结果。

    snapshot: 可调用（返回快照）或快照值。rollback: 可调用(snapshot) 执行回滚。
    """
    snap = snapshot() if callable(snapshot) else snapshot
    try:
        return fn(*(args or ()), **(kwargs or {}))
    except Exception:
        if callable(rollback):
            rollback(snap)
        raise


def hashlib_sha256(data):
    import hashlib

    return hashlib.sha256(data).hexdigest()
