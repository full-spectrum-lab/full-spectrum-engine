#!/usr/bin/env python3
"""
v1.4 ReplayBundle — the frozen set of 9 version bindings plus input reference.

A :class:`ReplayBundle` captures everything required to *deterministically*
replay an evaluation (FR-02 / FR-03 / NFR-01):

    subject / schema / adapter / engine / profile / policy / knowledge / model / environment

``seed`` and ``clock`` are folded into ``environment`` (architecture §4.3,
decision #1). The bundle is built from an original Input/Output Envelope pair
via :meth:`ReplayBundle.build_from_envelope`, or reconstructed from a stored
:class:`~src.governance_chain.evaluation_event.EvaluationEvent` via
:meth:`ReplayBundle.from_event`, or from a serialized JSON dict via
:meth:`ReplayBundle.from_dict`.

The single most important safety property is :meth:`ReplayBundle.recompute_or_raise`
(NFR-02): before any replay it resolves *every* version binding against the live
:class:`~src.governance_chain.registry.ObjectRegistry`. If any binding cannot be
resolved — a missing Profile/Policy/Knowledge version, or a missing externalized
input file — it raises :class:`ReplayDependencyError` **explicitly**. It never
guesses, never silently degrades a dependency into a placeholder.

Zero intrusion: brand-new additive module; it imports only v1.2/v1.3 helpers
(``envelope``, ``registry``, ``policy``) and never mutates them.
"""
import copy
import hashlib
import json
import os
import platform
import sys
import tempfile

from .envelope import canonical_json, content_digest

INPUT_SCHEMA_ID = "gie-1.2"
OUTPUT_SCHEMA_ID = "goe-1.2"
ENGINE_OBSERVER = "govchain@1.4.0"
ENGINE_COMPUTATION = "profile_driven_v1.3"
MODEL_ID = "risk_vector/profile_driven_v1.3"
MODEL_VERSION = "1.3.0"
CONTRACT_VERSION = "1.2.0"


class ReplayDependencyError(Exception):
    """Raised when a ReplayBundle dependency cannot be resolved (NFR-02).

    This is the explicit, never-guess failure mode: a missing Profile/Policy/
    Knowledge version or an unresolvable externalized input. A replay that hits
    this error must NOT be reported as EXACT — it simply cannot be reproduced.
    """

    code = "REPLAY_DEPENDENCY"

    def __init__(self, message):
        super().__init__(message)


def _split_ref(ref):
    """Split a ``id`` or ``id@version`` reference into ``(id, version)``."""
    ref = str(ref)
    if "@" in ref:
        pid, ver = ref.split("@", 1)
        return pid, ver
    return ref, None


def _utcnow_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_policy_ref():
    """Return the default governance policy reference ``id@version``."""
    from . import policy as policy_mod

    pol = policy_mod.load_policy()
    return f"{pol.get('policy_id')}@{pol.get('version')}"


def _resolve_policy_version(requested_version):
    """Verify a requested policy version is actually available; else raise.

    The default policy always resolves. A different version resolves only if a
    matching ``governance-rules.<version>.json`` file exists; otherwise we
    raise :class:`ReplayDependencyError` (NFR-02, never guess).
    """
    from . import policy as policy_mod

    pol = policy_mod.load_policy()
    default_ver = pol.get("version")
    if requested_version is None or requested_version == default_ver:
        return default_ver
    candidate = os.path.join(
        os.path.dirname(policy_mod.DEFAULT_POLICY),
        f"governance-rules.{requested_version}.json",
    )
    if os.path.exists(candidate):
        alt = policy_mod.load_policy(candidate)
        return alt.get("version")
    raise ReplayDependencyError(
        f"policy version '{requested_version}' is not available for replay"
    )


def _write_external_input(env, external_input_dir=None):
    """Write the input envelope to disk; return its absolute path (NFR-03)."""
    digest = content_digest(env)
    if external_input_dir is None:
        external_input_dir = tempfile.mkdtemp(prefix="fse_extinput_")
    os.makedirs(external_input_dir, exist_ok=True)
    path = os.path.join(external_input_dir, f"{digest}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(env, handle, ensure_ascii=False)
    return path


class ReplayBundle:
    """Immutable frozen reference bundle for a single replay (FR-02 / FR-03)."""

    def __init__(self, bundle_id, bindings, input_ref, input_envelope, bundle_digest):
        self.bundle_id = bundle_id
        self.bindings = bindings
        self.input_ref = input_ref
        self.input_envelope = input_envelope  # dict or None (externalized)
        self.bundle_digest = bundle_digest
        self.source_event_id = None  # set when derived from a stored event

    # --------------------------------------------------------------
    # Construction
    # --------------------------------------------------------------
    @classmethod
    def build_from_envelope(cls, env, output, *, clock=None, externalize=False,
                            external_input_dir=None):
        """Build a bundle from an original Input Envelope + Output Envelope.

        Args:
            env: the v1.2 Input Envelope (gie-1.2).
            output: the v1.2 Output Envelope (goe-1.2) produced by ``run_envelope``.
            clock: pinned ISO-8601 clock for deterministic ``recorded_at``; when
                ``None`` the current UTC time is used.
            externalize: when True, the input envelope is NOT inlined; instead it
                is written to ``external_input_dir`` (or a temp dir) and only an
                ``input_ref`` (digest + location) is kept (NFR-03).
            external_input_dir: where to write the externalized input.
        """
        subject_refs = env.get("subject_refs") or []
        subject_ref = subject_refs[0] if subject_refs else None
        industry = (env.get("business_data") or {}).get("industry")
        adapter_ref = industry or "unknown"

        profile_refs = env.get("profile_refs") or []
        source_profile_versions = (
            (output.get("risk_vector") or {}).get("source_profile_versions") or []
        )
        knowledge_refs = env.get("knowledge_source_refs") or []

        environment = {
            "seed": 0,
            "clock": clock or _utcnow_iso(),
            "contract_version": CONTRACT_VERSION,
            "python": platform.python_version(),
            "platform": sys.platform,
        }

        bindings = {
            "subject": {"ref": subject_ref} if subject_ref else {},
            "schema": {"input": INPUT_SCHEMA_ID, "output": OUTPUT_SCHEMA_ID},
            "adapter": {"ref": adapter_ref},
            "engine": {"observer": ENGINE_OBSERVER, "computation": ENGINE_COMPUTATION},
            "profile": {
                "refs": list(profile_refs),
                "source_profile_versions": list(source_profile_versions),
            },
            "policy": {"ref": _default_policy_ref()},
            "knowledge": {"refs": list(knowledge_refs)},
            "model": {"id": MODEL_ID, "version": MODEL_VERSION},
            "environment": environment,
        }

        input_digest = content_digest(env)
        if externalize:
            location = _write_external_input(env, external_input_dir)
            input_envelope = None
        else:
            location = "inline"
            input_envelope = copy.deepcopy(env)

        input_ref = {"digest": input_digest, "location": location}
        bundle_id = "bundle_" + content_digest(
            {
                "input": canonical_json(env),
                "bindings": bindings,
                "clock": environment["clock"],
            }
        )[:16]
        bundle_digest = content_digest({"bindings": bindings, "input_ref": input_ref})
        return cls(bundle_id, bindings, input_ref, input_envelope, bundle_digest)

    @classmethod
    def from_event(cls, event):
        """Reconstruct a bundle from a stored EvaluationEvent (replay-by-event-id)."""
        vb = event.get("version_bindings", {})
        input_env = event.get("input_envelope")
        input_ref = event.get("input_ref", {}) or {}
        goe = event.get("output_envelope") or {}
        ref = goe.get("replay_ref") or {}
        bundle_id = ref.get("bundle_ref") or (
            "bundle_" + content_digest({"event": event.get("event_id")})[:16]
        )
        bundle_digest = content_digest({"bindings": vb, "input_ref": input_ref})
        bundle = cls(bundle_id, vb, input_ref, input_env, bundle_digest)
        bundle.source_event_id = event.get("event_id")
        return bundle

    @classmethod
    def from_dict(cls, data):
        """Reconstruct a bundle from a serialized dict (e.g. a fixture/file)."""
        bundle = cls(
            data["bundle_id"],
            data["bindings"],
            data.get("input_ref", {}),
            data.get("input_envelope"),
            data.get("bundle_digest", ""),
        )
        bundle.source_event_id = data.get("source_event_id")
        return bundle

    def to_dict(self):
        """Serialize the bundle to a JSON-friendly dict."""
        return {
            "bundle_id": self.bundle_id,
            "bindings": self.bindings,
            "input_ref": self.input_ref,
            "input_envelope": self.input_envelope,
            "bundle_digest": self.bundle_digest,
            "source_event_id": self.source_event_id,
        }

    # --------------------------------------------------------------
    # Dependency resolution (NFR-02)
    # --------------------------------------------------------------
    def recompute_or_raise(self, reg):
        """Resolve every version binding against the live registry.

        Raises :class:`ReplayDependencyError` on the first unresolvable binding.
        Never guesses, never silently substitutes a placeholder.

        Resolution targets:
          * ``profile.source_profile_versions`` — the fully expanded set that
            actually drove the deterministic risk_vector (same-version recompute).
          * ``knowledge.refs`` — knowledge source versions.
          * ``policy.ref`` — policy version (default or overridden).
          * externalized input — ``input_envelope is None`` requires a resolvable
            ``input_ref.location`` file.
        """
        # 1) Profile versions (the critical same-version recompute anchors)
        for ref in self.bindings.get("profile", {}).get("source_profile_versions", []):
            pid, ver = _split_ref(ref)
            try:
                reg.get(pid, ver)
            except KeyError:
                raise ReplayDependencyError(
                    f"profile version not resolvable: '{ref}'"
                )

        # 2) Knowledge source versions
        for ref in self.bindings.get("knowledge", {}).get("refs", []):
            pid, ver = _split_ref(ref)
            try:
                reg.get(pid, ver)
            except KeyError:
                raise ReplayDependencyError(
                    f"knowledge version not resolvable: '{ref}'"
                )

        # 3) Policy version
        policy_ref = self.bindings.get("policy", {}).get("ref")
        if policy_ref:
            _, ver = _split_ref(policy_ref)
            _resolve_policy_version(ver)

        # 4) Externalized input must be resolvable (NFR-03)
        if self.input_envelope is None:
            location = self.input_ref.get("location")
            if not location or not os.path.exists(location):
                raise ReplayDependencyError(
                    f"externalized input not resolvable at '{location}'"
                )
        return None
