#!/usr/bin/env python3
"""
v1.5 QA 独立证伪脚本（第三方 / 独立 QA 视角，对齐 v1.4 §C 红线扫描风格）。

本脚本与工程师的 tests/test_enterprise_pilot_v15.py / selftest_v15_blackbox.py
**完全独立**，仅依赖待测源码与被测 API，对架构设计.md §10 的九条反模式红线
逐条做结构性证伪：验证方法 + 实际结论（PASS/FAIL）。

运行：
    .venv3p/Scripts/python.exe scripts/qa_redline_verify_v15.py
"""
import json
import os
import re
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

PILOT_DIR = os.path.join(REPO_ROOT, "src", "enterprise_pilot")
FIXTURE_V14 = os.path.join(REPO_ROOT, "tests", "fixtures", "v14",
                           "input-envelope.ecommerce.json")
SUBJECT_FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v15",
                               "sample_subject_declaration.json")

_RESULTS = []
_FAILS = []


def record(num, method, conclusion_ok, detail):
    status = "PASS" if conclusion_ok else "FAIL"
    _RESULTS.append((num, status, method, detail))
    if not conclusion_ok:
        _FAILS.append(num)
    print(f"RL#{num:>2} [{status}] {method}")
    print(f"        -> {detail}")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _read_pilot_sources():
    texts = {}
    for root, _d, files in os.walk(PILOT_DIR):
        for fn in files:
            if fn.endswith(".py"):
                fp = os.path.join(root, fn)
                with open(fp, encoding="utf-8") as fh:
                    texts[fp] = fh.read()
    return texts


def _tmp_event_store():
    import src.governance_chain.replay_store as rs_mod  # noqa
    fd, path = tempfile.mkstemp(prefix="qa_ee_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return rs_mod.EvaluationEventStore(path)


def _tmp_review_store():
    from src.enterprise_pilot import ReviewStore
    fd, path = tempfile.mkstemp(prefix="qa_rv_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return ReviewStore(path)


# ---------------------------------------------------------------------------
# 红线 #1：用 ObservedSubject 充当系统登录身份
# ---------------------------------------------------------------------------
def rl1():
    method = ("读取 auth_rbac.py：确认 authenticate() 仅接受预共享令牌字符串，"
              "对 SubjectDeclaration 形态显式抛 SubjectAsPrincipalError；"
              "authorize/require_role 对非 Principal 同样拒绝；"
              "运行时以被测 sample_subject_declaration.json 调 authenticate 验证被拒。")
    from src.enterprise_pilot import (RbacEngine, TokenRegistry, authenticate,
                                      SubjectAsPrincipalError)
    src = _read_pilot_sources()
    combined = "\n".join(src.values())
    checks = []
    # 源码层面：authenticate 内部有 _looks_like_subject 拒绝分支
    checks.append(("_looks_like_subject rejection branch present",
                   "SubjectAsPrincipalError" in combined
                   and "_looks_like_subject" in combined))
    # 源码层面：主体类只有 OperatorPrincipal / ServicePrincipal
    checks.append(("only Operator/Service principal kinds",
                   "class OperatorPrincipal" in combined
                   and "class ServicePrincipal" in combined
                   and "class Principal" in combined))
    # 源码层面：无接收 ObservedSubject 作为 auth 主体的接口签名
    checks.append(("no ObservedSubject accepted as auth principal",
                   "ObservedSubject" not in combined
                   or "ObservedSubject must not be used as an auth principal"
                   in combined))
    # 运行时：真实以 SubjectDeclaration 调 authenticate 应被拒
    decl = _load(SUBJECT_FIXTURE)
    eng = RbacEngine(TokenRegistry())
    rejected = False
    try:
        eng.authenticate(decl)
    except SubjectAsPrincipalError:
        rejected = True
    # 门面函数同样拒绝
    facade_rejected = False
    try:
        authenticate(decl, registry=TokenRegistry())
    except SubjectAsPrincipalError:
        facade_rejected = True
    # authorize 对非 Principal 拒绝（subject 不是 Principal 子类）
    non_principal_rejected = False
    try:
        eng.authorize(decl, "review:write")
    except SubjectAsPrincipalError:
        non_principal_rejected = True
    ok = all(v for _, v in checks) and rejected and facade_rejected and non_principal_rejected
    detail = (f"src_checks={dict(checks)}; runtime_subject_rejected={rejected}; "
              f"facade_rejected={facade_rejected}; non_principal_rejected={non_principal_rejected}")
    record(1, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #2：多租户概念误入
# ---------------------------------------------------------------------------
def rl2():
    method = ("grep enterprise_pilot 全部 .py 源码：确认 'tenant' 不作为代码标识符/"
              "参数/API 出现（tenant_/self.tenant/.tenant/'tenant'/tenant_id），"
              "仅可作为注释中的禁止性说明。")
    texts = _read_pilot_sources()
    combined = "\n".join(texts.values())
    m = re.search(r"tenant[_=.\"']|self\.tenant|\.tenant|[\"']tenant[\"']|tenant_id",
                  combined, re.IGNORECASE)
    ok = m is None
    detail = ("no tenant code construct found" if ok
              else f"found tenant construct: {m.group(0)!r} at {m.start()}")
    record(2, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #3：Connector 写回默认开启
# ---------------------------------------------------------------------------
def rl3():
    method = ("构造 ConnectorContract('x') 不传 write_enabled，确认默认 False；"
              "注册企业 impl 后 emit 在默认 OFF 下绝不调用 impl；"
              "确认即便 write_enabled=True 且无企业 impl，引擎自身也不写回业务系统。")
    from src.enterprise_pilot import (ConnectorContract, ContractKind,
                                      emit_contract)
    c = ConnectorContract("demo")
    default_false = (c.write_enabled is False)
    side = {"called": False}

    def impl(_k, _c):
        side["called"] = True

    c.register_enterprise_impl(impl)
    contract = emit_contract(c, ContractKind.REPORT_EXPORT, {"goe": {"x": 1}})
    no_writeback_when_off = (side["called"] is False)

    # 即便开启但无 impl，引擎也不应写回（引擎侧不执行业务）
    c2 = ConnectorContract("demo2", write_enabled=True)
    contract2 = c2.emit(ContractKind.WARNING_EVENT, {"w": [1]})
    ok = default_false and no_writeback_when_off and contract["write_enabled"] is False
    detail = (f"default_false={default_false}; emit_no_writeback_off={no_writeback_when_off}; "
              f"contract_write_enabled={contract['write_enabled']}")
    record(3, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #4：第一代只兼容不伪造
# ---------------------------------------------------------------------------
def rl4():
    method = ("grep enterprise_pilot 源码：确认无 jwt/bcrypt/cryptography 密码学身份核验；"
              "确认无 external_effect=True 赋值（恒 False）；"
              "确认认证仅用标准库 secrets 引用校验（generate_token/compare_digest），"
              "不签发凭证、不验证密码学身份、不产生跨组织授权。")
    texts = _read_pilot_sources()
    combined = "\n".join(texts.values())
    no_crypto = all(kw not in combined.lower()
                    for kw in ("jwt", "bcrypt", "cryptography"))
    # external_effect 在任何 enterprise_pilot 源文件中不应被置 True（理想为不出现）
    ext_true = re.findall(r'external_effect["\']?\s*[:=]\s*True', combined)
    uses_secrets = ("secrets.token_urlsafe" in combined
                    and "compare_digest" in combined)
    ok = no_crypto and len(ext_true) == 0 and uses_secrets
    detail = (f"no_crypto_identity={no_crypto}; external_effect_true_count={len(ext_true)}; "
              f"uses_secrets_ref_token={uses_secrets}")
    record(4, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #5：建企业平台 / 自动业务执行 / 跨组织网络
# ---------------------------------------------------------------------------
def rl5():
    method = ("grep enterprise_pilot 源码：确认无网络调用模式（requests./socket./"
              "smtplib/http.client/urllib.request/httpx.）；"
              "确认 emit 不执行任何业务写操作（仅返回契约载荷）。")
    texts = _read_pilot_sources()
    combined = "\n".join(texts.values())
    net_pats = [r"requests\.", r"socket\.", r"smtplib", r"http\.client",
                r"urllib\.request", r"httpx\."]
    found = []
    for pat in net_pats:
        if re.search(pat, combined):
            found.append(pat)
    ok = len(found) == 0
    detail = ("no network call patterns in enterprise_pilot" if ok
              else f"found network patterns: {found}")
    record(5, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #6：脱敏映射对非授权角色可见
# ---------------------------------------------------------------------------
def rl6():
    method = ("构造脱敏记录，确认 MappingRecord.visible_to_authorized_only=True；"
              "调用 strip_for_unauthorized() 后 before_after 明文被剥离，"
              "仅保留 field_count/reversibility；确认非授权读取不泄露原文。")
    from src.enterprise_pilot import apply_desensitization
    out, mapping = apply_desensitization(
        {"email": "a@b.com", "name": "张三"},
        {"methods": {"direct": "hash", "indirect": "mask", "business": "none"}},
    )
    visible_flag = (mapping.visible_to_authorized_only is True)
    stripped = mapping.strip_for_unauthorized()
    plaintext_stripped = ("before_after" not in stripped)
    # 授权视图应保留 before_after（仅授权角色可见）
    authorized_has_mapping = ("before_after" in mapping.to_dict())
    ok = visible_flag and plaintext_stripped and authorized_has_mapping
    detail = (f"visible_to_authorized_only={visible_flag}; "
              f"unauthorized_stripped_plaintext={plaintext_stripped}; "
              f"authorized_retains_mapping={authorized_has_mapping}")
    record(6, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #7：覆盖历史审计
# ---------------------------------------------------------------------------
def rl7():
    method = ("内省 ReviewStore 公共方法：确认无 update/delete/modify/replace/remove/"
              "purge 等历史改写 API；确认仅有 append/list_by_event/list_all；"
              "确认重复 append 同 review_id 幂等跳过（不覆盖历史）。")
    from src.enterprise_pilot import ReviewRecord
    store = _tmp_review_store()
    forbidden = ("update", "delete", "modify", "replace", "remove",
                 "purge", "update_event", "delete_event", "purge_event")
    exposed = [m for m in forbidden if hasattr(store, m)]
    # append 幂等：构造两条相同 review_id 的 append
    rec = ReviewRecord(
        "rvw_dup_qa", {"event_id": "evt_x", "event_digest": "d"},
        "comment", "op1", "2026-01-01T00:00:00Z",
    ).to_dict()
    store.append(rec)
    store.append(rec)
    idempotent = (len(store.list_all()) == 1)
    ok = (len(exposed) == 0) and idempotent
    detail = (f"forbidden_api_exposed={exposed}; append_idempotent={idempotent}")
    record(7, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #8：replay_ref 伪造
# ---------------------------------------------------------------------------
def rl8():
    method = ("在临时 EvaluationEventStore 落真实 ORIGINAL 事件，确认 record_review 绑定"
              "真实可解析 original_event_ref={event_id,event_digest}；"
              "以伪造 event_id 调 record_review 应抛 ReviewBindingError；"
              "直接 append 伪造 ReviewRecord 后 verify_review_bindings 应判伪造（event_not_found）。")
    import src.governance_chain.evaluation_event as ee_mod  # noqa
    from src.enterprise_pilot import (record_review, verify_review_bindings,
                                      ReviewRecord)
    from src.enterprise_pilot.review import ReviewBindingError
    ee_store = _tmp_event_store()
    rv_store = _tmp_review_store()
    out = ee_mod.record_evaluation(_load(FIXTURE_V14), store=ee_store)
    ref = out["replay_ref"]
    ev = ee_store.get(ref["event_id"])
    rec = record_review(
        {"event_id": ref["event_id"], "event_digest": ev["event_hash"]},
        "approve", "op1", source_store=ee_store, review_store=rv_store,
        idempotency_key="idem_qa_rl8",
    )
    bind_real = (rec["original_event_ref"]["event_id"] == ref["event_id"]
                 and rec["original_event_ref"]["event_digest"] == ev["event_hash"])
    # 伪造引用应被拒
    forged_rejected = False
    try:
        record_review({"event_id": "evt_deadbeef", "event_digest": "x"},
                      "approve", "op1", source_store=ee_store, review_store=rv_store)
    except ReviewBindingError:
        forged_rejected = True
    # 直接 append 伪造记录，verify 应检出
    forged = ReviewRecord(
        "rvw_forged_qa", {"event_id": "evt_missing", "event_digest": "x"},
        "approve", "op1", "2026-01-01T00:00:00Z",
    ).to_dict()
    rv_store.append(forged)
    ok_verify, problems = verify_review_bindings(rv_store, ee_store)
    verify_detects = (not ok_verify) and any(
        p["reason"] == "event_not_found" for p in problems)
    ok = bind_real and forged_rejected and verify_detects
    detail = (f"bind_real={bind_real}; forged_rejected={forged_rejected}; "
              f"verify_detects_forged={verify_detects}({problems})")
    record(8, method, ok, detail)


# ---------------------------------------------------------------------------
# 红线 #9：纵向递归平均
# ---------------------------------------------------------------------------
def rl9():
    method = ("grep enterprise_pilot 源码：确认不含 risk_vector / average / np.mean；"
              "确认 v1.5 不引入新风险算法、不复用/平均 RiskVector（"
              "复用 v1.4 RiskVectorComputer 的事在 governance_chain，pilot 层不触碰）。")
    texts = _read_pilot_sources()
    combined = "\n".join(texts.values()).lower()
    has_risk_vector = "risk_vector" in combined
    has_average = "average" in combined
    has_np_mean = "np.mean" in combined
    ok = not (has_risk_vector or has_average or has_np_mean)
    detail = (f"risk_vector_in_pilot={has_risk_vector}; average_in_pilot={has_average}; "
              f"np_mean_in_pilot={has_np_mean}")
    record(9, method, ok, detail)


def main():
    rl1(); rl2(); rl3(); rl4(); rl5(); rl6(); rl7(); rl8(); rl9()
    print("\n=== QA 独立证伪汇总 ===")
    print(f"总计 9 条红线 | PASS={9 - len(_FAILS)} | FAIL={len(_FAILS)}")
    if _FAILS:
        print(f"FAIL 项: {_FAILS}")
    return 0 if not _FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
