#!/usr/bin/env python3
"""
v1.5「企业试点候选」— enterprise_pilot 单元 / 契约套件（T13）。

覆盖 C-01 ~ C-09 + 九条反模式红线的结构性验证（架构设计.md §4 / §10）。
所有测试用临时 SQLite / 临时文件，不污染默认库；不触网。

运行：
    .venv3p/Scripts/python.exe -m pytest tests/test_enterprise_pilot_v15.py -q
"""
import json
import os
import re
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.enterprise_pilot import (  # noqa: E402
    ConfigSecretManager,
    split_config_secrets,
    resolve_secret_ref,
    write_secret_file,
    RbacEngine,
    TokenRegistry,
    OperatorPrincipal,
    ServicePrincipal,
    Role,
    authenticate,
    authorize,
    generate_token,
    SubjectAsPrincipalError,
    AuthorizationError,
    AuthenticationError,
    Desensitizer,
    MappingRecord,
    apply_desensitization,
    ReviewRecord,
    ReviewStore,
    record_review,
    verify_review_bindings,
    IdempotencyKey,
    RetryPolicy,
    Timeout,
    with_retry,
    with_timeout,
    run_resilient,
    StructuredLogger,
    HealthCheck,
    Metrics,
    health,
    metrics_snapshot,
    BackupManager,
    Rollback,
    backup,
    restore,
    ConnectorContract,
    ContractKind,
    emit_contract,
    DeployWalkthrough,
    run_walkthrough,
)

from src.governance_chain import evaluation_event as ee_mod  # noqa: E402
from src.governance_chain import replay_store as rs_mod  # noqa: E402

PILOT_DIR = os.path.join(REPO_ROOT, "src", "enterprise_pilot")
FIXTURE_V14 = os.path.join(REPO_ROOT, "tests", "fixtures", "v14", "input-envelope.ecommerce.json")
SUBJECT_FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v15", "sample_subject_declaration.json")
DEMO_RECORD = os.path.join(REPO_ROOT, "tests", "fixtures", "v15", "demo_desensitize_record.json")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _tmp_event_store():
    fd, path = tempfile.mkstemp(prefix="fse_v15_ee_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return rs_mod.EvaluationEventStore(path)


def _tmp_review_store():
    fd, path = tempfile.mkstemp(prefix="fse_v15_rv_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return ReviewStore(path)


def _record_real_event(store):
    """在临时 EvaluationEventStore 中落一个真实 ORIGINAL 事件，返回 (event_id, event_digest)。"""
    out = ee_mod.record_evaluation(_load(FIXTURE_V14), store=store)
    ref = out["replay_ref"]
    ev = store.get(ref["event_id"])
    return ref["event_id"], ev["event_hash"]


def _read_pilot_sources():
    """读取 enterprise_pilot 全部 .py 源码，合为单一文本（反模式结构扫描用）。"""
    texts = {}
    for root, _dirs, files in os.walk(PILOT_DIR):
        for fn in files:
            if fn.endswith(".py"):
                fp = os.path.join(root, fn)
                try:
                    with open(fp, encoding="utf-8") as fh:
                        texts[fp] = fh.read()
                except Exception:
                    continue
    return texts


# ----------------------------------------------------------------------------
# C-01 配置与秘密分离
# ----------------------------------------------------------------------------
class TestConfigSecretSeparation(unittest.TestCase):
    def test_split_config_secrets_extracts_refs(self):
        doc = {
            "db": {"host": "localhost", "password": "${secret:db_password}"},
            "api_key": "${env:API_KEY}",
        }
        _cfg, refs = split_config_secrets(doc)
        self.assertIn("${secret:db_password}", refs)
        self.assertIn("${env:API_KEY}", refs)
        # 引用仍保留在配置中（真实凭证未内联）
        self.assertEqual(doc["db"]["password"], "${secret:db_password}")

    def test_resolve_secret_from_secret_file(self):
        cfg_fd, cfg_path = tempfile.mkstemp(prefix="fse_v15_cfg_", suffix=".json")
        os.close(cfg_fd)
        sec_fd, sec_path = tempfile.mkstemp(prefix="fse_v15_sec_", suffix=".json")
        os.close(sec_fd)
        try:
            write_secret_file(sec_path, {"db_password": "S3cr3t!"})
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump({"db_password": "${secret:db_password}"}, fh)
            mgr = ConfigSecretManager(cfg_path, secret_backend="secret-file", secret_file=sec_path)
            resolved = mgr.resolve_secret("${secret:db_password}")
            self.assertEqual(resolved, "S3cr3t!")
            # 真实凭证不进配置仓库（配置中仍是引用）
            with open(cfg_path, encoding="utf-8") as fh:
                cfg_on_disk = json.load(fh)
            self.assertEqual(cfg_on_disk["db_password"], "${secret:db_password}")
            self.assertNotIn("S3cr3t!", json.dumps(cfg_on_disk))
        finally:
            for p in (cfg_path, sec_path):
                if os.path.exists(p):
                    os.remove(p)

    def test_secret_not_inline_in_enterprise_pilot(self):
        # 结构性红线条：enterprise_pilot 源码不应出现真实内联口令/令牌常量
        texts = "\n".join(_read_pilot_sources().values())
        forbidden_inline = re.findall(r'(password|token|secret)\s*=\s*["\'][A-Za-z0-9]{8,}["\']',
                                      texts, re.IGNORECASE)
        self.assertEqual(forbidden_inline, [], "found possible inline secret in enterprise_pilot")


# ----------------------------------------------------------------------------
# C-02 最小认证 + RBAC（仅 Operator / Service Principal）
# ----------------------------------------------------------------------------
class TestAuthRbac(unittest.TestCase):
    def _registry(self):
        return TokenRegistry({
            generate_token(): {"principal_id": "op1", "kind": "operator", "roles": ["operator"]},
            generate_token(): {"principal_id": "svc1", "kind": "service", "roles": ["auditor"]},
            generate_token(): {"principal_id": "adm1", "kind": "operator", "roles": ["admin"]},
        })

    def test_authenticate_returns_operator_or_service(self):
        reg = self._registry()
        tokens = list(reg._entries.keys())
        op = authenticate(tokens[0], registry=reg)
        svc = authenticate(tokens[1], registry=reg)
        self.assertIsInstance(op, OperatorPrincipal)
        self.assertIsInstance(svc, ServicePrincipal)
        self.assertEqual(op.kind, "operator")
        self.assertEqual(svc.kind, "service")

    def test_authorize_respects_role_permissions(self):
        reg = self._registry()
        tokens = list(reg._entries.keys())
        svc = authenticate(tokens[1], registry=reg)  # auditor
        self.assertTrue(authorize(svc, "audit:read"))
        self.assertFalse(authorize(svc, "review:write"))
        self.assertFalse(authorize(svc, "config:write"))

    def test_observed_subject_rejected_as_principal(self):
        declaration = _load(SUBJECT_FIXTURE)
        eng = RbacEngine(self._registry())
        with self.assertRaises(SubjectAsPrincipalError):
            eng.authenticate(declaration)
        # 门面函数同样拒绝
        with self.assertRaises(SubjectAsPrincipalError):
            authenticate(declaration, registry=self._registry())

    def test_unknown_token_rejected(self):
        eng = RbacEngine(self._registry())
        with self.assertRaises(AuthenticationError):
            eng.authenticate("not-a-known-token")

    def test_rbac_has_no_tenant_concept(self):
        # 红线 #2：无多租户概念（无 tenant 隔离 API）
        eng = RbacEngine(self._registry())
        op = OperatorPrincipal("op1", ["operator"])
        for obj in (eng, op):
            self.assertFalse(hasattr(obj, "tenant"),
                             f"{type(obj).__name__} must not expose tenant")
        texts = "\n".join(_read_pilot_sources().values())
        # tenant 仅作为禁止性说明出现在注释/文档中，不得作为代码标识符/参数/API
        tenant_code = re.search(
            r"tenant[_=.\"']|self\.tenant|\.tenant|[\"']tenant[\"']|tenant_id",
            texts, re.IGNORECASE,
        )
        self.assertIsNone(tenant_code, "enterprise_pilot must not use tenant as a code construct")


# ----------------------------------------------------------------------------
# C-03 脱敏 / 字段最小化 / 留存
# ----------------------------------------------------------------------------
class TestDesensitize(unittest.TestCase):
    def test_classification_and_methods(self):
        record = _load(DEMO_RECORD)
        policy = {
            "field_categories": {},
            "methods": {"direct": "hash", "indirect": "mask", "business": "none"},
            "reversible": {},
            "minimize": False,
        }
        out, mapping = apply_desensitization(record, policy)
        # 直接标识符 → 哈希（不可逆，前缀 h_）
        self.assertTrue(out["name"].startswith("h_"))
        self.assertTrue(out["email"].startswith("h_"))
        self.assertTrue(out["phone"].startswith("h_"))
        # 间接标识符 → 掩码
        self.assertNotEqual(out["ip"], record["ip"])
        self.assertIn("*", out["ip"])
        # 业务字段默认不脱敏
        self.assertEqual(out["order_id"], record["order_id"])
        self.assertEqual(out["amount"], record["amount"])

    def test_mapping_visible_to_authorized_only(self):
        record = _load(DEMO_RECORD)
        policy = {"methods": {"direct": "hash", "indirect": "mask", "business": "none"}}
        _out, mapping = apply_desensitization(record, policy)
        self.assertTrue(mapping.visible_to_authorized_only)  # 红线 #6
        stripped = mapping.strip_for_unauthorized()
        self.assertNotIn("before_after", stripped)  # 非授权读取被剥离明文
        self.assertIn("field_count", stripped)

    def test_reversible_tokenize_roundtrip(self):
        record = {"email": "a@b.com"}
        vault = {}
        policy = {
            "methods": {"direct": "tokenize", "indirect": "mask", "business": "none"},
            "reversible": {"direct": True},
        }
        _out, mapping = apply_desensitization(record, policy, vault=vault)
        from src.enterprise_pilot.desensitize import detokenize
        self.assertEqual(detokenize(_out["email"], vault), "a@b.com")
        self.assertEqual(mapping.reversibility["email"], "reversible")


# ----------------------------------------------------------------------------
# C-04 人工复核（复用 v1.4 replay_ref 风格真实绑定）
# ----------------------------------------------------------------------------
class TestReviewBinding(unittest.TestCase):
    def test_record_review_binds_real_event(self):
        ee_store = _tmp_event_store()
        rv_store = _tmp_review_store()
        event_id, event_digest = _record_real_event(ee_store)
        rec = record_review(
            {"event_id": event_id, "event_digest": event_digest},
            "approve", "op1",
            source_store=ee_store, review_store=rv_store,
            idempotency_key="idem_test_1",
        )
        self.assertEqual(rec["original_event_ref"]["event_id"], event_id)
        self.assertEqual(rec["original_event_ref"]["event_digest"], event_digest)
        ok, problems = verify_review_bindings(rv_store, ee_store)
        self.assertTrue(ok, msg=f"unexpected binding problems: {problems}")

    def test_record_review_rejects_forged_ref(self):
        ee_store = _tmp_event_store()
        rv_store = _tmp_review_store()
        _record_real_event(ee_store)
        with self.assertRaises(Exception):
            record_review(
                {"event_id": "evt_deadbeefdeadbeef", "event_digest": "x"},
                "approve", "op1",
                source_store=ee_store, review_store=rv_store,
            )

    def test_verify_review_bindings_detects_forged(self):
        ee_store = _tmp_event_store()
        rv_store = _tmp_review_store()
        # 直接 append 一条伪造绑定（绕过 record_review 的校验，模拟攻击）
        forged = ReviewRecord(
            "rvw_forged", {"event_id": "evt_missing", "event_digest": "x"},
            "approve", "op1", "2026-01-01T00:00:00Z",
        ).to_dict()
        forged["review_hash"] = forged.get("review_hash", "h_forged")
        rv_store.append(forged)
        ok, problems = verify_review_bindings(rv_store, ee_store)
        self.assertFalse(ok)
        self.assertTrue(any(p["reason"] == "event_not_found" for p in problems))


# ----------------------------------------------------------------------------
# C-04 / 红线 #7 ReviewStore append-only
# ----------------------------------------------------------------------------
class TestReviewStoreAppendOnly(unittest.TestCase):
    def test_no_history_mutation_api(self):
        store = _tmp_review_store()
        forbidden = ("update", "delete", "modify", "replace", "remove",
                     "purge", "update_event", "delete_event", "purge_event")
        exposed = [m for m in forbidden if hasattr(store, m)]
        self.assertEqual(exposed, [], f"store must not expose history API: {exposed}")

    def test_reappend_same_id_is_idempotent(self):
        store = _tmp_review_store()
        rec = ReviewRecord(
            "rvw_dup", {"event_id": "evt_x", "event_digest": "d"},
            "comment", "op1", "2026-01-01T00:00:00Z",
        ).to_dict()
        store.append(rec)
        store.append(rec)  # 重复 append 幂等
        self.assertEqual(len(store.list_all()), 1)


# ----------------------------------------------------------------------------
# C-05 幂等 / 重试 / 超时 / 失败可恢复
# ----------------------------------------------------------------------------
class TestResilience(unittest.TestCase):
    def test_idempotency_key_deterministic(self):
        k1 = IdempotencyKey.compute({"a": 1, "b": [1, 2]})
        k2 = IdempotencyKey.compute({"b": [1, 2], "a": 1})
        self.assertEqual(k1, k2)
        self.assertTrue(k1.startswith("idem_"))

    def test_retry_policy_retries_then_succeeds(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("transient")
            return "ok"

        result = with_retry(flaky, RetryPolicy(max_attempts=5, backoff=0.0))
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_timeout_raises_on_slow_fn(self):
        import time
        with self.assertRaises(Exception):
            with_timeout(time.sleep, Timeout(seconds=0.2), 1.0)

    def test_run_resilient_rolls_back_on_failure(self):
        state = {"value": 0}

        def snapshot():
            return dict(state)

        def rollback(snap):
            state.update(snap)

        def boom():
            state["value"] = 999
            raise RuntimeError("fail")

        with self.assertRaises(RuntimeError):
            run_resilient(boom, snapshot=snapshot, rollback=rollback)
        self.assertEqual(state["value"], 0)  # 回滚到操作前快照，无半成品


# ----------------------------------------------------------------------------
# C-06 结构化日志 / 健康 / 指标
# ----------------------------------------------------------------------------
class TestObservability(unittest.TestCase):
    def test_health_status(self):
        st = health()
        self.assertEqual(st["status"], "ok")
        self.assertEqual(st["component"], "enterprise_pilot")
        self.assertTrue(st["pilot_enabled"])

    def test_metrics_snapshot(self):
        m = Metrics()
        m.inc_processed()
        m.inc_processed()
        m.inc_failed()
        snap = m.snapshot()
        self.assertEqual(snap["processed"], 2)
        self.assertEqual(snap["failed"], 1)

    def test_structured_logger_emits_json(self):
        import io
        import logging
        buf = io.StringIO()
        logger = StructuredLogger("test_pilot", level=logging.INFO)
        # 替换 handler 以捕获输出
        for h in logger._logger.handlers:
            h.stream = buf
        logger.log("info", "demo_event", {"k": "v"})
        line = buf.getvalue().strip()
        obj = json.loads(line)
        self.assertEqual(obj["event"], "demo_event")
        self.assertEqual(obj["ctx"], {"k": "v"})


# ----------------------------------------------------------------------------
# C-07 本地部署 / 备份 / 回滚
# ----------------------------------------------------------------------------
class TestLifecycle(unittest.TestCase):
    def test_backup_restore_roundtrip(self):
        src_fd, src = tempfile.mkstemp(prefix="fse_v15_src_", suffix=".txt")
        os.close(src_fd)
        bak_fd, bak = tempfile.mkstemp(prefix="fse_v15_bak_", suffix=".txt")
        os.close(bak_fd)
        try:
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("ORIGINAL")
            backup(src, bak)
            # 修改源
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("MODIFIED")
            ok = restore(bak, src)
            self.assertTrue(ok)
            with open(src, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "ORIGINAL")
        finally:
            for p in (src, bak):
                if os.path.exists(p):
                    os.remove(p)

    def test_rollback_plan_execute(self):
        rb = Rollback()
        plan = rb.plan("current.sqlite", "backup.sqlite")
        self.assertEqual(plan["action"], "rollback")
        self.assertEqual(plan["will_restore_from"], "backup.sqlite")


# ----------------------------------------------------------------------------
# C-08 企业 Connector 契约（写回默认 OFF）
# ----------------------------------------------------------------------------
class TestConnectorContract(unittest.TestCase):
    def test_write_enabled_default_false(self):
        c = ConnectorContract("demo")  # 红线 #3：默认 False
        self.assertFalse(c.write_enabled)

    def test_emit_returns_contract_without_writeback(self):
        c = ConnectorContract("demo", write_enabled=False)
        side_effect = {"called": False}

        def impl(_kind, _contract):
            side_effect["called"] = True

        c.register_enterprise_impl(impl)
        contract = emit_contract(c, ContractKind.REPORT_EXPORT, {"goe": {"x": 1}})
        self.assertEqual(contract["contract"], "report_export")
        self.assertFalse(contract["write_enabled"])
        self.assertFalse(side_effect["called"])  # 默认 OFF：引擎绝不写回

    def test_emit_unknown_kind_rejected(self):
        c = ConnectorContract("demo")
        with self.assertRaises(ValueError):
            c.emit("not_a_kind", {})


# ----------------------------------------------------------------------------
# C-09 非作者部署走查
# ----------------------------------------------------------------------------
class TestDeployWalkthrough(unittest.TestCase):
    def test_walkthrough_independent_and_complete(self):
        result = run_walkthrough(REPO_ROOT)
        self.assertIsInstance(result, object)
        # 完整性：全部模块 + 6 schema 齐备
        self.assertTrue(result.complete, msg=f"checks={result.checks}")
        # 独立性：受保护核心目录零侵入
        self.assertTrue(result.independent, msg=f"checks={result.checks}")


# ----------------------------------------------------------------------------
# 九条反模式红线 — 结构性验证（架构设计.md §10）
# ----------------------------------------------------------------------------
class TestAntiPatternRedLines(unittest.TestCase):
    def test_redline_1_subject_not_principal(self):
        eng = RbacEngine(TokenRegistry())
        with self.assertRaises(SubjectAsPrincipalError):
            eng.authenticate(_load(SUBJECT_FIXTURE))

    def test_redline_2_no_multitenant(self):
        texts = "\n".join(_read_pilot_sources().values())
        # tenant 仅作为禁止性说明出现在注释中，不得作为代码构造
        tenant_code = re.search(
            r"tenant[_=.\"']|self\.tenant|\.tenant|[\"']tenant[\"']|tenant_id",
            texts, re.IGNORECASE,
        )
        self.assertIsNone(tenant_code, "enterprise_pilot must not use tenant as a code construct")

    def test_redline_3_connector_default_off(self):
        self.assertFalse(ConnectorContract("x").write_enabled)

    def test_redline_4_compat_not_forge_no_external_effect(self):
        texts = "\n".join(_read_pilot_sources().values())
        # 源码中 external_effect 不得被置 True
        for m in re.finditer(r'external_effect["\']?\s*[:=]\s*(True|False)', texts):
            self.assertEqual(m.group(1), "False", "external_effect must be False")
        # 引擎不签发/验证密码学身份（无 jwt/bcrypt/cryptography 核验）
        self.assertNotIn("jwt", texts.lower())
        self.assertNotIn("bcrypt", texts.lower())
        self.assertNotIn("cryptography", texts.lower())

    def test_redline_5_no_cross_org_network(self):
        texts = "\n".join(_read_pilot_sources().values())
        net_patterns = ["requests\\.", "socket\\.", "smtplib", "http\\.client",
                        "urllib\\.request", "httpx\\."]
        for pat in net_patterns:
            self.assertEqual(re.findall(pat, texts), [],
                             f"found network call pattern {pat} in enterprise_pilot")

    def test_redline_6_mapping_visibility(self):
        _out, mapping = apply_desensitization(
            {"email": "a@b.com"},
            {"methods": {"direct": "hash", "indirect": "mask", "business": "none"}},
        )
        self.assertTrue(mapping.visible_to_authorized_only)
        self.assertNotIn("before_after", mapping.strip_for_unauthorized())

    def test_redline_7_review_append_only(self):
        store = _tmp_review_store()
        self.assertFalse(any(hasattr(store, m)
                             for m in ("update", "delete", "modify", "replace")))

    def test_redline_8_no_replay_ref_forgery(self):
        ee_store = _tmp_event_store()
        rv_store = _tmp_review_store()
        with self.assertRaises(Exception):
            record_review(
                {"event_id": "evt_forged", "event_digest": "x"},
                "approve", "op1",
                source_store=ee_store, review_store=rv_store,
            )

    def test_redline_9_no_vertical_averaging(self):
        # 纵向递归不平均：enterprise_pilot 不得复用/平均 RiskVector
        texts = "\n".join(_read_pilot_sources().values())
        self.assertNotIn("risk_vector", texts.lower())
        self.assertNotIn("average", texts.lower())
        self.assertNotIn("np.mean", texts.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
