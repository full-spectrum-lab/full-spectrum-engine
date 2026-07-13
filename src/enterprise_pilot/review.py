#!/usr/bin/env python3
"""
C-04 人工复核（复用 v1.4 replay_ref 风格真实绑定 / FR-04 / C-04）。

设计（共享知识 §8.4 / §8.5 / 红线 #7 / #8）：
  * ``ReviewRecord.original_event_ref = {event_id, event_digest[, bundle_ref]}``
    指向**真实存在**的 EvaluationEvent（v1.4 ``EvaluationEventStore``）；
    缺失 / 伪造引用 → 显式拒绝（红线 #8）。
  * ``ReviewStore`` 仅 append（复用 v1.4 独立 SQLite 模式，与 v1.2 ``src/storage`` 解耦）；
    不提供历史改写 API（红线 #7）。
  * 复用 v1.4 公开 API（EvaluationEventStore / IntegrityChecker）**只调用不修改**。
"""
import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

from src.governance_chain import envelope as envelope_mod

REVIEW_SCHEMA_ID = "rvw-1.5"
_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store")


def _utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _review_id(digest):
    return "rvw_" + digest[:16]


def _compute_review_hash(record):
    """对稳定字段（不含 review_id / review_hash）做 SHA-256。"""
    payload = {k: v for k, v in record.items() if k not in ("review_id", "review_hash")}
    return hashlib.sha256(envelope_mod.canonical_json(payload).encode("utf-8")).hexdigest()


class ReviewError(Exception):
    code = "REVIEW"


class ReviewBindingError(ReviewError):
    """original_event_ref 伪造 / 不可解析（红线 #8）。"""

    code = "REVIEW_BINDING_FORGED"


class ReviewRecord:
    """人工复核记录（关联真实 EvaluationEvent）。"""

    def __init__(self, review_id, original_event_ref, action, reviewer_principal_id,
                 recorded_at, comment=None):
        self.review_id = review_id
        self.original_event_ref = dict(original_event_ref)
        self.action = action
        self.reviewer_principal_id = reviewer_principal_id
        self.recorded_at = recorded_at
        self.comment = comment
        self.review_hash = _compute_review_hash(self.to_dict())

    def to_dict(self):
        return {
            "schema_id": REVIEW_SCHEMA_ID,
            "review_id": self.review_id,
            "original_event_ref": {
                "event_id": self.original_event_ref.get("event_id"),
                "event_digest": self.original_event_ref.get("event_digest"),
                "bundle_ref": self.original_event_ref.get("bundle_ref"),
            },
            "action": self.action,
            "reviewer_principal_id": self.reviewer_principal_id,
            "comment": self.comment,
            "recorded_at": self.recorded_at,
        }


class ReviewStore:
    """独立 append-only SQLite 复核存储（红线 #7：仅 append）。"""

    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(_DEFAULT_DIR, "review.sqlite")
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                rowid_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def append(self, record):
        """仅 append；重复 review_id 幂等跳过。返回 review_id。"""
        with self._lock:
            rid = record["review_id"]
            dup = self._conn.execute(
                "SELECT 1 FROM reviews WHERE review_id=?", (rid,)
            ).fetchone()
            if dup:
                return rid
            self._conn.execute(
                "INSERT INTO reviews (review_id, payload) VALUES (?,?)",
                (rid, envelope_mod.canonical_json(record)),
            )
            self._conn.commit()
            return rid

    def list_by_event(self, event_id):
        rows = self._conn.execute("SELECT payload FROM reviews").fetchall()
        out = []
        for row in rows:
            rec = json.loads(row["payload"])
            ref = rec.get("original_event_ref") or {}
            if ref.get("event_id") == event_id:
                out.append(rec)
        return out

    def list_all(self):
        rows = self._conn.execute("SELECT payload FROM reviews").fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def close(self):
        self._conn.close()


_default_store = None


def _default_review_store():
    global _default_store
    if _default_store is None:
        _default_store = ReviewStore()
    return _default_store


def record_review(event_ref, action, reviewer_principal_id, *,
                  source_store=None, review_store=None, comment=None,
                  recorded_at=None, idempotency_key=None):
    """记录一次人工复核，绑定真实存在的 EvaluationEvent（红线 #8）。

    Args:
        event_ref: {event_id, event_digest[, bundle_ref]}（真实可解析引用）。
        action: approve / reject / comment。
        reviewer_principal_id: 复核人主体 id（非 ObservedSubject）。
        source_store: 提供原始 EvaluationEvent 的 v1.4 EvaluationEventStore。
        review_store: 落库的 ReviewStore（默认模块级单例）。
    """
    if not isinstance(event_ref, dict) or not event_ref.get("event_id"):
        raise ReviewBindingError("event_ref must contain event_id")
    if action not in ("approve", "reject", "comment"):
        raise ReviewError(f"invalid review action {action!r}")

    from src.governance_chain import replay_store as rs_mod

    store = source_store or rs_mod.get_default_store()
    event = store.get(event_ref["event_id"])
    if event is None:
        raise ReviewBindingError(
            f"original event {event_ref['event_id']} not found (forged binding)"
        )
    if event.get("event_hash") != event_ref.get("event_digest"):
        raise ReviewBindingError(
            f"event_digest mismatch for {event_ref['event_id']} (forged binding)"
        )

    rid = idempotency_key or _review_id(envelope_mod.content_digest({
        "event_id": event_ref["event_id"],
        "action": action,
        "reviewer": reviewer_principal_id,
    }))
    recorded = recorded_at or _utcnow_iso()
    rec = ReviewRecord(
        rid, event_ref, action, reviewer_principal_id, recorded, comment=comment,
    )
    record = rec.to_dict()
    record["review_hash"] = rec.review_hash
    rs = review_store or _default_review_store()
    rs.append(record)
    return record


def verify_review_bindings(review_store=None, source_store=None):
    """扫描所有 ReviewRecord，校验 original_event_ref 真实可解析（红线 #8）。

    返回 (ok, problems)。缺失事件或 digest 不符 → 判伪造。
    """
    from src.governance_chain import replay_store as rs_mod

    store = source_store or rs_mod.get_default_store()
    rs = review_store or _default_review_store()
    problems = []
    for rec in rs.list_all():
        ref = rec.get("original_event_ref") or {}
        event = store.get(ref.get("event_id"))
        if event is None:
            problems.append({"review_id": rec.get("review_id"), "reason": "event_not_found"})
        elif event.get("event_hash") != ref.get("event_digest"):
            problems.append({"review_id": rec.get("review_id"), "reason": "digest_mismatch"})
    return (len(problems) == 0, problems)
