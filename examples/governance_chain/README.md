# Governance Chain — Ecommerce Example

This folder is the runnable input for the Full Spectrum governance-chain CLI.

`raw-input.ecommerce.json` describes one ecommerce after-sales dialogue: a
customer says "我要退款。" and the AI agent replies "可以给您全额退款。" even
though it has no refund authority and its boundary requires human review.

Feed it to the CLI and it produces the complete governance object chain,
validated against the vendored protocol schemas:

```bash
python -m src.governance_chain generate \
    --input examples/governance_chain/raw-input.ecommerce.json \
    --out out/governance_chain
```

Output (in `out/governance_chain/`). Each JSON maps to a protocol spec:

| File | Spec |
| --- | --- |
| `governance-event.ecommerce.json` | [Governance Event](https://github.com/full-spectrum-lab/full-spectrum-protocol/blob/main/specs/governance-event.md) |
| `canonical-context.ecommerce.json` | [Canonical Context](https://github.com/full-spectrum-lab/full-spectrum-protocol/blob/main/specs/canonical-context.md) |
| `cell-manifest.ecommerce.json` | [L1 Cell Protocol](https://github.com/full-spectrum-lab/full-spectrum-protocol/blob/main/specs/l1-cell-protocol.md) |
| `output-envelope.ecommerce.json` | [Governance Output Envelope](https://github.com/full-spectrum-lab/full-spectrum-protocol/blob/main/specs/governance-output-envelope.md) |
| `enterprise-writeback.ecommerce.json` | [Enterprise Writeback](https://github.com/full-spectrum-lab/full-spectrum-protocol/blob/main/specs/enterprise-writeback.md) |
| `report.ecommerce.md` | human-readable summary |

The CLI output is byte-for-byte reproducible against the committed example in
`full-spectrum-protocol/examples/cases/ecommerce_chain/`. See
`tests/test_governance_chain.py` for the regression assertion.
