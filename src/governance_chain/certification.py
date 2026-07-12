#!/usr/bin/env python3
"""
Certification combination engine (FR-07): local eligibility evaluation ONLY.

First-generation Observer only COMPATIBLES with, never FORGES, auth (SRS §6 /
实现文档 §4 铁律 #1). This engine evaluates a ``CertificationRequirement`` against
externally-provided **Attestations** / **Verification results** and returns ONLY
candidate state:

  * ``eligibility_candidate``  ∈ {CANDIDATE, NOT_CANDIDATE, UNKNOWN}
  * ``requirements_satisfied`` : bool
  * ``external_auth_required`` : bool
  * ``trust_domain_results``   : {domain: bool}  (multi trust domain, NEVER merged)

It never emits a "certified" / "authorized" / "active" / "granted" conclusion
(反模式红线). The five combination logics are: ALL_OF / ANY_OF / AT_LEAST_N /
ONE_OF / NOT_REQUIRED, judged by issuer / scope / validity window / revocation
status / trust domain.

Zero intrusion: brand-new additive module.
"""
from .envelope import canonical_json  # noqa: F401  (kept for parity with other modules)

CERT_LOGIC = ("ALL_OF", "ANY_OF", "AT_LEAST_N", "ONE_OF", "NOT_REQUIRED")
DEFAULT_AS_OF = "2026-07-12"

# Trust domains treated as internal (no external authorization required).
_INTERNAL_TRUST_DOMAINS = ("internal", "example.enterprise.internal")


def _attestation_satisfies(att, req, as_of):
    """Return True if attestation ``att`` satisfies requirement ``req``."""
    # issuer (if specified)
    if req.get("issuer") is not None and att.get("issuer") != req.get("issuer"):
        return False
    # scope (if specified)
    if req.get("scope") is not None and att.get("scope") != req.get("scope"):
        return False
    # trust domain (if specified)
    if req.get("trust_domain") is not None and att.get("trust_domain") != req.get("trust_domain"):
        return False
    # revocation status
    if req.get("not_revoked") is True and att.get("revoked") is True:
        return False
    if req.get("not_revoked") is False and att.get("revoked") is False:
        return False
    # validity window (as_of must fall inside [valid_from, valid_until])
    vf = att.get("valid_from")
    vu = att.get("valid_until")
    if vf and as_of < vf:
        return False
    if vu and as_of > vu:
        return False
    return True


def _requirement_satisfied(req, attestations, as_of):
    """Return True if ANY attestation satisfies the requirement."""
    return any(_attestation_satisfies(att, req, as_of) for att in (attestations or []))


class CertificationEngine:
    """Evaluate a CertificationRequirement against attestations (candidate only)."""

    def evaluate(self, requirement, attestations, verification_results=None, as_of=DEFAULT_AS_OF):
        """Evaluate ``requirement`` and return an eligibility-candidate dict.

        ``requirement`` is a CertificationRequirementProfile dict (or any dict with
        a ``domain`` carrying ``logic`` / ``n`` / ``requirements``). ``attestations``
        is a list of attestation dicts; ``verification_results`` is accepted for
        interface parity but the local evaluation uses ``attestations`` directly.
        """
        domain = (requirement.get("domain") or {})
        logic = domain.get("logic", "ALL_OF")
        n = domain.get("n", 1)
        reqs = domain.get("requirements", [])
        if logic not in CERT_LOGIC:
            raise ValueError(f"unsupported certification logic: {logic}")

        attestations = attestations or []
        verification_results = verification_results or []

        satisfied_flags = [
            _requirement_satisfied(r, attestations, as_of) for r in reqs
        ]

        if logic == "ALL_OF":
            requirements_satisfied = all(satisfied_flags) if reqs else False
        elif logic == "ANY_OF":
            requirements_satisfied = any(satisfied_flags)
        elif logic == "AT_LEAST_N":
            requirements_satisfied = sum(1 for f in satisfied_flags if f) >= int(n)
        elif logic == "ONE_OF":
            requirements_satisfied = sum(1 for f in satisfied_flags if f) == 1
        elif logic == "NOT_REQUIRED":
            requirements_satisfied = True
        else:  # pragma: no cover - guarded above
            requirements_satisfied = False

        # Multi trust-domain results: NEVER merged into a single boolean.
        trust_domain_results = {}
        for r in reqs:
            td = r.get("trust_domain", "internal")
            td_sat = _requirement_satisfied(r, attestations, as_of)
            trust_domain_results[td] = trust_domain_results.get(td, False) or td_sat

        if logic == "NOT_REQUIRED":
            eligibility = "CANDIDATE"
        elif requirements_satisfied:
            eligibility = "CANDIDATE"
        elif not attestations and not verification_results:
            # No attestation / verification evidence at all: the first-gen Observer
            # cannot decide, so it must surface UNKNOWN rather than silently
            # concluding NOT_CANDIDATE (NFR-05: never silently pass / 降级).
            eligibility = "UNKNOWN"
        else:
            eligibility = "NOT_CANDIDATE"

        external_auth_required = any(
            r.get("trust_domain") not in _INTERNAL_TRUST_DOMAINS
            for r in reqs
        )

        return {
            "eligibility_candidate": eligibility,
            "requirements_satisfied": bool(requirements_satisfied),
            "external_auth_required": bool(external_auth_required),
            "trust_domain_results": trust_domain_results,
            "note": f"v1.3 local eligibility evaluation only; logic={logic}; "
                    f"not a certification/authorization conclusion",
        }
