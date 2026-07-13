# Full Spectrum Engine v1.5.0 — Enterprise Pilot Candidate

Release date: 2026-07-13

v1.5.0 adds a bounded enterprise-pilot layer without changing the nine protected core directories. It introduces configuration/secret separation, local reference-token RBAC, desensitization, append-only human review, resilience primitives, structured health and metrics, local backup/rollback, Connector output contracts and a non-author deployment walkthrough.

## Independent acceptance

- pytest: 285 passed + 3 subtests, 0 failed;
- v1.5 black box: 13/13;
- v1.4 regression black box: 9/9;
- independent red-line verification: 9/9;
- protected-core diff against portable tag `v1.2.0`: 0 bytes;
- public pilot CLI smoke: `auth roles` and `connector list` passed after fixing missing facade exports;
- timeout fault injection proves that a 0.2 s deadline returns before 0.75 s for a 1 s worker.

## Fixed during independent review

Independent Codex review found that the initial timeout wrapper waited for its worker during executor shutdown, and that two public CLI commands imported constants not exposed by the package facade. Both defects now have regression tests.

## Boundaries

- local controlled pilot, not an enterprise platform;
- no ObservedSubject login identity and no multi-tenant authorization model;
- no automatic business execution or cross-organization network;
- Connector writeback remains off by default;
- thread-based timeout returns at the deadline but cannot forcibly terminate an already-running Python function; mutating operations must use idempotency and rollback or an external process boundary.
