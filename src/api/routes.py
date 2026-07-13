#!/usr/bin/env python3
"""
Full Spectrum Engine API — Route definitions (v1.0.0)

8 endpoints:
    GET    /api/v1/health                    — Health check (enhanced: storage metadata)
    POST   /api/v1/evaluate                  — Simulation evaluation (direct mode + adapter mode)
    POST   /api/v1/runestone                 — Standalone runestone generation
    GET    /api/v1/decisions/{id}            — Decision record lookup (from SQLite)
    GET    /api/v1/audit/decisions           — Decision audit list query (v0.6)
    GET    /api/v1/audit/runestones          — Runestone audit list query (v0.6)
    GET    /api/v1/audit/runestones/{id}     — Single runestone lookup (v0.6)
    DELETE /api/v1/audit/decisions           — Data cleanup with safety valve (v0.6)

Engineering constraints:
    - API body strictly compatible with CLI output (no envelope) (P1-1)
    - Metadata goes in HTTP headers (P1-1)
    - decision_id and runestone_id strictly separated (P0-1)
    - Error codes unified 422/404/500 (P1-2)
    - risk_vector validation failure returns 422, not bare 500 (P1-3)
    - include_input_metrics defaults to false (P1-5)
    - v0.6: SQLite persistence layer, X-Storage-Mode=sqlite-persistent
    - v0.6: X-Input-Metrics-Persisted response header (NFR-16)
    - v0.6: DELETE safety valve (confirm + before/all + local-only binding)
    - v1.0: All error responses use structured format {"message", "error_code"}
"""

import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from .models import EvaluateRequest, RunestoneRequest, HealthResponse, EnvelopeRequest, ProfileLoadRequest, PolicyLoadRequest
from .registry import get_registry
from src.governance_chain import envelope as envelope_mod

# Ensure project root is on sys.path so we can import simulate.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from simulate import run_simulation  # noqa: E402
from src.bridge.runestone import Runestone, RiskVector, ReasonField  # noqa: E402
from src.subject import normalize_declaration, subject_ref, SubjectDeclarationError  # noqa: E402
from src.governance_chain.profiles.registry import get_default_registry as get_profile_registry  # noqa: E402
from src.governance_chain.registry import ProfileIntegrityError  # noqa: E402

router = APIRouter(prefix="/api/v1", tags=["v1.3.0"])

# API version identifiers
API_VERSION = "1.3.0"
ENGINE_VERSION = "1.3.0"

# Required risk vector fields (must match RiskVector.to_dict())
# Note: the field name "reversibility" is retained for protocol compatibility,
# but its semantics are "irreversibility" (higher value = more irreversible).
RISK_VECTOR_FIELDS = [
    "survival_impact",
    "trust_impact",
    "meaning_impact",
    "reversibility",  # semantics: irreversibility
    "explainability",
    "diffusivity",
    "urgency",
    "uncertainty",
]


# ============================================================
# Helper functions
# ============================================================

def _generate_decision_id(scenario: dict, seed: int, subject_ref_value=None) -> str:
    """
    Generate a deterministic decision_id from scenario content and seed (P0-1).

    decision_id is the API-layer evaluation record ID, strictly separated from
    runestone_id (the audit token ID). The same scenario + seed always produces
    the same decision_id, ensuring reproducibility.
    """
    payload = json.dumps(
        {"scenario": scenario, "seed": seed, "subject_ref": subject_ref_value},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return f"DEC_{hashlib.sha256(payload).hexdigest()[:16]}"


def _set_metadata_headers(
    response: Response,
    decision_id: Optional[str] = None,
    input_metrics_persisted: Optional[bool] = None,
) -> None:
    """
    Set API metadata headers on the response (P1-1).

    These are kept out of the body so the API body can be diffed against CLI output.
    v0.6: X-Storage-Mode updated to sqlite-persistent.
    v0.6: NFR-16 X-Input-Metrics-Persisted response header.
    """
    response.headers["X-Storage-Mode"] = "sqlite-persistent"
    response.headers["X-Full-Spectrum-Notice"] = "local-dev-only"
    response.headers["X-Production-Ready"] = "false"
    if decision_id:
        response.headers["X-Decision-Id"] = decision_id
    # NFR-16: X-Input-Metrics-Persisted
    if input_metrics_persisted is not None:
        response.headers["X-Input-Metrics-Persisted"] = str(input_metrics_persisted).lower()


def _validate_risk_vector(rv_dict: dict) -> None:
    """
    Validate a risk vector dict (P1-3).

    Raises 422 with a structured error when required fields are missing,
    instead of letting the RiskVector constructor throw a bare 500.
    """
    missing = [f for f in RISK_VECTOR_FIELDS if f not in rv_dict]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": f"Invalid risk_vector: missing fields: {missing}. Required fields: {RISK_VECTOR_FIELDS}",
                "error_code": "VALIDATION_ERROR",
            },
        )
    # Validate value types
    for field in RISK_VECTOR_FIELDS:
        val = rv_dict[field]
        if not isinstance(val, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": f"Invalid risk_vector: field '{field}' must be a number, got {type(val).__name__}",
                    "error_code": "VALIDATION_ERROR",
                },
            )


# ============================================================
# 端点 1: GET /api/v1/health
# ============================================================

@router.get("/health", response_model=HealthResponse)
async def health(request: Request, response: Response):
    """
    Health check endpoint.

    v0.6: Enhanced — original fields retained + new storage metadata.
    """
    registry = get_registry()
    _set_metadata_headers(response)

    # 判断网络暴露级别
    app = request.app
    host = getattr(app.state, "bind_host", "127.0.0.1")
    network_exposure = "local" if host in ("127.0.0.1", "localhost") else "non-local"

    # v0.6: 从 storage 获取统计信息
    storage = getattr(app.state, "storage", None)
    if storage:
        stats = storage.get_stats()
        return {
            "status": "ok",
            "version": API_VERSION,
            "engine_version": ENGINE_VERSION,
            "registered_adapters": registry.list_industries(),
            "storage_mode": stats["storage_mode"],
            "network_exposure": network_exposure,
            "db_path": stats["db_path"],
            "db_size_bytes": stats["db_size_bytes"],
            "decision_count": stats["decision_count"],
            "runestone_count": stats["runestone_count"],
            "ttl_days": stats["ttl_days"],
            "max_records": stats["max_records"],
        }

    return HealthResponse(
        status="ok",
        version=API_VERSION,
        engine_version=ENGINE_VERSION,
        registered_adapters=registry.list_industries(),
        storage_mode="sqlite-persistent",
        network_exposure=network_exposure,
    )


# ============================================================
# 端点 2: POST /api/v1/evaluate
# ============================================================

@router.post("/evaluate")
async def evaluate(req: EvaluateRequest, request: Request, response: Response):
    """
    Simulation evaluation endpoint.

    Supports two modes:
    1. Direct mode: pass a complete scenario dict
    2. Adapter mode: pass industry + metrics

    Response body is strictly equal to run_simulation() output, fully CLI-compatible.
    decision_id is returned via the X-Decision-Id header (P0-1, P1-1).
    """
    registry = get_registry()

    # Validate: exactly one mode must be used
    has_scenario = req.scenario is not None
    has_adapter = req.industry is not None and req.metrics is not None

    if has_scenario and has_adapter:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Cannot use both 'scenario' (direct mode) and 'industry'+'metrics' (adapter mode). Choose one.",
                "error_code": "VALIDATION_ERROR",
            },
        )

    if not has_scenario and not has_adapter:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Must provide either 'scenario' (direct mode) or 'industry'+'metrics' (adapter mode).",
                "error_code": "VALIDATION_ERROR",
            },
        )

    # Build scenario
    if has_scenario:
        # Direct mode: use the provided scenario dict
        scenario = req.scenario
    else:
        # Adapter mode: build scenario via MetricAdapter
        adapter = registry.get(req.industry)
        if adapter is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": f"Unregistered adapter: '{req.industry}'. Registered adapters: {registry.list_industries()}",
                    "error_code": "ADAPTER_NOT_FOUND",
                },
            )

        # Validate required metrics
        missing = adapter.validate_metrics(req.metrics)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": f"Missing required metrics for '{req.industry}': {missing}. Required: {adapter.required_metrics}",
                    "error_code": "VALIDATION_ERROR",
                },
            )

        # Build scenario (include_input_metrics defaults to false, P1-5 privacy minimization)
        scenario = adapter.to_scenario(
            req.metrics,
            simulation_id=req.simulation_id,
            input_query=req.input_query,
            sensitivity_level=req.sensitivity_level,
            enterprise_id=req.enterprise_id,
            rule_version=req.rule_version,
            include_input_metrics=req.include_input_metrics,
        )

    # Run simulation
    try:
        result = run_simulation(scenario, seed=req.seed)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": f"Simulation error: {str(e)}",
                "error_code": "SIMULATION_ERROR",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Internal simulation error: {str(e)}",
                "error_code": "INTERNAL_ERROR",
            },
        )

    if req.subject_declaration is not None:
        try:
            declaration, warnings = normalize_declaration(req.subject_declaration)
        except SubjectDeclarationError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "error_code": exc.code})
        result["subject_ref"] = subject_ref(declaration)
        if warnings:
            result["subject_declaration_warnings"] = warnings

    # v0.6 rc2 fix MH-BUG-v0.6-001: inject input_metrics into result when include_input_metrics=true
    # Ensures X-Input-Metrics-Persisted header / API response body / DB result_json are all consistent.
    # run_simulation() output does not include input_metrics (only in scenario._adapter),
    # so we explicitly inject it to make persisted data match the header declaration.
    if has_adapter and req.include_input_metrics:
        adapter_meta = scenario.get("_adapter", {})
        if "input_metrics" in adapter_meta:
            result["input_metrics"] = adapter_meta["input_metrics"]

    # Generate decision_id (P0-1: strictly separated from runestone_id)
    decision_id = _generate_decision_id(scenario, req.seed, result.get("subject_ref"))

    # v0.6: Persist to SQLite (replaces v0.5 in-memory cache)
    runestone_id = result.get("runestone", {}).get("runestone_id", "")
    app = request.app
    storage = getattr(app.state, "storage", None)

    if storage:
        try:
            storage.save_decision(
                decision_id=decision_id,
                simulation_id=req.simulation_id or result.get("simulation_id", ""),
                runestone_id=runestone_id,
                result=result,
                adapter=req.industry,
                seed=req.seed,
            )
        except Exception as e:
            # NFR-06/NFR-15: storage write failure returns structured 500, no simulation result
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Storage write failed",
                    "error_code": "STORAGE_ERROR",
                    "storage_detail": str(e),
                },
            )

    # Set metadata headers (P1-1: metadata in headers, not body)
    # NFR-16: X-Input-Metrics-Persisted
    _set_metadata_headers(
        response,
        decision_id=decision_id,
        input_metrics_persisted=req.include_input_metrics,
    )

    # Return raw simulation result (strictly CLI-compatible, no envelope)
    return result


# ============================================================
# 端点 3: POST /api/v1/runestone
# ============================================================

@router.post("/runestone")
async def create_runestone(req: RunestoneRequest, request: Request, response: Response):
    """
    Standalone runestone generation endpoint.

    Bypasses the full simulation pipeline and directly creates a runestone audit token.
    Response body equals Runestone.to_dict() output.
    """
    # Validate reason fields
    if "enterprise_id" not in req.reason or "rule_version" not in req.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "reason must contain 'enterprise_id' and 'rule_version' fields.",
                "error_code": "VALIDATION_ERROR",
            },
        )

    # Validate risk_vector (P1-3: validation failure returns 422, not bare 500)
    _validate_risk_vector(req.risk_vector)

    # Construct objects
    try:
        reason_field = ReasonField(
            enterprise_id=req.reason["enterprise_id"],
            rule_version=req.reason["rule_version"],
        )
        risk_vector = RiskVector(**req.risk_vector)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": f"Failed to construct runestone components: {str(e)}",
                "error_code": "VALIDATION_ERROR",
            },
        )

    # Generate deterministic runestone_id (if seed provided)
    import numpy as np
    np.random.seed(req.seed)

    runestone_id = None
    if req.seed is not None:
        # Use deterministic ID generation
        payload = json.dumps(
            {
                "decision": req.decision,
                "reason": str(reason_field),
                "risk_vector": risk_vector.to_dict(),
                "seed": req.seed,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        runestone_id = f"RS_{hashlib.sha256(payload).hexdigest()[:16]}"

    # Deterministic timestamp
    from simulate import DETERMINISTIC_UNIX_TS
    timestamp = DETERMINISTIC_UNIX_TS + float(req.seed)

    runestone = Runestone.create(
        decision=req.decision,
        reason=str(reason_field),
        risk_vector=risk_vector,
        parent=req.parent_runestone,
        agents=req.agent_trail,
        ess_data=req.ess_snapshot,
        runestone_id=runestone_id,
        timestamp=timestamp,
    )

    _set_metadata_headers(response)

    runestone_dict = runestone.to_dict()

    # v0.6: Persist standalone runestone (decision_id is NULL)
    app = request.app
    storage = getattr(app.state, "storage", None)
    if storage:
        rs_id = runestone_dict.get("runestone_id", "")
        if rs_id:
            try:
                storage.save_standalone_runestone(
                    runestone_id=rs_id,
                    runestone_data=runestone_dict,
                    parent_runestone=req.parent_runestone,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "message": "Storage write failed",
                        "error_code": "STORAGE_ERROR",
                        "storage_detail": str(e),
                    },
                )

    return runestone_dict


# ============================================================
# 端点 4: GET /api/v1/decisions/{decision_id}
# ============================================================

@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str, request: Request, response: Response):
    """
    Decision record lookup endpoint.

    v0.6: Reads from SQLite (replaces v0.5 in-memory dict). Survives service restart.
    """
    app = request.app
    storage = getattr(app.state, "storage", None)

    result = None
    if storage:
        result = storage.get_decision(decision_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"Decision '{decision_id}' not found.",
                "error_code": "NOT_FOUND",
            },
        )

    _set_metadata_headers(response, decision_id=decision_id)

    # Return the persisted raw result (consistent with /evaluate response)
    return result


# ============================================================
# Endpoint 5: GET /api/v1/audit/decisions — Decision audit list (v0.6)
# ============================================================

@router.get("/audit/decisions")
async def list_decisions(
    request: Request,
    response: Response,
    limit: int = 20,
    offset: int = 0,
    adapter: Optional[str] = None,
    since: Optional[str] = None,
):
    """
    v0.6: Paginated decision list query.

    Query parameters:
        limit: page size (1-100, default 20)
        offset: offset (default 0)
        adapter: filter by adapter (optional)
        since: UTC ISO 8601 start time (optional)
    """
    _set_metadata_headers(response)

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "limit must be between 1 and 100",
                "error_code": "VALIDATION_ERROR",
            },
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "offset must be >= 0",
                "error_code": "VALIDATION_ERROR",
            },
        )

    # Validate since format if provided
    if since:
        try:
            datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": f"Invalid 'since' format: {since}, use UTC ISO 8601",
                    "error_code": "VALIDATION_ERROR",
                },
            )

    storage = request.app.state.storage
    return storage.list_decisions(limit=limit, offset=offset, adapter=adapter, since=since)


# ============================================================
# Endpoint 6: GET /api/v1/audit/runestones — Runestone audit list (v0.6)
# ============================================================

@router.get("/audit/runestones")
async def list_runestones(
    request: Request,
    response: Response,
    limit: int = 20,
    offset: int = 0,
    since: Optional[str] = None,
):
    """
    v0.6: Runestone list query.

    Query parameters:
        limit: page size (1-100, default 20)
        offset: offset (default 0)
        since: UTC ISO 8601 start time (optional)
    """
    _set_metadata_headers(response)

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "limit must be between 1 and 100",
                "error_code": "VALIDATION_ERROR",
            },
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "offset must be >= 0",
                "error_code": "VALIDATION_ERROR",
            },
        )

    if since:
        try:
            datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": f"Invalid 'since' format: {since}, use UTC ISO 8601",
                    "error_code": "VALIDATION_ERROR",
                },
            )

    storage = request.app.state.storage
    return storage.list_runestones(limit=limit, offset=offset, since=since)


# ============================================================
# Endpoint 7: GET /api/v1/audit/runestones/{runestone_id} — Single runestone lookup (v0.6)
# ============================================================

@router.get("/audit/runestones/{runestone_id}")
async def get_runestone(runestone_id: str, request: Request, response: Response):
    """
    v0.6: Look up a runestone by runestone_id.

    Can query runestones auto-generated by evaluate and standalone POST /runestone runestones.
    """
    _set_metadata_headers(response)

    storage = request.app.state.storage
    result = storage.get_runestone(runestone_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"Runestone '{runestone_id}' not found.",
                "error_code": "NOT_FOUND",
            },
        )

    return result


# ============================================================
# Endpoint 8: DELETE /api/v1/audit/decisions — Data cleanup (v0.6, with safety valve)
# ============================================================

@router.delete("/audit/decisions")
async def delete_data(
    request: Request,
    response: Response,
    confirm: Optional[str] = None,
    before: Optional[str] = None,
    all: Optional[str] = None,
):
    """
    v0.6: Data cleanup endpoint (with safety valve).

    Safety valve rules:
    1. Must pass confirm=true, otherwise 422
    2. Must pass before=<UTC ISO> or all=true, otherwise 422
    3. Returns 403 when bind_host is not 127.0.0.1/localhost
    """
    _set_metadata_headers(response)

    # Safety valve 1: non-local binding check
    bind_host = getattr(request.app.state, "bind_host", "127.0.0.1")
    if bind_host not in ("127.0.0.1", "localhost"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "DELETE endpoint disabled on non-local bind",
                "error_code": "FORBIDDEN",
            },
        )

    # Safety valve 2: confirm parameter
    if confirm != "true":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Missing confirm=true parameter",
                "error_code": "VALIDATION_ERROR",
            },
        )

    # Safety valve 3: before or all parameter
    if all == "true":
        storage = request.app.state.storage
        return storage.delete_data(all_data=True)
    elif before:
        try:
            datetime.fromisoformat(before.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": f"Invalid 'before' format: {before}, use UTC ISO 8601",
                    "error_code": "VALIDATION_ERROR",
                },
            )
        storage = request.app.state.storage
        return storage.delete_data(before=before)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Must provide before=<UTC ISO> or all=true",
                "error_code": "VALIDATION_ERROR",
            },
        )


# ============================================================
# 端点 9: POST /api/v1/envelope  (v1.2 Observer I/O contract)
# ============================================================

@router.post("/envelope")
async def envelope_run(req: EnvelopeRequest, response: Response):
    """
    v1.2 Observer Input/Output Envelope endpoint.

    Request body = v1.2 Input Envelope (EnvelopeRequest.input_envelope).
    Response body = v1.2 Output Envelope, produced by the SAME
    `envelope.run_envelope` function the CLI uses, so REST and CLI are
    byte-for-byte equivalent (FR-03 / AC-01). Pure local computation; no
    network calls. L4_CANDIDATE references are carried but never produce
    external effect (external_effect is always false in v1.2).
    """
    _set_metadata_headers(response)
    try:
        out = envelope_mod.run_envelope(req.input_envelope)
    except envelope_mod.InputEnvelopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": f"Input Envelope invalid: {exc}",
                "error_code": "INPUT_ENVELOPE_INVALID",
                "errors": exc.errors,
            },
        )
    ok, errors = envelope_mod.validate_output_envelope(out)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Output Envelope failed schema validation: {errors}",
                "error_code": "OUTPUT_ENVELOPE_INVALID",
            },
        )
    return out


# ============================================================
# v1.3 additive endpoints (Profile / Policy load) — NOT FOR PRODUCTION / local only
# ============================================================

@router.post("/profile/load")
async def profile_load(req: ProfileLoadRequest, response: Response):
    """
    v1.3 additive endpoint: validate + ingest a Profile into the shared registry.

    No authentication is added (consistent with the v1.2 local / offline posture).
    Returns the resolved ``id@version`` key plus the recomputed digest.
    """
    _set_metadata_headers(response)
    reg = get_profile_registry()
    try:
        key = reg.ingest(req.profile)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(exc), "error_code": "PROFILE_INVALID"},
        )
    except ProfileIntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(exc), "error_code": "PROFILE_INTEGRITY"},
        )
    return {
        "key": key,
        "profile_id": req.profile.get("id"),
        "version": req.profile.get("version"),
    }


@router.get("/profile/{profile_id}")
async def profile_get(profile_id: str, response: Response, version: Optional[str] = None):
    """
    v1.3 additive endpoint: fetch a Profile by id (optionally pinned version).
    """
    _set_metadata_headers(response)
    reg = get_profile_registry()
    try:
        obj = reg.get(profile_id, version)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"profile {profile_id} not found", "error_code": "NOT_FOUND"},
        )
    return obj


@router.post("/policy/load")
async def policy_load(req: PolicyLoadRequest, response: Response):
    """
    v1.3 additive endpoint: validate a governance policy dict (never executed).

    The Observer only COMPATIBLES with, never FORGES, auth; a policy is validated
    for schema completeness but is not run by the first-generation engine.
    """
    _set_metadata_headers(response)
    policy = req.policy
    for field in ("policy_id", "version", "source", "approved_by", "change_log", "rules", "default"):
        if field not in policy:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"message": f"policy missing required field: {field}", "error_code": "POLICY_INVALID"},
            )
    return {"policy_id": policy.get("policy_id"), "version": policy.get("version")}
