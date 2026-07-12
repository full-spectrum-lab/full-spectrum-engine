"""Deterministic, offline Subject Declaration handling for Engine v1.1."""
import copy
import hashlib
import json
from datetime import datetime


class SubjectDeclarationError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


TOP_LEVEL = {
    "declaration_id", "schema_version", "mode", "source", "declared_by_ref",
    "declared_at", "effective_from", "effective_until", "status", "digest",
    "schema_unknown_field_policy", "subject", "l4_interop",
}
MODES = {"tool", "compatible", "certified_reference"}


def _canonical_digest(doc):
    value = copy.deepcopy(doc)
    value.pop("digest", None)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _date_time(value, field):
    if not isinstance(value, str):
        raise SubjectDeclarationError("SUBJECT_INVALID_FIELD", f"{field} must be an ISO-8601 string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SubjectDeclarationError("SUBJECT_INVALID_FIELD", f"{field} must be ISO-8601") from exc


def normalize_declaration(data):
    if not isinstance(data, dict):
        raise SubjectDeclarationError("SUBJECT_INVALID_TYPE", "subject declaration must be an object")
    doc = copy.deepcopy(data)
    policy = doc.get("schema_unknown_field_policy", "reject")
    if policy not in {"reject", "preserve", "warn"}:
        raise SubjectDeclarationError("SUBJECT_INVALID_FIELD", "schema_unknown_field_policy must be reject, preserve or warn")
    extras = sorted(set(doc) - TOP_LEVEL)
    if extras and policy == "reject":
        raise SubjectDeclarationError("SUBJECT_UNKNOWN_FIELD", f"unknown fields: {extras}")
    warnings = [f"preserved unknown field: {name}" for name in extras] if policy == "warn" else []

    required = ["declaration_id", "schema_version", "mode", "source", "declared_by_ref", "declared_at", "status", "subject"]
    missing = [name for name in required if name not in doc]
    if missing:
        raise SubjectDeclarationError("SUBJECT_REQUIRED_FIELD_MISSING", f"missing required fields: {missing}")
    if doc["schema_version"] != "sd-1.1":
        raise SubjectDeclarationError("SUBJECT_SCHEMA_VERSION_UNSUPPORTED", "schema_version must be sd-1.1")
    if doc["mode"] not in MODES:
        raise SubjectDeclarationError("SUBJECT_MODE_INVALID", f"mode must be one of {sorted(MODES)}")
    _date_time(doc["declared_at"], "declared_at")
    for field in ("effective_from", "effective_until"):
        if field in doc:
            _date_time(doc[field], field)
    if doc["status"] not in {"draft", "active", "suspended", "expired", "revoked"}:
        raise SubjectDeclarationError("SUBJECT_STATUS_INVALID", "invalid declaration status")

    subject = doc["subject"]
    if not isinstance(subject, dict):
        raise SubjectDeclarationError("SUBJECT_INVALID_TYPE", "subject must be an object")
    mode_required = {"tool": ["local_subject_id", "subject_type"], "compatible": ["local_subject_id", "subject_type", "enterprise_scope", "capabilities", "boundaries", "unknown_policy"], "certified_reference": ["local_subject_id", "subject_type", "enterprise_scope", "capabilities", "boundaries", "unknown_policy"]}
    missing = [name for name in mode_required[doc["mode"]] if name not in subject]
    if missing:
        raise SubjectDeclarationError("SUBJECT_REQUIRED_FIELD_MISSING", f"{doc['mode']} subject missing fields: {missing}")
    for field in ("capabilities", "boundaries"):
        if field in subject and (not isinstance(subject[field], list) or not all(isinstance(x, str) for x in subject[field])):
            raise SubjectDeclarationError("SUBJECT_INVALID_FIELD", f"{field} must be an array of strings")
    if doc["mode"] == "certified_reference" and not doc.get("l4_interop", {}).get("enabled"):
        raise SubjectDeclarationError("SUBJECT_L4_REFERENCE_REQUIRED", "certified_reference mode requires enabled l4_interop references")
    l4 = doc.setdefault("l4_interop", {"enabled": False, "external_identity_refs": [], "credential_refs": [], "trust_domain_refs": [], "verification_result_refs": []})
    l4.setdefault("enabled", False)
    for field in ("external_identity_refs", "credential_refs", "trust_domain_refs", "verification_result_refs"):
        l4.setdefault(field, [])
        if not isinstance(l4[field], list) or not all(isinstance(x, str) for x in l4[field]):
            raise SubjectDeclarationError("SUBJECT_INVALID_FIELD", f"l4_interop.{field} must be an array of strings")

    calculated = _canonical_digest(doc)
    if doc.get("digest") and doc["digest"] != calculated:
        raise SubjectDeclarationError("SUBJECT_DIGEST_MISMATCH", "subject declaration digest does not match canonical content")
    doc["digest"] = calculated
    return doc, warnings


def load_declaration(path):
    with open(path, encoding="utf-8-sig") as handle:
        text = handle.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError as exc:
            raise SubjectDeclarationError("SUBJECT_YAML_SUPPORT_UNAVAILABLE", "install PyYAML to read YAML declarations") from exc
        data = yaml.safe_load(text)
    return normalize_declaration(data)


def resolve_declarations(declarations):
    normalized = [normalize_declaration(item)[0] for item in declarations]
    by_id = {}
    for item in normalized:
        subject_id = item["subject"]["local_subject_id"]
        if subject_id in by_id and by_id[subject_id]["digest"] != item["digest"]:
            raise SubjectDeclarationError("SUBJECT_DECLARATION_CONFLICT", f"conflicting active declarations for {subject_id}")
        by_id[subject_id] = item
    return list(by_id.values())


def subject_ref(declaration):
    if not declaration:
        return {"id": "none", "mode": "none", "declaration_id": "none", "digest": "none", "external_effect": False}
    return {"id": declaration["subject"]["local_subject_id"], "mode": declaration["mode"], "declaration_id": declaration["declaration_id"], "digest": declaration["digest"], "external_effect": False}
