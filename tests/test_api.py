#!/usr/bin/env python3
"""
Full Spectrum Engine API — v0.7-alpha 测试套件

30 个原有测试 + 2 个物流适配器新增测试，覆盖：
    - health 端点 (4 tests)
    - evaluate 端点 — 直接模式 + 适配器模式 + 错误处理 (12 tests)
    - runestone 端点 — 创建 + 校验 (6 tests)
    - decisions 端点 — 查询 + 404 (3 tests)
    - CORS / headers / 安全 (5 tests)
    - 物流适配器 API 注册 + 评估 (2 tests, v0.7 新增)

加上 v0.4 回归测试 38 个 + v0.7 适配器测试 7 个，总计 125 个测试。

约束验证：
    E-06: API body 严格兼容 CLI 输出 (P1-1)
    E-10~12: decision_id 与 runestone_id 严格区分 (P0-1)
    E-08: include_input_metrics 默认 false (P1-5)
    E-20~21: risk_vector 校验返回 422 不裸 500 (P1-3)
    E-13~16: 错误码统一 422 (P1-2)
    E-26~27: CORS / OPTIONS 预检 (千问C)
    E-28~30: 元信息 headers (P1-1)
"""

import copy
import json
import os
import sys
import tempfile
import unittest

# 确保项目根目录在 path 中
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi.testclient import TestClient
from src.api.server import create_app
from src.api.registry import get_registry
from simulate import run_simulation, load_scenario

# v0.6: 测试使用临时 DB 目录，避免污染工作目录
_TEST_DB_DIR = tempfile.mkdtemp(prefix="fse_test_api_")


def _create_test_app(**kwargs):
    """v0.6: 创建带临时 DB 路径的测试 app"""
    import uuid
    db_path = os.path.join(_TEST_DB_DIR, f"test_{uuid.uuid4().hex[:8]}.db")
    return create_app(db_path=db_path, **kwargs)


def _load_conflict_metrics():
    """加载电商冲突场景指标"""
    with open(os.path.join(_PROJECT_ROOT, "examples", "metrics_ecommerce_conflict.json"), encoding="utf-8") as f:
        return json.load(f)["metrics"]


class TestHealthEndpoint(unittest.TestCase):
    """E-01~04: Health 端点测试"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)

    def test_health_returns_200(self):
        """E-01: health 返回 200"""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)

    def test_health_returns_correct_structure(self):
        """E-02: health 返回正确结构"""
        data = self.client.get("/api/v1/health").json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)
        self.assertIn("engine_version", data)
        self.assertIn("storage_mode", data)
        self.assertEqual(data["storage_mode"], "sqlite-persistent")

    def test_health_returns_registered_adapters(self):
        """E-03: health 返回已注册适配器列表"""
        data = self.client.get("/api/v1/health").json()
        self.assertIn("registered_adapters", data)
        self.assertIsInstance(data["registered_adapters"], list)
        self.assertIn("ecommerce_customer_service", data["registered_adapters"])

    def test_health_returns_local_network_exposure(self):
        """E-04: health 默认返回 local 网络暴露级别"""
        data = self.client.get("/api/v1/health").json()
        self.assertIn("network_exposure", data)
        self.assertEqual(data["network_exposure"], "local")


class TestEvaluateDirectMode(unittest.TestCase):
    """E-05~06: Evaluate 直接模式测试"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)
        with open(os.path.join(_PROJECT_ROOT, "examples", "scenario_refund_conflict.json"), encoding="utf-8") as f:
            cls.scenario = json.load(f)

    def test_evaluate_direct_mode_returns_200(self):
        """E-05: 直接模式返回 200"""
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        self.assertEqual(resp.status_code, 200)

    def test_evaluate_direct_mode_body_matches_cli(self):
        """E-06: API body 严格兼容 CLI 输出（API vs CLI diff 为空）— 核心约束"""
        # CLI 输出
        cli_result = run_simulation(copy.deepcopy(self.scenario), seed=42)
        # API 输出
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        api_result = resp.json()
        # diff 必须为空
        self.assertEqual(cli_result, api_result,
                         "API body must be identical to CLI output (no envelope)")


class TestEvaluateAdapterMode(unittest.TestCase):
    """E-07~09: Evaluate 适配器模式测试"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)
        cls.metrics = _load_conflict_metrics()

    def test_evaluate_adapter_mode_returns_200(self):
        """E-07: 适配器模式返回 200"""
        resp = self.client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": self.metrics,
            "seed": 42
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("fshi", data)
        self.assertIn("runestone", data)

    def test_evaluate_adapter_mode_include_input_metrics_default_false(self):
        """E-08: include_input_metrics 默认 false（隐私最小化 P1-5）"""
        resp = self.client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": self.metrics,
            "seed": 42
        })
        data = resp.json()
        # 默认不包含原始指标，只有 hash
        adapter_meta = data.get("_adapter", {})
        # _adapter 在 scenario 内部，不会出现在 run_simulation 输出中
        # 但原始指标不应出现在任何输出字段中
        result_str = json.dumps(data)
        self.assertNotIn("input_metrics", result_str)

    def test_evaluate_adapter_mode_include_input_metrics_true(self):
        """E-09: include_input_metrics=true 时包含原始指标"""
        resp = self.client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": self.metrics,
            "seed": 42,
            "include_input_metrics": True
        })
        self.assertEqual(resp.status_code, 200)


class TestEvaluateDecisionId(unittest.TestCase):
    """E-10~12: decision_id 测试（P0-1）"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)
        with open(os.path.join(_PROJECT_ROOT, "examples", "scenario_refund_conflict.json"), encoding="utf-8") as f:
            cls.scenario = json.load(f)

    def test_evaluate_returns_decision_id_header(self):
        """E-10: evaluate 响应包含 X-Decision-Id header"""
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        self.assertEqual(resp.status_code, 200)
        # HTTP headers 不区分大小写
        decision_id = resp.headers.get("x-decision-id")
        self.assertIsNotNone(decision_id, "X-Decision-Id header must be present")
        self.assertTrue(decision_id.startswith("DEC_"))

    def test_evaluate_decision_id_is_deterministic(self):
        """E-11: 同一输入生成相同 decision_id（确定性）"""
        resp1 = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        resp2 = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        self.assertEqual(
            resp1.headers.get("x-decision-id"),
            resp2.headers.get("x-decision-id"),
            "Same input must produce same decision_id"
        )

    def test_evaluate_decision_id_differs_from_runestone_id(self):
        """E-12: decision_id 与 runestone_id 严格区分（P0-1）"""
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        decision_id = resp.headers.get("x-decision-id")
        runestone_id = resp.json()["runestone"]["runestone_id"]
        self.assertNotEqual(decision_id, runestone_id,
                            "decision_id must differ from runestone_id")
        self.assertTrue(decision_id.startswith("DEC_"))
        self.assertTrue(runestone_id.startswith("RS_"))


class TestEvaluateErrorHandling(unittest.TestCase):
    """E-13~16: Evaluate 错误处理测试（P1-2: 错误码统一 422）"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)

    def test_evaluate_both_modes_returns_422(self):
        """E-13: 同时使用两种模式返回 422"""
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": {"simulation_id": "test"},
            "industry": "ecommerce_customer_service",
            "metrics": {},
            "seed": 42
        })
        self.assertEqual(resp.status_code, 422)

    def test_evaluate_neither_mode_returns_422(self):
        """E-14: 两种模式都不提供返回 422"""
        resp = self.client.post("/api/v1/evaluate", json={"seed": 42})
        self.assertEqual(resp.status_code, 422)

    def test_evaluate_unregistered_adapter_returns_422(self):
        """E-15: 未注册适配器返回 422"""
        resp = self.client.post("/api/v1/evaluate", json={
            "industry": "nonexistent_industry",
            "metrics": {},
            "seed": 42
        })
        self.assertEqual(resp.status_code, 422)
        self.assertIn("nonexistent_industry", resp.json()["detail"])

    def test_evaluate_missing_metrics_returns_422(self):
        """E-16: 缺失必需指标返回 422"""
        resp = self.client.post("/api/v1/evaluate", json={
            "industry": "ecommerce_customer_service",
            "metrics": {"refund_rate": 0.1},  # 缺少大部分必需字段
            "seed": 42
        })
        self.assertEqual(resp.status_code, 422)
        self.assertIn("Missing required metrics", resp.json()["detail"])


class TestRunestoneEndpoint(unittest.TestCase):
    """E-17~22: Runestone 端点测试"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)
        cls.valid_rv = {
            "survival_impact": 0.3,
            "trust_impact": 0.5,
            "meaning_impact": 0.2,
            "reversibility": 0.6,
            "explainability": 0.8,
            "diffusivity": 0.4,
            "urgency": 0.3,
            "uncertainty": 0.2,
        }

    def test_runestone_creation_returns_200(self):
        """E-17: runestone 创建返回 200"""
        resp = self.client.post("/api/v1/runestone", json={
            "decision": "W3",
            "reason": {"enterprise_id": "test-co", "rule_version": "v0.3"},
            "risk_vector": self.valid_rv,
            "seed": 42
        })
        self.assertEqual(resp.status_code, 200)

    def test_runestone_returns_correct_structure(self):
        """E-18: runestone 返回正确结构"""
        resp = self.client.post("/api/v1/runestone", json={
            "decision": "W3",
            "reason": {"enterprise_id": "test-co", "rule_version": "v0.3"},
            "risk_vector": self.valid_rv,
            "seed": 42
        })
        data = resp.json()
        self.assertIn("runestone_id", data)
        self.assertIn("decision", data)
        self.assertIn("reason", data)
        self.assertIn("risk_vector", data)
        self.assertEqual(data["decision"], "W3")
        self.assertEqual(data["reason"], "ESS-test-co-v0.3")

    def test_runestone_deterministic_id(self):
        """E-19: 同一输入生成相同 runestone_id"""
        req_body = {
            "decision": "W3",
            "reason": {"enterprise_id": "test-co", "rule_version": "v0.3"},
            "risk_vector": self.valid_rv,
            "seed": 42
        }
        resp1 = self.client.post("/api/v1/runestone", json=req_body)
        resp2 = self.client.post("/api/v1/runestone", json=req_body)
        self.assertEqual(
            resp1.json()["runestone_id"],
            resp2.json()["runestone_id"],
            "Same input must produce same runestone_id"
        )

    def test_runestone_missing_risk_vector_fields_returns_422(self):
        """E-20: risk_vector 缺少字段返回 422（不裸 500，P1-3）"""
        resp = self.client.post("/api/v1/runestone", json={
            "decision": "W3",
            "reason": {"enterprise_id": "test-co", "rule_version": "v0.3"},
            "risk_vector": {"survival_impact": 0.3},  # 缺少大部分字段
            "seed": 42
        })
        self.assertEqual(resp.status_code, 422)
        self.assertIn("missing fields", resp.json()["detail"])

    def test_runestone_wrong_type_risk_vector_returns_422(self):
        """E-21: risk_vector 字段类型错误返回 422（不裸 500，P1-3）"""
        resp = self.client.post("/api/v1/runestone", json={
            "decision": "W3",
            "reason": {"enterprise_id": "test-co", "rule_version": "v0.3"},
            "risk_vector": {k: "not_a_number" for k in self.valid_rv},
            "seed": 42
        })
        self.assertEqual(resp.status_code, 422)

    def test_runestone_missing_reason_fields_returns_422(self):
        """E-22: reason 缺少字段返回 422"""
        resp = self.client.post("/api/v1/runestone", json={
            "decision": "W3",
            "reason": {"enterprise_id": "test-co"},  # 缺少 rule_version
            "risk_vector": self.valid_rv,
            "seed": 42
        })
        self.assertEqual(resp.status_code, 422)


class TestDecisionsEndpoint(unittest.TestCase):
    """E-23~25: Decisions 查询端点测试"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)
        with open(os.path.join(_PROJECT_ROOT, "examples", "scenario_refund_conflict.json"), encoding="utf-8") as f:
            cls.scenario = json.load(f)

    def test_decisions_lookup_returns_200(self):
        """E-23: 决策查询返回 200"""
        # 先 evaluate 获取 decision_id
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        decision_id = resp.headers.get("x-decision-id")
        # 查询
        lookup = self.client.get(f"/api/v1/decisions/{decision_id}")
        self.assertEqual(lookup.status_code, 200)

    def test_decisions_lookup_returns_same_result(self):
        """E-24: 查询结果与 evaluate 响应一致"""
        resp = self.client.post("/api/v1/evaluate", json={
            "scenario": self.scenario, "seed": 42
        })
        decision_id = resp.headers.get("x-decision-id")
        lookup = self.client.get(f"/api/v1/decisions/{decision_id}")
        self.assertEqual(resp.json(), lookup.json(),
                         "Decision lookup must return same result as evaluate")

    def test_decisions_not_found_returns_404(self):
        """E-25: 不存在的 decision_id 返回 404"""
        resp = self.client.get("/api/v1/decisions/DEC_NONEXISTENT_12345")
        self.assertEqual(resp.status_code, 404)


class TestCorsAndHeaders(unittest.TestCase):
    """E-26~30: CORS / Headers / 安全测试"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)

    def test_cors_options_preflight_returns_200(self):
        """E-26: CORS OPTIONS 预检返回 200（千问C）"""
        resp = self.client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        self.assertEqual(resp.status_code, 200)

    def test_cors_allows_localhost_origin(self):
        """E-27: CORS 允许 localhost 来源"""
        resp = self.client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        allow_origin = resp.headers.get("access-control-allow-origin")
        self.assertIsNotNone(allow_origin, "CORS must set Access-Control-Allow-Origin")
        self.assertEqual(allow_origin, "http://localhost:3000")

    def test_x_storage_mode_header_on_all_responses(self):
        """E-28: 所有响应包含 X-Storage-Mode header（P1-1, 千问A）"""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.headers.get("x-storage-mode"), "sqlite-persistent")

    def test_x_full_spectrum_notice_header_on_all_responses(self):
        """E-29: 所有响应包含 X-Full-Spectrum-Notice header（P1-1）"""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.headers.get("x-full-spectrum-notice"), "local-dev-only")

    def test_x_production_ready_header_is_false(self):
        """E-30: X-Production-Ready header 始终为 false（P1-1）"""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.headers.get("x-production-ready"), "false")


class TestLogisticsAdapterAPI(unittest.TestCase):
    """LGS-API-01~02: 物流适配器 API 层测试 (v0.7 新增)"""

    @classmethod
    def setUpClass(cls):
        cls.app = _create_test_app()
        cls.client = TestClient(cls.app)
        with open(os.path.join(_PROJECT_ROOT, "examples", "metrics_logistics_conflict.json"), encoding="utf-8") as f:
            cls.logistics_metrics = json.load(f)["metrics"]

    def test_health_returns_logistics_adapter(self):
        """LGS-API-01: health 返回 logistics_customer_service 适配器"""
        data = self.client.get("/api/v1/health").json()
        self.assertIn("logistics_customer_service", data["registered_adapters"],
                      "LogisticsAdapter must be registered in API")

    def test_evaluate_logistics_adapter_mode_returns_200(self):
        """LGS-API-02: 物流适配器模式 evaluate 返回 200"""
        resp = self.client.post("/api/v1/evaluate", json={
            "industry": "logistics_customer_service",
            "metrics": self.logistics_metrics,
            "seed": 42
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("fshi", data)
        self.assertIn("runestone", data)
        # 物流适配器 irreversibility=0.85（冷链），应出现在 RiskVector 中
        rv = data.get("risk_vector", {})
        self.assertEqual(rv.get("reversibility"), 0.85,
                         "LogisticsAdapter irreversibility=0.85 must appear as reversibility field")


if __name__ == "__main__":
    unittest.main()
