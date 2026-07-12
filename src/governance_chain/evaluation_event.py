#!/usr/bin/env python3
"""
v1.4 EvaluationEvent — immutable, content-addressed, append-only audit record.

This module is the single facade for "analyze → record" (FR-01 / FR-03):

    record_evaluation(env, store=...)  ->  audited Output Envelope

It wraps the *unchanged* v1.3 ``envelope.run_envelope`` to produce the
Observer output, builds a frozen :class:`~src.governance_chain.replay_bundle.ReplayBundle`
(9 version bindings), constructs an immutable :class:`EvaluationEvent`, fills the
Output Envelope's ``replay_ref`` with a *real, resolvable* reference to that
event, recomputes the Output Envelope ``content_digest``, and appends the event
to the store. The v1.2/v1.3 direct ``run_envelope`` path is untouched and still
emits ``replay_ref=None`` (zero regression, anti-pattern inheritance).

Immutability & hash chain (shared knowledge #1):
  * ``event_hash = SHA-256(canonical_json(event without event_hash/event_id/
    output_envelope))`` — ``output_envelope`` is excluded only to break the
    ``replay_ref`` self-reference cycle (the reference points back at this very
    event); its integrity is guaranteed by its own ``content_digest`` and by the
    ``IntegrityChecker`` resolving ``replay_ref.event_id``.
  * ``event_id = "evt_" + event_hash[:16]`` (immutable handle).
  * ``previous_event_hash`` links the chain; the first event uses ``"GENESIS"``.
  * Existing events are never UPDATE/DELETE (FR-06 red-line); replay only appends.

Also provides :func:`compute_canonical_diff` (FR-04): a structured, field-level
difference across the seven categories input/profile/policy/knowledge/
environment/output/reason.

Zero intrusion: brand-new additive module; imports only v1.2/v1.3 helpers.
"""
import copy
import hashlib
import json
import os

from . import envelope as envelope_mod
from . import validator
from .envelope import canonical_json, content_digest
from .replay_bundle import ReplayBundle, ReplayDependencyError

EVENT_SCHEMA_ID = "eve-1.4"
GENESIS = "GENESIS"
_SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")

# Fields excluded from the event_hash. ``output_envelope`` is excluded to avoid a
# circular dependency with ``replay_ref.event_id`` (which points back at this
# event); its integrity is covered by its own content_digest + replay_ref check.
_HASH_EXCLUDE = ("event_hash", "event_id", "output_envelope")


class EventIntegrityError(Exception):
    """Raised when an EvaluationEvent fails hash-chain / content validation."""

    code = "EVENT_INTEGRITY"

    def __init__(self, message):
        super().__init__(message)


def _load_schema(name):
    with open(os.path.join(_SCHEMA_DIR, name), encoding="utf-8-sig") as handle:
        return json.load(handle)


def compute_event_hash(event):
    """SHA-256 over the canonical form of ``event`` (excluding hash/id/output)."""
    payload = {k: v for k, v in event.items() if k not in _HASH_EXCLUDE}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def finalize_event(event):
    """Assign ``event_hash`` and derived ``event_id``; return a new dict."""
    ev = {k: v for k, v in event.items() if k not in ("event_hash", "event_id")}
    digest = compute_event_hash(ev)
    ev["event_hash"] = digest
    ev["event_id"] = "evt_" + digest[:16]
    return ev


def verify_event(event):
    """Recompute and check the event_hash and event_id derivation.

    Returns True on success; raises :class:`EventIntegrityError` otherwise.
    """
    actual = compute_event_hash(event)
    if actual != event.get("event_hash"):
        raise EventIntegrityError(
            f"event_hash mismatch for {event.get('event_id')}"
        )
    if event.get("event_id") != "evt_" + str(event.get("event_hash", ""))[:16]:
        raise EventIntegrityError(
            f"event_id does not derive from event_hash for {event.get('event_id')}"
        )
    return True


def validate_event(event):
    """Validate ``event`` against the evaluation-event schema (additive check)."""
    schema = _load_schema("evaluation-event.schema.json")
    ok, errors = validator.validate_instance(event, schema)
    return ok, errors


def _extract_fingerprint(output):
    """Build the deterministic ``result_fingerprint`` subset from a goe-1.2."""
    rv = output.get("risk_vector") or {}
    return {
        # The canonical result digest (replay_ref-independent) used for AC-01
        # equivalence: it is the run_envelope content_digest BEFORE replay_ref
        # is filled, so it is stable across original/replay of the same input.
        "output_content_digest": output.get("content_digest"),
        "risk_vector": {
            "dimensions": rv.get("dimensions"),
            "values": rv.get("values"),
            "source_profile_versions": rv.get("source_profile_versions"),
            "deterministic": rv.get("deterministic"),
        },
        "scenario_refs": output.get("scenario_refs"),
        "eligibility_candidate": output.get("eligibility_candidate"),
        "explanation_basis": (output.get("explanation") or {}).get("basis"),
        "hard_forbidden": output.get("hard_forbidden"),
        "unknown_flags": output.get("unknown_flags"),
    }


def _attach_replay_ref(event, bundle_id):
    """Fill the Output Envelope ``replay_ref`` with a real reference + recompute."""
    goe = event["output_envelope"]
    goe["replay_ref"] = {
        "event_id": event["event_id"],
        "event_digest": event["event_hash"],
        "bundle_ref": bundle_id,
    }
    stable = {k: v for k, v in goe.items() if k != "content_digest"}
    goe["content_digest"] = content_digest(stable)


def record_evaluation(env, *, clock=None, externalize_input=False,
                      external_input_dir=None, store=None):
    """Facade: run the Observer, record an immutable EvaluationEvent, return audited output.

    Flow (architecture §5.1):
      1. ``run_envelope(env)`` — unchanged v1.3 behavior, ``replay_ref=None``.
      2. Build a frozen ``ReplayBundle`` (9 version bindings) from env + output.
      3. Construct an ``EvaluationEvent`` (ORIGINAL) linked to the store tail.
      4. Fill the Output Envelope ``replay_ref`` with this event's real id/digest
         and recompute its ``content_digest``.
      5. Append to ``store`` (if provided) and return the audited Output Envelope.

    The direct ``run_envelope`` path is never modified; this facade is additive
    and shared by both CLI and REST (shared-single-function principle).
    """
    output = envelope_mod.run_envelope(env)  # v1.3 behavior, replay_ref=None
    bundle = ReplayBundle.build_from_envelope(
        env, output, clock=clock, externalize=externalize_input,
        external_input_dir=external_input_dir,
    )
    recorded_at = clock or _utcnow_iso()
    previous_event_hash = store.tail_hash() if store is not None else GENESIS

    event = {
        "schema_id": EVENT_SCHEMA_ID,
        "schema_version": EVENT_SCHEMA_ID,
        "event_type": "ORIGINAL",
        "replay_mode": None,
        "source_original_event_id": None,
        "recorded_at": recorded_at,
        "previous_event_hash": previous_event_hash,
        "version_bindings": bundle.bindings,
        "input_ref": bundle.input_ref,
        "input_envelope": bundle.input_envelope,  # env (inline) or None (externalized)
        "result_fingerprint": _extract_fingerprint(output),
        "output_envelope": output,  # replay_ref still None at this point
        "operation": None,
    }
    event = finalize_event(event)
    # Fill real replay_ref + recompute goe content_digest (red-line: real, resolvable)
    _attach_replay_ref(event, bundle.bundle_id)

    if store is not None:
        store.append(event)
    return event["output_envelope"]


def _utcnow_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Canonical Diff (FR-04) — seven categories
# ---------------------------------------------------------------------------
def _ver_diff(left_binding, right_binding):
    """Compare profile/policy/knowledge version sets; return changed versions."""
    left = set(
        (left_binding or {}).get("source_profile_versions")
        or (left_binding or {}).get("refs")
        or []
    )
    right = set(
        (right_binding or {}).get("source_profile_versions")
        or (right_binding or {}).get("refs")
        or []
    )
    changed = sorted(left ^ right)
    return changed


def _obj_diff(left, right):
    """Field-level changed/added/removed between two dicts."""
    left = left or {}
    right = right or {}
    changed = [k for k in set(left) | set(right) if left.get(k) != right.get(k)]
    added = [k for k in right if k not in left]
    removed = [k for k in left if k not in right]
    return {"changed": changed, "added": added, "removed": removed}


def _build_narrative(categories, semantic_equal):
    parts = []
    for cat, diff in categories.items():
        if isinstance(diff, dict) and (diff.get("changed") or diff.get("changed_versions")
                                       or diff.get("added") or diff.get("removed")):
            parts.append(f"{cat}: {diff}")
    verdict = "equivalent" if semantic_equal else "divergent"
    if not parts:
        return f"Outputs are {verdict}; no binding-level differences detected."
    return f"Outputs are {verdict}. Differences: " + "; ".join(parts)


def compute_canonical_diff(left, right, mode="EXPLANATORY"):
    """Compute a structured Canonical Diff between two EvaluationEvents (FR-04).

    Categories: input / profile / policy / knowledge / environment / output / reason.
    ``semantic_equal`` reports whether the deterministic result is equivalent
    (AC-02). ``narrative`` is populated for EXPLANATORY mode.
    """
    vb_l = left.get("version_bindings", {})
    vb_r = right.get("version_bindings", {})
    fp_l = left.get("result_fingerprint", {})
    fp_r = right.get("result_fingerprint", {})

    categories = {
        "input": _obj_diff(vb_l.get("subject"), vb_r.get("subject")),
        "profile": {"changed_versions": _ver_diff(vb_l.get("profile"), vb_r.get("profile"))},
        "policy": {"changed_versions": _ver_diff(vb_l.get("policy"), vb_r.get("policy"))},
        "knowledge": {"changed_versions": _ver_diff(vb_l.get("knowledge"), vb_r.get("knowledge"))},
        "environment": _obj_diff(vb_l.get("environment"), vb_r.get("environment")),
        "output": _obj_diff(fp_l, fp_r),
        "reason": _obj_diff(
            {"basis": fp_l.get("explanation_basis")},
            {"basis": fp_r.get("explanation_basis")},
        ),
    }

    semantic_equal = (
        fp_l.get("output_content_digest") == fp_r.get("output_content_digest")
        and (fp_l.get("risk_vector") or {}).get("values")
        == (fp_r.get("risk_vector") or {}).get("values")
    )

    narrative = ""
    if mode == "EXPLANATORY":
        narrative = _build_narrative(categories, semantic_equal)

    return {
        "schema_id": "cdf-1.4",
        "left_event_id": left.get("event_id"),
        "right_event_id": right.get("event_id"),
        "categories": categories,
        "semantic_equal": semantic_equal,
        "narrative": narrative,
    }
