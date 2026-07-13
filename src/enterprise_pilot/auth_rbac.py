#!/usr/bin/env python3
"""
C-02 最小认证 + RBAC（仅 Operator / Service Principal）。

闭合决策（主理人封板）：
  * 认证仅用预共享操作员令牌（reference token）：标准库 ``secrets`` 生成、
    ``secrets.compare_digest`` 常量时间比较。属**引用校验**，**非密码学身份核验**
    （第一代只兼容不伪造 / 红线 #4）。
  * RBAC 只接受 ``OperatorPrincipal`` / ``ServicePrincipal``（系统操作者）。
    ``ObservedSubject``（src/subject/declaration.py 的 SubjectDeclaration）是分析上下文
    的浓度 Tier，**绝对不是**系统登录身份，不得传入 ``authenticate()``；
    以 SubjectDeclaration 充当凭证 → 显式拒绝（AC-06 / 红线 #1）。
  * 角色权限矩阵（最小集合，主理人闭合）：
        admin:    config:read, config:write, review:write, metrics:read, audit:read, deploy:read
        operator: config:read, review:write, metrics:read, audit:read
        auditor:  review:read, metrics:read, audit:read
        viewer:   metrics:read, audit:read
  * 无多租户（红线 #2）：认证基于主体与最小权限，不含 tenant 隔离 / 跨组织鉴权。
"""
import secrets

VALID_ROLES = ("admin", "operator", "auditor", "viewer")

# 角色 → 权限集合（主理人闭合决策，权威来源架构设计.md §9.2 / 待明确 #1）
ROLE_PERMISSIONS = {
    "admin": {"config:read", "config:write", "review:write", "metrics:read", "audit:read", "deploy:read"},
    "operator": {"config:read", "review:write", "metrics:read", "audit:read"},
    "auditor": {"review:read", "metrics:read", "audit:read"},
    "viewer": {"metrics:read", "audit:read"},
}

# 受 RBAC 闸门保护的所有 action（供文档/测试枚举）
PROTECTED_ACTIONS = (
    "config:read", "config:write", "review:read", "review:write",
    "metrics:read", "audit:read", "deploy:read",
)


class SubjectAsPrincipalError(Exception):
    """红线 #1：以 ObservedSubject（SubjectDeclaration）充当登录身份被显式拒绝。"""

    code = "SUBJECT_AS_PRINCIPAL"

    def __init__(self, message="ObservedSubject must not be used as an auth principal"):
        super().__init__(message)


class AuthenticationError(Exception):
    """令牌未知或格式非法（引用校验失败，非密码学身份核验）。"""

    code = "AUTHENTICATION_FAILED"

    def __init__(self, message="authentication failed"):
        super().__init__(message)


class AuthorizationError(Exception):
    """主体权限不足。"""

    code = "AUTHORIZATION_DENIED"

    def __init__(self, action, principal_id):
        super().__init__(f"principal '{principal_id}' not authorized for '{action}'")
        self.action = action
        self.principal_id = principal_id


def generate_token(nbytes=32):
    """生成预共享操作员令牌（reference token）。使用标准库 ``secrets``。"""
    return secrets.token_urlsafe(nbytes)


def _looks_like_subject(token):
    """粗判传入对象是否为 ObservedSubject / SubjectDeclaration（红线 #1）。"""
    if isinstance(token, dict):
        subject = token.get("subject")
        if isinstance(subject, dict) and "local_subject_id" in subject:
            return True
        if token.get("schema_version") == "sd-1.1":
            return True
    return False


class Role:
    """RBAC 角色：名称 + 权限集合。"""

    def __init__(self, name, permissions=None):
        if name not in VALID_ROLES:
            raise ValueError(f"unknown role {name!r}; valid={sorted(VALID_ROLES)}")
        self.name = name
        self.permissions = set(
            permissions if permissions is not None else ROLE_PERMISSIONS[name]
        )

    def to_dict(self):
        return {"name": self.name, "permissions": sorted(self.permissions)}


class Principal:
    """RBAC 主体基类（仅 Operator / Service 使用）。"""

    kind = "principal"

    def __init__(self, principal_id, roles):
        self.principal_id = principal_id
        self.roles = [r if isinstance(r, Role) else Role(r) for r in roles]
        if not self.roles:
            raise ValueError("principal must have at least one role")

    def permissions(self):
        perms = set()
        for role in self.roles:
            perms |= role.permissions
        return perms

    def role_names(self):
        return sorted({r.name for r in self.roles})

    def to_dict(self):
        return {
            "principal_id": self.principal_id,
            "kind": self.kind,
            "roles": self.role_names(),
            "permissions": sorted(self.permissions()),
        }


class OperatorPrincipal(Principal):
    kind = "operator"


class ServicePrincipal(Principal):
    kind = "service"


class TokenRegistry:
    """预共享令牌注册表：token -> {principal_id, kind, roles}。"""

    def __init__(self, mapping=None):
        self._entries = {}
        for token, info in (mapping or {}).items():
            self.register(token, info["principal_id"], info["kind"], info["roles"])

    def register(self, token, principal_id, kind, roles):
        if kind not in ("operator", "service"):
            raise ValueError(f"unsupported principal kind {kind!r}")
        self._entries[token] = {
            "principal_id": principal_id,
            "kind": kind,
            "roles": list(roles),
        }

    def lookup(self, token):
        return self._entries.get(token)


class RbacEngine:
    """最小认证 + RBAC 闸门（仅作用于 Operator / Service Principal）。"""

    def __init__(self, registry=None):
        self._registry = registry or TokenRegistry()

    @property
    def registry(self):
        return self._registry

    def authenticate(self, token):
        """认证预共享令牌，返回 OperatorPrincipal / ServicePrincipal。

        若传入的是 ObservedSubject / SubjectDeclaration → 显式拒绝（红线 #1 / AC-06）。
        """
        if _looks_like_subject(token):
            raise SubjectAsPrincipalError()
        if not isinstance(token, str):
            raise AuthenticationError("token must be a string reference token")
        entry = self._registry.lookup(token)
        if entry is None:
            raise AuthenticationError("unknown reference token")
        roles = entry["roles"]
        if entry["kind"] == "service":
            return ServicePrincipal(entry["principal_id"], roles)
        return OperatorPrincipal(entry["principal_id"], roles)

    def authorize(self, principal, action):
        if not isinstance(principal, Principal):
            raise SubjectAsPrincipalError()
        return action in principal.permissions()

    def require_role(self, principal, role):
        if not isinstance(principal, Principal):
            raise SubjectAsPrincipalError()
        if role not in principal.role_names():
            raise AuthorizationError(role, principal.principal_id)

    def gate(self, action):
        """返回一个校验函数 principal -> None / raise（供 REST 依赖注入风格使用）。"""

        def _check(principal):
            if not self.authorize(principal, action):
                raise AuthorizationError(action, getattr(principal, "principal_id", "?"))
            return principal

        return _check


def authenticate(token, registry=None):
    """门面函数（§4.2 签名）。"""
    return RbacEngine(registry).authenticate(token)


def authorize(principal, action, registry=None):
    """门面函数（§4.2 签名）。"""
    return RbacEngine(registry).authorize(principal, action)
