# Ecommerce Governance Chain Report

> Example only. This report uses mock synthetic data and does not represent production validation.

## Summary

- Raw input: `raw_ecom_001`
- Observed subject: `none` (none)
- Scenario: ecommerce_customer_service
- Detected issue: REFUND_COMMITMENT_WITHOUT_AUTHORITY
- Risk level: high
- Recommended action: human_review_required
- Related GovernanceEvent: `ge_ecom_refund_001`
- Related EnterpriseWriteback: `audit_ecom_001`

## Finding

The observed AI response was:

> 可以给您全额退款。

The adapter recorded `REFUND_COMMITMENT_WITHOUT_AUTHORITY`. The configured governance policy requires human review and prevents the observer from treating the recommendation as an enterprise action.

## Protocol mapping

| Chain step | Full Spectrum object |
| --- | --- |
| Business raw input | `raw-input.ecommerce.json` |
| Adapter mapping | I/O Contract (EcommerceAdapter) |
| Governance Event | `governance-event.ecommerce.json` |
| Canonical Context | `canonical-context.ecommerce.json` |
| Subject declaration | `cell-manifest.ecommerce.json` (L1 Cell Protocol) |
| Engine output | `output-envelope.ecommerce.json` |
| Enterprise decision | `enterprise-writeback.ecommerce.json` |
| Audit reference | `audit_ecom_001` |

## Decision

The observer did not execute an enterprise action. It returned an Enterprise Writeback that:

- blocks auto-reply and auto-execution;
- blocks the commitment;
- routes the case to `after_sales_review` for human review by `customer_service_supervisor`.

## Boundary

The protocol does not execute the enterprise action. It records a reviewable recommendation and hands off to the enterprise's own system.
