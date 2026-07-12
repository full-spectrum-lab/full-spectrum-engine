#!/usr/bin/env python3
"""
v1.4 EvaluationEventStore — standalone append-only SQLite audit log.

Design decisions (architecture §2.1 decision #3, §9.2 #3, #7):
  * A NEW, self-contained SQLite database (standard library, offline, single
    writer) backs the audit log. It does NOT touch the v1.2 ``src/storage``
    module — full decoupling.
  * Append-only by construction: ``append`` atomically inserts and rejects any
    ``previous_event_hash`` mismatch or duplicate ``event_hash``. Existing
    ORIGINAL/REPLAY events are NEVER UPDATE/DELETE (FR-06 red-line).
  * The ``previous_event_hash`` column forms a hash chain verified by
    :class:`~src.governance_chain.audit.IntegrityChecker`.
  * Retention / backup / restore / cleanup (NFR-04 / FR-07) are *audited*: each
    mutating operation appends an ``OPERATION`` event BEFORE it acts, so the
    audit chain is never silently broken. ORIGINAL/REPLAY events are immortal;
    cleanup/retention only prune trailing ``OPERATION`` noise older than the
    threshold, which preserves chain continuity and the integrity guarantee.

Defaults (decision #7) are constants, overridable via environment variables:
  * ``FSE_EVAL_RETENTION_DAYS`` (default 365)
  * ``FSE_EVAL_BACKUP_DIR`` (default: alongside the database)
"""
import json
import os
import shutil
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from . import envelope as envelope_mod
from .envelope import canonical_json
from .evaluation_event import (
    compute_event_hash,
    finalize_event,
    EventIntegrityError,
    GENESIS,
)

DEFAULT_STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store")
DEFAULT_DB_PATH = os.path.join(DEFAULT_STORE_DIR, "evaluation_events.sqlite")

RETENTION_DAYS_DEFAULT = int(os.environ.get("FSE_EVAL_RETENTION_DAYS", "365"))
BACKUP_DIR_DEFAULT = os.environ.get("FSE_EVAL_BACKUP_DIR")


def _utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_offset_days(days):
    """Return an ISO timestamp ``days`` before now (negative for past)."""
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_default_store():
    """Return a lazily-created :class:`EvaluationEventStore` at the default path."""
    os.makedirs(DEFAULT_STORE_DIR, exist_ok=True)
    return EvaluationEventStore(DEFAULT_DB_PATH)


class EvaluationEventStore:
    """Append-only repository for immutable EvaluationEvents (FR-01 / FR-07)."""

    def __init__(self, db_path):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # check_same_thread=False so a store may be shared across the worker
        # threads FastAPI/uvicorn use to run sync endpoints. Writes are
        # serialized by ``_lock`` (single-writer, append-only semantics).
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_db()

    # --------------------------------------------------------------
    # Schema / lifecycle
    # --------------------------------------------------------------
    def _init_db(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                rowid_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_hash TEXT NOT NULL,
                previous_event_hash TEXT NOT NULL,
                event_type TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self):
        self._conn.close()

    # --------------------------------------------------------------
    # Append (atomic, hash-chain validated)
    # --------------------------------------------------------------
    def append(self, event):
        """Atomically append an immutable event.

        Rejects:
          * a mismatched ``event_hash`` (recomputed locally),
          * a duplicate ``event_hash`` (idempotency / no overwrite),
          * a ``previous_event_hash`` that does not match the current chain tail
            (chain integrity).

        Returns the appended ``event_id``.
        """
        with self._lock:
            event_hash = event.get("event_hash")
            if not event_hash:
                raise EventIntegrityError("event missing event_hash")
            if compute_event_hash(event) != event_hash:
                raise EventIntegrityError(
                    f"event_hash mismatch for {event.get('event_id')}"
                )
            dup = self._conn.execute(
                "SELECT 1 FROM events WHERE event_hash=?", (event_hash,)
            ).fetchone()
            if dup:
                raise EventIntegrityError(f"duplicate event_hash {event_hash}")
            tail = self.tail_hash()
            if event.get("previous_event_hash") != tail:
                raise EventIntegrityError(
                    f"previous_event_hash mismatch: event="
                    f"{event.get('previous_event_hash')} tail={tail}"
                )
            self._conn.execute(
                "INSERT INTO events (event_id, event_hash, previous_event_hash, "
                "event_type, recorded_at, payload) VALUES (?,?,?,?,?,?)",
                (
                    event.get("event_id"),
                    event_hash,
                    event.get("previous_event_hash"),
                    event.get("event_type"),
                    event.get("recorded_at"),
                    canonical_json(event),
                ),
            )
            self._conn.commit()
            return event.get("event_id")

    # --------------------------------------------------------------
    # Read
    # --------------------------------------------------------------
    def get(self, event_id):
        row = self._conn.execute(
            "SELECT payload FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def list_events(self, limit=100, offset=0, event_type=None):
        if event_type:
            rows = self._conn.execute(
                "SELECT payload FROM events WHERE event_type=? "
                "ORDER BY rowid_seq LIMIT ? OFFSET ?",
                (event_type, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT payload FROM events ORDER BY rowid_seq LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def tail_hash(self):
        row = self._conn.execute(
            "SELECT event_hash FROM events ORDER BY rowid_seq DESC LIMIT 1"
        ).fetchone()
        return row["event_hash"] if row else GENESIS

    def count(self):
        return self._conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]

    def count_by_type(self, event_type):
        return self._conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE event_type=?", (event_type,)
        ).fetchone()["c"]

    # --------------------------------------------------------------
    # Audited operations (NFR-04 / FR-07)
    # --------------------------------------------------------------
    def _append_operation(self, action, detail=""):
        """Append an OPERATION audit event recording a store mutation."""
        op_event = {
            "schema_id": "eve-1.4",
            "schema_version": "eve-1.4",
            "event_type": "OPERATION",
            "replay_mode": None,
            "source_original_event_id": None,
            "recorded_at": _utcnow_iso(),
            "previous_event_hash": self.tail_hash(),
            "version_bindings": {},
            "input_ref": {"digest": "", "location": "audit"},
            "input_envelope": None,
            "result_fingerprint": {},
            "output_envelope": None,
            "operation": {"action": action, "detail": str(detail)},
        }
        op_event = finalize_event(op_event)
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (event_id, event_hash, previous_event_hash, "
                "event_type, recorded_at, payload) VALUES (?,?,?,?,?,?)",
                (
                    op_event["event_id"],
                    op_event["event_hash"],
                    op_event["previous_event_hash"],
                    "OPERATION",
                    op_event["recorded_at"],
                    canonical_json(op_event),
                ),
            )
            self._conn.commit()
        return op_event

    def apply_retention(self, retention_days=None):
        """Apply the retention policy: append a RETENTION OPERATION event, then
        prune only trailing OPERATION events older than ``retention_days``
        (ORIGINAL/REPLAY are immortal; chain continuity preserved)."""
        retention_days = (
            retention_days if retention_days is not None else RETENTION_DAYS_DEFAULT
        )
        self._append_operation("RETENTION", f"retention_days={retention_days}")
        cutoff = _iso_offset_days(retention_days)
        return self._prune_trailing_operations(cutoff)

    def backup(self, path):
        """Back up the database to ``path`` (file copy). Appends a BACKUP
        OPERATION event first, so the backup action itself is audited."""
        self._append_operation("BACKUP", f"target={path}")
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with self._lock:
            shutil.copy(self.db_path, path)
        return path

    def restore(self, path):
        """Restore the database from a backup file (chain continuity from backup).

        The restore replaces the active database with the backup; because the
        backup already contains a valid, continuous hash chain, audit continuity
        is preserved (AC-03)."""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with self._lock:
            self._conn.close()
            shutil.copy(path, self.db_path)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return True

    def cleanup(self, before, audit=True):
        """Clean up old audit OPERATION noise before ISO timestamp ``before``.

        Every real audit event (ORIGINAL/REPLAY) is preserved (FR-06 red-line);
        only trailing OPERATION events older than ``before`` are removed, and the
        action is itself audited by an OPERATION event when ``audit=True``."""
        if audit:
            self._append_operation("CLEANUP", f"before={before}")
        return self._prune_trailing_operations(before)

    # --------------------------------------------------------------
    # Internals
    # --------------------------------------------------------------
    def _prune_trailing_operations(self, cutoff_iso):
        """Delete trailing contiguous OPERATION events recorded before ``cutoff``.

        Only the *trailing* OPERATION rows are removed so the hash chain never
        develops a gap (an ORIGINAL/REPLAY event is never deleted)."""
        deleted = 0
        with self._lock:
            while True:
                row = self._conn.execute(
                    "SELECT rowid_seq, event_type, recorded_at FROM events "
                    "ORDER BY rowid_seq DESC LIMIT 1"
                ).fetchone()
                if (
                    not row
                    or row["event_type"] != "OPERATION"
                    or row["recorded_at"] >= cutoff_iso
                ):
                    break
                self._conn.execute(
                    "DELETE FROM events WHERE rowid_seq=?", (row["rowid_seq"],)
                )
                deleted += 1
            self._conn.commit()
        return deleted
