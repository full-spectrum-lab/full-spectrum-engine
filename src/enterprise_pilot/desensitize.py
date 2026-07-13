#!/usr/bin/env python3
"""
C-03 脱敏 / 字段最小化 / 留存（FR-03 / C-03）。

分类（闭合决策 #3 / 共享知识 §8.3）：
  * DIRECT（直接标识符：姓名 / 身份证 / 邮箱 / 手机号）
        → 哈希（不可逆）或令牌化（可逆，存映射 vault）
  * INDIRECT（间接标识符：IP / 设备号 / 地址）
        → 掩码（部分可逆 / 不可逆视策略）
  * BUSINESS（业务字段）
        → 默认不脱敏，按需最小化

脱敏前后字段映射（MappingRecord.before_after）``visible_to_authorized_only = true``；
非授权角色读取时被门禁剥离（红线 #6）。
"""
import hashlib

CATEGORY_DIRECT = "direct"
CATEGORY_INDIRECT = "indirect"
CATEGORY_BUSINESS = "business"

REVERSIBILITY_IRREVERSIBLE = "irreversible"  # 哈希
REVERSIBILITY_REVERSIBLE = "reversible"      # 令牌化（vault）
REVERSIBILITY_PARTIAL = "partial"            # 掩码（部分可逆/不可逆视策略）

# 默认字段分类（可被策略 field_categories 覆盖）
DEFAULT_FIELD_CATEGORY = {
    "name": CATEGORY_DIRECT, "id_card": CATEGORY_DIRECT, "email": CATEGORY_DIRECT,
    "phone": CATEGORY_DIRECT, "national_id": CATEGORY_DIRECT,
    "ip": CATEGORY_INDIRECT, "device_id": CATEGORY_INDIRECT, "address": CATEGORY_INDIRECT,
    "order_id": CATEGORY_BUSINESS, "amount": CATEGORY_BUSINESS, "sku": CATEGORY_BUSINESS,
}


class DesensitizeError(ValueError):
    code = "DESENSITIZE"


class MappingRecord:
    """脱敏前后字段映射。``visible_to_authorized_only = true``（红线 #6）。"""

    def __init__(self, before_after, reversibility=None):
        self.before_after = dict(before_after)
        self.visible_to_authorized_only = True  # 红线 #6
        self.reversibility = dict(reversibility or {})

    def to_dict(self):
        return {
            "before_to_author": True,  # 兼容字段名；语义同下
            "visible_to_authorized_only": self.visible_to_authorized_only,
            "before_after": self.before_after,
            "reversibility": self.reversibility,
        }

    def strip_for_unauthorized(self):
        """非授权角色读取时，剥离原始值（仅暴露字段数与可逆性，不泄露明文）。"""
        return {
            "visible_to_authorized_only": True,
            "field_count": len(self.before_after),
            "reversibility": self.reversibility,
        }


def classify(field_name, policy):
    """分类字段：先看策略显式定义，否则回退默认分类。"""
    explicit = (policy or {}).get("field_categories", {})
    if field_name in explicit:
        return explicit[field_name]
    return DEFAULT_FIELD_CATEGORY.get(field_name, CATEGORY_BUSINESS)


def mask(value, reversible=False, keep=2):
    """掩码：保留前 ``keep`` 位，其余以 ``*`` 替代。``reversible`` 仅声明策略。"""
    text = str(value)
    if len(text) <= keep:
        return "*" * len(text)
    return text[:keep] + "*" * (len(text) - keep)


def hash_value(value, salt=""):
    """哈希（不可逆）：SHA-256(salt + value)。"""
    digest = hashlib.sha256(f"{salt}|{value}".encode("utf-8")).hexdigest()
    return "h_" + digest[:32]


def tokenize(value, vault):
    """令牌化（可逆）：value -> token，映射存于 vault（dict）。"""
    text = str(value)
    if text not in vault:
        token = "tok_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        vault[text] = token
        vault["__rev__:" + token] = text
    return vault[text]


def detokenize(token, vault):
    """令牌还原（可逆性证明；仅授权角色可用）。"""
    return vault.get("__rev__:" + token)


class Desensitizer:
    """脱敏执行器（策略对象）。"""

    def __init__(self, salt="", vault=None):
        self.salt = salt
        self.vault = vault if vault is not None else {}

    def apply_policy(self, record, policy):
        """对 ``record`` 应用脱敏策略，返回 (脱敏后记录, MappingRecord)。

        policy: {field_categories, methods, reversible, minimize}
          methods: {direct: hash|tokenize, indirect: mask, business: none|minimize}
        """
        policy = policy or {}
        methods = policy.get("methods", {})
        reversible = policy.get("reversible", {})
        minimize = policy.get("minimize", False)

        out = {}
        mapping = {}
        rev = {}
        for field, value in record.items():
            category = classify(field, policy)
            if category == CATEGORY_DIRECT:
                method = methods.get("direct", "hash")
                if method == "tokenize":
                    out[field] = tokenize(value, self.vault)
                    mapping[field] = {"from": value, "to": out[field], "method": "tokenize"}
                    rev[field] = REVERSIBILITY_REVERSIBLE
                else:  # hash（默认，不可逆）
                    out[field] = hash_value(value, self.salt)
                    mapping[field] = {"from": value, "to": out[field], "method": "hash"}
                    rev[field] = REVERSIBILITY_IRREVERSIBLE
            elif category == CATEGORY_INDIRECT:
                out[field] = mask(
                    value,
                    reversible=(methods.get("indirect", "mask") == "mask"
                                and reversible.get("indirect", False)),
                )
                mapping[field] = {"from": value, "to": out[field], "method": "mask"}
                rev[field] = REVERSIBILITY_PARTIAL if reversible.get("indirect", False) else REVERSIBILITY_IRREVERSIBLE
            else:  # business
                if minimize:
                    out[field] = "__MINIMIZED__"  # 仅当策略要求最小化时占位
                else:
                    out[field] = value

        return out, MappingRecord(mapping, rev)


def apply_desensitization(record, policy, salt="", vault=None):
    """门面函数（§4.2 签名）：返回 (dict, MappingRecord)。"""
    desensitizer = Desensitizer(salt=salt, vault=vault)
    return desensitizer.apply_policy(record, policy)
