#!/usr/bin/env python3
"""
C-08 企业 Connector 契约（FR-08 / C-08）。

设计（闭合决策 #6 / 共享知识 §8.6 / 红线 #3 / #5）：
  * 四契约（复用 v1.4 既有输出作为推荐字段）：
        - report_export:         goe（v1.2 Output Envelope）
        - warning_event:         warning event（goe 的 warnings）
        - review_recommendation: ReviewRecord
        - audit_export:          audit export JSONL
  * ``write_enabled`` 默认 **False**（红线 #3）：``emit`` 仅返回契约载荷，
    **绝不写回业务系统**（红线 #5：第一代只兼容不伪造，引擎不执行业务）。
  * 企业自行 ``register_enterprise_impl`` 并承担授权与责任（默认不调用）。

零新增依赖；不触网、不执行业务、不做跨组织网络。
"""
CONTRACT_REPORT_EXPORT = "report_export"
CONTRACT_WARNING_EVENT = "warning_event"
CONTRACT_REVIEW_RECOMMENDATION = "review_recommendation"
CONTRACT_AUDIT_EXPORT = "audit_export"

CONTRACT_KINDS = (
    CONTRACT_REPORT_EXPORT,
    CONTRACT_WARNING_EVENT,
    CONTRACT_REVIEW_RECOMMENDATION,
    CONTRACT_AUDIT_EXPORT,
)


class ContractKind:
    """四契约常量（与 CONTRACT_KINDS 一致）。"""

    REPORT_EXPORT = CONTRACT_REPORT_EXPORT
    WARNING_EVENT = CONTRACT_WARNING_EVENT
    REVIEW_RECOMMENDATION = CONTRACT_REVIEW_RECOMMENDATION
    AUDIT_EXPORT = CONTRACT_AUDIT_EXPORT


class ConnectorContract:
    """连接器契约：仅声明输出契约 shape；业务写回默认 OFF。"""

    def __init__(self, name, write_enabled=False):
        self.name = name
        self.write_enabled = bool(write_enabled)  # 默认 False（红线 #3）
        self._enterprise_impl = None

    def register_enterprise_impl(self, fn):
        """企业注入写回实现（默认不调用；企业自行担责）。"""
        self._enterprise_impl = fn

    def emit(self, kind, payload):
        """返回契约载荷（四契约之一）。**绝不写回业务系统**。

        即便 ``write_enabled`` 为真，引擎自身也不写回；写回由企业注入的 impl
        在受控环境中执行（责任在企业侧）。
        """
        if kind not in CONTRACT_KINDS:
            raise ValueError(f"unknown contract kind {kind!r}; valid={CONTRACT_KINDS}")
        contract = self._shape(kind, payload)
        # 引擎侧绝不写回：仅在 write_enabled 且企业已注入 impl 时透传给企业 impl。
        if self.write_enabled and self._enterprise_impl is not None:
            try:
                self._enterprise_impl(kind, contract)
            except Exception:
                # 写回失败不影响契约载荷返回；由企业侧处理。
                pass
        return contract

    def _shape(self, kind, payload):
        if kind == CONTRACT_REPORT_EXPORT:
            return {"contract": kind, "name": self.name,
                    "write_enabled": self.write_enabled, "goe": payload}
        if kind == CONTRACT_WARNING_EVENT:
            return {"contract": kind, "name": self.name,
                    "write_enabled": self.write_enabled, "warnings": payload}
        if kind == CONTRACT_REVIEW_RECOMMENDATION:
            return {"contract": kind, "name": self.name,
                    "write_enabled": self.write_enabled, "review_record": payload}
        # audit_export
        return {"contract": kind, "name": self.name,
                "write_enabled": self.write_enabled, "audit_jsonl": payload}


def emit_contract(contract, kind, payload):
    """门面函数（§4.2 签名）：write_enabled 默认 False。"""
    return contract.emit(kind, payload)
