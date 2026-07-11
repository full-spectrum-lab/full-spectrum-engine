#!/usr/bin/env python3
"""Render a human-readable governance-chain report (Markdown)."""


def render(raw_doc, artifacts, run_id, audit_id):
    ri = raw_doc["raw_input"]
    suffix = raw_doc["adapter_id"]
    ge = artifacts["governance-event"]
    cc = artifacts["canonical-context"]
    ew = artifacts["enterprise-writeback"]
    raw_id = ri["raw_input_id"]
    authority_ok = cc["authority"]["verified"]
    risk_level = ew["risk_level"]
    safety = ew["safety_action"]

    L = []
    L.append(f"# {suffix.capitalize()} Governance Chain Report")
    L.append("")
    L.append("> Example only. This report uses mock synthetic data and does not represent production validation.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append(f"- Raw input: `{raw_id}`")
    L.append(f"- Scenario: ecommerce after-sales refund request")
    if not authority_ok:
        L.append(f"- Detected issue: unauthorized refund commitment")
    else:
        L.append(f"- Detected issue: none")
    L.append(f"- Risk level: {risk_level}")
    L.append(f"- Recommended action: {safety}")
    L.append(f"- Related GovernanceEvent: `{ge['event_id']}`")
    L.append(f"- Related EnterpriseWriteback: `{audit_id}`")
    L.append("")
    L.append("## Finding")
    L.append("")
    L.append("The user requested a refund. The AI agent replied with an unconditional full-refund promise:")
    L.append("")
    L.append(f"> {ri['ai_response']}")
    L.append("")
    if not authority_ok:
        L.append(
            "The agent's declared capability did not include refund authority, and its boundary "
            "required human review before any refund commitment. This is an unauthorized commitment: "
            "the agent promised a business action it was not certified to make."
        )
    else:
        L.append("The agent acted within its certified authority.")
    L.append("")
    L.append("## Protocol mapping")
    L.append("")
    L.append("| Chain step | Full Spectrum object |")
    L.append("| --- | --- |")
    L.append(f"| Business raw input | `raw-input.{suffix}.json` |")
    L.append(f"| Adapter mapping | I/O Contract ({suffix.capitalize()}Adapter) |")
    L.append(f"| Governance Event | `governance-event.{suffix}.json` |")
    L.append(f"| Canonical Context | `canonical-context.{suffix}.json` |")
    L.append(f"| Subject declaration | `cell-manifest.{suffix}.json` (L1 Cell Protocol) |")
    L.append(f"| Engine output | `output-envelope.{suffix}.json` |")
    L.append(f"| Enterprise decision | `enterprise-writeback.{suffix}.json` |")
    L.append(f"| Audit reference | `{audit_id}` |")
    L.append("")
    L.append("## Decision")
    L.append("")
    L.append("The engine did not execute the refund. It returned an Enterprise Writeback that:")
    L.append("")
    if not ew["allow_auto_reply"]:
        L.append("- blocks auto-reply and auto-execution;")
    else:
        L.append("- allows auto-reply;")
    if not ew["allow_commitment"]:
        L.append("- blocks the commitment;")
    else:
        L.append("- allows the commitment;")
    if ew.get("review_role"):
        L.append(f"- routes the case to `{ew['review_queue']}` for human review by `{ew['review_role']}`.")
    L.append("")
    L.append("## Boundary")
    L.append("")
    L.append(
        "The protocol does not execute the enterprise action. It records a reviewable recommendation "
        "and hands off to the enterprise's own system."
    )
    L.append("")
    return "\n".join(L)
