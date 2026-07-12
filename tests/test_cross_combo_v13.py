#!/usr/bin/env python3
"""
v1.3 四组交叉组合（cross-combo）测试套件 (FR-01/FR-05/FR-06/FR-07).

覆盖 SRS §3 要求的 4 组行业 × 场景 组合：
    ecommerce_customer_service × knowledge_conflict
    ecommerce_customer_service × overcommitment
    logistics_cold_chain       × knowledge_conflict
    logistics_cold_chain       × overcommitment

每个组合都经过 run_envelope，验证：
  * 加法扩展后 Output Envelope 仍满足 goe-1.2 schema（含 v1.3 可选字段）
  * risk_vector 由 Profile 驱动（profile_driven / deterministic）
  * scenario 的 hard_forbidden 条件被显式命中（不平均、不静默通过）
  * ecommerce 组合携带 certification_requirement_refs + attestations ->
        eligibility_candidate 仅输出候选态，multi trust-domain 结果为 dict（不合并）
  * logistics 组合不携带 certification -> 无 eligibility_candidate
  * 全局铁律：external_effect 恒为 False，replay_ref 恒为 None
  * 确定性：同输入两次 content_digest 一致
"""
import json
import os
import unittest

from src.governance_chain import envelope as env

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "cross_combo")

COMBOS = {
    "ecom_kc": "cross_ecom_knowledge_conflict.json",
    "ecom_oc": "cross_ecom_overcommitment.json",
    "logi_kc": "cross_logi_knowledge_conflict.json",
    "logi_oc": "cross_logi_overcommitment.json",
}


def _load(name):
    return json.load(open(os.path.join(FIX, COMBOS[name]), encoding="utf-8-sig"))


def _run(name):
    return env.run_envelope(_load(name))


class TestCrossComboSchema(unittest.TestCase):
    """每一组交叉组合的输出都必须满足 goe-1.2 schema。"""

    def test_all_combos_schema_valid(self):
        for name in COMBOS:
            out = _run(name)
            ok, errors = env.validate_output_envelope(out)
            self.assertTrue(ok, f"{name} schema invalid: {errors}")
            # 全局铁律：external_effect 恒 False，replay_ref 恒 None
            self.assertIs(out["external_effect"], False)
            self.assertIsNone(out["replay_ref"])


class TestProfileDrivenRiskVector(unittest.TestCase):
    """risk_vector 必须由 Profile 驱动且确定性。"""

    def test_profile_driven_and_deterministic(self):
        for name in COMBOS:
            out = _run(name)
            rv = out["risk_vector"]
            self.assertTrue(rv["profile_driven"], f"{name}: not profile_driven")
            self.assertTrue(rv["deterministic"], f"{name}: not deterministic")
            self.assertEqual(rv["computation"], "profile_driven_v1.3")
            # source_profile_versions 暴露用于 v1.4 replay，且非空
            self.assertTrue(rv["source_profile_versions"])
            # 维度与权重点数一一对应
            self.assertEqual(len(rv["dimensions"]), len(rv["values"]))
            # 所有分值落在 [0,1]
            for v in rv["values"]:
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)

    def test_source_versions_expose_fshi_risk_validation(self):
        out = _run("ecom_kc")
        sv = out["risk_vector"]["source_profile_versions"]
        # ecommerce 组合：FSHI + Risk + Validation 三类源 Profile 的 id@version
        self.assertIn("prof_fshi_ecom_001@1.0.0", sv)
        self.assertIn("prof_risk_ecom_001@1.0.0", sv)
        self.assertIn("prof_validation_ecom_001@1.0.0", sv)


class TestScenarioHardForbidden(unittest.TestCase):
    """scenario 的 hard_forbidden 条件被显式命中，且 scenario_refs 被记录。"""

    def test_hard_forbidden_triggered_all_combos(self):
        for name in COMBOS:
            out = _run(name)
            self.assertTrue(out["scenario_refs"], f"{name}: scenario_refs empty")
            # 四个组合的业务数据均触发各自的 hard_forbidden 条件
            self.assertTrue(out["hard_forbidden"], f"{name}: hard_forbidden empty")
            # 命中后必须触发人工复核（显式，不靠聚合分掩盖）
            self.assertTrue(out["human_review_recommendation"]["required"])
            self.assertIn("hard_forbidden_condition",
                          out["human_review_recommendation"]["reason"])

    def test_knowledge_conflict_condition_id(self):
        out = _run("ecom_kc")
        ids = [h["condition_id"] for h in out["hard_forbidden"]]
        self.assertIn("knowledge_source_conflict_unresolved", ids)


class TestCertificationCandidateOnly(unittest.TestCase):
    """认证仅输出候选态；multi trust-domain 结果为 dict（绝不合并为单一 bool）。"""

    def test_ecom_combos_carry_eligibility_candidate(self):
        for name in ("ecom_kc", "ecom_oc"):
            out = _run(name)
            elig = out.get("eligibility_candidate")
            self.assertIsNotNone(elig, f"{name}: eligibility_candidate missing")
            self.assertIn(elig["eligibility_candidate"],
                          ("CANDIDATE", "NOT_CANDIDATE", "UNKNOWN"))
            # 反模式红线：绝不能出现 certified / authorized 结论字段
            self.assertNotIn("certified", elig)
            self.assertNotIn("authorized", elig)
            self.assertNotIn("active", elig)

    def test_ecom_kc_multi_trust_domain_not_merged(self):
        out = _run("ecom_kc")
        elig = out["eligibility_candidate"]
        tdr = elig["trust_domain_results"]
        # 两个 trust domain 分别为独立 bool，绝不合并为一个
        self.assertEqual(set(tdr.keys()),
                         {"example.enterprise.internal", "external.ca.org"})
        self.assertIsInstance(tdr["example.enterprise.internal"], bool)
        self.assertIsInstance(tdr["external.ca.org"], bool)
        # 存在外部 trust domain -> 需要外部授权（候选态，非结论）
        self.assertTrue(elig["external_auth_required"])
        self.assertEqual(elig["eligibility_candidate"], "CANDIDATE")

    def test_logi_combos_no_eligibility(self):
        for name in ("logi_kc", "logi_oc"):
            out = _run(name)
            self.assertIsNone(
                out.get("eligibility_candidate"),
                f"{name}: logistics combo must not carry eligibility (no cert ref)",
            )


class TestDeterminism(unittest.TestCase):
    """同输入两次执行，content_digest 与 source_profile_versions 一致（AC-03）。"""

    def test_deterministic(self):
        for name in COMBOS:
            a = _run(name)
            b = _run(name)
            self.assertEqual(a["content_digest"], b["content_digest"],
                             f"{name}: content_digest not stable")
            self.assertEqual(
                a["risk_vector"]["source_profile_versions"],
                b["risk_vector"]["source_profile_versions"],
                f"{name}: source_profile_versions not stable",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
