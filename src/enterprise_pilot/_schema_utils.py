#!/usr/bin/env python3
"""
v1.5 内部工具：从本包自带的 schemas/ 目录加载并校验 JSON Schema。

复用 v1.4 的 ``src.governance_chain.validator``（jsonschema 优先、否则内置轻量校验），
不修改它；仅让 v1.5 的新 schema 可被独立加载与校验。
所有 v1.5 schema 均 ``additionalProperties:false``（红线衍生 / 共享知识 §8.8）。
"""
import json
import os

from src.governance_chain import validator

_SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")


def load_pilot_schema(name):
    """加载 ``schemas/<name>`` 并返回 dict。"""
    with open(os.path.join(_SCHEMA_DIR, name), encoding="utf-8-sig") as handle:
        return json.load(handle)


def validate_pilot(instance, schema_name):
    """用 ``schemas/<schema_name>`` 校验 ``instance``，返回 (ok, errors)。"""
    schema = load_pilot_schema(schema_name)
    return validator.validate_instance(instance, schema)
