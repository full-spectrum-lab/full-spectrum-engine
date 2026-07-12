"""Versioned, auditable governance policy loading and deterministic evaluation."""
import json
import os

DEFAULT_POLICY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "policies",
    "governance-rules.v1.json",
)


def load_policy(path=None):
    policy_path = path or DEFAULT_POLICY
    with open(policy_path, encoding="utf-8-sig") as handle:
        policy = json.load(handle)
    for field in ("policy_id", "version", "source", "approved_by", "change_log", "rules", "default"):
        if field not in policy:
            raise ValueError(f"policy missing required field: {field}")
    return policy


def evaluate(reason_code, policy):
    matched = next(
        (rule for rule in policy["rules"] if rule["when_reason_code"] == reason_code),
        policy["default"],
    )
    return matched, {
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "policy_source": policy["source"],
        "approved_by": policy["approved_by"],
        "matched_rule_id": matched["rule_id"],
    }
