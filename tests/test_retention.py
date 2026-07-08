#!/usr/bin/env python3
"""
v0.6 数据保留策略测试 (TTL-01 ~ TTL-05)

5 个测试，覆盖：
    - TTL 自动过期
    - 自定义 TTL 值
    - 容量上限触发清理
    - DELETE 端点按时间清理
    - DELETE 端点全量清理
"""

import json
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi.testclient import TestClient
from src.api.server import create_app
from src.storage.backend import StorageBackend

_TEST_DB_DIR = tempfile.mkdtemp(prefix="fse_test_retention_")


def _make_db_path():
    return os.path.join(_TEST_DB_DIR, f"test_{uuid.uuid4().hex[:8]}.db")


class TestTtlAutoExpire(unittest.TestCase):
    """TTL-01: 超过 TTL 的记录自动过期"""

    def test_ttl_auto_expire(self):
        db_path = _make_db_path()
        storage = StorageBackend(db_path=db_path, ttl_days=1)

        # 写入一条记录
        storage.save_decision(
            decision_id="DEC_TTL_001",
            simulation_id="SIM_001",
            runestone_id="RS_TTL_001",
            result={"test": "data", "runestone": {"runestone_id": "RS_TTL_001"}},
            seed=42,
        )

        # 修改 created_at 为过去（3 天前）
        old_time = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        storage._conn.execute(
            "UPDATE decisions SET created_at = ? WHERE decision_id = ?",
            (old_time, "DEC_TTL_001"),
        )
        storage._conn.execute(
            "UPDATE runestones SET created_at = ? WHERE runestone_id = ?",
            (old_time, "RS_TTL_001"),
        )
        storage._conn.commit()

        # 触发 TTL 清理
        deleted = storage.cleanup_ttl(ttl_days=1)
        self.assertGreater(deleted, 0)

        # 验证记录已被删除
        result = storage.get_decision("DEC_TTL_001")
        self.assertIsNone(result)

        storage.close()


class TestTtlCustomValue(unittest.TestCase):
    """TTL-02: 自定义 TTL 值"""

    def test_ttl_custom_value(self):
        db_path = _make_db_path()
        storage = StorageBackend(db_path=db_path, ttl_days=7)

        # 写入记录
        storage.save_decision(
            decision_id="DEC_TTL_CUSTOM_001",
            simulation_id="SIM_001",
            runestone_id="RS_TTL_CUSTOM_001",
            result={"test": "data", "runestone": {"runestone_id": "RS_TTL_CUSTOM_001"}},
            seed=42,
        )

        # 修改为 10 天前（超过 7 天 TTL）
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        storage._conn.execute(
            "UPDATE decisions SET created_at = ? WHERE decision_id = ?",
            (old_time, "DEC_TTL_CUSTOM_001"),
        )
        storage._conn.execute(
            "UPDATE runestones SET created_at = ? WHERE runestone_id = ?",
            (old_time, "RS_TTL_CUSTOM_001"),
        )
        storage._conn.commit()

        deleted = storage.cleanup_ttl(ttl_days=7)
        self.assertGreater(deleted, 0)

        storage.close()


class TestCapacityCap(unittest.TestCase):
    """TTL-03: 容量上限触发清理"""

    def test_capacity_cap(self):
        db_path = _make_db_path()
        storage = StorageBackend(db_path=db_path, max_records=3)

        # 写入 5 条记录
        for i in range(5):
            storage.save_decision(
                decision_id=f"DEC_CAP_{i:03d}",
                simulation_id=f"SIM_{i}",
                runestone_id=f"RS_CAP_{i:03d}",
                result={"test": f"data_{i}", "runestone": {"runestone_id": f"RS_CAP_{i:03d}"}},
                seed=42,
            )

        # 容量上限为 3，应该只保留最新 3 条
        stats = storage.get_stats()
        self.assertLessEqual(stats["decision_count"], 3)

        # 最旧的记录应被删除
        oldest = storage.get_decision("DEC_CAP_000")
        self.assertIsNone(oldest, "Oldest record should be deleted by capacity cap")

        # 最新记录应存在
        newest = storage.get_decision("DEC_CAP_004")
        self.assertIsNotNone(newest, "Newest record should still exist")

        storage.close()


class TestCleanupEndpoint(unittest.TestCase):
    """TTL-04: DELETE /api/v1/audit/decisions?before=...&confirm=true"""

    def test_cleanup_endpoint(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        storage = app.state.storage

        # 写入记录
        storage.save_decision(
            decision_id="DEC_CLEANUP_001",
            simulation_id="SIM_001",
            runestone_id="RS_CLEANUP_001",
            result={"test": "data", "runestone": {"runestone_id": "RS_CLEANUP_001"}},
            seed=42,
        )

        # 修改 created_at 为过去
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        storage._conn.execute(
            "UPDATE decisions SET created_at = ? WHERE decision_id = ?",
            (old_time, "DEC_CLEANUP_001"),
        )
        storage._conn.execute(
            "UPDATE runestones SET created_at = ? WHERE runestone_id = ?",
            (old_time, "RS_CLEANUP_001"),
        )
        storage._conn.commit()

        # 执行清理
        before_time = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        resp = client.delete(f"/api/v1/audit/decisions?before={before_time}&confirm=true")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("deleted_decisions", data)
        self.assertIn("deleted_runestones", data)
        self.assertGreater(data["deleted_decisions"], 0)


class TestCleanupAll(unittest.TestCase):
    """TTL-05: DELETE /api/v1/audit/decisions?all=true&confirm=true"""

    def test_cleanup_all(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        storage = app.state.storage

        # 写入多条记录
        for i in range(3):
            storage.save_decision(
                decision_id=f"DEC_ALL_{i:03d}",
                simulation_id=f"SIM_{i}",
                runestone_id=f"RS_ALL_{i:03d}",
                result={"test": f"data_{i}", "runestone": {"runestone_id": f"RS_ALL_{i:03d}"}},
                seed=42,
            )

        stats_before = storage.get_stats()
        self.assertGreater(stats_before["decision_count"], 0)

        # 全量清理
        resp = client.delete("/api/v1/audit/decisions?all=true&confirm=true")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["deleted_decisions"], 0)

        # 验证全部清除
        stats_after = storage.get_stats()
        self.assertEqual(stats_after["decision_count"], 0)


if __name__ == "__main__":
    unittest.main()
