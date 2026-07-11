# Explainability Walkthrough (`v1.0.0`)

This walkthrough explains how one inspected request becomes a structured audit path.

It is written for reviewers who want to understand **what the engine is doing**, not only how to call the API.

## 1. Start from one request

Example source artifact:

- `examples/scenario_refund_conflict.json`

Typical question:

> A user requests a refund after merchant refusal.  
> Should the system keep refusing, automatically compensate, or escalate to a safer handling path?

At this stage the engine is **not** making the final business ruling.

It is turning the request into a reproducible governance inspection trace.

## 2. The engine builds a scenario

There are two entry paths:

1. direct scenario mode
2. adapter mode

Both converge into the same internal simulation shape:

- governance starting state
- actor / agent mix
- sensitivity level
- conflict density
- reversibility / rollback difficulty
- diffusivity
- ESS-lite search horizon

## 3. The engine runs a deterministic simulation

With a fixed seed:

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
```

the engine produces stable output.

So the first explainability guarantee is:

> the same input plus the same seed should produce the same audited structure.

## 4. The engine emits `RiskVector`

The first compressed explanation artifact is `RiskVector`.

Instead of saying only “high risk”, the engine exposes which dimensions are driving concern:

- survival / continuity impact
- trust impact
- meaning / legitimacy impact
- rollback difficulty (`reversibility` field name retained)
- explainability
- diffusivity
- urgency
- uncertainty

## 5. The engine emits `Runestone`

The second explanation artifact is `Runestone`.

`Runestone` binds:

- decision code
- reason binding
- risk signature
- optional parent token
- optional agent trail

Reference sample:

- `examples/api-samples/runestone-refund-seed42.json`

## 6. The engine preserves an audit trace preview

Current engine samples also expose a local audit-trace-style preview:

- `examples/api-samples/audit-trace-preview-refund-seed42.json`

This is not yet the full cross-node protocol `AuditTrace`.

But it already shows the intended direction:

```text
request -> simulation -> risk summary -> runestone -> queryable local audit record
```

## 7. Where ESS-lite appears

ESS-lite is the current local path suggestion layer.

It does not claim final legal or compliance authority.

Its function is narrower:

- expose plausible treatment paths
- make tradeoffs visible
- preserve why one path was considered safer or more reversible

## 8. Human review is still outside the engine

The engine explains and records.

It does not:

- directly refund users
- directly impose penalties
- directly make legal rulings
- directly replace human or enterprise authorization

## 9. Fastest way to inspect the chain yourself

1. run `simulate.py` with a fixed seed
2. inspect `test-records/v0.8-public-beta/`
3. inspect `examples/api-samples/`
4. start the local API
5. compare API output with CLI output

## 10. Current explainability claim

At `v1.0.0`, the engine can honestly claim:

> We can show how a local inspection request becomes a reproducible risk summary, a runestone token, and a locally queryable audit trail preview.

