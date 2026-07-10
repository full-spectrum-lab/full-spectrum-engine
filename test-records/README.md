# Test Records

This directory stores reproducibility and verification traces for `full-spectrum-engine`.

It is not the main test framework itself. Instead, it preserves selected outputs that help humans and future automation compare behavior across versions.

---

## Current record sets

```text
test-records/2026-07-04-v0.3-candidate/
test-records/v0.8-public-beta/
```

These records include:

- compile checks
- unit-test outputs
- experiment outputs
- CLI sample outputs
- seeded golden samples

The current public beta golden files are:

```text
golden_refund_seed42.json
golden_knowledge_seed42.json
```

They are generated with `--seed 42` and are used to verify that later versions do not silently break the main public output structure.

---

## Why keep these files

The project needs more than “it runs”.

It also needs a visible trace of:

- how it was run
- what it produced
- which version was checked
- what later versions changed

These files help with:

- AI handoff
- human review
- version rollback checks
- release-note preparation
- stable comparison between release lines

---

## How to regenerate

```bash
python -m compileall .
python -m unittest tests.test_bomb -v
python experiments/experiment_A_baseline.py
python experiments/experiment_B_ess.py
python experiments/experiment_C_l0_ess.py
python experiments/experiment_D_guardian_short.py
python experiments/experiment_E_guardian_long.py
python experiments/experiment_F_frequency.py
python experiments/experiment_G_threshold.py
python experiments/experiment_H_stress.py
python simulate.py --config examples/scenario_refund_conflict.json --output test-records/2026-07-04-v0.3-candidate/simulate_refund_conflict.json
python simulate.py --config examples/scenario_knowledge_conflict.json --output test-records/2026-07-04-v0.3-candidate/simulate_knowledge_conflict.json
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --output test-records/2026-07-04-v0.3-candidate/golden_refund_seed42.json
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42 --output test-records/2026-07-04-v0.3-candidate/golden_knowledge_seed42.json

# v0.8 public beta
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --output test-records/v0.8-public-beta/golden_refund_seed42.json
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42 --output test-records/v0.8-public-beta/golden_knowledge_seed42.json
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1
```

---

## Future direction

As the project matures, raw text outputs should gradually give way to:

- CI artifacts
- structured snapshots
- stable golden samples
- schema validation
- release attachments

For now, fuller trace retention remains useful because the project is still in a fast-moving handoff and auditability phase.
