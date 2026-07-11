#!/usr/bin/env python3
"""
Business adapters: map a raw business input into the Full Spectrum governance
object chain (Governance Event + Canonical Context + Cell Manifest).

The EcommerceAdapter reproduces the documented ecommerce after-sales
unauthorized-refund example end-to-end, so the CLI output is byte-for-byte
reproducible against the protocol repo's committed example
(examples/cases/ecommerce_chain/...).

ID convention for the ecommerce adapter (deterministic from raw_input_id):
    raw_input_id "raw_ecom_001" -> stem "ecom", num "001"
    event_id       "ge_ecom_refund_001"
    canonical_id   "cc_ecom_refund_001"
    run_id         "run_ecom_001"
    audit_id       "audit_ecom_001"
"""
from typing import Any, Dict


DEFAULT_TIMESTAMP = "2026-07-11T09:00:00Z"
ENGINE_VERSION = "v1.0.0"


def _split_raw_id(raw_input_id: str):
    num = raw_input_id.rsplit("_", 1)[-1]
    stem = raw_input_id[len("raw_"):].rsplit("_", 1)[0]
    return stem, num


class EcommerceAdapter:
    adapter_id = "ecommerce"

    # --- subject / cell identity (certified declaration, fixed) ---
    CELL_ID = "cs_ai_001"
    CELL_TYPE = "ai_customer_service"
    DOMAIN = "ecommerce_after_sales"
    REVIEW_ROLE = "customer_service_supervisor"
    REVIEW_QUEUE = "after_sales_review"
    RECOMMENDED_RESPONSE = "当前信息不足，需人工核实退款权限后再处理。"
    # baseline risk vector for this scenario class (engine profile)
    RISK_VECTOR = {
        "dimensions": ["survival", "coordination", "meaning"],
        "values": [0.72, 0.41, 0.55],
    }
    ENGINE_VERSION = ENGINE_VERSION

    def build_governance_event(self, doc: Dict[str, Any], timestamp: str = DEFAULT_TIMESTAMP) -> Dict[str, Any]:
        ri = doc["raw_input"]
        raw_id = ri["raw_input_id"]
        stem, num = _split_raw_id(raw_id)
        event_id = f"ge_{stem}_refund_{num}"
        refund_authority = bool(ri.get("refund_authority", False))
        return {
            "event_id": event_id,
            "event_type": "commitment",
            "timestamp": timestamp,
            "actor": {
                "type": "ai_agent",
                "id": "agent.customer_service.ecom_001",
                "display_name": "Ecommerce Customer Service Agent",
            },
            "action": {
                "type": "commitment",
                "description": "The AI agent promised a full refund without confirmed refund authority.",
            },
            "context": {
                "domain": "ecommerce_customer_service",
                "data_mode": "synthetic",
                "channel": "chat",
                "case_type": "refund_conflict",
            },
            "declared_capability": {
                "can_explain_policy": True,
                "can_collect_information": True,
                "can_commit_refund": refund_authority,
            },
            "declared_boundary": {
                "requires_human_review_for_refund": True,
                "may_execute_enterprise_action": False,
            },
            "risk_hint": {
                "risk_type": "unauthorized_commitment",
                "risk_level": "high",
            },
            "review_requirement": "human_review_required",
            "source_reference": {
                "source_type": "synthetic_dialogue",
                "source_id": raw_id,
            },
        }

    def build_canonical_context(self, doc: Dict[str, Any], event_id: str,
                                timestamp: str = DEFAULT_TIMESTAMP) -> Dict[str, Any]:
        ri = doc["raw_input"]
        raw_id = ri["raw_input_id"]
        stem, num = _split_raw_id(raw_id)
        refund_authority = bool(ri.get("refund_authority", False))
        human_review = bool(ri.get("human_review_completed", False))
        cc_id = f"cc_{stem}_refund_{num}"
        authority_verified = refund_authority
        authority = {"verified": authority_verified}
        if not authority_verified:
            authority["reason_code"] = "REFUND_COMMITMENT_WITHOUT_AUTHORITY"
            authority["reason"] = "AI customer-service agent lacks refund commitment authority."
        return {
            "schema_version": "cc-0.1",
            "canonical_context_id": cc_id,
            "source_event_id": event_id,
            "actor": {"id": self.CELL_ID, "type": "ai_agent"},
            "action": {
                "intent": "refund_request",
                "commitment_type": "refund_commitment",
                "authority_verified": authority_verified,
            },
            "authority": authority,
            "known_facts": [
                {"description": "User requested a refund."},
                {"description": "AI made a full-refund commitment without authority."},
            ],
            "unknowns": [
                {
                    "description": "Human review has not been completed.",
                    "severity": "high",
                    "required_for_commitment": (not human_review),
                }
            ] if not human_review else [],
            "risk_axes": {
                "commitment_risk": 0.9 if not authority_verified else 0.3,
                "authority_risk": 0.9 if not authority_verified else 0.1,
                "knowledge_conflict_risk": 0.1,
            },
            "privacy": {"public_shareable": True, "redaction_status": "synthetic"},
            "extension_fields": {},
        }

    def build_cell_manifest(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "cell_id": self.CELL_ID,
            "cell_type": self.CELL_TYPE,
            "domain": self.DOMAIN,
            "certification": {
                "issuer_type": "enterprise",
                "issuer_id": "enterprise_cert_node_001",
                "trust_domain": "example.enterprise.internal",
                "certification_scope": "enterprise_private",
            },
            "capability_scope": ["explain_public_policy", "collect_required_materials"],
            "boundary_scope": ["no_refund_commitment_without_authority"],
            "forbidden_claims": ["full_refund_without_authority"],
            "unknown_policy": "declare_unknown_and_escalate",
            "human_anchor": {"anchor_type": "role", "anchor_id": self.REVIEW_ROLE},
            "lifecycle": {"status": "active", "exit_policy": "graceful_shutdown_with_audit_snapshot"},
        }


REGISTRY = {"ecommerce": EcommerceAdapter}


def get_adapter(adapter_id: str) -> EcommerceAdapter:
    if adapter_id not in REGISTRY:
        raise ValueError(f"unknown adapter_id {adapter_id!r}; available: {sorted(REGISTRY)}")
    return REGISTRY[adapter_id]()
