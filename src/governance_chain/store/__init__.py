#!/usr/bin/env python3
"""
v1.4 append-only audit store package.

This directory holds the standalone SQLite database that backs the
``EvaluationEvent`` append-only log (FR-01 / FR-07). It is intentionally
decoupled from the v1.2 ``src/storage`` module: SQLite is standard-library,
offline, single-writer atomic-append, and the ``previous_event_hash`` column
forms a natural hash chain.

The database file (``evaluation_events.sqlite``) is git-ignored (see repo
``.gitignore``) and is only ever created at runtime.
"""
