#!/usr/bin/env python3
"""
v0.6 向后兼容性测试 (COMP-01 ~ COMP-04)

4 个测试，覆盖：
    - v0.5 evaluate 请求格式不变
    - v0.5 runestone 请求格式不变
    - health 端点向后兼容
    - decision_id 格式不变
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

_TEST_DB_DIR = tempfile.mkdtemp(prefix="fse_test_compat_")


def _make_db_path():
    return os.path.join(_TEST_DB_DIR, f"test_{uuid.uuid4().hex[:8]}.db")


def _load_scenario():
    with open(os.path.join(_PROJECT_ROOT, "examples", "scenario_refund_conflict.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_conflict_metrics():
    with open(os.path.join(_PROJECT_ROOT, "examples", "metrics_ecommerce_conflict.json"), encoding="utf-8") as f:
        return json.load(f)["metrics"]


class TestV05EvaluateUnchanged(unittest.TestCase):
    """COMP-01: v0.5 evaluate 请求格式不变"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)
        cls.scenario = _load_scenario()
        cls.metrics = _load_conflict_metrics()

    def test_v05_evaluate_direct_mode_unchanged(self):
        """直接模式请求格式不变"""
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # 验证 v0.5 body 结构
        self.assertIn("simulation_id", body)
        self.assertIn("fshi", body)
        self.assertIn("runestone", body)

    def test_v05_evaluate_adapter_mode_unchanged(self):
        """适配器模式请求格式不变"""
        resp = self.client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": self.metrics,
            "seed": 42,
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("simulation_id", body)
        self.assertIn("fshi", body)


class TestV05RunestoneUnchanged(unittest.TestCase):
    """COMP-02: v0.5 runestone 请求格式不变"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)

    def test_v05_runestone_unchanged(self):
        resp = self.client.post("/api/v1/runestone", json={
            "decision": "W3",
            "reason": {"enterprise_id": "test_ent", "rule_version": "v0.3"},
            "risk_vector": {
                "survival_impact": 0.3, "trust_impact": 0.2, "meaning_impact": 0.1,
                "reversibility": 0.5, "explainability": 0.8, "diffusivity": 0.4,
                "urgency": 0.6, "uncertainty": 0.3,
            },
            "seed": 42,
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # v0.5 runestone 结构：10 字段
        self.assertIn("runestone_id", body)
        self.assertIn("decision", body)
        self.assertIn("reason", body)
        self.assertIn("risk_vector", body)


class TestV05HealthBackwardCompatible(unittest.TestCase):
    """COMP-03: health 端点原有字段保留，storage_mode 更新"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)

    def test_v05_health_backward_compatible(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # v0.5 原有字段保留
        self.assertIn("status", data)
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)
        self.assertIn("engine_version", data)
        self.assertIn("registered_adapters", data)
        self.assertIn("network_exposure", data)

        # storage_mode 更新为 sqlite-persistent
        self.assertEqual(data["storage_mode"], "sqlite-persistent")

        # v0.6 新增字段
        self.assertIn("db_path", data)
        self.assertIn("db_size_bytes", data)
        self.assertIn("decision_count", data)
        self.assertIn("runestone_count", data)
        self.assertIn("ttl_days", data)
        self.assertIn("max_records", data)


class TestV05DecisionIdFormat(unittest.TestCase):
    """COMP-04: decision_id 格式不变（DEC_ 前缀）"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)
        cls.scenario = _load_scenario()

    def test_v05_decision_id_format(self):
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        decision_id = resp.headers.get("x-decision-id")
        self.assertIsNotNone(decision_id)
        self.assertTrue(decision_id.startswith("DEC_"))


if __name__ == "__main__":
    unittest.main()
