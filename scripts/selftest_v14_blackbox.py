#!/usr/bin/env python3
"""
v1.4 Replay 与 Audit 加固 — 黑盒自测脚本（第三方可复现，BB-01 ~ BB-09）

不依赖 pytest 内部，以「纯导入 / compileall / 真实子进程 pytest / 模型级 API 检查 /
git diff / 源码反模式扫描」方式逐项验证 v1.4 的第三方可测能力。

运行：
    python scripts/selftest_v14_blackbox.py [--out DIR]

BB 映射（与架构设计.md §5.2 / §6 一致）：
    BB-01  导入 v1.4 六个新模块（evaluation_event/replay_bundle/replay_store/
            replay/audit/schemas）
    BB-02  compileall src/governance_chain/ 无语法错误
    BB-03  全量 pytest（从仓库根）0 failed
    BB-04  record_evaluation 追加不可变 ORIGINAL 事件 + 真实可解析 replay_ref
    BB-05  ReplayEngine.replay 追加 REPLAY 事件、原事件不变（AC-01 digest 稳定）
    BB-06  NFR-02 缺失 Profile 版本 → 显式 ReplayDependencyError（绝不猜测）
    BB-07  Audit 导出 canonical JSONL + verify_chain 干净链 (True, [])
    BB-08  零侵入：git diff 86b9f0a -- 核心模块 为空
    BB-09  反模式扫描：v1.3 路径 replay_ref 恒 null / v1.4 路径 replay_ref 真实；
            external_effect 恒 false / gate 对象形式 / EXTERNAL_ACTIVE 不启用 /
            L4_CANDIDATE 不生效

设计原则：仅本地 / 离线计算，无网络调用；加法扩展，不改动 v1.2/v1.3 核心。
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
]
PY = sys.executable

FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v14", "input-envelope.ecommerce.json")
CROSS = os.path.join(REPO_ROOT, "tests", "fixtures", "cross_combo", "cross_ecom_knowledge_conflict.json")
GATE_KEYS = ("layer_flow", "qualification", "authorization", "mutual_auth", "effective_state")


def _check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": str(detail)}


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _tmp_store():
    import sqlite3 as _sq

    fd, path = tempfile.mkstemp(prefix="fse_v14_bb_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    from src.governance_chain import replay_store as rs_mod

    return rs_mod.EvaluationEventStore(path)


def bb01_import():
    """BB-01: 导入 v1.4 六个新模块成功。"""
    try:
        import src.governance_chain.evaluation_event as ee  # noqa: F401
        import src.governance_chain.replay_bundle as rb  # noqa: F401
        import src.governance_chain.replay_store as rs  # noqa: F401
        import src.governance_chain.replay as rp  # noqa: F401
        import src.governance_chain.audit as au  # noqa: F401
        ok = all([
            hasattr(ee, "record_evaluation"),
            hasattr(ee, "compute_event_hash"),
            hasattr(rb, "ReplayBundle"),
            hasattr(rb, "ReplayDependencyError"),
            hasattr(rs, "EvaluationEventStore"),
            hasattr(rp, "ReplayEngine"),
            hasattr(au, "AuditExporter"),
            hasattr(au, "IntegrityChecker"),
        ])
        detail = "imported evaluation_event/replay_bundle/replay_store/replay/audit OK"
    except Exception as e:  # noqa
        ok, detail = False, f"import error: {e}"
    return _check("BB-01 模块导入 (v1.4 六模块)", ok, detail)


def bb02_compileall():
    """BB-02: compileall src/governance_chain/ 无语法错误。"""
    proc = subprocess.run(
        [PY, "-m", "compileall", "-q", os.path.join(REPO_ROOT, "src", "governance_chain")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    return _check("BB-02 compileall src/governance_chain/", proc.returncode == 0,
                  f"exit={proc.returncode} {proc.stderr.strip()[:200] or 'ok'}")


def bb03_pytest():
    """BB-03: 全量 pytest（从仓库根）0 failed。"""
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests/", "-q"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    summary = [l for l in proc.stdout.splitlines()
               if "passed" in l or "failed" in l or "error" in l]
    ok = proc.returncode == 0
    return _check("BB-03 全量 pytest 0 failed (从仓库根)", ok,
                  summary[-1] if summary else (proc.stderr[:200] or "no summary"))


def bb04_record_immutable():
    """BB-04: record_evaluation 追加不可变 ORIGINAL 事件 + 真实可解析 replay_ref。"""
    try:
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import replay_store as rs_mod
        from src.governance_chain.evaluation_event import GENESIS
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ev = store.get(out["replay_ref"]["event_id"])
        real_ref = (
            ev is not None
            and ev["event_type"] == "ORIGINAL"
            and ev["previous_event_hash"] == GENESIS
            and isinstance(out.get("replay_ref"), dict)
            and store.get(out["replay_ref"]["event_id"]) is not None
            and out["replay_ref"]["event_digest"] == ev["event_hash"]
        )
        ok = real_ref
        detail = (f"event_type={ev['event_type']}; prev={ev['previous_event_hash']}; "
                  f"replay_ref_resolves={store.get(out['replay_ref']['event_id']) is not None}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-04 record_evaluation 不可变 ORIGINAL + 真实 replay_ref", ok, detail)


def bb05_replay_original_untouched():
    """BB-05: ReplayEngine.replay 追加 REPLAY 事件、原事件不变（AC-01 稳定）。"""
    try:
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import replay as replay_mod
        from src.governance_chain import replay_bundle as rb_mod
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        orig = store.get(out["replay_ref"]["event_id"])
        orig_hash = orig["event_hash"]
        bundle = rb_mod.ReplayBundle.from_event(orig)
        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(bundle, replay_mode="EXACT")
        same_digest = (
            new_event["result_fingerprint"]["output_content_digest"]
            == orig["result_fingerprint"]["output_content_digest"]
        )
        original_untouched = store.get(orig["event_id"])["event_hash"] == orig_hash
        ok = (new_event["event_type"] == "REPLAY"
              and new_event["source_original_event_id"] == orig["event_id"]
              and same_digest and original_untouched)
        detail = (f"replay_type={new_event['event_type']}; "
                  f"ac01_digest_equal={same_digest}; original_untouched={original_untouched}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-05 replay 追加 REPLAY + 原事件不变 (AC-01)", ok, detail)


def bb06_nfr02_dependency_error():
    """BB-06: NFR-02 缺失 Profile 版本 → 显式 ReplayDependencyError。"""
    try:
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import replay as replay_mod
        from src.governance_chain import replay_bundle as rb_mod
        from src.governance_chain.replay_bundle import ReplayDependencyError
        store = _tmp_store()
        bad = rb_mod.ReplayBundle.from_dict({
            "bundle_id": "bundle_bad",
            "bindings": {
                "subject": {"ref": "subj_ecom_001"},
                "schema": {"input": "gie-1.2", "output": "goe-1.2"},
                "adapter": {"ref": "ecommerce_customer_service"},
                "engine": {"observer": "govchain@1.4.0", "computation": "profile_driven_v1.3"},
                "profile": {"refs": ["prof_fshi_ecom_001@9.9.9"],
                            "source_profile_versions": ["prof_fshi_ecom_001@9.9.9"]},
                "policy": {"ref": "gov_rules_default@1.0.0"},
                "knowledge": {"refs": []},
                "model": {"id": "risk_vector/profile_driven_v1.3", "version": "1.3.0"},
                "environment": {"seed": 0, "clock": "2026-01-01T00:00:00Z",
                                "contract_version": "1.2.0", "python": "3.x", "platform": "win32"},
            },
            "input_ref": {"digest": "x", "location": "inline"},
            "input_envelope": _load(FIXTURE),
            "bundle_digest": "x",
            "source_event_id": None,
        })
        engine = replay_mod.ReplayEngine(store)
        raised = False
        try:
            engine.replay(bad)
        except ReplayDependencyError:
            raised = True
        ok = raised
        detail = "ReplayDependencyError raised on missing profile version" if raised \
            else "ERROR: no error raised (would be a silent guess)"
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-06 NFR-02 缺失依赖显式报错 (ReplayDependencyError)", ok, detail)


def bb07_audit_export_verify():
    """BB-07: Audit 导出 canonical JSONL + verify_chain 干净链 (True, [])。"""
    try:
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import audit as audit_mod
        store = _tmp_store()
        ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ee_mod.record_evaluation(_load(CROSS), store=store)
        events = store.list_events(limit=10 ** 9)
        fd, path = tempfile.mkstemp(prefix="fse_v14_bb_aud_", suffix=".jsonl")
        os.close(fd)
        audit_mod.AuditExporter.export_range(events, path)
        with open(path, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        no_hash_in_line = all("event_hash" not in json.loads(ln) for ln in lines)
        ok_chain, tampered = audit_mod.IntegrityChecker.verify_chain(store)
        ok = (len(lines) == 2 and no_hash_in_line and ok_chain and tampered == [])
        detail = (f"exported_lines={len(lines)}; no_event_hash_in_line={no_hash_in_line}; "
                  f"verify_ok={ok_chain}; tampered={len(tampered)}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-07 Audit 导出 canonical JSONL + verify 干净链", ok, detail)


def bb08_zero_intrusion():
    """BB-08: 零侵入 — 核心模块相对 86b9f0a 的 diff 为空。"""
    proc = subprocess.run(
        ["git", "-C", REPO_ROOT, "diff", BASE_COMMIT, "--"] + CORE_MODULES,
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    ok = proc.returncode == 0 and not proc.stdout.strip()
    return _check("BB-08 零侵入 (核心模块 diff 为空)", ok,
                  f"exit={proc.returncode} diff_len={len(proc.stdout.strip())}")


def bb09_anti_pattern():
    """BB-09: 反模式扫描（静态 + 运行时）。"""
    probs = []
    gc_dir = os.path.join(REPO_ROOT, "src", "governance_chain")
    py_files = []
    for root, _dirs, files in os.walk(gc_dir):
        for fn in files:
            if fn.endswith(".py") or fn.endswith(".json"):
                py_files.append(os.path.join(root, fn))
    texts = {}
    for fp in py_files:
        try:
            with open(fp, encoding="utf-8") as fh:
                texts[fp] = fh.read()
        except Exception:
            continue

    # external_effect 绝不被置为 True（源码静态）
    for fp, t in texts.items():
        for m in re.finditer(r'external_effect["\']?\s*[:=]\s*(True|False)', t):
            if m.group(1) == "True":
                probs.append(f"{os.path.basename(fp)}: external_effect=True")
    # EXTERNAL_ACTIVE 不在源码中被启用
    for fp, t in texts.items():
        if "EXTERNAL_ACTIVE" in t and '"EXTERNAL_ACTIVE"' not in t:
            probs.append(f"{os.path.basename(fp)}: EXTERNAL_ACTIVE referenced as code (not enum literal)")

    # ---- 运行时扫描 ----
    try:
        from src.governance_chain import envelope as env_mod
        from src.governance_chain import evaluation_event as ee_mod
        from src.governance_chain import replay_store as rs_mod
        # 1) v1.3 直接路径：replay_ref 必须恒为 None
        out_v13 = env_mod.run_envelope(_load(CROSS))
        if out_v13.get("replay_ref") is not None:
            probs.append("runtime: v1.3 run_envelope replay_ref != None")
        if out_v13.get("external_effect") is not False:
            probs.append("runtime: v1.3 external_effect != False")
        gate = out_v13.get("gate", {})
        if not isinstance(gate, dict):
            probs.append("runtime: v1.3 gate not object form")
        elif gate.get("effective_state") == "EXTERNAL_ACTIVE":
            probs.append("runtime: v1.3 effective_state==EXTERNAL_ACTIVE")
        # L4_CANDIDATE 不生效
        l4 = _load(CROSS)
        l4["l4_mode"] = "NETWORK_CANDIDATE"
        out_l4 = env_mod.run_envelope(l4)
        if out_l4.get("external_effect") is not False:
            probs.append("runtime: L4 NETWORK_CANDIDATE set external_effect=True")

        # 2) v1.4 记录路径：replay_ref 必须真实存在（反模式反向约束）
        store = _tmp_store()
        out_v14 = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ref = out_v14.get("replay_ref")
        if not isinstance(ref, dict) or not ref.get("event_id"):
            probs.append("runtime: v1.4 record replay_ref missing/forged")
        elif store.get(ref["event_id"]) is None:
            probs.append("runtime: v1.4 record replay_ref not resolvable")
    except Exception as e:  # noqa
        probs.append(f"runtime error: {e}")

    ok = len(probs) == 0
    detail = "all anti-pattern checks green" if ok else "; ".join(probs)
    return _check("BB-09 反模式扫描 (replay_ref/external_effect/gate/L4)", ok, detail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO_ROOT, "out", "v14_selftest"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    results = [
        bb01_import(),
        bb02_compileall(),
        bb03_pytest(),
        bb04_record_immutable(),
        bb05_replay_original_untouched(),
        bb06_nfr02_dependency_error(),
        bb07_audit_export_verify(),
        bb08_zero_intrusion(),
        bb09_anti_pattern(),
    ]

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    report = {
        "component": "v1.4 Replay & Audit Hardening",
        "suite": "blackbox",
        "passed": passed,
        "total": total,
        "all_ok": passed == total,
        "base_commit": BASE_COMMIT,
        "results": results,
    }
    json_path = os.path.join(args.out, "selftest_v14.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = [
        "# v1.4 黑盒自测报告（第三方可复现）", "",
        f"组件：v1.4 Replay 与 Audit 加固",
        f"基线提交：{BASE_COMMIT}",
        f"结果：**{passed}/{total} 通过**，all_ok={report['all_ok']}", "",
        "| 编号 | 能力 | 结果 | 说明 |",
        "|------|------|------|------|",
    ]
    for r in results:
        md.append(f"| {r['name'].split()[0]} | {r['name']} | "
                  f"{'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
    md_path = os.path.join(args.out, "selftest_v14.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"v1.4 blackbox selftest: {passed}/{total} passed -> {md_path}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
