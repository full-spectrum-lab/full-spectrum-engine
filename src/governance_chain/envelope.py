#!/usr/bin/env python3
"""
v1.2 Observer Input/Output Envelope contract.

This module is the single source of truth for the v1.2 "观察者输入输出契约".
Both the CLI (`fsengine-govchain envelope ...`) and the REST API
(`POST /api/v1/envelope`) import from here, so they are guaranteed to emit
byte-for-byte equivalent Envelopes (FR-03 / AC-01).

Design boundaries (per Engine Wiki v1.2 项目需求文档 / 技术设计纲要):
  - First-generation Observer only COMPATIBLES with, and never FORGES, auth.
    L4 reference fields (trust domain / credential / mutual-auth / authorization
    / verification result) are carried and schema-checked, but never validated
    cryptographically and never produce external effect.
  - L4_CANDIDATE means "local format + data prepared", NOT "externally active".
  - Broken relationships and UNKNOWN evidence must be explicit, never silently
    passed through (NFR-05 / AC-05 / AC-06).
  - v1.2 freezes the I/O contract; the real measurement/Profile computation is
    deferred to v1.3 (Profile-driven) and v1.4 (Replay). The deterministic
    values produced here are contract stubs, clearly marked, not business
    insights.

Zero intrusion: this module does not modify any v1.1 artifact or schema.
"""
import hashlib
import json
import os

from . import validator

# v1.2 envelope contract identifiers
INPUT_SCHEMA_ID = "gie-1.2"
OUTPUT_SCHEMA_ID = "goe-1.2"
CONTRACT_VERSION = "1.2.0"

L4_MODES = ("DISABLED", "LOCAL_SIMULATION", "NETWORK_CANDIDATE")
GATE_STATES = ("OPEN", "CLOSED", "INTERNAL_OPEN_EXTERNAL_CLOSED")
DEFAULT_GATE_STATE = "INTERNAL_OPEN_EXTERNAL_CLOSED"


# ----------------------------------------------------------------
# Canonical serialization + content digest (FR-05 / AC-03)
# ----------------------------------------------------------------
def canonical_json(obj):
    """Deterministic JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_digest(obj):
    """SHA-256 hex digest over the canonical serialization of obj."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


# ----------------------------------------------------------------
# Gate framework (§5 / §11 第三轮评审冻结修订)
# ----------------------------------------------------------------
def make_gate(state=DEFAULT_GATE_STATE, reason_code="OK", note=""):
    """Build a single gate record with a stable reason code (object form)."""
    if state not in GATE_STATES:
        raise ValueError(f"invalid gate state {state!r}; expected one of {GATE_STATES}")
    return {
        "state": state,
        "reason_code": reason_code,
        "note": note,
    }


def default_gates():
    """Default gate set: internal open (still traced), external closed."""
    return {
        "layer_flow": make_gate(DEFAULT_GATE_STATE, "INTERNAL_OPEN_EXTERNAL_CLOSED"),
        "qualification": make_gate(DEFAULT_GATE_STATE, "INTERNAL_OPEN_EXTERNAL_CLOSED"),
        "authorization": make_gate("CLOSED", "EXTERNAL_CLOSED_BY_DEFAULT"),
        "mutual_auth": make_gate("CLOSED", "EXTERNAL_CLOSED_BY_DEFAULT"),
        "effective_state": "INTERNAL_ONLY",
    }


# ----------------------------------------------------------------
# Input Envelope (SRS §3.1 / §3.2)
# ----------------------------------------------------------------
class InputEnvelopeError(Exception):
    code = "INPUT_ENVELOPE_INVALID"

    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or []


def _coerce_layer(value):
    if value not in ("L1", "L2", "L3", "L4"):
        raise InputEnvelopeError(f"invalid layer {value!r}; expected L1/L2/L3/L4")
    return value


def _coerce_scope(value):
    if value not in ("internal", "external_candidate"):
        raise InputEnvelopeError(f"invalid scope {value!r}; expected internal/external_candidate")
    return value


def _coerce_l4_mode(value):
    if value not in L4_MODES:
        raise InputEnvelopeError(f"invalid l4_mode {value!r}; expected one of {L4_MODES}")
    return value


def build_input_envelope(
    layer,
    scope,
    subject_refs,
    business_data,
    *,
    relationship_refs=None,
    evidence_refs=None,
    known_facts=None,
    unknowns=None,
    profile_refs=None,
    knowledge_source_refs=None,
    credential_refs=None,
    verification_result_refs=None,
    authorization_refs=None,
    gate=None,
    l4_mode="DISABLED",
    l4_refs=None,
    context_metadata=None,
    audit_metadata=None,
    contract_version=CONTRACT_VERSION,
):
    """Construct a v1.2 Input Envelope dict with all SRS §3.1/§3.2 fields."""
    _coerce_layer(layer)
    _coerce_scope(scope)
    _coerce_l4_mode(l4_mode)
    if not subject_refs:
        raise InputEnvelopeError("subject_refs must contain at least one subject reference")

    env = {
        "schema_id": INPUT_SCHEMA_ID,
        "schema_version": INPUT_SCHEMA_ID,
        "contract_version": contract_version,
        "layer": layer,
        "scope": scope,
        "subject_refs": list(subject_refs),
        "business_data": business_data,
        "relationship_refs": list(relationship_refs or []),
        "evidence_refs": list(evidence_refs or []),
        "known_facts": known_facts or {},
        "unknowns": unknowns or {},
        "profile_refs": list(profile_refs or []),
        "knowledge_source_refs": list(knowledge_source_refs or []),
        "credential_refs": list(credential_refs or []),
        "verification_result_refs": list(verification_result_refs or []),
        "authorization_refs": list(authorization_refs or []),
        "gate": gate if gate is not None else default_gates(),
        "l4_mode": l4_mode,
        "l4_refs": l4_refs or {},
        "context_metadata": context_metadata or {},
        "audit_metadata": audit_metadata or {},
    }
    return env


def validate_input_envelope(env):
    """Validate an Input Envelope against the v1.2 schema. Returns (ok, errors)."""
    schema = validator.load_schema("input-envelope.schema.json")
    ok, errors = validator.validate_instance(env, schema)
    return ok, errors


def normalize_legacy_input(raw, *, layer="L1", scope="internal", subject_refs=None):
    """
    FR-06 — v1.0 input compatibility.

    A v1.0-era raw business input (e.g. raw-input.ecommerce.json) is wrapped
    into a v1.2 Input Envelope so old inputs keep flowing. The original raw
    doc is preserved verbatim inside `business_data`.
    """
    subject_refs = subject_refs or ["legacy/unknown"]
    return build_input_envelope(
        layer=layer,
        scope=scope,
        subject_refs=subject_refs,
        business_data=raw,
        unknowns={"legacy_wrap": True},
    )


# ----------------------------------------------------------------
# Broken-link detection (FR-02 / AC-05)
# ----------------------------------------------------------------
def check_envelope_links(env, known_ids):
    """
    Return the list of broken reference ids in an Input Envelope.

    A reference (subject_ref / relationship_ref) is "broken" when its target
    is not present in `known_ids`. Empty/unknown references are NOT broken by
    themselves; only *declared but unresolved* references are flagged. This is
    the explicit, non-silent handling required by NFR-05.
    """
    known = set(known_ids or [])
    broken = []
    for ref in env.get("subject_refs", []):
        if ref not in known:
            broken.append(("subject_ref", ref))
    for ref in env.get("relationship_refs", []):
        if ref not in known:
            broken.append(("relationship_ref", ref))
    return broken


def detect_broken_links(chain_objects):
    """
    Detect broken `relationships` across a set of protocol objects.

    `chain_objects` is a list of dicts each carrying an `id` and a
    `relationships` list of {relation_type, target_type, target_id}.
    Returns a list of (source_id, relation_type, missing_target_id).
    """
    index = {obj.get("id"): obj for obj in chain_objects if obj.get("id")}
    broken = []
    for obj in chain_objects:
        src = obj.get("id")
        for rel in obj.get("relationships", []) or []:
            tgt = rel.get("target_id")
            if tgt not in index:
                broken.append((src, rel.get("relation_type"), tgt))
    return broken


# ----------------------------------------------------------------
# Output Envelope (SRS §3.3)
# ----------------------------------------------------------------
def _stub_risk_vector(business_data):
    """
    Deterministic contract stub for risk_vector.

    v1.2 only freezes the I/O contract; real measurement is deferred to v1.3.
    The values are derived from the business_data digest so they are
    reproducible, but they are explicitly marked as placeholder stubs.
    """
    digest = content_digest(business_data)
    seed = int(digest[:8], 16) % 1000 / 1000.0  # [0,1)
    return {
        "dimensions": ["commitment_risk", "authority_risk", "knowledge_conflict_risk"],
        "values": [seed, seed, 1.0 - seed],
        "note": "v1.2 contract stub; real measurement deferred to v1.3 Profile-driven",
    }


def run_envelope(env, subject_declaration=None):
    """
    Run the v1.2 Observer over an Input Envelope and produce an Output Envelope.

    This is the function shared by CLI and REST (FR-03 / AC-01). It is pure
    local computation — no network calls (NFR-01 / AC-04). L4 references are
    carried through but never produce external effect: when l4_mode is
    NETWORK_CANDIDATE the output marks `external_effect=False` and the mutual
    auth gate stays CLOSED.
    """
    if not isinstance(env, dict):
        raise InputEnvelopeError("input envelope must be a dict")
    # Validate input first (raises InputEnvelopeError on failure)
    ok, errors = validate_input_envelope(env)
    if not ok:
        raise InputEnvelopeError("input envelope failed schema validation", errors)

    business_data = env.get("business_data", {})
    l4_mode = env.get("l4_mode", "DISABLED")
    _coerce_l4_mode(l4_mode)

    input_digest = content_digest(env)
    is_candidate = l4_mode == "NETWORK_CANDIDATE"  # candidate prepared, NOT active
    gates = dict(env.get("gate") or default_gates())
    # First-gen Observer only COMPATIBLES with L4: a NETWORK_CANDIDATE is locally
    # prepared but not yet mutually authorized, so its mutual-auth gate stays
    # CLOSED and external_effect stays False (v1.2 freeze).
    if is_candidate and "mutual_auth" in gates:
        gates["mutual_auth"] = {
            "state": "CLOSED",
            "reason_code": "L4_CANDIDATE_NOT_YET_AUTHORIZED",
            "note": "NETWORK_CANDIDATE prepared but not yet mutually authorized; no external effect",
        }

    unknown_count = len(env.get("unknowns", {}) or {})
    human_review_required = unknown_count > 0 or is_candidate

    output = {
        "schema_id": OUTPUT_SCHEMA_ID,
        "schema_version": OUTPUT_SCHEMA_ID,
        "contract_version": CONTRACT_VERSION,
        "analysis_result": {
            "layer": env.get("layer"),
            "scope": env.get("scope"),
            "subject_count": len(env.get("subject_refs", [])),
            "summary": "v1.2 observer I/O contract frozen; analysis deferred to v1.3",
        },
        "fshi_measurement": {
            "status": "contract_frozen",
            "deferred_to": "v1.3",
            "measurement_digest": input_digest,
        },
        "risk_vector": _stub_risk_vector(business_data),
        "ess_candidates": [],
        "warnings": (
            ["UNKNOWN evidence present; explicit handling only, no silent pass"]
            if unknown_count else []
        ),
        "human_review_recommendation": {
            "required": human_review_required,
            "reason": "unknown_evidence" if unknown_count else (
                "l4_candidate_pending_authorization" if is_candidate else "none"
            ),
        },
        "explanation": {
            "text": "v1.2 freezes the I/O contract; this explanation is structural, "
                    "not a business conclusion.",
            "basis": ["contract_version=" + CONTRACT_VERSION, "l4_mode=" + l4_mode],
        },
        "runestone": {
            "id": "rs_" + input_digest[:16],
            "tokens": ["contract_frozen@1.2", "input_digest=" + input_digest[:12]],
        },
        "audit_ref": "audit_" + input_digest[:16],
        "replay_ref": None,  # full Replay deferred to v1.4
        "gate": gates,
        "l4_mode": l4_mode,
        "external_effect": False,  # v1.2 freeze: candidate != active; always False
        "content_digest": content_digest(None),  # placeholder; set below
    }
    # Set the real content digest over the stable part (everything except itself)
    stable = {k: v for k, v in output.items() if k != "content_digest"}
    output["content_digest"] = content_digest(stable)
    return output


def validate_output_envelope(env):
    """Validate an Output Envelope against the v1.2 schema. Returns (ok, errors)."""
    schema = validator.load_schema("observer-output-envelope.schema.json")
    ok, errors = validator.validate_instance(env, schema)
    return ok, errors
