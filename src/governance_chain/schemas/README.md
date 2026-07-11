# Vendored Full Spectrum Protocol schemas

These JSON Schemas (draft 2020-12) are **vendored copies** used by the
governance-chain CLI to validate generated artifacts locally, so the CLI runs
in ten minutes with no network access and no extra install.

| Schema | Object | Source repo |
| --- | --- | --- |
| `governance-event.schema.json` | Governance Event | `full-spectrum-lab/full-spectrum-protocol` @ `08ba162` |
| `canonical-context.schema.json` | Canonical Context | `full-spectrum-lab/full-spectrum-protocol` @ `08ba162` |
| `l1-cell-protocol.schema.json` | Cell Manifest (L1 Cell Protocol) | `full-spectrum-lab/full-spectrum-protocol` @ `08ba162` |
| `governance-output-envelope.schema.json` | Governance Output Envelope | `full-spectrum-lab/full-spectrum-protocol` @ `08ba162` |
| `enterprise-writeback.schema.json` | Enterprise Writeback | `full-spectrum-lab/full-spectrum-protocol` @ `08ba162` |

Source tree in the protocol repo: `schemas/`.

**Update policy:** when the protocol repo bumps a schema, copy the new file
here and update the `@ <commit>` reference. The CLI's `validate` step will
then enforce the new contract.
