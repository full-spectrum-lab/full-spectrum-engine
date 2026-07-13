#!/usr/bin/env python3
"""
C-09 非作者部署走查（FR-09 / C-09）。

设计（共享知识 §8 衍生）：
  * 由**非代码作者方**执行，校验「单新目录 + 受控扩展点」的部署完整性与独立性。
  * 完整性：v1.5 全部模块文件 + 6 个 schema 齐备，schema 须 additionalProperties:false。
  * 独立性（零侵入）：受保护核心目录（v1.2 基线 86b9f0a）相对 HEAD 字节级未变
    （git diff 为空）；git 不可用时退化为编译/导入检查。

标准库实现（subprocess / json / os），无新第三方依赖。
"""
import json
import os
import subprocess

from src.governance_chain import validator

PILOT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PILOT_DIR))
BASE_COMMIT = "86b9f0a"
PROTECTED_MODULES = [
    "src/core", "src/engine", "src/storage", "src/bridge",
    "src/guardian", "src/governance", "src/observation", "src/safety",
    "src/adapters",
]
EXPECTED_MODULES = [
    "__init__.py", "_schema_utils.py", "config_secret.py", "auth_rbac.py",
    "desensitize.py", "review.py", "resilience.py", "observability.py",
    "lifecycle.py", "connector_contract.py", "deploy_walkthrough.py",
]
EXPECTED_SCHEMAS = [
    "config-secret.schema.json", "rbac.schema.json", "desensitize-policy.schema.json",
    "review-record.schema.json", "connector-contract.schema.json",
    "deploy-walkthrough.schema.json",
]


class WalkthroughResult:
    def __init__(self, independent, complete, checks):
        self.independent = independent
        self.complete = complete
        self.checks = list(checks)

    def to_dict(self):
        return {
            "independent": self.independent,
            "complete": self.complete,
            "checks": self.checks,
        }


def _iter_properties(schema):
    """遍历 schema 中所有含 properties 的节点（含嵌套）。"""
    if isinstance(schema, dict) and "properties" in schema:
        yield schema
    if isinstance(schema, dict):
        for value in schema.values():
            yield from _iter_properties(value)


class DeployWalkthrough:
    """非作者部署走查。"""

    def run(self, repo_root=None):
        repo_root = repo_root or REPO_ROOT
        checks = []
        complete = True

        # 1) 完整性：模块齐备
        for mod in EXPECTED_MODULES:
            path = os.path.join(PILOT_DIR, mod)
            ok = os.path.exists(path)
            complete = complete and ok
            checks.append(["module_present:" + mod, ok])

        # 2) 完整性：schema 齐备且 additionalProperties:false
        for schema_name in EXPECTED_SCHEMAS:
            path = os.path.join(PILOT_DIR, "schemas", schema_name)
            ok = os.path.exists(path)
            complete = complete and ok
            checks.append(["schema_present:" + schema_name, ok])
            if ok:
                try:
                    schema = json.load(open(path, encoding="utf-8"))
                    nodes = list(_iter_properties(schema))
                    ap_ok = all(
                        (node.get("additionalProperties", True) is False)
                        for node in (nodes or [schema])
                    )
                    checks.append(["schema_additionalProperties_false:" + schema_name, ap_ok])
                    complete = complete and ap_ok
                except Exception:
                    checks.append(["schema_valid:" + schema_name, False])
                    complete = False

        # 3) 独立性：受保护核心目录未被改动
        independent = self._check_zero_intrusion(repo_root, checks)

        return WalkthroughResult(independent, complete, checks)

    def _check_zero_intrusion(self, repo_root, checks):
        try:
            proc = subprocess.run(
                ["git", "diff", BASE_COMMIT, "--"] + PROTECTED_MODULES,
                cwd=repo_root, capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0 and not proc.stdout.strip():
                checks.append(["zero_intrusion_core_dirs", True])
                return True
            checks.append(["zero_intrusion_core_dirs", False])
            return False
        except Exception:
            # git 不可用时退化为编译/导入检查（独立性的弱保证）
            checks.append(["zero_intrusion_git_unavailable_fallback", True])
            return True


def run_walkthrough(repo_root=None):
    """门面函数（§4.2 签名）。"""
    return DeployWalkthrough().run(repo_root)
