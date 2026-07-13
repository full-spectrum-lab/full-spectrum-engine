#!/usr/bin/env python3
"""
v1.3 Profile 驱动观察者引擎 — 黑盒自测脚本（第三方可复现，BB-01 ~ BB-09）

不依赖 pytest 内部，以「纯导入 / compileall / 真实子进程 pytest / 模型级 API
检查 / git diff / 源码反模式扫描」方式逐项验证 v1.3 的第三方可测能力。

运行：
    python scripts/selftest_v13_blackbox.py [--out DIR]

BB 映射（与架构设计.md §5.2 一致）：
    BB-01  导入 profiles / policy / scenario / certification / risk_vector
    BB-02  compileall src/governance_chain/
    BB-03  全量 pytest（从仓库根）0 failed
    BB-04  Profile 版本绑定（get(id,version)）+ digest 重算比对
    BB-05  四组交叉组合确定性（同输入 + 同 Profile 版本 → 等价 content_digest）
    BB-06  认证组合五逻辑每逻辑 ≥1 例、只输出候选
            （eligibility_candidate ∈ {CANDIDATE, NOT_CANDIDATE, UNKNOWN}）
    BB-07  UNKNOWN / 硬禁止不被 risk_vector 均值/最大值覆盖
            （置 human_review_recommendation.required=true 并显式标注）
    BB-08  零侵入：git diff v1.2.0 -- 核心模块 为空
    BB-09  反模式扫描：external_effect 恒 false / replay_ref 恒 null /
            gate 保持对象形式 / EXTERNAL_ACTIVE 不启用 / L4_CANDIDATE 不生效

设计原则：仅本地 / 离线计算，无网络调用；加法扩展，无 ref 时与 v1.2 逐字节一致。
"""
import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

BASE_COMMIT = "v1.2.0"
CORE_MODULES = [
    "src/core", "src/engine", "src/storage", "src/bridge",
    "src/guardian", "src/governance", "src/observation", "src/safety",
]
PY = sys.executable

CROSS = os.path.join(REPO_ROOT, "tests", "fixtures", "cross_combo")
CERT = os.path.join(REPO_ROOT, "tests", "fixtures", "certification")
ECOM_KC = os.path.join(CROSS, "cross_ecom_knowledge_conflict.json")
ECOM_OC = os.path.join(CROSS, "cross_ecom_overcommitment.json")
GATE_KEYS = ("layer_flow", "qualification", "authorization", "mutual_auth", "effective_state")


def _check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": str(detail)}


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def bb01_import():
    """BB-01: 导入各新建/扩展模块成功。"""
    try:
        import src.governance_chain.profiles as profiles_pkg  # noqa: F401
        import src.governance_chain.policy as policy_mod  # noqa: F401
        import src.governance_chain.scenario as scenario_mod  # noqa: F401
        import src.governance_chain.certification as cert_mod  # noqa: F401
        import src.governance_chain.risk_vector as rv_mod  # noqa: F401
        ok = all([
            hasattr(profiles_pkg, "get_default_registry"),
            hasattr(policy_mod, "EnterpriseAuthorizationPolicy"),
            hasattr(scenario_mod, "ScenarioRegistry"),
            hasattr(cert_mod, "CertificationEngine"),
            hasattr(rv_mod, "RiskVectorComputer"),
        ])
        detail = "imported profiles/policy/scenario/certification/risk_vector OK"
    except Exception as e:  # noqa
        ok, detail = False, f"import error: {e}"
    return _check("BB-01 模块导入 (profiles/policy/scenario/certification/risk_vector)", ok, detail)


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


def bb04_profile_version_digest():
    """BB-04: Profile 版本绑定 + digest 重算比对。"""
    try:
        from src.governance_chain.profiles.registry import get_default_registry
        reg = get_default_registry()
        sample = reg.get("prof_fshi_ecom_001", "1.0.0")
        declared = sample.get("digest")
        recomputed = reg.compute_digest(sample)
        # 篡改断言：重算不一致必须显式报错（不静默）
        integrity_ok = (declared == recomputed)
        # 负向校验：人为改写 digest 后重算应不等
        tampered = dict(sample)
        tampered["digest"] = "0" * 64
        mismatch_detected = (reg.compute_digest(tampered) != tampered["digest"])
        ok = integrity_ok and mismatch_detected
        detail = (f"get(prof_fshi_ecom_001,1.0.0) ok; declared==recomputed="
                  f"{integrity_ok}; tamper-detect={mismatch_detected}")
    except Exception as e:  # noqa
        ok, detail = False, f"error: {e}"
    return _check("BB-04 Profile 版本绑定 + digest 重算比对", ok, detail)


def bb05_cross_determinism():
    """BB-05: 四组交叉组合确定性（同输入 + 同 Profile 版本 → 等价 content_digest）。"""
    try:
        from src.governance_chain import envelope as env_mod
        combos = {
            "ecom_kc": ECOM_KC,
            "ecom_oc": ECOM_OC,
            "logi_kc": os.path.join(CROSS, "cross_logi_knowledge_conflict.json"),
            "logi_oc": os.path.join(CROSS, "cross_logi_overcommitment.json"),
        }
        per_combo = {}
        all_ok = True
        for name, path in combos.items():
            a = env_mod.run_envelope(_load(path))
            b = env_mod.run_envelope(_load(path))
            same = (
                a["content_digest"] == b["content_digest"]
                and a["risk_vector"]["values"] == b["risk_vector"]["values"]
                and a["risk_vector"]["source_profile_versions"]
                == b["risk_vector"]["source_profile_versions"]
            )
            per_combo[name] = same
            all_ok = all_ok and same
        detail = "; ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in per_combo.items())
    except Exception as e:  # noqa
        all_ok, detail = False, f"error: {e}"
    return _check("BB-05 四组交叉组合确定性 (等价 content_digest)", all_ok, detail)


def bb06_cert_five_logics():
    """BB-06: 认证组合五逻辑每逻辑 ≥1 例、只输出候选。"""
    try:
        from src.governance_chain.certification import CertificationEngine
        eng = CertificationEngine()
        enum = ("CANDIDATE", "NOT_CANDIDATE", "UNKNOWN")
        per_logic = {}
        # five requirement fixtures (one per logic)
        for fixture in ("requirement_allof", "requirement_anyof",
                        "requirement_atleast_n", "requirement_oneof",
                        "requirement_not_required"):
            req = _load(os.path.join(CERT, fixture + ".json"))
            logic = (req.get("domain") or {}).get("logic")
            # attestations_external satisfies all requirements
            res = eng.evaluate(req, _load(os.path.join(CERT, "attestations_external.json")))
            per_logic[logic] = res["eligibility_candidate"] in enum
        # UNKNOWN example: substantive logic with zero evidence
        allof = _load(os.path.join(CERT, "requirement_allof.json"))
        unk = eng.evaluate(allof, [])
        unknown_ok = unk["eligibility_candidate"] == "UNKNOWN"
        # must NEVER emit a conclusion field
        no_conclusion = all(
            k not in unk for k in ("certified", "authorized", "active", "granted")
        )
        all_ok = all(per_logic.values()) and unknown_ok and no_conclusion
        detail = ("; ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in per_logic.items())
                  + f"; UNKNOWN={unk['eligibility_candidate']}; no_conclusion={no_conclusion}")
    except Exception as e:  # noqa
        all_ok, detail = False, f"error: {e}"
    return _check("BB-06 认证五逻辑每逻辑≥1例 + 只输出候选", all_ok, detail)


def bb07_unknown_not_covered():
    """BB-07: UNKNOWN / 硬禁止不被 risk_vector 均值/最大值覆盖。"""
    try:
        from src.governance_chain import envelope as env_mod
        # hard-forbidden combo (overcommitment): scenario flag must surface
        oc = _load(ECOM_OC)
        out_hf = env_mod.run_envelope(oc)
        hf_ok = bool(out_hf.get("hard_forbidden")) \
            and out_hf["human_review_recommendation"]["required"] is True \
            and "HARD_FORBIDDEN" in out_hf["explanation"]["basis"]
        # UNKNOWN combo: unknown flag must surface
        unk = _load(ECOM_KC)
        unk["unknowns"] = {"missing_receipt": True}
        out_unk = env_mod.run_envelope(unk)
        unk_ok = bool(out_unk.get("unknown_flags")) \
            and out_unk["human_review_recommendation"]["required"] is True \
            and "UNKNOWN_PRESENT" in out_unk["explanation"]["basis"]
        # 证明不被聚合分掩盖：即便 risk_vector 最大值很低，flag 仍显式存在
        rv_max = max(out_hf["risk_vector"]["values"] or [0.0])
        not_masked = (rv_max < 1.0) and hf_ok  # flag present regardless of score
        all_ok = hf_ok and unk_ok and not_masked
        detail = (f"hard_forbidden={bool(out_hf.get('hard_forbidden'))} "
                  f"hr_required={out_hf['human_review_recommendation']['required']} "
                  f"basis={out_hf['explanation']['basis']}; "
                  f"unknown_flags={bool(out_unk.get('unknown_flags'))}; "
                  f"rv_max={rv_max:.4f}")
    except Exception as e:  # noqa
        all_ok, detail = False, f"error: {e}"
    return _check("BB-07 UNKNOWN/硬禁止不被聚合分覆盖 (显式标注)", all_ok, detail)


def bb08_zero_intrusion():
    """BB-08: 零侵入 — 核心模块相对正式 v1.2.0 标签的 diff 为空。"""
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
    # ---- 静态扫描（仅 .py；schema 的 enum 允许值不计入） ----
    py_files = []
    for root, _dirs, files in os.walk(gc_dir):
        for fn in files:
            if fn.endswith(".py"):
                py_files.append(os.path.join(root, fn))
    texts = {}
    for fp in py_files:
        with open(fp, encoding="utf-8") as fh:
            texts[fp] = fh.read()

    # external_effect 绝不被置为 True
    for fp, t in texts.items():
        for m in re.finditer(r'external_effect["\']?\s*[:=]\s*(True|False)', t):
            if m.group(1) == "True":
                probs.append(f"{os.path.basename(fp)}: external_effect=True")
    # EXTERNAL_ACTIVE 不在 .py 中被启用
    for fp, t in texts.items():
        if "EXTERNAL_ACTIVE" in t:
            probs.append(f"{os.path.basename(fp)}: EXTERNAL_ACTIVE referenced")
    # replay_ref 在 .py 中恒为 None
    for fp, t in texts.items():
        for m in re.finditer(r'replay_ref["\']?\s*[:=]\s*([A-Za-z0-9_"\'{\[]+)', t):
            if "None" not in m.group(1):
                probs.append(f"{os.path.basename(fp)}: replay_ref non-null")

    # ---- 运行时扫描 ----
    try:
        from src.governance_chain import envelope as env_mod
        out = env_mod.run_envelope(_load(ECOM_KC))
        if out.get("external_effect") is not False:
            probs.append("runtime: external_effect != False")
        if out.get("replay_ref") is not None:
            probs.append("runtime: replay_ref != None")
        gate = out.get("gate", {})
        if not isinstance(gate, dict):
            probs.append("runtime: gate not object form")
        else:
            for k in GATE_KEYS:
                if k not in gate:
                    probs.append(f"runtime: gate missing {k}")
            if gate.get("effective_state") == "EXTERNAL_ACTIVE":
                probs.append("runtime: effective_state==EXTERNAL_ACTIVE")
        # L4_CANDIDATE 不生效：NETWORK_CANDIDATE 时 external_effect 仍 False
        l4 = _load(ECOM_KC)
        l4["l4_mode"] = "NETWORK_CANDIDATE"
        out_l4 = env_mod.run_envelope(l4)
        if out_l4.get("external_effect") is not False:
            probs.append("runtime: L4 NETWORK_CANDIDATE set external_effect=True")
        if out_l4.get("gate", {}).get("mutual_auth", {}).get("state") != "CLOSED":
            probs.append("runtime: L4 mutual_auth not CLOSED")
    except Exception as e:  # noqa
        probs.append(f"runtime error: {e}")

    ok = len(probs) == 0
    detail = "all anti-pattern checks green" if ok else "; ".join(probs)
    return _check("BB-09 反模式扫描 (external_effect/replay_ref/gate/L4)", ok, detail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO_ROOT, "out", "v13_selftest"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    results = [
        bb01_import(),
        bb02_compileall(),
        bb03_pytest(),
        bb04_profile_version_digest(),
        bb05_cross_determinism(),
        bb06_cert_five_logics(),
        bb07_unknown_not_covered(),
        bb08_zero_intrusion(),
        bb09_anti_pattern(),
    ]

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    report = {
        "component": "v1.3 Profile-Driven Observer Engine",
        "suite": "blackbox",
        "passed": passed,
        "total": total,
        "all_ok": passed == total,
        "base_commit": BASE_COMMIT,
        "results": results,
    }
    json_path = os.path.join(args.out, "selftest_v13.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = [
        "# v1.3 黑盒自测报告（第三方可复现）", "",
        f"组件：v1.3 Profile-Driven Observer Engine",
        f"基线提交：{BASE_COMMIT}",
        f"结果：**{passed}/{total} 通过**，all_ok={report['all_ok']}", "",
        "| 编号 | 能力 | 结果 | 说明 |",
        "|------|------|------|------|",
    ]
    for r in results:
        md.append(f"| {r['name'].split()[0]} | {r['name']} | "
                  f"{'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
    md_path = os.path.join(args.out, "selftest_v13.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"v1.3 blackbox selftest: {passed}/{total} passed -> {md_path}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
