#!/usr/bin/env python3
"""
v0.6 审计查询端点测试 (AUD-01 ~ AUD-06)

6 个测试，覆盖：
    - 符石列表查询
    - 列表分页 limit
    - 列表分页 offset
    - 时间范围过滤 since
    - 符石 404
    - 决策列表查询
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

_TEST_DB_DIR = tempfile.mkdtemp(prefix="fse_test_audit_")


def _make_db_path():
    return os.path.join(_TEST_DB_DIR, f"test_{uuid.uuid4().hex[:8]}.db")


def _load_scenario():
    with open(os.path.join(_PROJECT_ROOT, "examples", "scenario_refund_conflict.json"), encoding="utf-8") as f:
        return json.load(f)


def _make_runestone_request(seed=42):
    return {
        "decision": "W3",
        "reason": {"enterprise_id": "test_ent", "rule_version": "v0.3"},
        "risk_vector": {
            "survival_impact": 0.3, "trust_impact": 0.2, "meaning_impact": 0.1,
            "reversibility": 0.5, "explainability": 0.8, "diffusivity": 0.4,
            "urgency": 0.6, "uncertainty": 0.3,
        },
        "seed": seed,
    }


class TestAuditRunestoneList(unittest.TestCase):
    """AUD-01: GET /api/v1/audit/runestones 返回列表"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)
        # 写入几条 runestone
        for i in range(3):
            cls.client.post("/api/v1/runestone", json=_make_runestone_request(seed=42 + i))

    def test_audit_runestone_list(self):
        resp = self.client.get("/api/v1/audit/runestones")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertIn("limit", data)
        self.assertIn("offset", data)
        self.assertGreaterEqual(data["total"], 3)


class TestAuditRunestoneListLimit(unittest.TestCase):
    """AUD-02: 列表分页参数 limit"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)
        for i in range(5):
            cls.client.post("/api/v1/runestone", json=_make_runestone_request(seed=42 + i))

    def test_audit_runestone_list_default_limit(self):
        resp = self.client.get("/api/v1/audit/runestones")
        data = resp.json()
        self.assertEqual(data["limit"], 20)

    def test_audit_runestone_list_custom_limit(self):
        resp = self.client.get("/api/v1/audit/runestones?limit=2")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["items"]), 2)

    def test_audit_runestone_list_limit_too_large(self):
        resp = self.client.get("/api/v1/audit/runestones?limit=200")
        self.assertEqual(resp.status_code, 422)

    def test_audit_runestone_list_limit_zero(self):
        resp = self.client.get("/api/v1/audit/runestones?limit=0")
        self.assertEqual(resp.status_code, 422)


class TestAuditRunestoneListOffset(unittest.TestCase):
    """AUD-03: 列表分页参数 offset"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)
        for i in range(5):
            cls.client.post("/api/v1/runestone", json=_make_runestone_request(seed=42 + i))

    def test_audit_runestone_list_offset(self):
        resp_all = self.client.get("/api/v1/audit/runestones?limit=100")
        all_items = resp_all.json()["items"]

        resp_offset = self.client.get("/api/v1/audit/runestones?limit=2&offset=1")
        self.assertEqual(resp_offset.status_code, 200)
        offset_items = resp_offset.json()["items"]
        self.assertEqual(len(offset_items), 2)
        # offset=1 应跳过第一条
        self.assertEqual(offset_items[0], all_items[1])


class TestAuditRunestoneTimeFilter(unittest.TestCase):
    """AUD-04: 时间范围过滤（since 参数）"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)
        cls.client.post("/api/v1/runestone", json=_make_runestone_request(seed=42))

    def test_audit_runestone_time_filter_since(self):
        # 用一个过去时间查询，应该能查到
        resp = self.client.get("/api/v1/audit/runestones?since=2020-01-01T00:00:00Z")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total"], 1)

    def test_audit_runestone_time_filter_invalid_format(self):
        resp = self.client.get("/api/v1/audit/runestones?since=not-a-date")
        self.assertEqual(resp.status_code, 422)


class TestAuditRunestone404(unittest.TestCase):
    """AUD-05: 查询不存在的 runestone_id 返回 404"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)

    def test_audit_runestone_404(self):
        resp = self.client.get("/api/v1/audit/runestones/RS_NONEXISTENT_99999")
        self.assertEqual(resp.status_code, 404)


class TestAuditDecisionList(unittest.TestCase):
    """AUD-06: GET /api/v1/audit/decisions 返回列表"""

    @classmethod
    def setUpClass(cls):
        cls.db_path = _make_db_path()
        cls.app = create_app(db_path=cls.db_path)
        cls.client = TestClient(cls.app)
        scenario = _load_scenario()
        cls.client.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})

    def test_audit_decision_list(self):
        resp = self.client.get("/api/v1/audit/decisions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertIn("limit", data)
        self.assertIn("offset", data)
        self.assertGreaterEqual(data["total"], 1)
        # 验证列表项包含基本字段
        item = data["items"][0]
        self.assertIn("decision_id", item)
        self.assertIn("created_at", item)


if __name__ == "__main__":
    unittest.main()
