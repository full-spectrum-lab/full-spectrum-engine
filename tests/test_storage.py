#!/usr/bin/env python3
"""
v0.6 存储与 API 持久化测试 (STO-01 ~ STO-13)

13 个测试，覆盖：
    - X-Storage-Mode header 更新
    - DB 自动创建
    - 自定义 DB 路径
    - 决策持久化 + 查询
    - 跨重启查询
    - 符石持久化 + 查询
    - 404 从 DB 查询
    - 数据完整性
    - 连接生命周期
    - 线程安全
    - 并发写入
"""

import json
import os
import sys
import tempfile
import threading
import unittest
import uuid

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi.testclient import TestClient
from src.api.server import create_app
from src.storage.backend import StorageBackend

_TEST_DB_DIR = tempfile.mkdtemp(prefix="fse_test_storage_")


def _make_db_path():
    """生成唯一临时 DB 路径"""
    return os.path.join(_TEST_DB_DIR, f"test_{uuid.uuid4().hex[:8]}.db")


def _load_scenario():
    """加载测试场景"""
    with open(os.path.join(_PROJECT_ROOT, "examples", "scenario_refund_conflict.json"), encoding="utf-8") as f:
        return json.load(f)


def _make_runestone_request():
    """构建独立 runestone 请求体"""
    return {
        "decision": "W3",
        "reason": {"enterprise_id": "test_ent", "rule_version": "v0.3"},
        "risk_vector": {
            "survival_impact": 0.3,
            "trust_impact": 0.2,
            "meaning_impact": 0.1,
            "reversibility": 0.5,
            "explainability": 0.8,
            "diffusivity": 0.4,
            "urgency": 0.6,
            "uncertainty": 0.3,
        },
        "seed": 42,
    }


class TestStorageModeHeader(unittest.TestCase):
    """STO-01: X-Storage-Mode 更新为 sqlite-persistent"""

    def test_storage_mode_header(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        resp = client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("x-storage-mode"), "sqlite-persistent")


class TestDbAutoCreate(unittest.TestCase):
    """STO-02: 首次启动自动创建 SQLite 文件"""

    def test_db_auto_create(self):
        db_path = _make_db_path()
        # 确保文件不存在
        self.assertFalse(os.path.exists(db_path))
        app = create_app(db_path=db_path)
        # 文件应该已创建
        self.assertTrue(os.path.exists(db_path))


class TestDbCustomPath(unittest.TestCase):
    """STO-03: 自定义 DB 路径"""

    def test_db_custom_path(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        # health 端点应返回自定义路径
        resp = client.get("/api/v1/health")
        data = resp.json()
        self.assertIn("db_path", data)
        self.assertTrue(data["db_path"].endswith(".db"))


class TestDecisionPersist(unittest.TestCase):
    """STO-04: evaluate 后决策记录写入 DB"""

    def test_decision_persist(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        scenario = _load_scenario()

        resp = client.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})
        self.assertEqual(resp.status_code, 200)
        decision_id = resp.headers.get("x-decision-id")

        # 直接通过 StorageBackend 验证 DB 中有记录
        storage = app.state.storage
        result = storage.get_decision(decision_id)
        self.assertIsNotNone(result, "Decision should be persisted in DB")


class TestDecisionQueryById(unittest.TestCase):
    """STO-05: GET /decisions/{id} 从 DB 读取"""

    def test_decision_query_by_id(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        scenario = _load_scenario()

        resp = client.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})
        decision_id = resp.headers.get("x-decision-id")
        evaluate_body = resp.json()

        lookup = client.get(f"/api/v1/decisions/{decision_id}")
        self.assertEqual(lookup.status_code, 200)
        self.assertEqual(lookup.json(), evaluate_body)


class TestDecisionSurviveRestart(unittest.TestCase):
    """STO-06: 跨重启查询"""

    def test_decision_survive_restart(self):
        db_path = _make_db_path()
        scenario = _load_scenario()

        # 第一个 app 实例
        app1 = create_app(db_path=db_path)
        client1 = TestClient(app1)
        resp = client1.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})
        decision_id = resp.headers.get("x-decision-id")
        evaluate_body = resp.json()

        # 销毁第一个连接
        app1.state.storage.close()

        # 第二个 app 实例（同 DB 路径）
        app2 = create_app(db_path=db_path)
        client2 = TestClient(app2)

        # 查询第一个实例写入的记录
        lookup = client2.get(f"/api/v1/decisions/{decision_id}")
        self.assertEqual(lookup.status_code, 200)
        self.assertEqual(lookup.json(), evaluate_body)


class TestRunestonePersist(unittest.TestCase):
    """STO-07: runestone 端点生成的令牌写入 DB"""

    def test_runestone_persist(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)

        resp = client.post("/api/v1/runestone", json=_make_runestone_request())
        self.assertEqual(resp.status_code, 200)
        runestone_id = resp.json().get("runestone_id")

        # 直接通过 StorageBackend 验证
        storage = app.state.storage
        result = storage.get_runestone(runestone_id)
        self.assertIsNotNone(result, "Runestone should be persisted in DB")


class TestRunestoneQueryById(unittest.TestCase):
    """STO-08: GET /api/v1/audit/runestones/{id}"""

    def test_runestone_query_by_id(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)

        resp = client.post("/api/v1/runestone", json=_make_runestone_request())
        runestone_id = resp.json().get("runestone_id")
        runestone_body = resp.json()

        lookup = client.get(f"/api/v1/audit/runestones/{runestone_id}")
        self.assertEqual(lookup.status_code, 200)
        self.assertEqual(lookup.json(), runestone_body)


class TestDecision404Persistent(unittest.TestCase):
    """STO-09: 查询不存在的 decision_id 返回 404（从 DB 查询）"""

    def test_decision_404_persistent(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)

        resp = client.get("/api/v1/decisions/DEC_NONEXISTENT_99999")
        self.assertEqual(resp.status_code, 404)


class TestDecisionDataIntegrity(unittest.TestCase):
    """STO-10: 持久化数据完整性"""

    def test_decision_data_integrity(self):
        db_path = _make_db_path()
        app = create_app(db_path=db_path)
        client = TestClient(app)
        scenario = _load_scenario()

        resp = client.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})
        decision_id = resp.headers.get("x-decision-id")
        original = resp.json()

        # 从 DB 查询
        lookup = client.get(f"/api/v1/decisions/{decision_id}")
        stored = lookup.json()

        # 完整性检查：所有顶层 key 都在
        for key in original:
            self.assertIn(key, stored, f"Key '{key}' missing in stored data")

        # 深度比较
        self.assertEqual(original, stored)


class TestDbConnectionLifecycle(unittest.TestCase):
    """STO-11: 连接创建与关闭（无连接泄漏）"""

    def test_db_connection_lifecycle(self):
        db_path = _make_db_path()
        storage = StorageBackend(db_path=db_path)

        # 写入一条记录
        storage.save_decision(
            decision_id="DEC_TEST_001",
            simulation_id="SIM_001",
            runestone_id="RS_TEST_001",
            result={"test": "data", "runestone": {"runestone_id": "RS_TEST_001"}},
            adapter=None,
            seed=42,
        )

        # 查询
        result = storage.get_decision("DEC_TEST_001")
        self.assertIsNotNone(result)

        # 关闭
        storage.close()

        # 重新打开同一 DB
        storage2 = StorageBackend(db_path=db_path)
        result2 = storage2.get_decision("DEC_TEST_001")
        self.assertIsNotNone(result2)
        storage2.close()


class TestDbThreadSafety(unittest.TestCase):
    """STO-12: 基本线程安全"""

    def test_db_thread_safety(self):
        db_path = _make_db_path()
        storage = StorageBackend(db_path=db_path)

        errors = []

        def worker():
            try:
                for i in range(5):
                    storage.save_decision(
                        decision_id=f"DEC_THREAD_{threading.current_thread().name}_{i}",
                        simulation_id=f"SIM_{i}",
                        runestone_id=f"RS_THREAD_{threading.current_thread().name}_{i}",
                        result={"test": f"data_{i}", "runestone": {"runestone_id": f"RS_THREAD_{threading.current_thread().name}_{i}"}},
                        seed=42,
                    )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, name=f"T{i}") for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")

        # 验证所有记录都写入成功
        stats = storage.get_stats()
        self.assertEqual(stats["decision_count"], 15)  # 3 threads * 5 records

        storage.close()


class TestConcurrentWrites(unittest.TestCase):
    """STO-13: 多线程并发写入"""

    def test_concurrent_writes(self):
        db_path = _make_db_path()
        storage = StorageBackend(db_path=db_path)

        results = {}

        def write_decision(decision_id):
            storage.save_decision(
                decision_id=decision_id,
                simulation_id=f"SIM_{decision_id}",
                runestone_id=f"RS_{decision_id}",
                result={"test": decision_id, "runestone": {"runestone_id": f"RS_{decision_id}"}},
                seed=42,
            )

        # 两个线程同时写入不同 decision_id
        t1 = threading.Thread(target=write_decision, args=("DEC_CONCURRENT_1",))
        t2 = threading.Thread(target=write_decision, args=("DEC_CONCURRENT_2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 两条记录都正确写入
        r1 = storage.get_decision("DEC_CONCURRENT_1")
        r2 = storage.get_decision("DEC_CONCURRENT_2")
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        self.assertEqual(r1["test"], "DEC_CONCURRENT_1")
        self.assertEqual(r2["test"], "DEC_CONCURRENT_2")

        storage.close()


if __name__ == "__main__":
    unittest.main()
