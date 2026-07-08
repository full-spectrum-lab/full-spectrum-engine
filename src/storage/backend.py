#!/usr/bin/env python3
"""
Full Spectrum Engine — SQLite Persistence Backend (v0.6)

StorageBackend: SQLite-based persistence for decision records and runestone audit tokens.

Design principles:
    - Zero third-party dependencies (only stdlib sqlite3)
    - Transactional atomic writes (decision + runestone)
    - Thread-safe (threading.RLock protects all reads/writes)
    - Local file storage (no external DB service)
    - WAL mode + busy_timeout + foreign_keys

Constraints:
    - Single-process, multi-thread safe
    - NOT multi-process safe (no multi-worker writing to same DB)
    - result_json stores API response body, not raw request body
    - include_input_metrics=false => result_json must NOT contain input_metrics
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


class StorageBackend:
    """
    SQLite 持久化后端。

    提供 decision + runestone 的原子事务写入、分页查询、TTL 清理、容量上限管理。
    """

    def __init__(
        self,
        db_path: str = "./data/fse.db",
        ttl_days: int = 0,
        max_records: int = 10000,
    ):
        """
        初始化存储后端。

        Args:
            db_path: SQLite 文件路径（相对于当前工作目录，内部转为绝对路径）
            ttl_days: TTL 天数，0 表示不自动清理
            max_records: decisions 表最大记录数，超过时清理最旧记录
        """
        self._db_path = os.path.abspath(db_path)
        self._ttl_days = ttl_days
        self._max_records = max_records
        self._lock = threading.RLock()

        # 确保目录存在
        db_dir = os.path.dirname(self._db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # 初始化连接 (check_same_thread=False for FastAPI thread pool)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # PRAGMA settings
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA foreign_keys=ON")

        # 初始化表结构
        self._init_tables()

        # TTL startup cleanup
        if ttl_days > 0:
            self.cleanup_ttl(ttl_days)

    # ================================================================
    # Table initialization
    # ================================================================

    def _init_tables(self):
        """创建表和索引（如不存在）"""
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id   TEXT PRIMARY KEY,
                    simulation_id TEXT,
                    runestone_id  TEXT,
                    result_json   TEXT NOT NULL,
                    created_at    TEXT NOT NULL,
                    adapter       TEXT,
                    seed          INTEGER
                );

                CREATE TABLE IF NOT EXISTS runestones (
                    runestone_id       TEXT PRIMARY KEY,
                    decision_id        TEXT,
                    runestone_json     TEXT NOT NULL,
                    created_at         TEXT NOT NULL,
                    parent_runestone   TEXT,
                    FOREIGN KEY(decision_id) REFERENCES decisions(decision_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS storage_meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_decisions_created_at
                    ON decisions(created_at);
                CREATE INDEX IF NOT EXISTS idx_decisions_adapter
                    ON decisions(adapter);
                CREATE INDEX IF NOT EXISTS idx_decisions_runestone_id
                    ON decisions(runestone_id);
                CREATE INDEX IF NOT EXISTS idx_runestones_created_at
                    ON runestones(created_at);
                CREATE INDEX IF NOT EXISTS idx_runestones_decision_id
                    ON runestones(decision_id);
            """)
            self._conn.commit()

    # ================================================================
    # Time helper
    # ================================================================

    @staticmethod
    def _now_utc() -> str:
        """返回当前 UTC 时间 (ISO 8601 Z 格式)"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ================================================================
    # Write: decision + runestone (atomic transaction)
    # ================================================================

    def save_decision(
        self,
        decision_id: str,
        simulation_id: str,
        runestone_id: str,
        result: dict,
        adapter: Optional[str] = None,
        seed: int = 42,
    ) -> None:
        """
        保存决策记录 + 关联符石（事务原子写入）。
        写入后触发 TTL 清理和容量上限检查。

        Args:
            decision_id: 决策 ID
            simulation_id: 仿真 ID
            runestone_id: 符石令牌 ID
            result: API 响应 body (dict, already processed per include_input_metrics)
            adapter: 适配器名称 (直接模式为 None)
            seed: 随机种子

        Raises:
            sqlite3.Error: 写入失败时抛出，由 routes 层捕获返回 500
        """
        now = self._now_utc()
        result_json = json.dumps(result, ensure_ascii=False, sort_keys=True)

        # Extract runestone portion (if exists in result)
        runestone_data = result.get("runestone", {})
        runestone_json = json.dumps(runestone_data, ensure_ascii=False, sort_keys=True)
        parent_rs = runestone_data.get("parent_runestone")

        with self._lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute("BEGIN")

                # Write decisions table
                cursor.execute(
                    """INSERT OR REPLACE INTO decisions
                       (decision_id, simulation_id, runestone_id, result_json, created_at, adapter, seed)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (decision_id, simulation_id, runestone_id, result_json, now, adapter, seed),
                )

                # Write runestones table (linked to decision_id, FK constraint)
                if runestone_id:
                    cursor.execute(
                        """INSERT OR REPLACE INTO runestones
                           (runestone_id, decision_id, runestone_json, created_at, parent_runestone)
                           VALUES (?, ?, ?, ?, ?)""",
                        (runestone_id, decision_id, runestone_json, now, parent_rs),
                    )

                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            finally:
                cursor.close()

        # Post-write TTL prune (outside the save transaction; opens its own write tx)
        if self._ttl_days > 0:
            self.cleanup_ttl(self._ttl_days)

        # Post-write capacity enforcement
        self._enforce_max_records()

    def save_standalone_runestone(
        self,
        runestone_id: str,
        runestone_data: dict,
        parent_runestone: Optional[str] = None,
    ) -> None:
        """
        保存独立 POST /runestone 生成的符石 (decision_id 为 NULL)。

        Args:
            runestone_id: 符石令牌 ID
            runestone_data: 完整符石数据 (dict)
            parent_runestone: 父符石 ID
        """
        now = self._now_utc()
        runestone_json = json.dumps(runestone_data, ensure_ascii=False, sort_keys=True)

        with self._lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute("BEGIN")
                cursor.execute(
                    """INSERT OR REPLACE INTO runestones
                       (runestone_id, decision_id, runestone_json, created_at, parent_runestone)
                       VALUES (?, ?, ?, ?, ?)""",
                    (runestone_id, None, runestone_json, now, parent_runestone),
                )
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            finally:
                cursor.close()

    # ================================================================
    # Read: decision
    # ================================================================

    def get_decision(self, decision_id: str) -> Optional[dict]:
        """按 decision_id 查询完整决策记录"""
        with self._lock:
            row = self._conn.execute(
                "SELECT result_json FROM decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()

        if row is None:
            return None
        return json.loads(row["result_json"])

    def list_decisions(
        self,
        limit: int = 20,
        offset: int = 0,
        adapter: Optional[str] = None,
        since: Optional[str] = None,
    ) -> dict:
        """
        分页查询决策列表。

        Returns:
            {"items": [...], "total": int, "limit": int, "offset": int}
        """
        conditions = []
        params: list[Any] = []

        if adapter:
            conditions.append("adapter = ?")
            params.append(adapter)
        if since:
            conditions.append("created_at >= ?")
            params.append(since)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) as cnt FROM decisions {where_clause}",
                params,
            ).fetchone()["cnt"]

            rows = self._conn.execute(
                f"""SELECT decision_id, simulation_id, runestone_id, created_at, adapter, seed
                    FROM decisions {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                params + [limit, offset],
            ).fetchall()

        items = [dict(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    # ================================================================
    # Read: runestone
    # ================================================================

    def get_runestone(self, runestone_id: str) -> Optional[dict]:
        """按 runestone_id 直接查询符石"""
        with self._lock:
            row = self._conn.execute(
                "SELECT runestone_json FROM runestones WHERE runestone_id = ?",
                (runestone_id,),
            ).fetchone()

        if row is None:
            return None
        return json.loads(row["runestone_json"])

    def list_runestones(
        self,
        limit: int = 20,
        offset: int = 0,
        since: Optional[str] = None,
    ) -> dict:
        """分页查询符石列表"""
        conditions = []
        params: list[Any] = []

        if since:
            conditions.append("created_at >= ?")
            params.append(since)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) as cnt FROM runestones {where_clause}",
                params,
            ).fetchone()["cnt"]

            rows = self._conn.execute(
                f"""SELECT runestone_id, decision_id, created_at, parent_runestone
                    FROM runestones {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                params + [limit, offset],
            ).fetchall()

        items = [dict(row) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    # ================================================================
    # Delete: cleanup
    # ================================================================

    def delete_data(
        self,
        before: Optional[str] = None,
        all_data: bool = False,
    ) -> dict:
        """
        删除数据（按时间或全量）。
        外键 ON DELETE CASCADE 自动删除关联 runestones。

        Args:
            before: UTC ISO 8601，删除此时间之前的所有记录
            all_data: True 表示全量删除

        Returns:
            {"deleted_decisions": int, "deleted_runestones": int}
        """
        with self._lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute("BEGIN")

                if all_data:
                    # Full delete: decisions first (cascade deletes linked runestones)
                    d_deleted = cursor.execute("DELETE FROM decisions").rowcount
                    # Standalone runestones (decision_id IS NULL) not cascade-deleted
                    r_indep = cursor.execute(
                        "DELETE FROM runestones WHERE decision_id IS NULL"
                    ).rowcount
                    r_total = d_deleted + r_indep
                elif before:
                    d_deleted = cursor.execute(
                        "DELETE FROM decisions WHERE created_at < ?",
                        (before,),
                    ).rowcount
                    # Standalone runestones by time
                    r_indep = cursor.execute(
                        "DELETE FROM runestones WHERE decision_id IS NULL AND created_at < ?",
                        (before,),
                    ).rowcount
                    r_total = d_deleted + r_indep
                else:
                    cursor.execute("COMMIT")
                    return {"deleted_decisions": 0, "deleted_runestones": 0}

                cursor.execute("COMMIT")
                return {"deleted_decisions": d_deleted, "deleted_runestones": r_total}
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            finally:
                cursor.close()

    # ================================================================
    # Retention: TTL + capacity
    # ================================================================

    def cleanup_ttl(self, ttl_days: int) -> int:
        """清理超过 TTL 天数的记录，返回删除的 decision 条数"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = self.delete_data(before=cutoff_str)
        return result["deleted_decisions"]

    def _enforce_max_records(self) -> None:
        """容量上限检查：超过 max_records 时删除最旧 decisions（级联删除 runestones）"""
        with self._lock:
            count = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM decisions"
            ).fetchone()["cnt"]

            if count > self._max_records:
                excess = count - self._max_records
                self._conn.execute(
                    """DELETE FROM decisions WHERE decision_id IN (
                        SELECT decision_id FROM decisions
                        ORDER BY created_at ASC
                        LIMIT ?
                    )""",
                    (excess,),
                )
                self._conn.commit()

    # ================================================================
    # Stats
    # ================================================================

    def get_stats(self) -> dict:
        """返回存储统计信息"""
        with self._lock:
            d_count = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM decisions"
            ).fetchone()["cnt"]
            r_count = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM runestones"
            ).fetchone()["cnt"]

        db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0

        return {
            "storage_mode": "sqlite-persistent",
            "db_path": self._db_path,
            "db_size_bytes": db_size,
            "decision_count": d_count,
            "runestone_count": r_count,
            "ttl_days": self._ttl_days,
            "max_records": self._max_records,
        }

    # ================================================================
    # Connection lifecycle
    # ================================================================

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            self._conn.close()
