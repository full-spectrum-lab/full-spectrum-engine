#!/usr/bin/env python3
"""
Full Spectrum Engine API — 服务器工厂与启动入口 (v0.7.2-alpha)

设计原则：
    - create_app() 工厂函数，seed 在此处初始化（千问B：不在路由中改变全局状态）
    - CORSMiddleware 允许 localhost（千问C：OPTIONS 预检支持）
    - 全局 headers 中间件（P1-1：X-Storage-Mode / X-Full-Spectrum-Notice / X-Production-Ready）
    - 默认 127.0.0.1，0.0.0.0 时打印非生产警告（P2-2）
    - 启动日志含 NOT FOR PRODUCTION 警告
    - v0.6: SQLite 持久化层 (StorageBackend)，替代 v0.5 内存字典

启动方式：
    python -m src.api.server
    python -m src.api.server --host 127.0.0.1 --port 8000
    python -m src.api.server --host 0.0.0.0 --port 8000  # 会打印警告
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
    创建 FastAPI 应用实例。

    Args:
        seed: 全局随机种子，在应用创建时初始化（千问B：不在路由中改变全局状态）
        bind_host: 绑定地址，用于 health 端点报告网络暴露级别 + DELETE 安全阀判断
        db_path: SQLite 数据库路径 (v0.6 新增)
        ttl_days: TTL 天数，0 表示不自动清理 (v0.6 新增)
        max_records: decisions 表最大记录数 (v0.6 新增)

    Returns:
        FastAPI 应用实例
    """
    # 在应用创建时初始化随机数种子（千问B）
    import numpy as np
    np.random.seed(seed)

    app = FastAPI(
        title="Full Spectrum Engine API",
        description=(
            "本地 REST API — 将全频谱引擎从 CLI 脚本变为可被业务系统调用的 HTTP 服务。\n\n"
            "⚠️ NOT FOR PRODUCTION — 本地开发接口，不做认证、不做生产级部署。\n"
            "存储模式: sqlite-persistent（v0.6 SQLite 持久化）"
        ),
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 存储全局状态
    app.state.seed = seed
    app.state.bind_host = bind_host

    # v0.6: 初始化 SQLite 存储后端（替代 v0.5 内存字典）
    storage = StorageBackend(db_path=db_path, ttl_days=ttl_days, max_records=max_records)
    app.state.storage = storage

    # ============================================================
    # CORS 中间件（千问C：支持 OPTIONS 预检）
    # ============================================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============================================================
    # 全局 headers 中间件（P1-1：元信息走 headers）
    # v0.6: X-Storage-Mode 更新为 sqlite-persistent
    # ============================================================
    @app.middleware("http")
    async def add_metadata_headers(request: Request, call_next):
        response = await call_next(request)
        # 所有响应都携带这些元信息 headers
        response.headers["X-Storage-Mode"] = "sqlite-persistent"
        response.headers["X-Full-Spectrum-Notice"] = "local-dev-only"
        response.headers["X-Production-Ready"] = "false"
        return response

    # 注册路由
    app.include_router(router)

    # 根路径重定向到 docs
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
# Uvicorn 启动入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Full Spectrum Engine v0.7.2-alpha API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.api.server                           # 默认 127.0.0.1:8000
  python -m src.api.server --port 9000               # 自定义端口
  python -m src.api.server --host 0.0.0.0 --port 8000  # 暴露到外网（会打印警告）
  python -m src.api.server --db-path /tmp/fse.db --ttl-days 30

⚠️ NOT FOR PRODUCTION — 本地开发接口，不做认证。
        """,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="绑定地址（默认 127.0.0.1，使用 0.0.0.0 会打印非生产警告）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="绑定端口（默认 8000）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="全局随机种子（默认 42）",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开发模式热重载",
    )
    # v0.6 新增参数
    parser.add_argument(
        "--db-path",
        default="./data/fse.db",
        help="SQLite 数据库路径（默认 ./data/fse.db）",
    )
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=0,
        help="TTL 天数，0 表示不自动清理（默认 0）",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=10000,
        help="decisions 最大记录数（默认 10000）",
    )
    args = parser.parse_args()

    # P2-2：非本地绑定时打印警告
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

    # 启动日志 (v0.6 增强)
    print(
        f"\n"
        f"Full Spectrum Engine v0.7.2-alpha API Server\n"
        f"Running at http://{args.host}:{args.port}\n"
        f"Docs: http://{args.host}:{args.port}/docs\n"
        f"Database: {os.path.abspath(args.db_path)}\n"
        f"Max records: {args.max_records}\n"
        + (f"TTL: {args.ttl_days} days (cleanup on startup + post-save)\n" if args.ttl_days > 0 else "")
        + f"NOT FOR PRODUCTION\n"
        f"",
        file=sys.stderr,
    )

    # 创建应用
    app = create_app(
        seed=args.seed,
        bind_host=args.host,
        db_path=args.db_path,
        ttl_days=args.ttl_days,
        max_records=args.max_records,
    )

    # 启动 uvicorn
    import uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
