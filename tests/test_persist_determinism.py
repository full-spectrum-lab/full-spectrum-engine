#!/usr/bin/env python3
"""
v0.6 确定性测试 (DET-01 ~ DET-02)

2 个测试，覆盖：
    - 持久化不影响仿真确定性
    - 直接模式 API body 与 CLI 输出完整一致 (diff 为空)
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
from simulate import run_simulation

_TEST_DB_DIR = tempfile.mkdtemp(prefix="fse_test_det_")


def _make_db_path():
    return os.path.join(_TEST_DB_DIR, f"test_{uuid.uuid4().hex[:8]}.db")


def _load_scenario():
    with open(os.path.join(_PROJECT_ROOT, "examples", "scenario_refund_conflict.json"), encoding="utf-8") as f:
        return json.load(f)


class TestPersistNoAffectDeterminism(unittest.TestCase):
    """DET-01: 持久化不影响仿真确定性"""

    def test_persist_no_affect_determinism(self):
        scenario = _load_scenario()

        # 直接调用 run_simulation（不经过 API/存储层）
        cli_result = run_simulation(scenario, seed=42)

        # 通过 API（含存储层）
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        resp = client.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})

        api_result = resp.json()

        # 仿真结果应完全一致
        self.assertEqual(cli_result, api_result)


class TestApiCliDiffWithPersistence(unittest.TestCase):
    """DET-02: 直接模式 API body 与 CLI 输出完整一致 (diff 为空)"""

    def test_api_cli_diff_with_persistence(self):
        scenario = _load_scenario()

        # CLI 输出
        cli_result = run_simulation(scenario, seed=42)

        # API 输出（v0.6 含持久化层）
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        resp = client.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})

        api_result = resp.json()

        # 完整 body diff — 不比较 HTTP headers
        # runestone_id 等确定性字段参与 diff（与 v0.5 口径一致）
        # created_at 属于存储元数据，不进入 evaluate 响应 body
        self.assertEqual(
            json.dumps(cli_result, ensure_ascii=False, sort_keys=True),
            json.dumps(api_result, ensure_ascii=False, sort_keys=True),
            "API body must match CLI output exactly (direct mode, complete body diff)",
        )


if __name__ == "__main__":
    unittest.main()
