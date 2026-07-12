#!/usr/bin/env python3
"""
Lightweight JSON Schema (draft 2020-12 subset) validator.

Self-contained: uses only the standard library so the governance-chain CLI
runs in a minimal environment without `pip install`. When the `jsonschema`
package is installed it is used automatically for stricter checking; otherwise
this built-in checker is the fallback.

Supported keywords: type, required, enum, const, properties, items,
additionalProperties (false + patternProperties), minProperties, minimum,
maximum, minLength. `format: date-time` is accepted (not enforced).
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.join(_HERE, "schemas")

# filename keyword -> schema filename (mirrors the Full Spectrum object vocabulary)
SCHEMA_MAP = {
    "governance-event": "governance-event.schema.json",
    "cell-manifest": "l1-cell-protocol.schema.json",
    "l1-cell-protocol": "l1-cell-protocol.schema.json",
    "output-envelope": "governance-output-envelope.schema.json",
    "governance-output-envelope": "governance-output-envelope.schema.json",
    "enterprise-writeback": "enterprise-writeback.schema.json",
    "canonical-context": "canonical-context.schema.json",
    "subject-declaration": "subject-declaration.schema.json",
}


def load_schema(name):
    with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8-sig") as f:
        return json.load(f)


def map_schema_for_filename(fname):
    for key, schema_file in SCHEMA_MAP.items():
        if key in fname:
            return schema_file
    return None


def _type_ok(value, t):
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def _check(inst, schema, path, errors):
    t = schema.get("type")
    if t is not None and not _type_ok(inst, t):
        errors.append(f"{path}expected type {t}, got {type(inst).__name__}")
        return  # cannot recurse safely on a wrong-typed value
    if "const" in schema and inst != schema["const"]:
        errors.append(f"{path}value {inst!r} != const {schema['const']!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errors.append(f"{path}value {inst!r} not in enum {schema['enum']}")
    if "minLength" in schema and isinstance(inst, str) and len(inst) < schema["minLength"]:
        errors.append(f"{path}string shorter than minLength {schema['minLength']}")
    if "minimum" in schema and isinstance(inst, (int, float)) and inst < schema["minimum"]:
        errors.append(f"{path}value {inst} < minimum {schema['minimum']}")
    if "maximum" in schema and isinstance(inst, (int, float)) and inst > schema["maximum"]:
        errors.append(f"{path}value {inst} > maximum {schema['maximum']}")
    if isinstance(inst, dict):
        for k in schema.get("required", []):
            if k not in inst:
                errors.append(f"{path}missing required property '{k}'")
        props = schema.get("properties", {})
        for k, v in inst.items():
            if k in props:
                _check(v, props[k], f"{path}{k}.", errors)
            elif "patternProperties" in schema:
                matched = False
                for pat, subschema in schema["patternProperties"].items():
                    if re.match(pat, k):
                        matched = True
                        _check(v, subschema, f"{path}{k}.", errors)
                if not matched and schema.get("additionalProperties", True) is False:
                    errors.append(f"{path}extra property '{k}' not allowed")
            elif schema.get("additionalProperties", True) is False:
                errors.append(f"{path}extra property '{k}' not allowed")
        if "minProperties" in schema and len(inst) < schema["minProperties"]:
            errors.append(f"{path}fewer than minProperties {schema['minProperties']}")
    if isinstance(inst, list) and schema.get("type") == "array":
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, it in enumerate(inst):
                _check(it, items_schema, f"{path}[{i}].", errors)


def lightweight_errors(inst, schema, path=""):
    errors = []
    _check(inst, schema, path, errors)
    return errors


def validate_instance(inst, schema):
    """Return (ok, errors). Uses jsonschema when available, else the fallback."""
    try:
        import jsonschema  # noqa: F401
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(schema)
        errs = sorted(validator.iter_errors(inst), key=lambda e: list(e.path))
        if errs:
            return False, [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]
        return True, []
    except ImportError:
        errs = lightweight_errors(inst, schema)
        return (len(errs) == 0, errs)


def validate_file(json_path):
    """Validate one JSON file against its mapped schema. Returns (ok, errors, schema_file)."""
    fname = os.path.basename(json_path)
    schema_file = map_schema_for_filename(fname)
    if not schema_file:
        return None, ["no schema mapping for this filename"], None
    schema = load_schema(schema_file)
    with open(json_path, encoding="utf-8-sig") as f:
        inst = json.load(f)
    ok, errors = validate_instance(inst, schema)
    return ok, errors, schema_file
