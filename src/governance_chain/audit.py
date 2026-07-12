#!/usr/bin/env python3
"""
v1.4 Audit — canonical export + integrity verification (FR-09 / NFR-04).

:class:`AuditExporter` serializes EvaluationEvents to a canonical JSONL audit
log (one canonical JSON line per event, ``event_hash`` excluded so the line is
the exact recomputed payload). :class:`IntegrityChecker` verifies the full
append-only chain:

  1. every event's ``event_hash`` recomputes correctly,
  2. the ``previous_event_hash`` chain is contiguous (GENESIS → tail),
  3. every non-null ``replay_ref.event_id`` resolves to a real stored event
     (v1.4 red-line: no forged replay_ref),
  4. every Output Envelope ``content_digest`` is internally consistent.

Any failure yields ``(False, [tamper_points])``; a clean chain yields
``(True, [])``.

Zero intrusion: brand-new additive module; imports only package helpers.
"""
from . import envelope as envelope_mod
from .evaluation_event import compute_event_hash, GENESIS
from .envelope import canonical_json


class AuditExporter:
    """Export EvaluationEvents as canonical JSONL (FR-09)."""

    @staticmethod
    def export_event(event):
        """Return the canonical JSON line for a single event (no event_hash)."""
        payload = {k: v for k, v in event.items() if k != "event_hash"}
        return canonical_json(payload)

    @staticmethod
    def export_range(events, path):
        """Write ``events`` as one canonical JSON line per row to ``path``."""
        with open(path, "w", encoding="utf-8") as handle:
            for event in events:
                handle.write(AuditExporter.export_event(event) + "\n")
        return path


class IntegrityChecker:
    """Verify the append-only EvaluationEvent chain (FR-09)."""

    @staticmethod
    def _recompute_event_hash(event):
        return compute_event_hash(event)

    @staticmethod
    def verify_chain(store):
        """Verify the whole chain stored in ``store``.

        Returns ``(ok, tamper_points)`` where ``tamper_points`` is a list of
        dicts, each describing a detected problem:
          * ``event_hash_mismatch``
          * ``previous_hash_break`` (with expected/actual)
          * ``replay_ref_forged`` (unresolvable event_id)
          * ``output_content_digest_mismatch``
        """
        events = store.list_events(limit=10 ** 9)
        tampered = []
        prev = GENESIS
        for ev in events:
            # 1) event_hash recomputation
            actual = IntegrityChecker._recompute_event_hash(ev)
            if actual != ev.get("event_hash"):
                tampered.append(
                    {"event_id": ev.get("event_id"), "reason": "event_hash_mismatch"}
                )
                continue  # do not cascade chain checks on a corrupted node

            # 2) previous_event_hash chain continuity
            if ev.get("previous_event_hash") != prev:
                tampered.append(
                    {
                        "event_id": ev.get("event_id"),
                        "reason": "previous_hash_break",
                        "expected": prev,
                        "actual": ev.get("previous_event_hash"),
                    }
                )

            # 3) replay_ref forgery: non-null event_id must resolve (v1.4 red-line)
            goe = ev.get("output_envelope")
            ref = goe.get("replay_ref") if isinstance(goe, dict) else None
            if isinstance(ref, dict) and ref.get("event_id"):
                if store.get(ref["event_id"]) is None:
                    tampered.append(
                        {
                            "event_id": ev.get("event_id"),
                            "reason": "replay_ref_forged",
                            "ref_event_id": ref.get("event_id"),
                        }
                    )

            # 4) Output Envelope content_digest internal consistency
            if isinstance(goe, dict) and "content_digest" in goe:
                stable = {k: v for k, v in goe.items() if k != "content_digest"}
                if envelope_mod.content_digest(stable) != goe["content_digest"]:
                    tampered.append(
                        {
                            "event_id": ev.get("event_id"),
                            "reason": "output_content_digest_mismatch",
                        }
                    )

            prev = ev.get("event_hash")
        ok = len(tampered) == 0
        return ok, tampered
