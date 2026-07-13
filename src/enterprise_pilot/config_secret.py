#!/usr/bin/env python3
"""
C-01 配置与秘密分离（FR-01 / C-01）。

设计（闭合决策 #2 / 共享知识 §8.2）：
  * 配置文件只存**引用**，例如 ``db_password: ${secret:db_password}`` 或
    ``db_password: ${env:DB_PASSWORD}``；真实凭证**不进配置仓库**。
  * 默认后端 ``env``；可选 ``secret-file``（独立文件，权限 600，不入库、应被 .gitignore）。
  * 加载时 ``resolve_secret(ref)`` 按引用解析；secret 文件权限受控、不纳入版本库。

零新增第三方依赖：标准库 json / os / re / secrets。
"""
import json
import os
import re
import secrets

SECRET_REF_RE = re.compile(r"^\$\{(?P<backend>secret|env):(?P<name>[\w.\-]+)\}$")


class ConfigSecretError(ValueError):
    """配置 / 秘密解析错误。"""

    code = "CONFIG_SECRET"


def split_config_secrets(doc):
    """将配置文档拆分为 (config, secret_refs)。

    ``config`` 原样返回（引用字符串保留）；``secret_refs`` 是文档内所有
    ``${secret|env:name}`` 引用的有序去重集合。调用方据此确认凭证未内联进仓库。
    """
    refs = set()

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                if isinstance(value, str) and SECRET_REF_RE.match(value):
                    refs.add(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    return doc, sorted(refs)


class ConfigSecretManager:
    """配置与凭证分离存储、按引用解析。"""

    def __init__(self, config_path=None, secret_backend="env", secret_file=None):
        self.config_path = config_path
        self.secret_backend = secret_backend  # "env" | "secret-file"
        self.secret_file = secret_file
        self._file_cache = None

    @staticmethod
    def load_config(path):
        """从路径加载配置文件（引用字符串保留）。"""
        with open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)

    def resolve_secret(self, ref):
        """按引用解析秘密：``${env:NAME}`` 读环境变量；``${secret:NAME}`` 读 secret-file。"""
        if not isinstance(ref, str):
            raise ConfigSecretError(f"secret reference must be a string, got {type(ref)!r}")
        match = SECRET_REF_RE.match(ref)
        if not match:
            raise ConfigSecretError(f"not a secret reference: {ref!r}")
        backend = match.group("backend")
        name = match.group("name")
        if backend == "env":
            if name not in os.environ:
                raise ConfigSecretError(f"env secret '{name}' is not set")
            return os.environ[name]
        # secret-file 后端
        if self.secret_backend != "secret-file":
            raise ConfigSecretError(
                f"secret backend '{self.secret_backend}' cannot resolve secret-file ref '{ref}'"
            )
        data = self._load_secret_file()
        if name not in data:
            raise ConfigSecretError(f"secret-file is missing key '{name}'")
        return data[name]

    def _load_secret_file(self):
        if self._file_cache is not None:
            return self._file_cache
        if not self.secret_file or not os.path.exists(self.secret_file):
            raise ConfigSecretError(f"secret-file not found: {self.secret_file}")
        with open(self.secret_file, encoding="utf-8") as handle:
            self._file_cache = json.load(handle)
        return self._file_cache

    def load_resolved(self, path=None):
        """加载配置并把其中的引用就地解析为真实值（凭证仅在内存中，不落配置仓库）。"""
        path = path or self.config_path
        doc = self.load_config(path)

        def walk(node):
            if isinstance(node, dict):
                return {k: walk(v) for k, v in node.items()}
            if isinstance(node, list):
                return [walk(v) for v in node]
            if isinstance(node, str):
                if SECRET_REF_RE.match(node):
                    return self.resolve_secret(node)
                return node
            return node

        return walk(doc)


def resolve_secret_ref(manager, ref):
    """门面函数（§4.2 签名）：按引用解析秘密。"""
    return manager.resolve_secret(ref)


def write_secret_file(path, data):
    """写入 secret-file（权限 600，不入库）。Windows 上 chmod 可能失败，静默忽略。"""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def generate_secret_value(nbytes=24):
    """生成一个随机秘密值（用于 secret-file 填充；属引用校验用途）。"""
    return secrets.token_urlsafe(nbytes)
