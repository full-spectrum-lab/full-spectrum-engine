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
ENGINE_VERSION = "v1.4.0"


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
            "relationships": [
                {"relation_type": "derived_from", "target_type": "raw_input", "target_id": raw_id}
            ],
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
            "relationships": [
                {"relation_type": "normalized_from", "target_type": "governance_event", "target_id": event_id},
                {"relation_type": "derived_from", "target_type": "raw_input", "target_id": raw_id},
            ],
        }

    def build_cell_manifest(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        manifest = {
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
        raw_id = doc["raw_input"]["raw_input_id"]
        manifest["relationships"] = [
            {"relation_type": "declared_for", "target_type": "raw_input", "target_id": raw_id}
        ]
        return manifest


class LogisticsAdapter(EcommerceAdapter):
    adapter_id = "logistics"
    CELL_ID = "logistics_ai_001"
    CELL_TYPE = "ai_logistics_observer"
    DOMAIN = "logistics_cold_chain"
    REVIEW_ROLE = "logistics_quality_supervisor"
    REVIEW_QUEUE = "cold_chain_review"
    RECOMMENDED_RESPONSE = "冷链证据不完整，需人工核验温控记录后再确认交付状态。"
    RISK_VECTOR = {"dimensions": ["survival", "coordination", "meaning"], "values": [0.81, 0.62, 0.38]}

    def build_governance_event(self, doc, timestamp=DEFAULT_TIMESTAMP):
        ri = doc["raw_input"]
        raw_id = ri["raw_input_id"]
        stem, num = _split_raw_id(raw_id)
        return {
            "event_id": f"ge_{stem}_coldchain_{num}", "event_type": "recommendation", "timestamp": timestamp,
            "actor": {"type": "ai_agent", "id": "agent.logistics.coldchain_001", "display_name": "Logistics Observer"},
            "action": {"type": "recommendation", "description": "The AI recommended accepting a shipment with incomplete cold-chain evidence."},
            "context": {"domain": "logistics_cold_chain", "data_mode": "synthetic", "case_type": "temperature_evidence_gap"},
            "declared_capability": {"can_review_shipping_evidence": True, "can_accept_shipment": False},
            "declared_boundary": {"requires_human_review_for_evidence_gap": True, "may_execute_enterprise_action": False},
            "risk_hint": {"risk_type": "evidence_gap", "risk_level": "high"},
            "review_requirement": "human_review_required",
            "source_reference": {"source_type": "synthetic_logistics_record", "source_id": raw_id},
            "relationships": [{"relation_type": "derived_from", "target_type": "raw_input", "target_id": raw_id}],
        }

    def build_canonical_context(self, doc, event_id, timestamp=DEFAULT_TIMESTAMP):
        ri = doc["raw_input"]
        raw_id = ri["raw_input_id"]
        stem, num = _split_raw_id(raw_id)
        complete = bool(ri.get("temperature_evidence_complete", False))
        return {
            "schema_version": "cc-0.1", "canonical_context_id": f"cc_{stem}_coldchain_{num}",
            "source_event_id": event_id, "actor": {"id": self.CELL_ID, "type": "ai_agent"},
            "action": {"intent": "shipment_acceptance_review", "commitment_type": "operational_recommendation", "authority_verified": complete},
            "authority": {"verified": complete, **({} if complete else {"reason_code": "LOGISTICS_EVIDENCE_INCOMPLETE", "reason": "Required cold-chain evidence is incomplete."})},
            "known_facts": [{"description": "Shipment is awaiting acceptance."}],
            "unknowns": [] if complete else [{"description": "Continuous temperature evidence is incomplete.", "severity": "high", "required_for_commitment": True}],
            "risk_axes": {"evidence_risk": 0.9 if not complete else 0.1, "coordination_risk": 0.7 if not complete else 0.2},
            "privacy": {"public_shareable": True, "redaction_status": "synthetic"}, "extension_fields": {},
            "relationships": [{"relation_type": "normalized_from", "target_type": "governance_event", "target_id": event_id}, {"relation_type": "derived_from", "target_type": "raw_input", "target_id": raw_id}],
        }


class KnowledgeConflictAdapter(EcommerceAdapter):
    adapter_id = "knowledge_conflict"
    CELL_ID = "knowledge_ai_001"
    CELL_TYPE = "ai_knowledge_observer"
    DOMAIN = "enterprise_knowledge_governance"
    REVIEW_ROLE = "knowledge_governance_owner"
    REVIEW_QUEUE = "knowledge_conflict_review"
    RECOMMENDED_RESPONSE = "知识源存在冲突，需由知识责任人确认生效版本后再答复。"
    RISK_VECTOR = {"dimensions": ["survival", "coordination", "meaning"], "values": [0.34, 0.76, 0.88]}

    def build_governance_event(self, doc, timestamp=DEFAULT_TIMESTAMP):
        ri = doc["raw_input"]
        raw_id = ri["raw_input_id"]
        stem, num = _split_raw_id(raw_id)
        return {
            "event_id": f"ge_{stem}_knowledge_{num}", "event_type": "recommendation", "timestamp": timestamp,
            "actor": {"type": "ai_agent", "id": "agent.knowledge.001", "display_name": "Knowledge Observer"},
            "action": {"type": "recommendation", "description": "The AI selected an answer while authoritative knowledge sources disagreed."},
            "context": {"domain": "enterprise_knowledge", "data_mode": "synthetic", "case_type": "knowledge_source_conflict"},
            "declared_capability": {"can_compare_sources": True, "can_resolve_authority_conflict": False},
            "declared_boundary": {"requires_human_review_for_source_conflict": True, "may_execute_enterprise_action": False},
            "risk_hint": {"risk_type": "knowledge_conflict", "risk_level": "high"},
            "review_requirement": "human_review_required",
            "source_reference": {"source_type": "synthetic_knowledge_sources", "source_id": raw_id},
            "relationships": [{"relation_type": "derived_from", "target_type": "raw_input", "target_id": raw_id}],
        }

    def build_canonical_context(self, doc, event_id, timestamp=DEFAULT_TIMESTAMP):
        ri = doc["raw_input"]
        raw_id = ri["raw_input_id"]
        stem, num = _split_raw_id(raw_id)
        resolved = bool(ri.get("conflict_resolved", False))
        return {
            "schema_version": "cc-0.1", "canonical_context_id": f"cc_{stem}_knowledge_{num}",
            "source_event_id": event_id, "actor": {"id": self.CELL_ID, "type": "ai_agent"},
            "action": {"intent": "answer_from_enterprise_knowledge", "commitment_type": "knowledge_recommendation", "authority_verified": resolved},
            "authority": {"verified": resolved, **({} if resolved else {"reason_code": "KNOWLEDGE_SOURCE_CONFLICT", "reason": "Authoritative sources disagree and no owner resolution is recorded."})},
            "known_facts": [{"description": "Two enterprise knowledge sources provide different answers."}],
            "unknowns": [] if resolved else [{"description": "The governing source version is unresolved.", "severity": "high", "required_for_commitment": True}],
            "risk_axes": {"knowledge_conflict_risk": 0.95 if not resolved else 0.1, "meaning_risk": 0.85 if not resolved else 0.2},
            "privacy": {"public_shareable": True, "redaction_status": "synthetic"}, "extension_fields": {},
            "relationships": [{"relation_type": "normalized_from", "target_type": "governance_event", "target_id": event_id}, {"relation_type": "derived_from", "target_type": "raw_input", "target_id": raw_id}],
        }


REGISTRY = {"ecommerce": EcommerceAdapter, "logistics": LogisticsAdapter, "knowledge_conflict": KnowledgeConflictAdapter}


def get_adapter(adapter_id: str) -> EcommerceAdapter:
    if adapter_id not in REGISTRY:
        raise ValueError(f"unknown adapter_id {adapter_id!r}; available: {sorted(REGISTRY)}")
    return REGISTRY[adapter_id]()
