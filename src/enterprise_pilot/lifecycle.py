#!/usr/bin/env python3
"""
C-07 本地部署 / 备份 / 回滚（FR-07 / C-07）。

设计（共享知识 §8 衍生）：
  * BackupManager：本地文件/库拷贝式备份与恢复（受控、可演练）。
  * Rollback：基于「操作前快照 → 备份」的回滚计划与执行，保证数据连续。
标准库实现（shutil），无新第三方依赖。不触网、不执行业务。
"""
import os
import shutil


class LifecycleError(Exception):
    code = "LIFECYCLE"


class BackupManager:
    """本地备份 / 恢复（文件拷贝语义）。"""

    def backup(self, target, path):
        if not os.path.exists(target):
            raise LifecycleError(f"backup target not found: {target}")
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy(target, path)
        return path

    def restore(self, path, target):
        if not os.path.exists(path):
            raise LifecycleError(f"backup not found: {path}")
        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy(path, target)
        return True


class Rollback:
    """回滚计划与执行。"""

    def plan(self, current, backup):
        return {
            "action": "rollback",
            "current": current,
            "backup": backup,
            "will_restore_from": backup,
        }

    def execute(self, plan):
        manager = BackupManager()
        manager.restore(plan["backup"], plan["current"])
        return True


def backup(target, path):
    """门面函数（§4.2 签名）。"""
    return BackupManager().backup(target, path)


def restore(path, target):
    """门面函数（§4.2 签名）。"""
    return BackupManager().restore(path, target)
