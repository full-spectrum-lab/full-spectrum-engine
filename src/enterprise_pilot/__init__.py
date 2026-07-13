#!/usr/bin/env python3
"""
full-spectrum-engine v1.5「企业试点候选」— 受控、脱敏企业试点模块（加法式、零侵入）。

本包全部为 v1.5 新建增量模块；不修改 v1.2 / v1.3 / v1.4 任何核心模块。
设计铁律（详见架构设计.md §8 / §10）：
  * 身份严格分离（C-02 / NFR-05 / 红线 #1）：RBAC 仅作用于 Operator / Service Principal；
    ObservedSubject（src/subject/declaration.py 的 SubjectDeclaration）绝不作为登录身份。
  * 第一代只兼容不伪造（红线 #4）：external_effect 恒 false；不签发/验证密码学身份；
    不产生跨组织授权；Connector 写回默认 OFF（红线 #3 / #5）。
  * 无多租户（红线 #2）：按主体 + 最小权限，不含 tenant 隔离。
  * 脱敏映射 visible_to_authorized_only（红线 #6）；ReviewStore 仅 append（红线 #7）；
    ReviewRecord.original_event_ref 真实可解析（红线 #8）；纵向递归不平均（红线 #9）。
"""
from .config_secret import (
    ConfigSecretManager,
    split_config_secrets,
    resolve_secret_ref,
    write_secret_file,
)
from .auth_rbac import (
    RbacEngine,
    TokenRegistry,
    OperatorPrincipal,
    ServicePrincipal,
    Role,
    authenticate,
    authorize,
    generate_token,
    SubjectAsPrincipalError,
    AuthorizationError,
    AuthenticationError,
    ROLE_PERMISSIONS,
)
from .desensitize import (
    Desensitizer,
    MappingRecord,
    apply_desensitization,
    classify,
    mask,
    hash_value,
    tokenize,
)
from .review import (
    ReviewRecord,
    ReviewStore,
    ReviewBindingError,
    record_review,
    verify_review_bindings,
)
from .resilience import (
    IdempotencyKey,
    RetryPolicy,
    Timeout,
    TimeoutErrorR,
    with_retry,
    with_timeout,
    run_resilient,
)
from .observability import (
    StructuredLogger,
    HealthCheck,
    Metrics,
    health,
    metrics_snapshot,
)
from .lifecycle import (
    BackupManager,
    Rollback,
    backup,
    restore,
)
from .connector_contract import (
    ConnectorContract,
    ContractKind,
    CONTRACT_KINDS,
    emit_contract,
)
from .deploy_walkthrough import (
    DeployWalkthrough,
    WalkthroughResult,
    run_walkthrough,
)
from ._schema_utils import (
    load_pilot_schema,
    validate_pilot,
)

__version__ = "1.5.0"

__all__ = [
    "ConfigSecretManager", "split_config_secrets", "resolve_secret_ref",
    "write_secret_file",
    "RbacEngine", "TokenRegistry", "OperatorPrincipal", "ServicePrincipal", "Role",
    "authenticate", "authorize", "generate_token",
    "SubjectAsPrincipalError", "AuthorizationError", "AuthenticationError",
    "ROLE_PERMISSIONS",
    "Desensitizer", "MappingRecord", "apply_desensitization", "classify",
    "mask", "hash_value", "tokenize",
    "ReviewRecord", "ReviewStore", "ReviewBindingError", "record_review", "verify_review_bindings",
    "IdempotencyKey", "RetryPolicy", "Timeout", "TimeoutErrorR", "with_retry", "with_timeout",
    "run_resilient",
    "StructuredLogger", "HealthCheck", "Metrics", "health", "metrics_snapshot",
    "BackupManager", "Rollback", "backup", "restore",
    "ConnectorContract", "ContractKind", "emit_contract",
    "CONTRACT_KINDS",
    "DeployWalkthrough", "WalkthroughResult", "run_walkthrough",
    "load_pilot_schema", "validate_pilot",
    "__version__",
]
