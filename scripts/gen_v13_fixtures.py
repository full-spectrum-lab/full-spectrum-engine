#!/usr/bin/env python3
"""
Generate v1.3 Profile / Scenario fixtures with correct, recomputable digests.

This is a reproducible dev aid. It writes:
  * src/governance_chain/profiles/fixtures/*.json   (13 ecommerce + 3 logistics)
  * src/governance_chain/scenarios/fixtures/*.json  (3 scenarios)
  * tests/fixtures/profiles/*.json                  (copies of the 13 ecommerce)
  * tests/fixtures/scenarios/*.json                 (copies of the 3 scenarios)
  * tests/fixtures/certification/*.json             (requirement + attestation samples)

The digest of every object is SHA-256(canonical_json(obj without its digest
field)), matching the runtime registry recomputation, so fixtures validate and
reproduce exactly.

Run:  python scripts/gen_v13_fixtures.py
"""
import hashlib
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_of(obj):
    clean = {k: v for k, v in obj.items() if k != "digest"}
    return hashlib.sha256(canonical_json(clean).encode("utf-8")).hexdigest()


def finalize(obj):
    obj = dict(obj)
    obj["digest"] = digest_of(obj)
    return obj


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ----------------------------------------------------------------
# 13 ecommerce domain profiles (one per SRS §3.1 type) + 3 logistics
# ----------------------------------------------------------------
PROFILES = [
    # 1. LayerProfile (combo container)
    {
        "id": "prof_layer_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "LayerProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce layer profile", "status": "active",
        "domain": {
            "reference_profiles": ["prof_fshi_ecom_001@1.0.0", "prof_risk_ecom_001@1.0.0", "prof_validation_ecom_001@1.0.0"],
            "target_layers": ["L1", "L2", "L3"],
        },
    },
    # 2. FSHIProfile (carries measurement weights)
    {
        "id": "prof_fshi_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "FSHIProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce FSHI profile", "status": "active",
        "domain": {
            "parameters": {"weights": {"commitment_risk": 0.5, "authority_risk": 0.3, "knowledge_conflict_risk": 0.2}},
            "target_layers": ["L1", "L2"],
        },
    },
    # 3. RiskProfile
    {
        "id": "prof_risk_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "RiskProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce risk profile", "status": "active",
        "domain": {
            "parameters": {"weights": {"authority_risk": 0.4, "evidence_gap_risk": 0.3, "coordination_risk": 0.3}},
        },
    },
    # 4. ESSProfile
    {
        "id": "prof_ess_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "ESSProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce ESS profile", "status": "active",
        "domain": {"parameters": {"thresholds": {"survival": 0.5, "meaning": 0.5}}},
    },
    # 5. ValidationProfile (evaluation policy: thresholds)
    {
        "id": "prof_validation_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "ValidationProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce validation profile", "status": "active",
        "domain": {"parameters": {"thresholds": {"commitment_risk": 0.6, "authority_risk": 0.6}}},
    },
    # 6. HumanReviewProfile
    {
        "id": "prof_human_review_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "HumanReviewProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce human review profile", "status": "active",
        "domain": {"parameters": {"trigger_conditions": ["unknown_evidence", "hard_forbidden_condition"]}},
    },
    # 7. AggregationProfile
    {
        "id": "prof_aggregation_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "AggregationProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce aggregation profile", "status": "active",
        "domain": {"parameters": {"method": "no_average", "note": "纵向递归不平均"}},
    },
    # 8. ReportTemplate
    {
        "id": "prof_report_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "ReportTemplate", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce report template", "status": "active",
        "domain": {"template_id": "ecom_report_v1", "sections": ["summary", "risks", "review"]},
    },
    # 9. TrustDomainProfile
    {
        "id": "prof_trust_domain_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "TrustDomainProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce trust domain profile", "status": "active",
        "domain": {"trust_domains": ["example.enterprise.internal", "external.ca.org"]},
    },
    # 10. InteropProfile
    {
        "id": "prof_interop_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "InteropProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce interop profile", "status": "active",
        "domain": {"l4_modes": ["DISABLED", "LOCAL_SIMULATION", "NETWORK_CANDIDATE"], "protocols": ["l4_candidate"]},
    },
    # 11. CertificationRequirementProfile
    {
        "id": "prof_cert_req_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "CertificationRequirementProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce certification requirement", "status": "active",
        "domain": {
            "logic": "ALL_OF", "n": 1,
            "requirements": [
                {"issuer": "enterprise_cert_node_001", "scope": "enterprise_private", "trust_domain": "example.enterprise.internal", "not_revoked": True},
                {"issuer": "external_ca", "scope": "external", "trust_domain": "external.ca.org", "not_revoked": True},
            ],
        },
    },
    # 12. AuthorizationGateProfile (local conditions only; no execution)
    {
        "id": "prof_auth_gate_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "AuthorizationGateProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce auth gate profile", "status": "active",
        "domain": {"local_conditions": [{"gate": "qualification", "required": True}], "note": "仅本地资格条件，不执行"},
    },
    # 13. ActivationProfile
    {
        "id": "prof_activation_ecom_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "ActivationProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial ecommerce activation profile", "status": "active",
        "domain": {"lifecycle_status": "active", "exit_policy": "graceful_shutdown_with_audit_snapshot"},
    },
    # 14. logistics LayerProfile
    {
        "id": "prof_layer_logi_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "LayerProfile", "scope": "internal",
        "owner": "logistics_cert_node_001", "approved_by": "logistics_quality_supervisor",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial logistics layer profile", "status": "active",
        "domain": {
            "reference_profiles": ["prof_fshi_logi_001@1.0.0", "prof_risk_logi_001@1.0.0"],
            "target_layers": ["L1", "L2"],
        },
    },
    # 15. logistics FSHIProfile
    {
        "id": "prof_fshi_logi_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "FSHIProfile", "scope": "internal",
        "owner": "logistics_cert_node_001", "approved_by": "logistics_quality_supervisor",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial logistics FSHI profile", "status": "active",
        "domain": {"parameters": {"weights": {"evidence_risk": 0.6, "coordination_risk": 0.4}}},
    },
    # 16. logistics RiskProfile
    {
        "id": "prof_risk_logi_001", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "RiskProfile", "scope": "internal",
        "owner": "logistics_cert_node_001", "approved_by": "logistics_quality_supervisor",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial logistics risk profile", "status": "active",
        "domain": {"parameters": {"weights": {"evidence_risk": 0.5, "coordination_risk": 0.5}}},
    },
]

SCENARIOS = [
    {
        "id": "scn_overcommitment_001", "version": "1.0.0", "schema_version": "scenario-1.0",
        "scenario_type": "Overcommitment", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial overcommitment scenario", "status": "active",
        "domain": {
            "description": "越权承诺：在无已确认权限时作出超出权限的承诺",
            "triggers": [{"event": "commitment", "condition": "refund_authority == false"}],
            "hard_forbidden_conditions": [
                {
                    "id": "overcommitment_without_authority",
                    "description": "在无已确认退款权限时承诺全额退款",
                    "field": "business_data.refund_authority",
                    "op": "equals",
                    "value": False,
                }
            ],
        },
    },
    {
        "id": "scn_customer_service_audit_001", "version": "1.0.0", "schema_version": "scenario-1.0",
        "scenario_type": "CustomerServiceAudit", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial customer service audit scenario", "status": "active",
        "domain": {
            "description": "客服审计：未完成人工复核即给出确定性承诺",
            "triggers": [{"event": "commitment", "condition": "human_review_completed == false"}],
            "hard_forbidden_conditions": [
                {
                    "id": "cs_audit_without_human_review",
                    "description": "未完成人工复核即给出确定性承诺",
                    "field": "business_data.human_review_completed",
                    "op": "equals",
                    "value": False,
                }
            ],
        },
    },
    {
        "id": "scn_knowledge_conflict_001", "version": "1.0.0", "schema_version": "scenario-1.0",
        "scenario_type": "KnowledgeConflict", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "initial knowledge conflict scenario", "status": "active",
        "domain": {
            "description": "知识冲突：权威知识源冲突未解决即选定答案",
            "triggers": [{"event": "recommendation", "condition": "conflict_resolved == false"}],
            "hard_forbidden_conditions": [
                {
                    "id": "knowledge_source_conflict_unresolved",
                    "description": "权威知识源冲突未解决即选定答案",
                    "field": "business_data.conflict_resolved",
                    "op": "equals",
                    "value": False,
                }
            ],
        },
    },
]


def main():
    src_profiles = os.path.join(REPO_ROOT, "src", "governance_chain", "profiles", "fixtures")
    src_scenarios = os.path.join(REPO_ROOT, "src", "governance_chain", "scenarios", "fixtures")
    test_profiles = os.path.join(REPO_ROOT, "tests", "fixtures", "profiles")
    test_scenarios = os.path.join(REPO_ROOT, "tests", "fixtures", "scenarios")
    test_cert = os.path.join(REPO_ROOT, "tests", "fixtures", "certification")

    written = 0
    for p in PROFILES:
        obj = finalize(p)
        write_json(os.path.join(src_profiles, p["id"] + ".json"), obj)
        # ecommerce domain profiles also mirrored to tests/fixtures/profiles
        if p["id"].endswith("_ecom_001"):
            write_json(os.path.join(test_profiles, p["id"] + ".json"), obj)
        written += 1
    for s in SCENARIOS:
        obj = finalize(s)
        write_json(os.path.join(src_scenarios, s["id"] + ".json"), obj)
        write_json(os.path.join(test_scenarios, s["id"] + ".json"), obj)
        written += 1

    # Certification test fixtures (plain dicts; loaded directly by the test suite)
    cert_requirement = {
        "id": "cert_req_sample_allof", "version": "1.0.0", "schema_version": "profile-1.0",
        "profile_type": "CertificationRequirementProfile", "scope": "internal",
        "owner": "enterprise_cert_node_001", "approved_by": "knowledge_governance_owner",
        "approval_status": "approved", "effective_from": "2026-01-01", "effective_until": "2027-12-31",
        "supersedes": [], "change_reason": "sample ALL_OF requirement", "status": "active",
        "domain": {
            "logic": "ALL_OF", "n": 1,
            "requirements": [
                {"issuer": "enterprise_cert_node_001", "scope": "enterprise_private", "trust_domain": "example.enterprise.internal", "not_revoked": True},
                {"issuer": "external_ca", "scope": "external", "trust_domain": "external.ca.org", "not_revoked": True},
            ],
        },
    }
    cert_requirement_any = dict(cert_requirement)
    cert_requirement_any["id"] = "cert_req_sample_anyof"
    cert_requirement_any["domain"] = {"logic": "ANY_OF", "n": 1, "requirements": cert_requirement["domain"]["requirements"]}
    cert_requirement_atn = dict(cert_requirement)
    cert_requirement_atn["id"] = "cert_req_sample_atleast"
    cert_requirement_atn["domain"] = {"logic": "AT_LEAST_N", "n": 2, "requirements": cert_requirement["domain"]["requirements"]}
    cert_requirement_one = dict(cert_requirement)
    cert_requirement_one["id"] = "cert_req_sample_oneof"
    cert_requirement_one["domain"] = {"logic": "ONE_OF", "n": 1, "requirements": cert_requirement["domain"]["requirements"]}
    cert_requirement_not = dict(cert_requirement)
    cert_requirement_not["id"] = "cert_req_sample_notrequired"
    cert_requirement_not["domain"] = {"logic": "NOT_REQUIRED", "n": 1, "requirements": []}

    attestations_internal = [
        {"issuer": "enterprise_cert_node_001", "scope": "enterprise_private", "trust_domain": "example.enterprise.internal",
         "valid_from": "2026-01-01", "valid_until": "2027-12-31", "revoked": False},
    ]
    attestations_external = [
        {"issuer": "enterprise_cert_node_001", "scope": "enterprise_private", "trust_domain": "example.enterprise.internal",
         "valid_from": "2026-01-01", "valid_until": "2027-12-31", "revoked": False},
        {"issuer": "external_ca", "scope": "external", "trust_domain": "external.ca.org",
         "valid_from": "2026-01-01", "valid_until": "2027-12-31", "revoked": False},
    ]
    attestations_revoked = [
        {"issuer": "enterprise_cert_node_001", "scope": "enterprise_private", "trust_domain": "example.enterprise.internal",
         "valid_from": "2026-01-01", "valid_until": "2027-12-31", "revoked": True},
    ]

    for name, obj in [
        ("requirement_allof", cert_requirement),
        ("requirement_anyof", cert_requirement_any),
        ("requirement_atleast_n", cert_requirement_atn),
        ("requirement_oneof", cert_requirement_one),
        ("requirement_not_required", cert_requirement_not),
        ("attestations_internal", attestations_internal),
        ("attestations_external", attestations_external),
        ("attestations_revoked", attestations_revoked),
    ]:
        write_json(os.path.join(test_cert, name + ".json"), obj)
        written += 1

    print(f"wrote {written} fixture files")


if __name__ == "__main__":
    main()
