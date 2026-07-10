"""
Full Spectrum Engine — REST API Package (v0.7.2-alpha)

本地优先 API 层：在核心引擎之上提供 HTTP 调用、行业适配器评估、
SQLite 审计持久化与查询能力，不修改引擎核心。

端点：
    GET  /api/v1/health              — 健康检查
    POST /api/v1/evaluate            — 仿真评估
    POST /api/v1/runestone           — 符石生成
    GET  /api/v1/decisions/{id}      — 决策记录查询
    GET  /api/v1/audit/decisions     — 决策审计列表
    GET  /api/v1/audit/runestones    — 符石审计列表

约束：
    - 本地优先 (默认 127.0.0.1)
    - SQLite 本地持久化
    - API body 严格兼容 CLI 输出
    - 元信息走 HTTP headers
    - 不做认证 / SaaS / 协议网络 / 企业最终执行
"""

__version__ = "0.7.2a1"
