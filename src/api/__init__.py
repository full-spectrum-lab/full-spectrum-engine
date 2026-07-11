"""
Full Spectrum Engine — REST API Package (v1.0.0)

Local-first API layer: provides HTTP invocation, industry adapter evaluation,
SQLite audit persistence, and query capabilities on top of the core engine,
without modifying the engine core.

Endpoints:
    GET  /api/v1/health              — Health check
    POST /api/v1/evaluate            — Simulation evaluation
    POST /api/v1/runestone           — Runestone generation
    GET  /api/v1/decisions/{id}      — Decision record lookup
    GET  /api/v1/audit/decisions     — Decision audit list
    GET  /api/v1/audit/runestones    — Runestone audit list

Constraints:
    - Local-first (default 127.0.0.1)
    - SQLite local persistence
    - API body strictly compatible with CLI output
    - Metadata in HTTP headers
    - No authentication / SaaS / protocol network / final business execution
"""

__version__ = "1.0.0"
