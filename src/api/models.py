#!/usr/bin/env python3
"""
Full Spectrum Engine API — Pydantic 请求/响应模型

设计原则：
    - 请求字段使用 irreversibility（P0-2 修复，与 v0.4 对齐）
    - include_input_metrics 默认 false（P1-5 隐私最小化）
    - 可变默认值使用 Field(default_factory=...)（P1-3 防 bare 500）
    - 响应 body 严格兼容 CLI 输出，不加 envelope（P1-1）
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ============================================================
# 请求模型
# ============================================================

class EvaluateRequest(BaseModel):
    """
    POST /api/v1/evaluate 请求体

    支持两种模式：
    1. 直接模式（direct）：传入完整 scenario dict，等价于 simulate.py --config
    2. 适配器模式（adapter）：传入 industry + metrics，由 MetricAdapter 自动构建 scenario

    两种模式都必须且只能选一种。
    """
    # 直接模式：完整 scenario dict（与 simulate.py 的 JSON 格式一致）
    scenario: Optional[Dict[str, Any]] = Field(
        default=None,
        description="直接模式：完整场景配置，与 simulate.py --config 的 JSON 格式一致"
    )
    # 适配器模式
    industry: Optional[str] = Field(
        default=None,
        description="适配器模式：行业标识，如 'ecommerce_customer_service'"
    )
    metrics: Optional[Dict[str, float]] = Field(
        default=None,
        description="适配器模式：业务指标字典，键为指标名，值为 [0,1] 归一化值"
    )

    # 公共参数
    seed: int = Field(
        default=42,
        description="随机种子，用于确定性仿真。默认 42"
    )
    include_input_metrics: bool = Field(
        default=False,
        description="是否在响应中包含原始业务指标（隐私最小化：默认 false）"
    )

    # 适配器模式可选参数
    simulation_id: Optional[str] = Field(
        default=None,
        description="适配器模式：仿真 ID（直接模式从 scenario 中读取）"
    )
    input_query: Optional[str] = Field(
        default=None,
        description="适配器模式：场景描述"
    )
    sensitivity_level: str = Field(
        default="medium",
        description="适配器模式：敏感度等级 (low/medium/high)"
    )
    enterprise_id: str = Field(
        default="default",
        description="适配器模式：企业 ID"
    )
    rule_version: str = Field(
        default="v0.3",
        description="适配器模式：规则版本"
    )


class RunestoneRequest(BaseModel):
    """
    POST /api/v1/runestone 请求体

    独立生成符石审计令牌，不经过完整仿真流程。
    """
    decision: str = Field(
        ...,
        description="决策选项，如 'W3'"
    )
    reason: Dict[str, str] = Field(
        ...,
        description="审计原因，包含 enterprise_id 和 rule_version"
    )
    risk_vector: Dict[str, float] = Field(
        ...,
        description="八维风险向量，必须包含 survival_impact/trust_impact/meaning_impact/reversibility/explainability/diffusivity/urgency/uncertainty"
    )
    parent_runestone: Optional[str] = Field(
        default=None,
        description="父符石 ID（用于链式审计）"
    )
    agent_trail: List[str] = Field(
        default_factory=list,
        description="参与 Agent 列表"
    )
    ess_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="ESS 快照数据"
    )
    seed: int = Field(
        default=42,
        description="随机种子（影响 runestone_id 生成）"
    )


# ============================================================
# 响应模型（仅用于 /health，其他端点返回原始 dict）
# ============================================================

class HealthResponse(BaseModel):
    """
    GET /api/v1/health 响应体

    health 是唯一有自定义响应结构的端点。
    其他端点的响应 body 严格兼容 CLI 输出。

    v0.6: storage_mode 默认值更新为 sqlite-persistent。
    v0.6: 新增 db_path/db_size_bytes/decision_count/runestone_count/ttl_days/max_records (可选字段)。
    """
    status: str = Field(description="服务状态: 'ok'")
    version: str = Field(description="API 版本号")
    engine_version: str = Field(description="引擎版本号")
    registered_adapters: List[str] = Field(
        description="已注册的适配器行业标识列表"
    )
    storage_mode: str = Field(
        default="sqlite-persistent",
        description="存储模式: 'sqlite-persistent' (v0.6 SQLite 持久化)"
    )
    network_exposure: str = Field(
        default="local",
        description="网络暴露级别: 'local' (127.0.0.1) 或 'non-local' (0.0.0.0)"
    )
    # v0.6 新增字段 (可选，向后兼容)
    db_path: Optional[str] = Field(default=None, description="SQLite 数据库绝对路径")
    db_size_bytes: Optional[int] = Field(default=None, description="数据库文件大小 (bytes)")
    decision_count: Optional[int] = Field(default=None, description="决策记录总数")
    runestone_count: Optional[int] = Field(default=None, description="符石记录总数")
    ttl_days: Optional[int] = Field(default=None, description="TTL 天数 (0=不自动清理)")
    max_records: Optional[int] = Field(default=None, description="decisions 最大记录数")


# ============================================================
# v0.6 新增：审计列表查询模型
# ============================================================

class DecisionListItem(BaseModel):
    """决策列表项（不含完整结果）"""
    decision_id: str
    simulation_id: Optional[str] = None
    runestone_id: Optional[str] = None
    created_at: str
    adapter: Optional[str] = None
    seed: Optional[int] = None


class DecisionListResponse(BaseModel):
    """决策列表响应"""
    items: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class RunestoneListItem(BaseModel):
    """符石列表项"""
    runestone_id: str
    decision_id: Optional[str] = None  # 独立 runestone 时为 None
    created_at: str
    parent_runestone: Optional[str] = None


class RunestoneListResponse(BaseModel):
    """符石列表响应"""
    items: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class DeleteDataResponse(BaseModel):
    """数据清理响应"""
    deleted_decisions: int
    deleted_runestones: int
