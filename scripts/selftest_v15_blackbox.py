#!/usr/bin/env python3
"""
v1.5「企业试点候选」— 黑盒自测脚本（第三方可复现，BB-01 ~ BB-11）

不依赖 pytest 内部，以「纯导入 / compileall / 真实子进程 pytest / 模型级 API 检查 /
git diff / 源码反模式扫描」方式逐项验证 v1.5 的第三方可测能力。

运行：
    python scripts/selftest_v15_blackbox.py [--out DIR]

BB 映射（与任务派发 / 架构设计.md §6.2 对齐）：
    BB-01  配置 / 秘密分离：凭证不在配置仓，引用解析成功（C-01）
    BB-02  RBAC 闸门：合法通过 / 越权拒绝 / ObservedSubject 拒绝（AC-06 / 红线 #1）
    BB-03  脱敏端到端：输入→处理→输出全链路脱敏，分级符合 FR-03（C-03）
    BB-04  人工复核绑定原审计事件：replay_ref 真实可解析（AC-02 / 红线 #8）
    BB-05  幂等 / 重试 / 超时 / 失败可恢复（C-05）
    BB-06  健康检查 / 指标（C-06）
    BB-07  备份 → 回滚演练：数据连续（C-07）
    BB-08  Connector 默认 OFF：emit 不写回（C-08 / 红线 #3）
    BB-09  零侵入：git diff 86b9f0a -- 受保护 9 目录 为空
    BB-10  九条反模式 grep 全绿（§10）
    BB-11  与 v1.4 衔接：import v1.4 模块、replay_ref 复用无回归

附加（不计入 BB-01~BB-11  headline，但一并实跑）：
    BB-12  compileall src/enterprise_pilot/ 无语法错误
    BB-13  全量 pytest（从仓库根）0 failed

设计原则：仅本地 / 离线计算，无网络调用；加法扩展，不改动 v1.2~v1.4 核心。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

BASE_COMMIT = "86b9f0a"
CORE_MODULES = [
    "src/core", "src/engine", "src/storage", "src/bridge",
    "src/guardian", "src/governance", "src/observation", "src/safety",
    "src/adapters",
]
PILOT_DIR = os.path.join(REPO_ROOT, "src", "enterprise_pilot")
FIXTURE_V14 = os.path.join(REPO_ROOT, "tests", "fixtures", "v14", "input-envelope.ecommerce.json")
SUBJECT_FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v15", "sample_subject_declaration.json")
DEMO_RECORD = os.path.join(REPO_ROOT, "tests", "fixtures", "v15", "demo_desensitize_record.json")
PY = sys.executable


def _check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": str(detail)}


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _read_sources(paths):
    texts = {}
    for fp in paths:
        try:
            with open(fp, encoding="utf-8") as fh:
                texts[fp] = fh.read()
        except Exception:
            continue
    return texts


def _pilot_py_sources():
    files = []
    for root, _dirs, fs in os.walk(PILOT_DIR):
        for fn in fs:
            if fn.endswith(".py"):
                files.append(os.path.join(root, fn))
    return files


# ---------------------------------------------------------------------------
def bb01_config_secret():
    """BB-01: 配置 / 秘密分离（C-01）。"""
    try:
        from src.enterprise_pilot import (
            ConfigSecretManager, split_config_secrets, write_secret_file,
        )
        cfg_fd, cfg_path = tempfile.mkstemp(prefix="fse_v15_bb_cfg_", suffix=".json")
        os.close(cfg_fd)
        sec_fd, sec_path = tempfile.mkstemp(prefix="fse_v15_bb_sec_", suffix=".json")
        os.close(sec_fd)
        try:
            write_secret_file(sec_path, {"db_password": "S3cr3t!"})
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump({"db_password": "${secret:db_password}"}, fh)
            mgr = ConfigSecretManager(cfg_path, secret_backend="secret-file", secret_file=sec_path)
            resolved = mgr.resolve_secret("${secret:db_password}")
            _cfg, refs = split_config_secrets({"db_password": "${secret:db_password}"})
            with open(cfg_path, encoding="utf-8") as fh:
                on_disk = json.load(fh)
            ok = (
                resolved == "S3cr3t!"
                and "${secret:db_password}" in refs
                and on_disk["db_password"] == "${secret:db_password}"
                and "S3cr3t!" not in json.dumps(on_disk)
            )
            detail = "secret resolved by ref; not inline in config repo" if ok \
                else "secret separation broken"
        finally:
            for p in (cfg_path, sec_path):
                if os.path.exists(p):
                    os.remove(p)
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-01 配置/秘密分离 (C-01)", ok, detail)


def bb02_rbac_gate():
    """BB-02: RBAC 闸门（合法通过 / 越权拒绝 / ObservedSubject 拒绝）。"""
    try:
        from src.enterprise_pilot import (
            RbacEngine, TokenRegistry, authenticate, authorize,
            generate_token, SubjectAsPrincipalError, AuthorizationError,
        )
        reg = TokenRegistry({
            generate_token(): {"principal_id": "op1", "kind": "operator", "roles": ["operator"]},
            generate_token(): {"principal_id": "svc1", "kind": "service", "roles": ["auditor"]},
        })
        tokens = list(reg._entries.keys())
        op = authenticate(tokens[0], registry=reg)
        svc = authenticate(tokens[1], registry=reg)
        legal = authorize(op, "review:write") and authorize(svc, "audit:read")
        denied = (not authorize(svc, "review:write")) and (not authorize(svc, "config:write"))
        eng = RbacEngine(reg)
        subject_rejected = False
        try:
            eng.authenticate(_load(SUBJECT_FIXTURE))
        except SubjectAsPrincipalError:
            subject_rejected = True
        ok = legal and denied and subject_rejected
        detail = (f"legal={legal}; denied={denied}; subject_rejected={subject_rejected}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-02 RBAC 闸门 (合法/越权/ObservedSubject拒绝)", ok, detail)


def bb03_desensitize_e2e():
    """BB-03: 脱敏端到端（C-03 / AC-01 脱敏分级）。"""
    try:
        from src.enterprise_pilot import apply_desensitization
        record = _load(DEMO_RECORD)
        policy = {
            "methods": {"direct": "hash", "indirect": "mask", "business": "none"},
            "reversible": {},
            "minimize": False,
        }
        out, mapping = apply_desensitization(record, policy)
        ok = (
            out["name"].startswith("h_")
            and out["email"].startswith("h_")
            and out["ip"] != record["ip"] and "*" in out["ip"]
            and out["order_id"] == record["order_id"]
            and mapping.visible_to_authorized_only is True
            and "before_after" not in mapping.strip_for_unauthorized()
        )
        detail = (f"direct_hashed={out['name'][:6]}...; indirect_masked={out['ip']}; "
                  f"business_kept={out['order_id']}; mapping_authorized_only={mapping.visible_to_authorized_only}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-03 脱敏端到端 (C-03)", ok, detail)


def bb04_review_binds_original_event():
    """BB-04: 人工复核绑定原审计事件（AC-02 / 红线 #8）。"""
    try:
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import replay_store as rs_mod
        from src.enterprise_pilot import record_review, verify_review_bindings
        fd, ee_path = tempfile.mkstemp(prefix="fse_v15_bb_ee_", suffix=".sqlite")
        os.close(fd)
        os.remove(ee_path)
        rv_fd, rv_path = tempfile.mkstemp(prefix="fse_v15_bb_rv_", suffix=".sqlite")
        os.close(rv_fd)
        os.remove(rv_path)
        ee_store = None
        rv_store = None
        try:
            ee_store = rs_mod.EvaluationEventStore(ee_path)
            rv_store = __import__("src.enterprise_pilot", fromlist=["ReviewStore"]).ReviewStore(rv_path)
            out = ee_mod.record_evaluation(_load(FIXTURE_V14), store=ee_store)
            ref = out["replay_ref"]
            ev = ee_store.get(ref["event_id"])
            rec = record_review(
                {"event_id": ref["event_id"], "event_digest": ev["event_hash"]},
                "approve", "op1", source_store=ee_store, review_store=rv_store,
                idempotency_key="idem_bb04",
            )
            ok_bind = rec["original_event_ref"]["event_id"] == ref["event_id"]
            ok_verify, problems = verify_review_bindings(rv_store, ee_store)
            # 伪造引用必须被拒
            forged_rejected = False
            try:
                record_review(
                    {"event_id": "evt_deadbeef", "event_digest": "x"},
                    "approve", "op1", source_store=ee_store, review_store=rv_store,
                )
            except Exception:
                forged_rejected = True
            ok = ok_bind and ok_verify and forged_rejected
            detail = (f"bind={ok_bind}; verify_ok={ok_verify}({len(problems)}); "
                      f"forged_rejected={forged_rejected}")
        finally:
            for st in (ee_store, rv_store):
                try:
                    if st is not None:
                        st.close()
                except Exception:
                    pass
            for p in (ee_path, rv_path):
                if os.path.exists(p):
                    os.remove(p)
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-04 复核绑定原审计事件 (replay_ref真实)", ok, detail)


def bb05_idempotent_retry_timeout():
    """BB-05: 幂等 / 重试 / 超时 / 失败可恢复（C-05）。"""
    try:
        from src.enterprise_pilot import (
            IdempotencyKey, RetryPolicy, Timeout, with_retry, with_timeout, run_resilient,
        )
        import time
        k1 = IdempotencyKey.compute({"a": 1, "b": [1, 2]})
        k2 = IdempotencyKey.compute({"b": [1, 2], "a": 1})
        idem_ok = k1 == k2 and k1.startswith("idem_")

        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("t")
            return "ok"

        retry_ok = with_retry(flaky, RetryPolicy(max_attempts=5)) == "ok" and calls["n"] == 3

        timeout_ok = False
        try:
            with_timeout(time.sleep, Timeout(seconds=0.2), 1.0)
        except Exception:
            timeout_ok = True

        state = {"v": 0}

        def snap():
            return dict(state)

        def rollback(s):
            state.update(s)

        def boom():
            state["v"] = 999
            raise RuntimeError()

        recover_ok = False
        try:
            run_resilient(boom, snapshot=snap, rollback=rollback)
        except Exception:
            recover_ok = (state["v"] == 0)
        ok = idem_ok and retry_ok and timeout_ok and recover_ok
        detail = (f"idem={idem_ok}; retry={retry_ok}; timeout={timeout_ok}; "
                  f"recover={recover_ok}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-05 幂等/重试/超时/失败可恢复 (C-05)", ok, detail)


def bb06_health_metrics():
    """BB-06: 健康检查 / 指标（C-06）。"""
    try:
        from src.enterprise_pilot import health, metrics_snapshot, StructuredLogger
        import io
        import logging
        st = health()
        snap = metrics_snapshot()
        buf = io.StringIO()
        logger = StructuredLogger("bb_test", level=logging.INFO)
        for h in logger._logger.handlers:
            h.stream = buf
        logger.log("info", "demo", {"k": 1})
        log_json_ok = False
        try:
            obj = json.loads(buf.getvalue().strip())
            log_json_ok = obj.get("event") == "demo"
        except Exception:
            log_json_ok = False
        ok = (st.get("status") == "ok" and "processed" in snap and "failed" in snap
              and log_json_ok)
        detail = (f"health_status={st.get('status')}; "
                  f"metrics={snap}; structured_log={log_json_ok}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-06 健康检查/指标 (C-06)", ok, detail)


def bb07_backup_rollback():
    """BB-07: 备份 → 回滚演练（C-07）。"""
    try:
        from src.enterprise_pilot import backup, restore
        src_fd, src = tempfile.mkstemp(prefix="fse_v15_bb_src_", suffix=".txt")
        os.close(src_fd)
        bak_fd, bak = tempfile.mkstemp(prefix="fse_v15_bb_bak_", suffix=".txt")
        os.close(bak_fd)
        try:
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("ORIGINAL")
            backup(src, bak)
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("MODIFIED")
            restore(bak, src)
            with open(src, encoding="utf-8") as fh:
                ok = fh.read() == "ORIGINAL"
            detail = "backup->modify->restore == ORIGINAL" if ok else "restore mismatch"
        finally:
            for p in (src, bak):
                if os.path.exists(p):
                    os.remove(p)
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-07 备份→回滚演练 (C-07)", ok, detail)


def bb08_connector_default_off():
    """BB-08: Connector 默认 OFF（emit 不写回）（C-08 / 红线 #3）。"""
    try:
        from src.enterprise_pilot import ConnectorContract, ContractKind
        c = ConnectorContract("demo")
        default_off = (c.write_enabled is False)
        side = {"called": False}

        def impl(_k, _c):
            side["called"] = True

        c.register_enterprise_impl(impl)
        contract = c.emit(ContractKind.REPORT_EXPORT, {"goe": {"x": 1}})
        no_writeback = (side["called"] is False)
        ok = default_off and no_writeback and contract["write_enabled"] is False
        detail = (f"write_enabled_default={default_off}; "
                  f"emit_no_writeback={no_writeback}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-08 Connector 默认 OFF (emit不写回)", ok, detail)


def bb09_zero_intrusion():
    """BB-09: 零侵入 — 受保护核心目录相对 86b9f0a 的 diff 为空。"""
    proc = subprocess.run(
        ["git", "-C", REPO_ROOT, "diff", BASE_COMMIT, "--"] + CORE_MODULES,
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    ok = proc.returncode == 0 and not proc.stdout.strip()
    return _check("BB-09 零侵入 (受保护9目录 diff 为空)", ok,
                  f"exit={proc.returncode} diff_len={len(proc.stdout.strip())}")


def bb10_anti_pattern():
    """BB-10: 九条反模式扫描（§10）。"""
    probs = []
    try:
        from src.enterprise_pilot import (
            RbacEngine, TokenRegistry, authenticate, SubjectAsPrincipalError,
            apply_desensitization, ConnectorContract, ContractKind,
            record_review, ReviewStore,
        )
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import replay_store as rs_mod

        ext_files = [
            os.path.join(REPO_ROOT, "src", "governance_chain", "cli.py"),
            os.path.join(REPO_ROOT, "src", "api", "routes.py"),
            os.path.join(REPO_ROOT, "src", "api", "models.py"),
        ]
        texts = _read_sources(_pilot_py_sources() + ext_files)
        combined = "\n".join(texts.values())

        # 红线 #1: ObservedSubject 拒绝
        eng = RbacEngine(TokenRegistry())
        try:
            eng.authenticate(_load(SUBJECT_FIXTURE))
            probs.append("redline#1: ObservedSubject accepted as principal")
        except SubjectAsPrincipalError:
            pass

        # 红线 #2: 无 tenant（仅作为禁止性说明出现在注释中，不得作为代码构造）
        if re.search(r"tenant[_=.\"']|self\.tenant|\.tenant|[\"']tenant[\"']|tenant_id",
                     combined, re.IGNORECASE):
            probs.append("redline#2: 'tenant' used as a code construct in enterprise_pilot/extensions")

        # 红线 #3: Connector 默认 OFF
        if ConnectorContract("x").write_enabled is not False:
            probs.append("redline#3: ConnectorContract.write_enabled not False by default")

        # 红线 #4: external_effect 恒 False；无密码学身份核验
        for fp, t in texts.items():
            for m in re.finditer(r'external_effect["\']?\s*[:=]\s*(True|False)', t):
                if m.group(1) == "True":
                    probs.append(f"redline#4: {os.path.basename(fp)} external_effect=True")
        for kw in ("jwt", "bcrypt", "cryptography"):
            if kw in combined.lower():
                probs.append(f"redline#4: found '{kw}' (crypto identity verify forbidden)")

        # 红线 #5: 无跨组织网络写
        for pat in (r"requests\.", r"socket\.", r"smtplib", r"http\.client",
                    r"urllib\.request", r"httpx\."):
            if re.search(pat, combined):
                probs.append(f"redline#5: network call pattern '{pat}' in sources")

        # 红线 #6: 脱敏映射仅授权可见
        _o, mapping = apply_desensitization(
            {"email": "a@b.com"},
            {"methods": {"direct": "hash", "indirect": "mask", "business": "none"}},
        )
        if mapping.visible_to_authorized_only is not True:
            probs.append("redline#6: MappingRecord.visible_to_authorized_only != True")
        if "before_after" in mapping.strip_for_unauthorized():
            probs.append("redline#6: unauthorized read exposes before_after")

        # 红线 #7: ReviewStore 无历史改写 API
        rv_fd, rv_path = tempfile.mkstemp(prefix="fse_v15_bb_rv7_", suffix=".sqlite")
        os.close(rv_fd)
        os.remove(rv_path)
        try:
            store = ReviewStore(rv_path)
            if any(hasattr(store, m) for m in ("update", "delete", "modify", "replace", "remove")):
                probs.append("redline#7: ReviewStore exposes history-mutation API")
            store.close()
        finally:
            if os.path.exists(rv_path):
                os.remove(rv_path)

        # 红线 #8: replay_ref 伪造被拒（运行时）
        fd, ee_path = tempfile.mkstemp(prefix="fse_v15_bb_ee_", suffix=".sqlite")
        os.close(fd)
        os.remove(ee_path)
        rv_fd, rv_path = tempfile.mkstemp(prefix="fse_v15_bb_rv_", suffix=".sqlite")
        os.close(rv_fd)
        os.remove(rv_path)
        try:
            ee_store = rs_mod.EvaluationEventStore(ee_path)
            rv_store = ReviewStore(rv_path)
            forged_rejected = False
            try:
                record_review(
                    {"event_id": "evt_forged", "event_digest": "x"},
                    "approve", "op1", source_store=ee_store, review_store=rv_store,
                )
            except Exception:
                forged_rejected = True
            if not forged_rejected:
                probs.append("redline#8: forged replay_ref accepted")
            rv_store.close()
        finally:
            try:
                if ee_store is not None:
                    ee_store.close()
            except Exception:
                pass
            for p in (ee_path, rv_path):
                if os.path.exists(p):
                    os.remove(p)

        # 红线 #9: 纵向递归不平均（继承跨版本）
        # enterprise_pilot 自身不得出现 risk_vector 复用/平均（与单测
        # TestAntiPatternRedLines 一致，仅对 pilot 源码做裸词检查）；
        # 扩展文件（routes/models/cli）允许对 risk_vector 做输入校验/透传，
        # 但禁止复用 v1.4 RiskVectorComputer 算法或做 np.mean 简单平均。
        _pilot_only = "\n".join(_read_sources(_pilot_py_sources()).values())
        if ("risk_vector" in _pilot_only.lower() or "average" in _pilot_only.lower()
                or "np.mean" in _pilot_only.lower()):
            probs.append("redline#9: enterprise_pilot reuses/averages risk_vector (forbidden)")
        if "riskvectorcomputer" in combined.lower():
            probs.append("redline#9: RiskVectorComputer reused/averaged in pilot/extensions (forbidden)")
        if "np.mean" in combined.lower():
            probs.append("redline#9: found np.mean (simple averaging) in sources")

    except Exception as e:  # noqa
        probs.append(f"runtime error: {e}")

    ok = len(probs) == 0
    detail = "all 9 anti-pattern red-lines green" if ok else "; ".join(probs)
    return _check("BB-10 九条反模式扫描 (§10)", ok, detail)


def bb11_v14_interop():
    """BB-11: 与 v1.4 衔接（import v1.4 模块、replay_ref 复用无回归）。"""
    probs = []
    try:
        # 导入 v1.4 六个模块，确认仍存在且可用
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import replay_bundle as rb_mod
        from src.governance_chain import replay_store as rs_mod
        from src.governance_chain import replay as rp_mod
        from src.governance_chain import audit as au_mod
        for sym in ("record_evaluation", "ReplayBundle", "EvaluationEventStore",
                    "ReplayEngine", "AuditExporter", "IntegrityChecker"):
            mod = {"record_evaluation": ee_mod, "ReplayBundle": rb_mod,
                   "EvaluationEventStore": rs_mod, "ReplayEngine": rp_mod,
                   "AuditExporter": au_mod, "IntegrityChecker": au_mod}[sym]
            if not hasattr(mod, sym):
                probs.append(f"v1.4 symbol missing: {sym}")

        from src.enterprise_pilot import record_review, ReviewStore
        fd, ee_path = tempfile.mkstemp(prefix="fse_v15_bb_ee_", suffix=".sqlite")
        os.close(fd)
        os.remove(ee_path)
        rv_fd, rv_path = tempfile.mkstemp(prefix="fse_v15_bb_rv_", suffix=".sqlite")
        os.close(rv_fd)
        os.remove(rv_path)
        try:
            ee_store = rs_mod.EvaluationEventStore(ee_path)
            rv_store = ReviewStore(rv_path)
            out = ee_mod.record_evaluation(_load(FIXTURE_V14), store=ee_store)
            ref = out["replay_ref"]
            ev = ee_store.get(ref["event_id"])
            # v1.5 复用 v1.4 真实 replay_ref 绑定，无回归
            rec = record_review(
                {"event_id": ref["event_id"], "event_digest": ev["event_hash"]},
                "approve", "op1", source_store=ee_store, review_store=rv_store,
                idempotency_key="idem_bb11",
            )
            if rec["original_event_ref"]["event_id"] != ref["event_id"]:
                probs.append("v1.5 review binding mismatch with v1.4 event")
            rv_store.close()
        finally:
            try:
                if ee_store is not None:
                    ee_store.close()
            except Exception:
                pass
            for p in (ee_path, rv_path):
                if os.path.exists(p):
                    os.remove(p)
    except Exception as e:  # noqa
        probs.append(f"error: {e}")

    ok = len(probs) == 0
    detail = "v1.4 modules importable; replay_ref reuse no regression" if ok \
        else "; ".join(probs)
    return _check("BB-11 与 v1.4 衔接 (replay_ref复用无回归)", ok, detail)


def bb12_compileall():
    """BB-12 (附加): compileall src/enterprise_pilot/ 无语法错误。"""
    proc = subprocess.run(
        [PY, "-m", "compileall", "-q", PILOT_DIR],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    return _check("BB-12 compileall src/enterprise_pilot/", proc.returncode == 0,
                  f"exit={proc.returncode} {proc.stderr.strip()[:200] or 'ok'}")


def bb13_pytest():
    """BB-13 (附加): 全量 pytest（从仓库根）0 failed。"""
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests/", "-q"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    summary = [l for l in proc.stdout.splitlines()
               if "passed" in l or "failed" in l or "error" in l]
    ok = proc.returncode == 0
    return _check("BB-13 全量 pytest 0 failed (从仓库根)", ok,
                  summary[-1] if summary else (proc.stderr[:200] or "no summary"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO_ROOT, "out", "v15_selftest"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    results = [
        bb01_config_secret(),
        bb02_rbac_gate(),
        bb03_desensitize_e2e(),
        bb04_review_binds_original_event(),
        bb05_idempotent_retry_timeout(),
        bb06_health_metrics(),
        bb07_backup_rollback(),
        bb08_connector_default_off(),
        bb09_zero_intrusion(),
        bb10_anti_pattern(),
        bb11_v14_interop(),
        bb12_compileall(),
        bb13_pytest(),
    ]

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    report = {
        "component": "v1.5 Enterprise Pilot Candidate",
        "suite": "blackbox",
        "passed": passed,
        "total": total,
        "all_ok": passed == total,
        "base_commit": BASE_COMMIT,
        "results": results,
    }
    json_path = os.path.join(args.out, "selftest_v15.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = [
        "# v1.5 黑盒自测报告（第三方可复现）", "",
        "组件：v1.5「企业试点候选」",
        f"基线提交：{BASE_COMMIT}",
        f"结果：**{passed}/{total} 通过**，all_ok={report['all_ok']}",
        "",
        "| 编号 | 能力 | 结果 | 说明 |",
        "|------|------|------|------|",
    ]
    for r in results:
        md.append(f"| {r['name'].split()[0]} | {r['name']} | "
                  f"{'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
    md_path = os.path.join(args.out, "selftest_v15.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"v1.5 blackbox selftest: {passed}/{total} passed -> {md_path}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
