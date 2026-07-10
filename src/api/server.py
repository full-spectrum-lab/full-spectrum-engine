#!/usr/bin/env python3
"""
Full Spectrum Engine API — Server factory and startup entry point (v0.9.0-alpha)

Design principles:
    - create_app() factory function; seed initialized here (Qwen-B: no global state mutation in routes)
    - CORSMiddleware allows localhost (Qwen-C: OPTIONS preflight support)
    - Global headers middleware (P1-1: X-Storage-Mode / X-Full-Spectrum-Notice / X-Production-Ready)
    - Default 127.0.0.1; 0.0.0.0 prints non-production warning (P2-2)
    - Startup log includes NOT FOR PRODUCTION warning
    - v0.6: SQLite persistence layer (StorageBackend), replaces v0.5 in-memory dict

Startup:
    python -m src.api.server
    python -m src.api.server --host 127.0.0.1 --port 8000
    python -m src.api.server --host 0.0.0.0 --port 8000  # prints warning
    python -m src.api.server --db-path /path/to/fse.db --ttl-days 30 --max-records 10000
"""

import argparse
import logging
import os
import sys

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .routes import router, API_VERSION, ENGINE_VERSION
from src.storage.backend import StorageBackend

logger = logging.getLogger("full-spectrum.api.server")


def create_app(
    seed: int = 42,
    bind_host: str = "127.0.0.1",
    db_path: str = "./data/fse.db",
    ttl_days: int = 0,
    max_records: int = 10000,
) -> FastAPI:
    """
    Create a FastAPI application instance.

    Args:
        seed: Global random seed, initialized at app creation (Qwen-B: no global state mutation in routes)
        bind_host: Bind address, used by health endpoint for network exposure reporting + DELETE safety valve
        db_path: SQLite database path (v0.6)
        ttl_days: TTL days, 0 means no auto-cleanup (v0.6)
        max_records: Maximum decision records (v0.6)

    Returns:
        FastAPI application instance
    """
    # Initialize random seed at app creation time (Qwen-B)
    import numpy as np
    np.random.seed(seed)

    app = FastAPI(
        title="Full Spectrum Engine API",
        description=(
            "Local REST API — turns the Full Spectrum Engine from a CLI script into an HTTP service callable by business systems.\n\n"
            "WARNING: NOT FOR PRODUCTION — local development interface, no authentication, no production-grade deployment.\n"
            "Storage mode: sqlite-persistent (v0.6 SQLite persistence)"
        ),
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Store global state
    app.state.seed = seed
    app.state.bind_host = bind_host

    # v0.6: Initialize SQLite storage backend (replaces v0.5 in-memory dict)
    storage = StorageBackend(db_path=db_path, ttl_days=ttl_days, max_records=max_records)
    app.state.storage = storage

    # ============================================================
    # CORS middleware (Qwen-C: OPTIONS preflight support)
    # ============================================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============================================================
    # Global headers middleware (P1-1: metadata in headers)
    # v0.6: X-Storage-Mode updated to sqlite-persistent
    # ============================================================
    @app.middleware("http")
    async def add_metadata_headers(request: Request, call_next):
        response = await call_next(request)
        # All responses carry these metadata headers
        response.headers["X-Storage-Mode"] = "sqlite-persistent"
        response.headers["X-Full-Spectrum-Notice"] = "local-dev-only"
        response.headers["X-Production-Ready"] = "false"
        return response

    # Register routes
    app.include_router(router)

    # Root path redirects to docs
    @app.get("/")
    async def root():
        return {
            "service": "Full Spectrum Engine API",
            "version": API_VERSION,
            "engine_version": ENGINE_VERSION,
            "docs": "/docs",
            "health": "/api/v1/health",
            "notice": "NOT FOR PRODUCTION — local development interface only",
        }

    return app


# ============================================================
# Uvicorn startup entry point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Full Spectrum Engine v0.9.0-alpha API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.api.server                           # Default 127.0.0.1:8000
  python -m src.api.server --port 9000               # Custom port
  python -m src.api.server --host 0.0.0.0 --port 8000  # Expose to network (prints warning)
  python -m src.api.server --db-path /tmp/fse.db --ttl-days 30

WARNING: NOT FOR PRODUCTION — local development interface, no authentication.
        """,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default 127.0.0.1; 0.0.0.0 prints non-production warning)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port (default 8000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Global random seed (default 42)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Development hot-reload mode",
    )
    # v0.6 parameters
    parser.add_argument(
        "--db-path",
        default="./data/fse.db",
        help="SQLite database path (default ./data/fse.db)",
    )
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=0,
        help="TTL days, 0 means no auto-cleanup (default 0)",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=10000,
        help="Maximum decision records (default 10000)",
    )
    args = parser.parse_args()

    # P2-2: Print warning for non-local binding
    if args.host not in ("127.0.0.1", "localhost"):
        warning_line = (
            "=" * 70 + "\n"
            "WARNING: You are binding Full Spectrum Engine API to a non-local address.\n"
            "This API is a local development interface and is NOT production-hardened.\n"
            f"Binding to: {args.host}\n"
            "Do NOT use this in production without proper authentication and security measures.\n"
            + "=" * 70
        )
        print(warning_line, file=sys.stderr)
        logger.warning(f"Non-local binding detected: {args.host}")

    # Startup log (v0.6 enhanced)
    print(
        f"\n"
        f"Full Spectrum Engine v0.9.0-alpha API Server\n"
        f"Running at http://{args.host}:{args.port}\n"
        f"Docs: http://{args.host}:{args.port}/docs\n"
        f"Database: {os.path.abspath(args.db_path)}\n"
        f"Max records: {args.max_records}\n"
        + (f"TTL: {args.ttl_days} days (cleanup on startup + post-save)\n" if args.ttl_days > 0 else "")
        + f"NOT FOR PRODUCTION\n"
        f"",
        file=sys.stderr,
    )

    # Create application
    app = create_app(
        seed=args.seed,
        bind_host=args.host,
        db_path=args.db_path,
        ttl_days=args.ttl_days,
        max_records=args.max_records,
    )

    # Start uvicorn
    import uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
