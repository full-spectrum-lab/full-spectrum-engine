# Examples

This directory contains the smallest runnable examples for `full-spectrum-engine`.

All current examples are based on **synthetic or desensitized sample data**. They do not represent any confirmed real customer deployment, real user dataset, or real enterprise production system.

For the `v0.8.0-beta` public surface, every core example should satisfy three conditions:

1. it can be run directly;
2. it can be reproduced with `--seed`;
3. it can be compared against a committed golden sample.

---

## Example 1 — refund conflict

File:

```text
examples/scenario_refund_conflict.json
```

Run:

```bash
python simulate.py --config examples/scenario_refund_conflict.json
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
```

Use it to:

- simulate a conflict between user expectation, merchant rule, and platform handling logic;
- inspect the complete output chain: FSHI, ESS-lite, RiskVector, Runestone, and causal-chain report;
- demonstrate a bounded first public governance case.

---

## Example 2 — knowledge conflict

File:

```text
examples/scenario_knowledge_conflict.json
```

Run:

```bash
python simulate.py --config examples/scenario_knowledge_conflict.json
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42
```

Use it to:

- simulate conflicting answers between an AI assistant and enterprise knowledge sources;
- show how a knowledge-source mismatch becomes a visible governance risk;
- anchor later adapter work for platform rule, merchant rule, product knowledge, and order-state conflicts.

---

## Public beta golden samples

Current public beta preserves two fixed seeded outputs:

```text
test-records/v0.8-public-beta/golden_refund_seed42.json
test-records/v0.8-public-beta/golden_knowledge_seed42.json
```

Recommended validation command:

```bash
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1
```

---

## Example design rules

Public examples should:

- avoid real enterprise data;
- avoid real user private data;
- avoid implying confirmed production deployment;
- avoid presenting simulation output as a legal or compliance ruling;
- preserve the boundary that final review belongs to humans and organizations, not to the engine alone.

---

## Likely next example directions

- `scenario_customer_service_escalation.json`
- `scenario_multi_agent_permission_conflict.json`
- `scenario_cross_enterprise_audit.json`
- `scenario_cell_boundary.json`
- `scenario_logistics_customer_service.json`
- `scenario_ecommerce_product_knowledge.json`
