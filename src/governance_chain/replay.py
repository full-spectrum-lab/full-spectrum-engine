#!/usr/bin/env python3
"""
v1.4 ReplayEngine — deterministic, append-only Policy/Profile replay (FR-05/FR-06/FR-08).

The engine rebuilds a version-pinned Input Envelope from a :class:`ReplayBundle`
and re-invokes the *unchanged* ``envelope.run_envelope`` (NFR-01 / decision #4:
"same-version recompute", no new algorithm). The result is a brand-new
``REPLAY`` EvaluationEvent — the original event is never mutated (FR-06 red-line:
no overwrite of history).

Replay modes (§11 / decision #6):
  * ``EXACT``      — exact reproduction; any missing/changed dependency is an
                     explicit :class:`ReplayDependencyError` (NFR-02, never faked).
  * ``SEMANTIC``   — tolerates externalized-input re-reference; still requires
                     resolvable core bindings, and records the actual mode used.
  * ``EXPLANATORY`` — like SEMANTIC plus a human-readable narrative in the diff.

``--policy`` overrides the policy binding version (FR-05); it rewrites the
policy-type profile refs in the reconstructed input so the override is applied
to the deterministic computation, and is recorded in the new event's bindings.

Zero intrusion: imports only v1.2/v1.3 helpers + the new v1.4 modules; never
modifies ``run_envelope`` / ``risk_vector``.
"""
import copy

from . import envelope as envelope_mod
from . import replay_bundle as bundle_mod
from .evaluation_event import (
    finalize_event,
    _extract_fingerprint,
    _attach_replay_ref,
    _utcnow_iso,
)
from .replay_bundle import ReplayDependencyError, _split_ref

REPLAY_MODES = ("EXACT", "SEMANTIC", "EXPLANATORY")


class ReplayEngine:
    """Replays a ReplayBundle into a new REPLAY EvaluationEvent (no overwrite)."""

    def __init__(self, store):
        self._store = store
        self._reg = None

    def _registry(self):
        if self._reg is None:
            from .profiles.registry import get_default_registry

            self._reg = get_default_registry()
        return self._reg

    def replay(self, bundle, *, policy_version=None, replay_mode="EXACT"):
        """Replay ``bundle`` and append a new REPLAY event; return the event.

        Args:
            bundle: a :class:`~src.governance_chain.replay_bundle.ReplayBundle`.
            policy_version: optional override of the policy binding version (FR-05).
            replay_mode: ``EXACT`` / ``SEMANTIC`` / ``EXPLANATORY``.

        Returns the newly appended REPLAY EvaluationEvent (original untouched).

        Raises:
            ReplayDependencyError: when any required binding cannot be resolved
                (NFR-02) — never silently substituted.
            ValueError: on an unknown ``replay_mode``.
        """
        if replay_mode not in REPLAY_MODES:
            raise ValueError(
                f"unknown replay_mode '{replay_mode}'; expected one of {REPLAY_MODES}"
            )

        # NFR-02: explicit, never-guess dependency resolution BEFORE any compute.
        reg = self._registry()
        bundle.recompute_or_raise(reg)

        input_env = self._reconstruct_input(bundle, policy_version)
        output = envelope_mod.run_envelope(input_env)  # unchanged v1.3 path

        recorded_at = (
            bundle.bindings.get("environment", {}).get("clock") or _utcnow_iso()
        )
        previous_event_hash = self._store.tail_hash()

        event = {
            "schema_id": "eve-1.4",
            "schema_version": "eve-1.4",
            "event_type": "REPLAY",
            "replay_mode": replay_mode,
            "source_original_event_id": bundle.source_event_id,
            "recorded_at": recorded_at,
            "previous_event_hash": previous_event_hash,
            "version_bindings": copy.deepcopy(bundle.bindings),
            "input_ref": bundle.input_ref,
            "input_envelope": bundle.input_envelope,
            "result_fingerprint": _extract_fingerprint(output),
            "output_envelope": output,  # replay_ref still None at this point
            "operation": None,
        }
        event = finalize_event(event)
        _attach_replay_ref(event, bundle.bundle_id)
        self._store.append(event)
        return event

    def _reconstruct_input(self, bundle, policy_version):
        """Rebuild a version-pinned Input Envelope from the bundle.

        For inline bundles this is a deep copy of the stored input envelope. For
        externalized bundles the input file must be resolvable (already checked
        by ``recompute_or_raise``). When ``policy_version`` is given, any
        policy-type profile ref in ``profile_refs`` is rewritten to the override
        version (FR-05) and the bundle's policy binding is updated accordingly.
        """
        if bundle.input_envelope is None:
            # Externalized input must be resolvable; recompute_or_raise already
            # verified the file exists, but guard again for safety.
            location = bundle.input_ref.get("location")
            if not location or not __import__("os").path.exists(location):
                raise ReplayDependencyError(
                    f"externalized input not resolvable at '{location}'"
                )
            with open(location, encoding="utf-8") as handle:
                import json

                env = json.load(handle)
        else:
            env = copy.deepcopy(bundle.input_envelope)

        if policy_version is not None:
            reg = self._registry()
            new_refs = []
            for ref in env.get("profile_refs", []):
                pid, ver = _split_ref(ref)
                try:
                    prof = reg.get(pid, ver)
                    if prof.get("profile_type") in ("ValidationProfile", "EvaluationPolicy"):
                        new_refs.append(f"{pid}@{policy_version}")
                    else:
                        new_refs.append(ref)
                except KeyError:
                    new_refs.append(ref)
            env["profile_refs"] = new_refs
            # Record the override in the bundle's policy binding for the new event.
            policy_ref = bundle.bindings.get("policy", {}).get("ref", "@")
            pid, _ = _split_ref(policy_ref)
            bundle.bindings.setdefault("policy", {})["ref"] = f"{pid}@{policy_version}"
        return env
