# Knowledge_conflict Governance Chain Report

> Example only. This report uses mock synthetic data and does not represent production validation.

## Summary

- Raw input: `raw_knowledge_001`
- Scenario: enterprise_knowledge
- Detected issue: KNOWLEDGE_SOURCE_CONFLICT
- Risk level: high
- Recommended action: human_review_required
- Related GovernanceEvent: `ge_knowledge_knowledge_001`
- Related EnterpriseWriteback: `audit_knowledge_001`

## Finding

The adapter recorded `KNOWLEDGE_SOURCE_CONFLICT`. The configured governance policy requires human review and prevents the observer from treating the recommendation as an enterprise action.

## Protocol mapping

| Chain step | Full Spectrum object |
| --- | --- |
| Business raw input | `raw-input.knowledge_conflict.json` |
| Adapter mapping | I/O Contract (Knowledge_conflictAdapter) |
| Governance Event | `governance-event.knowledge_conflict.json` |
| Canonical Context | `canonical-context.knowledge_conflict.json` |
| Subject declaration | `cell-manifest.knowledge_conflict.json` (L1 Cell Protocol) |
| Engine output | `output-envelope.knowledge_conflict.json` |
| Enterprise decision | `enterprise-writeback.knowledge_conflict.json` |
| Audit reference | `audit_knowledge_001` |

## Decision

The observer did not execute an enterprise action. It returned an Enterprise Writeback that:

- blocks auto-reply and auto-execution;
- blocks the commitment;
- routes the case to `knowledge_conflict_review` for human review by `knowledge_governance_owner`.

## Boundary

The protocol does not execute the enterprise action. It records a reviewable recommendation and hands off to the enterprise's own system.
