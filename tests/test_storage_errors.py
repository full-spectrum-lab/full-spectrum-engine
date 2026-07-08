#!/usr/bin/env python3
"""
v0.6 错误处理 + 数据最小化测试 (ERR-01a, ERR-01b, ERR-02, ERR-03, ERR-04, SEC-01, SEC-02, SEC-03)

rc2 更新：
    - SEC-02 修复：include_input_metrics=true 时验证 DB 实际包含 input_metrics（MH-BUG-v0.6-001）
    - SEC-03 新增：header/body/DB 三者一致性测试

测试覆盖：
    - DB 文件损坏
    - DB 表结构损坏
    - DB 只读
    - 非法分页参数
    - DELETE 安全阀（缺 confirm / 缺 before/all / 非本地绑定）
    - 数据最小化：include_input_metrics=false 时 DB 不含 input_metrics
    - 数据最小化：include_input_metrics=true 时 DB 包含 input_metrics（rc2 修复）
    - 一致性：header/body/DB 三者一致（rc2 新增）
"""

import json
import os
import sys
import tempfile
import unittest
import uuid

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi.testclient import TestClient
from src.api.server import create_app
from src.storage.backend import StorageBackend

_TEST_DB_DIR = tempfile.mkdtemp(prefix="fse_test_err_")


def _make_db_path():
    return os.path.join(_TEST_DB_DIR, f"test_{uuid.uuid4().hex[:8]}.db")


def _load_conflict_metrics():
    with open(os.path.join(_PROJECT_ROOT, "examples", "metrics_ecommerce_conflict.json"), encoding="utf-8") as f:
        return json.load(f)["metrics"]


class TestDbFileCorrupt(unittest.TestCase):
    """ERR-01a: DB 文件内容损坏"""

    def test_db_file_corrupt(self):
        db_path = _make_db_path()

        # 写入随机字节（模拟损坏的 DB 文件）
        with open(db_path, "wb") as f:
            f.write(b"Not a valid SQLite database file content")

        # 尝试打开损坏的 DB
        with self.assertRaises(Exception):
            StorageBackend(db_path=db_path)


class TestDbTableMissing(unittest.TestCase):
    """ERR-01b: DB 表结构损坏"""

    def test_db_table_missing(self):
        db_path = _make_db_path()
        storage = StorageBackend(db_path=db_path)

        # 写入一条记录
        storage.save_decision(
            decision_id="DEC_TEST_001",
            simulation_id="SIM_001",
            runestone_id="RS_TEST_001",
            result={"test": "data", "runestone": {"runestone_id": "RS_TEST_001"}},
            seed=42,
        )

        # 模拟表结构损坏：DROP TABLE
        storage._conn.execute("DROP TABLE IF EXISTS decisions")
        storage._conn.execute("DROP TABLE IF EXISTS runestones")
        storage._conn.commit()

        # 查询应抛出异常（不自动重建）
        with self.assertRaises(Exception):
            storage.get_decision("DEC_TEST_001")

        storage.close()


class TestDbReadonly(unittest.TestCase):
    """ERR-02: DB 只读时写入失败"""

    def test_db_readonly(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        storage = app.state.storage

        # 先写入一条正常记录
        storage.save_decision(
            decision_id="DEC_READONLY_001",
            simulation_id="SIM_001",
            runestone_id="RS_READONLY_001",
            result={"test": "data", "runestone": {"runestone_id": "RS_READONLY_001"}},
            seed=42,
        )

        # 关闭连接，以只读模式重新打开（URI 方式）
        storage.close()
        import sqlite3 as _sqlite3
        readonly_conn = _sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        # 尝试写入应失败（只读模式）
        with self.assertRaises(_sqlite3.OperationalError):
            readonly_conn.execute(
                "INSERT INTO decisions VALUES ('DEC_READONLY_002', 'SIM_002', 'RS_002', '{}', '2026-01-01T00:00:00Z', NULL, 42)"
            )
        readonly_conn.close()


class TestInvalidAuditParams(unittest.TestCase):
    """ERR-03: 非法分页参数"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)

    def test_invalid_limit_zero(self):
        resp = self.client.get("/api/v1/audit/decisions?limit=0")
        self.assertEqual(resp.status_code, 422)

    def test_invalid_limit_too_large(self):
        resp = self.client.get("/api/v1/audit/decisions?limit=200")
        self.assertEqual(resp.status_code, 422)

    def test_invalid_offset_negative(self):
        resp = self.client.get("/api/v1/audit/decisions?offset=-1")
        self.assertEqual(resp.status_code, 422)


class TestCleanupSafetyValves(unittest.TestCase):
    """ERR-04: DELETE 安全阀测试"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path, bind_host="127.0.0.1")
        cls.client = TestClient(cls.app)
        # 写入一些数据
        storage = cls.app.state.storage
        storage.save_decision(
            decision_id="DEC_SAFETY_001",
            simulation_id="SIM_001",
            runestone_id="RS_SAFETY_001",
            result={"test": "data", "runestone": {"runestone_id": "RS_SAFETY_001"}},
            seed=42,
        )

    def test_cleanup_missing_confirm(self):
        """缺 confirm=true 返回 422"""
        resp = self.client.delete("/api/v1/audit/decisions?before=2026-07-04T00:00:00Z")
        self.assertEqual(resp.status_code, 422)

    def test_cleanup_missing_before_and_all(self):
        """缺 before/all 返回 422"""
        resp = self.client.delete("/api/v1/audit/decisions?confirm=true")
        self.assertEqual(resp.status_code, 422)

    def test_cleanup_non_local_binding(self):
        """非本地绑定返回 403"""
        db_path = _make_db_path()
        app = create_app(db_path=db_path, bind_host="0.0.0.0")
        client = TestClient(app)
        resp = client.delete("/api/v1/audit/decisions?all=true&confirm=true")
        self.assertEqual(resp.status_code, 403)


class TestPersistExcludesInputMetrics(unittest.TestCase):
    """SEC-01: include_input_metrics=false 时 DB result_json 不含 input_metrics"""

    def test_persist_excludes_input_metrics_by_default(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        metrics = _load_conflict_metrics()

        # 默认 include_input_metrics=false
        resp = client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": metrics,
            "seed": 42,
        })
        self.assertEqual(resp.status_code, 200)
        decision_id = resp.headers.get("x-decision-id")

        # 查询 DB 中的 result_json
        storage = app.state.storage
        result = storage.get_decision(decision_id)
        self.assertIsNotNone(result)

        # DB 中不应包含 input_metrics
        self.assertNotIn("input_metrics", result,
                          "DB result_json must NOT contain input_metrics when include_input_metrics=false")

        # X-Input-Metrics-Persisted header should be false
        self.assertEqual(resp.headers.get("x-input-metrics-persisted"), "false")


class TestPersistIncludesInputMetricsWhenExplicitTrue(unittest.TestCase):
    """SEC-02: include_input_metrics=true 时 DB result_json 包含 input_metrics（rc2 修复 MH-BUG-v0.6-001）"""

    def test_persist_includes_input_metrics_when_explicit_true(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        metrics = _load_conflict_metrics()

        # 显式 include_input_metrics=true
        resp = client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": metrics,
            "seed": 42,
            "include_input_metrics": True,
        })
        self.assertEqual(resp.status_code, 200)
        decision_id = resp.headers.get("x-decision-id")

        # NFR-16: X-Input-Metrics-Persisted header should be true
        self.assertEqual(resp.headers.get("x-input-metrics-persisted"), "true")

        # API response body 应包含 input_metrics
        resp_body = resp.json()
        self.assertIn("input_metrics", resp_body,
                      "API response body must contain input_metrics when include_input_metrics=true")
        # 验证 input_metrics 包含原始指标字段（如 refund_rate）
        self.assertIn("refund_rate", resp_body["input_metrics"],
                      "input_metrics must contain raw metric names like 'refund_rate'")

        # 查询 DB 中的 result_json — 必须包含 input_metrics
        storage = app.state.storage
        result = storage.get_decision(decision_id)
        self.assertIsNotNone(result)
        self.assertIn("input_metrics", result,
                      "DB result_json must contain input_metrics when include_input_metrics=true")
        self.assertIn("refund_rate", result["input_metrics"],
                      "DB input_metrics must contain raw metric names like 'refund_rate'")

        # header-body-DB 三者一致性
        self.assertEqual(
            resp.headers.get("x-input-metrics-persisted"), "true",
            "Header must be true when DB contains input_metrics"
        )
        self.assertIn("input_metrics", resp_body, "Body must contain input_metrics when header is true")
        self.assertIn("input_metrics", result, "DB must contain input_metrics when header is true")


class TestHeaderBodyDbConsistency(unittest.TestCase):
    """SEC-03: X-Input-Metrics-Persisted header / API body / DB result_json 三者一致性（rc2 新增）"""

    def test_consistency_when_false(self):
        """include_input_metrics=false 时：header=false, body 不含, DB 不含"""
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        metrics = _load_conflict_metrics()

        resp = client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": metrics,
            "seed": 42,
        })
        self.assertEqual(resp.status_code, 200)
        decision_id = resp.headers.get("x-decision-id")

        # header = false
        self.assertEqual(resp.headers.get("x-input-metrics-persisted"), "false")
        # body 不含 input_metrics
        self.assertNotIn("input_metrics", resp.json())
        # DB 不含 input_metrics
        result = app.state.storage.get_decision(decision_id)
        self.assertNotIn("input_metrics", result)

    def test_consistency_when_true(self):
        """include_input_metrics=true 时：header=true, body 含, DB 含"""
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        metrics = _load_conflict_metrics()

        resp = client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": metrics,
            "seed": 42,
            "include_input_metrics": True,
        })
        self.assertEqual(resp.status_code, 200)
        decision_id = resp.headers.get("x-decision-id")

        # header = true
        self.assertEqual(resp.headers.get("x-input-metrics-persisted"), "true")
        # body 含 input_metrics
        self.assertIn("input_metrics", resp.json())
        # DB 含 input_metrics
        result = app.state.storage.get_decision(decision_id)
        self.assertIn("input_metrics", result)


if __name__ == "__main__":
    unittest.main()
