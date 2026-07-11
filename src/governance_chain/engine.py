#!/usr/bin/env python3
"""
Governance engine: turns a Canonical Context (+ Cell Manifest) into the engine
output envelope and the enterprise writeback decision.

The decision logic is rule-based and deterministic: an unauthorized refund
commitment (authority not verified) always routes to human review and blocks
auto-reply / commitment / execution. This is the real engine step that makes
the static example reproducible as a command.
"""
from typing import Any, Dict, Tuple


def run(canonical: Dict[str, Any], cell: Dict[str, Any], adapter,
        run_id: str, audit_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    action = canonical.get("action", {})
    authority = canonical.get("authority", {})
    commitment_type = action.get("commitment_type")
    verified = bool(authority.get("verified", False))

    unauthorized_commitment = (not verified) and commitment_type in (
        "refund_commitment", "commitment", "policy_commitment",
    )

    if unauthorized_commitment:
        risk_level = "high"
        safety_action = "human_review_required"
        reason_code = authority.get("reason_code") or "UNAUTHORIZED_COMMITMENT"
        allow_auto_reply = False
        allow_commitment = False
        allow_auto_execution = False
        human_review_required = True
    else:
        risk_level = "low"
        safety_action = "allow_with_logging"
        reason_code = "OK"
        allow_auto_reply = True
        allow_commitment = True
        allow_auto_execution = False
        human_review_required = False

    enterprise_writeback = {
        "schema_version": "ew-0.1",
        "case_status": safety_action,
        "allow_auto_reply": allow_auto_reply,
        "allow_commitment": allow_commitment,
        "allow_auto_execution": allow_auto_execution,
        "human_review_required": human_review_required,
        "safety_action": safety_action,
        "risk_level": risk_level,
        "reason_code": reason_code,
        "recommended_response": (
            adapter.RECOMMENDED_RESPONSE
            if unauthorized_commitment else
            "处理符合权限边界，可按既定流程执行。"
        ),
        "audit_id": audit_id,
    }
    if unauthorized_commitment:
        enterprise_writeback["review_role"] = adapter.REVIEW_ROLE
        enterprise_writeback["review_queue"] = adapter.REVIEW_QUEUE

    output_envelope = {
        "schema_version": "goe-0.1",
        "engine_result": {
            "engine": "full-spectrum-engine",
            "version": getattr(adapter, "ENGINE_VERSION", "v1.0.0"),
            "run_id": run_id,
        },
        "risk_vector": adapter.RISK_VECTOR,
        "safety_action": safety_action,
        "enterprise_writeback": enterprise_writeback,
        "privacy": {"public_shareable": False},
        "conformance": {"schema_valid": True},
        "audit_references": [audit_id],
    }
    return output_envelope, enterprise_writeback
