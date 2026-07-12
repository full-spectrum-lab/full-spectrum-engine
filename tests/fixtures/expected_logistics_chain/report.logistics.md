# Logistics Governance Chain Report

> Example only. This report uses mock synthetic data and does not represent production validation.

## Summary

- Raw input: `raw_logistics_001`
- Scenario: logistics_cold_chain
- Detected issue: LOGISTICS_EVIDENCE_INCOMPLETE
- Risk level: high
- Recommended action: human_review_required
- Related GovernanceEvent: `ge_logistics_coldchain_001`
- Related EnterpriseWriteback: `audit_logistics_001`

## Finding

The adapter recorded `LOGISTICS_EVIDENCE_INCOMPLETE`. The configured governance policy requires human review and prevents the observer from treating the recommendation as an enterprise action.

## Protocol mapping

| Chain step | Full Spectrum object |
| --- | --- |
| Business raw input | `raw-input.logistics.json` |
| Adapter mapping | I/O Contract (LogisticsAdapter) |
| Governance Event | `governance-event.logistics.json` |
| Canonical Context | `canonical-context.logistics.json` |
| Subject declaration | `cell-manifest.logistics.json` (L1 Cell Protocol) |
| Engine output | `output-envelope.logistics.json` |
| Enterprise decision | `enterprise-writeback.logistics.json` |
| Audit reference | `audit_logistics_001` |

## Decision

The observer did not execute an enterprise action. It returned an Enterprise Writeback that:

- blocks auto-reply and auto-execution;
- blocks the commitment;
- routes the case to `cold_chain_review` for human review by `logistics_quality_supervisor`.

## Boundary

The protocol does not execute the enterprise action. It records a reviewable recommendation and hands off to the enterprise's own system.
