#!/usr/bin/env python3
"""
v1.2 观察者输入输出契约 — 黑盒自测脚本（第三方可复现）

不依赖 pytest，直接以「真实子进程调用 CLI」+「模型级 API 检查」方式验证
v1.2 的第三方可测能力。输出 JSON + Markdown 两份报告。

运行：
    python scripts/selftest_v12_blackbox.py [--out DIR]

能力覆盖（对应 SRS FR / AC）：
    BB-01  CLI envelope run 正常样例 -> 合法 Output Envelope, external_effect=false
    BB-02  CLI envelope validate-input 正常样例 -> 通过
    BB-03  CLI envelope check-links 断链 -> 非零退出, 报告断链
    BB-04  L4 NETWORK_CANDIDATE -> external_effect=false, mutual_auth CLOSED
    BB-05  v1.0 旧输入归一 -> 合法 Input Envelope (FR-06)
    BB-06  UNKNOWN 显式 -> human_review required, 警告存在 (FR-07)
    BB-07  确定性 -> 同一输入两次 run 的 content_digest 一致 (AC-03)
    BB-08  CLI run == 进程内 run_envelope (FR-03 线级等价)
    BB-09  全量 pytest 通过（仅统计，不替代 pytest 套件）
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.governance_chain import envelope as env_mod  # noqa: E402

EXAMPLE = os.path.join(REPO_ROOT, "examples", "envelope", "input-envelope.ecommerce.json")
PY = sys.executable


def _run_cli(args):
    return subprocess.run(
        [PY, "-m", "src.governance_chain", "envelope", *args],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )


def _check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO_ROOT, "out", "v12_selftest"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    results = []

    # BB-01: CLI run 正常样例
    cli = _run_cli(["run", "--input", EXAMPLE])
    bb01_ok = False
    bb01_detail = ""
    if cli.returncode == 0:
        try:
            out = json.loads(cli.stdout)
            ok_schema, errs = env_mod.validate_output_envelope(out)
            bb01_ok = ok_schema and out.get("external_effect") is False
            bb01_detail = f"exit0 schema_ok={ok_schema} external_effect={out.get('external_effect')}"
        except Exception as e:  # noqa
            bb01_detail = f"parse error: {e}"
    else:
        bb01_detail = cli.stderr[:300]
    results.append(_check("BB-01 CLI envelope run (正常样例)", bb01_ok, bb01_detail))

    # BB-02: CLI validate-input
    cli = _run_cli(["validate-input", "--input", EXAMPLE])
    ok, detail = (cli.returncode == 0), (cli.stdout.strip()[:200] or cli.stderr[:200])
    results.append(_check("BB-02 CLI envelope validate-input (正常样例)", ok, detail))

    # BB-03: CLI check-links 断链
    broken = dict(json.load(open(EXAMPLE, encoding="utf-8-sig")))
    broken["subject_refs"] = ["subj_ghost_999"]
    tmp = os.path.join(tempfile.mkdtemp(), "broken.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(broken, f, ensure_ascii=False)
    cli = _run_cli(["check-links", "--input", tmp,
                    "--known", json.dumps({"known_ids": ["subj_ecom_001"]})])
    ok = cli.returncode != 0 and "subj_ghost_999" in (cli.stdout + cli.stderr)
    results.append(_check("BB-03 CLI envelope check-links (断链报错)", ok,
                           f"exit={cli.returncode} mentions_ghost={'subj_ghost_999' in (cli.stdout+cli.stderr)}"))

    # BB-04: L4 NETWORK_CANDIDATE
    cand = dict(json.load(open(EXAMPLE, encoding="utf-8-sig")))
    cand["l4_mode"] = "NETWORK_CANDIDATE"
    cand["l4_refs"] = {"trust_domain": "example.org", "credential_ref": "cred_abc",
                       "mutual_auth_ref": "ma_abc", "authorization_ref": "az_abc"}
    out = env_mod.run_envelope(cand)
    ok = (out["external_effect"] is False) and (out["gate"]["mutual_auth"]["state"] == "CLOSED")
    results.append(_check("BB-04 L4 NETWORK_CANDIDATE 仅引用不生效", ok,
                           f"external_effect={out['external_effect']} mutual_auth={out['gate']['mutual_auth']['state']}"))

    # BB-05: v1.0 旧输入归一
    legacy = {"industry": "ecommerce_customer_service", "scenario": "after_sales", "order_id": "ORD-X"}
    env = env_mod.normalize_legacy_input(legacy)
    ok_schema, errs = env_mod.validate_input_envelope(env)
    ok = ok_schema and env["layer"] == "L1" and env["scope"] == "internal"
    results.append(_check("BB-05 v1.0 旧输入归一为合法 Input Envelope (FR-06)", ok,
                           f"schema_ok={ok_schema} layer={env.get('layer')} scope={env.get('scope')}"))

    # BB-06: UNKNOWN 显式
    unk = dict(json.load(open(EXAMPLE, encoding="utf-8-sig")))
    unk["unknowns"] = {"missing_receipt": True}
    out = env_mod.run_envelope(unk)
    ok = out["human_review_recommendation"]["required"] and any(
        "UNKNOWN" in w for w in out.get("warnings", []))
    results.append(_check("BB-06 UNKNOWN 显式处理 (FR-07)", ok,
                           f"human_review={out['human_review_recommendation']['required']} warns={out.get('warnings')}"))

    # BB-07: 确定性
    a = env_mod.run_envelope(json.load(open(EXAMPLE, encoding="utf-8-sig")))
    b = env_mod.run_envelope(json.load(open(EXAMPLE, encoding="utf-8-sig")))
    ok = a["content_digest"] == b["content_digest"]
    results.append(_check("BB-07 确定性 content_digest 一致 (AC-03)", ok,
                           f"digest={a['content_digest'][:16]}..."))

    # BB-08: CLI run == 进程内 run_envelope
    cli = _run_cli(["run", "--input", EXAMPLE])
    cli_out = json.loads(cli.stdout) if cli.returncode == 0 else {}
    inproc = env_mod.run_envelope(json.load(open(EXAMPLE, encoding="utf-8-sig")))
    ok = cli.returncode == 0 and env_mod.canonical_json(cli_out) == env_mod.canonical_json(inproc)
    results.append(_check("BB-08 CLI run ≡ 进程内 run_envelope (FR-03)", ok,
                           f"cli_exit={cli.returncode}"))

    # BB-09: 全量 pytest（仅统计）
    pytest = subprocess.run(
        [PY, "-m", "pytest", "tests/", "-q"], cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    summary_line = [l for l in pytest.stdout.splitlines() if "passed" in l or "failed" in l]
    ok = pytest.returncode == 0
    results.append(_check("BB-09 全量 pytest 通过", ok,
                           (summary_line[-1] if summary_line else pytest.stderr[:200])))

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    report = {
        "component": "v1.2 Observer Input/Output Envelope",
        "suite": "blackbox",
        "passed": passed,
        "total": total,
        "all_ok": passed == total,
        "results": results,
    }
    json_path = os.path.join(args.out, "selftest_v12.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = [f"# v1.2 黑盒自测报告（第三方可复现）", "",
          f"组件：v1.2 Observer Input/Output Envelope",
          f"结果：**{passed}/{total} 通过**，all_ok={report['all_ok']}", "",
          "| 编号 | 能力 | 结果 | 说明 |",
          "|------|------|------|------|"]
    for r in results:
        md.append(f"| {r['name'].split()[0]} | {r['name']} | {'✅' if r['ok'] else '❌'} | {r['detail']} |")
    md_path = os.path.join(args.out, "selftest_v12.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"blackbox selftest: {passed}/{total} passed -> {md_path}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
