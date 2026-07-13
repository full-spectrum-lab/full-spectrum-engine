#!/usr/bin/env python3
"""
Full Spectrum Engine API — Pydantic request/response models.

Design principles:
    - Request fields use irreversibility (P0-2 fix, aligned with v0.4)
    - include_input_metrics defaults to false (P1-5 privacy minimization)
    - Mutable default values use Field(default_factory=...) (P1-3 prevents bare 500)
    - Response body strictly compatible with CLI output, no envelope (P1-1)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ============================================================
# Request models
# ============================================================

class EvaluateRequest(BaseModel):
    """
    POST /api/v1/evaluate request body

    Supports two modes:
    1. Direct mode: pass a complete scenario dict, equivalent to simulate.py --config
    2. Adapter mode: pass industry + metrics, MetricAdapter builds the scenario automatically

    Exactly one mode must be used.
    """
    # Direct mode: complete scenario dict (matches simulate.py JSON format)
    scenario: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Direct mode: complete scenario config, matches simulate.py --config JSON format"
    )
    # Adapter mode
    industry: Optional[str] = Field(
        default=None,
        description="Adapter mode: industry identifier, e.g. 'ecommerce_customer_service'"
    )
    metrics: Optional[Dict[str, float]] = Field(
        default=None,
        description="Adapter mode: business metrics dict, keys are metric names, values are [0,1] normalized"
    )

    # Common parameters
    seed: int = Field(
        default=42,
        description="Random seed for deterministic simulation. Default 42"
    )
    include_input_metrics: bool = Field(
        default=False,
        description="Whether to include raw business metrics in response (privacy minimization: default false)"
    )

    # Adapter mode optional parameters
    simulation_id: Optional[str] = Field(
        default=None,
        description="Adapter mode: simulation ID (direct mode reads from scenario)"
    )
    input_query: Optional[str] = Field(
        default=None,
        description="Adapter mode: scenario description"
    )
    sensitivity_level: str = Field(
        default="medium",
        description="Adapter mode: sensitivity level (low/medium/high)"
    )
    enterprise_id: str = Field(
        default="default",
        description="Adapter mode: enterprise ID"
    )
    rule_version: str = Field(
        default="v0.3",
        description="Adapter mode: rule version"
    )
    subject_declaration: Optional[Dict[str, Any]] = Field(
        default=None,
        description="v1.1 Subject Declaration; validated locally and retained as subject_ref only"
    )


class EnvelopeRequest(BaseModel):
    """
    POST /api/v1/envelope request body (v1.2 Observer Input/Output Envelope contract).

    The body IS the v1.2 Input Envelope (see input-envelope.schema.json / gie-1.2).
    The response body is the v1.2 Output Envelope, produced by the exact same
    `src.governance_chain.envelope.run_envelope` function the CLI uses, so the
    REST and CLI outputs are byte-for-byte equivalent (FR-03 / AC-01).
    """
    input_envelope: Dict[str, Any] = Field(
        ...,
        description="v1.2 Input Envelope: layer/scope/subject_refs/business_data/unknowns/gate/l4_mode ..."
    )


class ProfileLoadRequest(BaseModel):
    """
    POST /api/v1/profile/load request body (v1.3 Profile load, additive endpoint).

    The body is a single Profile JSON conforming to profile.schema.json. No
    authentication is added (local / offline posture, consistent with v1.2).
    """
    profile: Dict[str, Any] = Field(
        ...,
        description="A Profile JSON conforming to profile.schema.json (13 profile_type values)."
    )


class PolicyLoadRequest(BaseModel):
    """
    POST /api/v1/policy/load request body (v1.3 Policy load, additive endpoint).

    The body is a governance policy JSON. It is validated but never executed by
    the Observer (first-gen only compatible, not forge).
    """
    policy: Dict[str, Any] = Field(
        ...,
        description="A governance policy JSON (policy_id/version/source/approved_by/change_log/rules/default)."
    )


# ============================================================
# v1.4 Replay & Audit additive request models
# ============================================================

class EvaluationRecordRequest(BaseModel):
    """
    POST /api/v1/evaluation/record request body (v1.4, additive endpoint).

    The body IS a v1.2 Input Envelope; the response is the audited goe-1.2 with a
    real, resolvable ``replay_ref`` (FR-01 / FR-03).
    """
    input_envelope: Dict[str, Any] = Field(
        ...,
        description="v1.2 Input Envelope (gie-1.2) to analyze and record.",
    )
    externalize_input: bool = Field(
        default=False,
        description="NFR-03: when true, the input is not inlined; only input_ref is kept.",
    )
    clock: Optional[str] = Field(
        default=None,
        description="Pinned ISO-8601 clock for deterministic recorded_at.",
    )


class ReplayRequest(BaseModel):
    """
    POST /api/v1/replay request body (v1.4, additive endpoint).

    Replay either a serialized ReplayBundle (``bundle``) or a stored event by id
    (``event_id``). ``policy_version`` overrides the policy binding (FR-05);
    ``replay_mode`` is EXACT/SEMANTIC/EXPLANATORY.
    """
    bundle: Optional[Dict[str, Any]] = Field(
        default=None,
        description="A serialized ReplayBundle dict.",
    )
    event_id: Optional[str] = Field(
        default=None,
        description="Stored EvaluationEvent id to replay (replay-by-event-id).",
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Override the policy version used for the replay (FR-05).",
    )
    replay_mode: str = Field(
        default="EXACT",
        description="Replay mode: EXACT | SEMANTIC | EXPLANATORY.",
    )


class AuditExportRequest(BaseModel):
    """
    POST /api/v1/audit/export request body (v1.4, additive endpoint).

    Exports the full append-only chain as canonical JSONL. ``limit`` bounds the
    number of events returned (default: all).
    """
    limit: int = Field(
        default=1_000_000,
        description="Maximum number of events to export (default: all).",
    )


class AuditVerifyRequest(BaseModel):
    """
    POST /api/v1/audit/verify request body (v1.4, additive endpoint).

    Verifies the append-only chain integrity (tamper detection). No body fields
    are required.
    """



class RunestoneRequest(BaseModel):
    """
    POST /api/v1/runestone request body

    Generate a standalone runestone audit token without the full simulation pipeline.
    """
    decision: str = Field(
        ...,
        description="Decision option, e.g. 'W3'"
    )
    reason: Dict[str, str] = Field(
        ...,
        description="Audit reason, must contain enterprise_id and rule_version"
    )
    risk_vector: Dict[str, float] = Field(
        ...,
        description="Eight-dimensional risk vector, must contain survival_impact/trust_impact/meaning_impact/reversibility/explainability/diffusivity/urgency/uncertainty"
    )
    parent_runestone: Optional[str] = Field(
        default=None,
        description="Parent runestone ID (for chain auditing)"
    )
    agent_trail: List[str] = Field(
        default_factory=list,
        description="Participating agent list"
    )
    ess_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="ESS snapshot data"
    )
    seed: int = Field(
        default=42,
        description="Random seed (affects runestone_id generation)"
    )


# ============================================================
# Response models (only for /health; other endpoints return raw dicts)
# ============================================================

class HealthResponse(BaseModel):
    """
    GET /api/v1/health response body

    health is the only endpoint with a custom response structure.
    All other endpoints return a body strictly compatible with CLI output.

    v0.6: storage_mode default updated to sqlite-persistent.
    v0.6: Added db_path/db_size_bytes/decision_count/runestone_count/ttl_days/max_records (optional fields).
    """
    status: str = Field(description="Service status: 'ok'")
    version: str = Field(description="API version number")
    engine_version: str = Field(description="Engine version number")
    registered_adapters: List[str] = Field(
        description="List of registered adapter industry identifiers"
    )
    storage_mode: str = Field(
        default="sqlite-persistent",
        description="Storage mode: 'sqlite-persistent' (v0.6 SQLite persistence)"
    )
    network_exposure: str = Field(
        default="local",
        description="Network exposure level: 'local' (127.0.0.1) or 'non-local' (0.0.0.0)"
    )
    # v0.6 optional fields (backward compatible)
    db_path: Optional[str] = Field(default=None, description="SQLite database absolute path")
    db_size_bytes: Optional[int] = Field(default=None, description="Database file size (bytes)")
    decision_count: Optional[int] = Field(default=None, description="Total decision records")
    runestone_count: Optional[int] = Field(default=None, description="Total runestone records")
    ttl_days: Optional[int] = Field(default=None, description="TTL days (0=no auto-cleanup)")
    max_records: Optional[int] = Field(default=None, description="Maximum decision records")


# ============================================================
# v0.6: Audit list query models
# ============================================================

class DecisionListItem(BaseModel):
    """Decision list item (without full result)"""
    decision_id: str
    simulation_id: Optional[str] = None
    runestone_id: Optional[str] = None
    created_at: str
    adapter: Optional[str] = None
    seed: Optional[int] = None


class DecisionListResponse(BaseModel):
    """Decision list response"""
    items: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class RunestoneListItem(BaseModel):
    """Runestone list item"""
    runestone_id: str
    decision_id: Optional[str] = None  # None for standalone runestones
    created_at: str
    parent_runestone: Optional[str] = None


class RunestoneListResponse(BaseModel):
    """Runestone list response"""
    items: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class DeleteDataResponse(BaseModel):
    """Data cleanup response"""
    deleted_decisions: int
    deleted_runestones: int


# ============================================================
# v1.5 enterprise_pilot additive request models
# ============================================================

class PilotAuthVerifyRequest(BaseModel):
    """
    POST /api/v1/pilot/auth/verify request body (v1.5, additive endpoint).

    The Bearer token is carried in the ``Authorization`` header; the body is
    optional. Authentication uses a pre-shared reference token (not a
    cryptographic identity proof) — first-gen only compatible, not forge.
    """
    token: str = Field(
        default="",
        description="Optional; primary token source is the Authorization: Bearer header.",
    )


class PilotReviewRequest(BaseModel):
    """
    POST /api/v1/pilot/review request body (v1.5, additive endpoint).

    Records a human review bound to a **real** EvaluationEvent (red-line #8):
    ``event_id`` / ``event_digest`` / ``bundle_ref`` must resolve in the v1.4 store.
    """
    event_id: str = Field(..., description="Real EvaluationEvent id to bind.")
    event_digest: str = Field(..., description="event_hash of the bound event.")
    bundle_ref: Optional[str] = Field(default=None, description="Optional replay bundle ref.")
    action: str = Field(default="approve", description="approve / reject / comment.")
    reviewer_principal_id: str = Field(..., description="Reviewer principal id (not ObservedSubject).")
    comment: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class PilotConnectorExportRequest(BaseModel):
    """
    POST /api/v1/pilot/connector/export request body (v1.5, additive endpoint).

    Returns the four-contract output shape; business write-back stays OFF.
    """
    name: str = Field(..., description="Connector name.")
    kind: str = Field(
        ...,
        description="report_export | warning_event | review_recommendation | audit_export.",
    )
    payload: Dict[str, Any] = Field(default_factory=dict, description="Contract payload.")


class PilotDeployWalkthroughRequest(BaseModel):
    """
    POST /api/v1/pilot/deploy/walkthrough request body (v1.5, additive endpoint).

    Runs the non-author deploy walkthrough (independence / completeness).
    """
    repo_root: Optional[str] = Field(default=None, description="Repo root (defaults to CWD).")
