# Examples

This directory contains minimum runnable examples for `full-spectrum-engine`.

All public examples are synthetic or desensitized. They do not represent real enterprises, real users, or real production systems.

## Current examples

### 1. Refund conflict scenario

File:

```text
examples/scenario_refund_conflict.json
```

Run:

```bash
python simulate.py --config examples/scenario_refund_conflict.json
```

### 2. Knowledge conflict scenario

File:

```text
examples/scenario_knowledge_conflict.json
```

Run:

```bash
python simulate.py --config examples/scenario_knowledge_conflict.json
```

### 3. Adapter-driven e-commerce metrics

Run:

```bash
python examples/run_ecommerce_adapter.py --metrics examples/metrics_ecommerce_conflict.json --seed 42
```

## Example design principles

All public examples should:

1. avoid real enterprise data;
2. avoid real personal data;
3. avoid implying already-deployed commercial customers;
4. avoid presenting simulation output as legal or compliance rulings;
5. preserve the boundary of final human or enterprise review.
