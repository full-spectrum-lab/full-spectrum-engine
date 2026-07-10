#!/usr/bin/env python3
"""
Full Spectrum Engine API — 路由定义 (v0.7.2-alpha)

8 个端点：
    GET    /api/v1/health                    — 健康检查（增强：storage metadata）
    POST   /api/v1/evaluate                  — 仿真评估（直接模式 + 适配器模式）
    POST   /api/v1/runestone                 — 独立符石生成
    GET    /api/v1/decisions/{id}            — 决策记录查询（从 SQLite 读取）
    GET    /api/v1/audit/decisions           — 决策审计列表查询 (v0.6 新增)
    GET    /api/v1/audit/runestones          — 符石审计列表查询 (v0.6 新增)
    GET    /api/v1/audit/runestones/{id}     — 单个符石查询 (v0.6 新增)
    DELETE /api/v1/audit/decisions           — 数据清理（带安全阀）(v0.6 新增)

工程约束：
    - API body 严格兼容 CLI 输出（无 envelope）(P1-1)
    - 元信息走 HTTP headers (P1-1)
    - decision_id 与 runestone_id 严格区分 (P0-1)
    - 错误码统一 422/404/500 (P1-2)
    - risk_vector 校验失败返回 422，不裸 500 (P1-3)
    - include_input_metrics 默认 false (P1-5)
    - v0.6: SQLite 持久化层，X-Storage-Mode=sqlite-persistent
    - v0.6: X-Input-Metrics-Persisted 响应头 (NFR-16)
    - v0.6: DELETE 安全阀 (confirm + before/all + 本地绑定)
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

from .models import EvaluateRequest, RunestoneRequest, HealthResponse
from .registry import get_registry

# 确保项目根目录在 sys.path 中，以便导入 simulate.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from simulate import run_simulation  # noqa: E402
from src.bridge.runestone import Runestone, RiskVector, ReasonField  # noqa: E402

router = APIRouter(prefix="/api/v1", tags=["v0.7.2-alpha"])

# API 版本标识
API_VERSION = "0.7.2a1"
ENGINE_VERSION = "0.7.2-alpha"

# 风险向量必需字段（与 RiskVector.to_dict() 一致）
# 注意：reversibility 字段名保留以兼容协议规范，语义为 irreversibility（值越高越不可逆）
RISK_VECTOR_FIELDS = [
    "survival_impact",
    "trust_impact",
    "meaning_impact",
    "reversibility",  # 语义为 irreversibility
    "explainability",
    "diffusivity",
    "urgency",
    "uncertainty",
]


# ============================================================
# 辅助函数
# ============================================================

def _generate_decision_id(scenario: dict, seed: int) -> str:
    """
    基于场景内容和种子生成确定性 decision_id (P0-1)。

    decision_id 是 API 层的评估记录 ID，与 runestone_id（审计令牌 ID）严格区分。
    同一 scenario + seed 总是生成相同的 decision_id，保证可复现。
    """
    payload = json.dumps(
        {"scenario": scenario, "seed": seed},
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
    在响应上设置 API 元信息 headers (P1-1)。

    这些信息不放入 body，确保 API body 能与 CLI 输出做 diff。
    v0.6: X-Storage-Mode 更新为 sqlite-persistent。
    v0.6: NFR-16 X-Input-Metrics-Persisted 响应头。
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
    校验风险向量字典 (P1-3)。

    缺少必需字段时抛出 422，而不是让 RiskVector 构造函数抛裸 500。
    """
    missing = [f for f in RISK_VECTOR_FIELDS if f not in rv_dict]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid risk_vector: missing fields: {missing}. Required fields: {RISK_VECTOR_FIELDS}",
        )
    # 校验值类型
    for field in RISK_VECTOR_FIELDS:
        val = rv_dict[field]
        if not isinstance(val, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid risk_vector: field '{field}' must be a number, got {type(val).__name__}",
            )


# ============================================================
# 端点 1: GET /api/v1/health
# ============================================================

@router.get("/health", response_model=HealthResponse)
async def health(request: Request, response: Response):
    """
    健康检查端点。

    v0.6: 增强版 — 原有字段保留 + 新增 storage metadata。
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
    仿真评估端点。

    支持两种模式：
    1. 直接模式：传入完整 scenario dict
    2. 适配器模式：传入 industry + metrics

    响应 body 严格等于 run_simulation() 的原始输出，与 CLI 完全兼容。
    decision_id 通过 X-Decision-Id header 返回 (P0-1, P1-1)。
    """
    registry = get_registry()

    # 验证：两种模式必须且只能选一种
    has_scenario = req.scenario is not None
    has_adapter = req.industry is not None and req.metrics is not None

    if has_scenario and has_adapter:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot use both 'scenario' (direct mode) and 'industry'+'metrics' (adapter mode). Choose one.",
        )

    if not has_scenario and not has_adapter:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Must provide either 'scenario' (direct mode) or 'industry'+'metrics' (adapter mode).",
        )

    # 构建场景
    if has_scenario:
        # 直接模式：使用传入的 scenario dict
        scenario = req.scenario
    else:
        # 适配器模式：通过 MetricAdapter 构建 scenario
        adapter = registry.get(req.industry)
        if adapter is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unregistered adapter: '{req.industry}'. Registered adapters: {registry.list_industries()}",
            )

        # 校验必需指标
        missing = adapter.validate_metrics(req.metrics)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Missing required metrics for '{req.industry}': {missing}. Required: {adapter.required_metrics}",
            )

        # 构建 scenario（include_input_metrics 默认 false，P1-5 隐私最小化）
        scenario = adapter.to_scenario(
            req.metrics,
            simulation_id=req.simulation_id,
            input_query=req.input_query,
            sensitivity_level=req.sensitivity_level,
            enterprise_id=req.enterprise_id,
            rule_version=req.rule_version,
            include_input_metrics=req.include_input_metrics,
        )

    # 执行仿真
    try:
        result = run_simulation(scenario, seed=req.seed)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Simulation error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal simulation error: {str(e)}",
        )

    # v0.6 rc2 修复 MH-BUG-v0.6-001: include_input_metrics=true 时将 input_metrics 注入 result
    # 确保 X-Input-Metrics-Persisted header / API response body / DB result_json 三者一致
    # run_simulation() 输出不包含 input_metrics（仅在 scenario._adapter 中），
    # 因此需要显式注入到 result 中，使持久化数据与 header 声明一致
    if has_adapter and req.include_input_metrics:
        adapter_meta = scenario.get("_adapter", {})
        if "input_metrics" in adapter_meta:
            result["input_metrics"] = adapter_meta["input_metrics"]

    # 生成 decision_id（P0-1：与 runestone_id 严格区分）
    decision_id = _generate_decision_id(scenario, req.seed)

    # v0.6: 持久化到 SQLite（替代 v0.5 内存缓存）
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
            # NFR-06/NFR-15: 写入失败返回结构化 500，不返回仿真结果
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Storage write failed",
                    "error_code": "STORAGE_ERROR",
                    "storage_detail": str(e),
                },
            )

    # 设置元信息 headers（P1-1：元信息走 headers，不放入 body）
    # NFR-16: X-Input-Metrics-Persisted
    _set_metadata_headers(
        response,
        decision_id=decision_id,
        input_metrics_persisted=req.include_input_metrics,
    )

    # 返回原始仿真结果（严格兼容 CLI，无 envelope）
    return result


# ============================================================
# 端点 3: POST /api/v1/runestone
# ============================================================

@router.post("/runestone")
async def create_runestone(req: RunestoneRequest, request: Request, response: Response):
    """
    独立符石生成端点。

    不经过完整仿真流程，直接根据输入创建符石审计令牌。
    响应 body 等于 Runestone.to_dict() 的输出。
    """
    # 校验 reason 字段
    if "enterprise_id" not in req.reason or "rule_version" not in req.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="reason must contain 'enterprise_id' and 'rule_version' fields.",
        )

    # 校验 risk_vector (P1-3：校验失败返回 422，不裸 500)
    _validate_risk_vector(req.risk_vector)

    # 构建对象
    try:
        reason_field = ReasonField(
            enterprise_id=req.reason["enterprise_id"],
            rule_version=req.reason["rule_version"],
        )
        risk_vector = RiskVector(**req.risk_vector)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Failed to construct runestone components: {str(e)}",
        )

    # 生成确定性 runestone_id（如果 seed 提供）
    import numpy as np
    np.random.seed(req.seed)

    runestone_id = None
    if req.seed is not None:
        # 使用确定性 ID 生成
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

    # 确定性时间戳
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

    # v0.6: 持久化独立 runestone (decision_id 为 NULL)
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
    决策记录查询端点。

    v0.6: 从 SQLite 查询（替代 v0.5 内存字典）。服务重启后仍可查询。
    """
    app = request.app
    storage = getattr(app.state, "storage", None)

    result = None
    if storage:
        result = storage.get_decision(decision_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' not found.",
        )

    _set_metadata_headers(response, decision_id=decision_id)

    # 返回持久化的原始结果（与 /evaluate 响应一致）
    return result


# ============================================================
# 端点 5: GET /api/v1/audit/decisions — 决策审计列表 (v0.6 新增)
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
    v0.6 新增：分页查询决策列表。

    查询参数：
        limit: 每页条数 (1-100, 默认 20)
        offset: 偏移量 (默认 0)
        adapter: 按适配器筛选 (可选)
        since: UTC ISO 8601 起始时间 (可选)
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
# 端点 6: GET /api/v1/audit/runestones — 符石审计列表 (v0.6 新增)
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
    v0.6 新增：符石列表查询。

    查询参数：
        limit: 每页条数 (1-100, 默认 20)
        offset: 偏移量 (默认 0)
        since: UTC ISO 8601 起始时间 (可选)
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
# 端点 7: GET /api/v1/audit/runestones/{runestone_id} — 单个符石查询 (v0.6 新增)
# ============================================================

@router.get("/audit/runestones/{runestone_id}")
async def get_runestone(runestone_id: str, request: Request, response: Response):
    """
    v0.6 新增：按 runestone_id 直接查询符石。

    可查询 evaluate 自动生成的 runestone 和独立 POST /runestone 生成的 runestone。
    """
    _set_metadata_headers(response)

    storage = request.app.state.storage
    result = storage.get_runestone(runestone_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runestone '{runestone_id}' not found.",
        )

    return result


# ============================================================
# 端点 8: DELETE /api/v1/audit/decisions — 数据清理 (v0.6 新增, 带安全阀)
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
    v0.6 新增：数据清理端点（带安全阀）。

    安全阀规则：
    1. 必须传 confirm=true，否则 422
    2. 必须传 before=<UTC ISO> 或 all=true，否则 422
    3. bind_host 非 127.0.0.1/localhost 时返回 403
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
