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


# =============================================================
# v1.3 Policy layer (FR-02): Measurement / Evaluation / Enterprise Authorization
#
# The original load_policy / evaluate above are UNCHANGED (zero intrusion).
# The three classes below are ADDITIVE and describe *how* to measure / judge /
# authorize. The Enterprise Authorization Policy is DECLARATIVE ONLY: the
# Observer never executes it.
# =============================================================

class ForbiddenError(Exception):
    """Raised when Enterprise Authorization would be executed by the Observer.

    First-generation Observer only COMPATIBLES with, never FORGES, auth; it must
    never perform an enterprise authorization action.
    """

    code = "ENTERPRISE_AUTH_FORBIDDEN"

    def __init__(self, message):
        super().__init__(message)


class MeasurementProfile:
    """How to COMPUTE / measure (measurement口径). Wraps a profile dict."""

    def __init__(self, profile):
        self.profile = profile or {}

    @property
    def id(self):
        return self.profile.get("id")

    @property
    def version(self):
        return self.profile.get("version")

    def compute_spec(self):
        """Return the measurement parameters (weights / method / reference_profiles)."""
        return (self.profile.get("domain") or {}).get("parameters", {})

    def weights(self):
        return self.compute_spec().get("weights", {})


class EvaluationPolicy:
    """How to JUDGE and flag risk. Wraps a profile dict (metadata only)."""

    def __init__(self, profile):
        self.profile = profile or {}

    @property
    def id(self):
        return self.profile.get("id")

    @property
    def version(self):
        return self.profile.get("version")

    def thresholds(self):
        return (self.profile.get("domain") or {}).get("parameters", {}).get("thresholds", {})

    def assess(self, risk_vector):
        """Return evaluation metadata. Does NOT alter the deterministic risk_vector.

        Per decision #6 the deterministic risk_vector formula does not consume
        evaluation thresholds, so this is a structural, non-effecting read.
        """
        return {
            "policy_id": self.id,
            "policy_version": self.version,
            "thresholds": self.thresholds(),
            "note": "EvaluationPolicy is metadata only; it does not alter the "
                    "deterministic risk_vector",
        }


class EnterpriseAuthorizationPolicy:
    """Enterprise Authorization Policy — DECLARATIVE ONLY, never executed.

    The Observer carries and schema-checks this policy but never runs
    :meth:`execute` in any normal path. :meth:`execute` is an explicit guard that
    raises :class:`ForbiddenError`, documenting that authorization belongs to the
    enterprise, not the first-generation Observer.
    """

    def __init__(self, profile=None, *, describe=None):
        self.profile = profile or {}
        self._describe = describe or {}

    def describe(self):
        if self.profile:
            return (self.profile.get("domain") or {})
        return self._describe

    def execute(self, *args, **kwargs):
        raise ForbiddenError(
            "first-gen Observer does not execute Enterprise Authorization"
        )
