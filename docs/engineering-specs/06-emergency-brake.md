# Emergency Brake historical design note

创建时间：2026-07-10 09:02（北京时间，UTC+8；依据 Git 首次提交）
最后更新时间：2026-08-01 12:18（北京时间，UTC+8）

```text
DOCUMENT_STATUS = HISTORICAL DESIGN NOTE
NORMATIVE = NO
CURRENT_RUNTIME_SPECIFICATION = NO
REAL_WORLD_EXECUTION_AUTHORITY = NONE
CODE_REFERENCE = PRESENT_IN_LEGACY_SIMULATION_PATH
```

## Historical ordering

The original five-line design order is preserved below as historical evidence:

1. PIBB (Physical Security Trigger) ← 最高，不可覆盖
2. 悲悯协议 (PainScore > 0.9)
3. ESS 伦理模拟
4. 守庙人网络
5. 节点自主决策 ← 最低

## Current interpretation boundary

`simulate.py` currently instantiates `src.safety.emergency.EmergencyBrakeEngine`, and the legacy simulation module includes automatic threshold triggers for FSHI, survival, conflict density, PainScore and consecutive awareness-bomb events.

The current implementation changes only in-process simulation state and records an in-memory shutdown snapshot/log. It does **not** stop an operating-system service, control PLC/MES/QMS equipment, write to a production system, authorize punishment, or perform another real-world action.

The thresholds and labels above are experimental simulation constructs. They are not proof of compassion, civilization survival, free will, production safety or authority. Any future real-system circuit-break specification requires a separate versioned contract covering threat model, input Schema, Evidence threshold, proportionality, least intervention, reversibility, expiry, independent review, responsible principal, Action Receipt, Replay and failure modes.

Until such a specification is approved, this file must not be cited as a normative runtime or production-control requirement.
