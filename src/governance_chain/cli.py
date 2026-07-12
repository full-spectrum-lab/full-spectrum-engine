#!/usr/bin/env python3
"""
CLI entry point for the Full Spectrum governance-chain generator.

Usage (no install required):
    python -m src.governance_chain generate \
        --input examples/governance_chain/raw-input.ecommerce.json \
        --out out/governance_chain

Or, after `pip install -e .`:
    fsengine-govchain generate -i examples/governance_chain/raw-input.ecommerce.json -o out/governance_chain
"""
import argparse
import json
import os
import sys

from .generate import write_chain
from . import validator
from . import envelope as envelope_mod
from src.subject import load_declaration, normalize_declaration, SubjectDeclarationError


def cmd_generate(args):
    with open(args.input, encoding="utf-8-sig") as f:
        raw_doc = json.load(f)
    declaration = None
    try:
        if args.subject and args.subject_file:
            print("error: use only one of --subject or --subject-file", file=sys.stderr)
            return 2
        if args.subject:
            declaration, _ = normalize_declaration(json.loads(args.subject))
        elif args.subject_file:
            declaration, _ = load_declaration(args.subject_file)
    except (json.JSONDecodeError, SubjectDeclarationError) as exc:
        code = getattr(exc, "code", "SUBJECT_INVALID_JSON")
        print(f"error: {code}: {exc}", file=sys.stderr)
        return 2
    writes, artifacts = write_chain(args.out, raw_doc, timestamp=args.timestamp, policy_path=args.policy, subject_declaration=declaration)
    print(f"Generated governance chain in {args.out}/:")
    for kind, path in writes.items():
        print(f"  - {os.path.relpath(path)}")

    failures = 0
    for kind in ("governance-event", "canonical-context", "cell-manifest",
                 "output-envelope", "enterprise-writeback"):
        schema_file = validator.map_schema_for_filename(kind + ".json")
        schema = validator.load_schema(schema_file)
        ok, errors = validator.validate_instance(artifacts[kind], schema)
        if ok:
            print(f"  [PASS] {kind} -> {schema_file}")
        else:
            failures += 1
            print(f"  [FAIL] {kind} -> {schema_file}: {errors[0]}")
    if failures:
        print(f"\n{failures} artifact(s) failed schema validation.", file=sys.stderr)
        return 1
    print("\nAll artifacts conform to Full Spectrum Protocol schemas.")
    return 0


def cmd_validate(args):
    target = args.dir or args.input
    if not target:
        print("error: provide a directory or --input file to validate", file=sys.stderr)
        return 2
    failures = 0
    checked = 0
    if os.path.isdir(target):
        for fn in sorted(os.listdir(target)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(target, fn)
            ok, errors, schema_file = validator.validate_file(path)
            if schema_file is None:
                print(f"[SKIP ] {fn} (no schema mapping)")
                continue
            checked += 1
            if ok:
                print(f"[PASS ] {fn} -> {schema_file}")
            else:
                failures += 1
                print(f"[FAIL ] {fn} -> {schema_file}: {errors[0]}")
    else:
        ok, errors, schema_file = validator.validate_file(target)
        checked = 1
        if ok:
            print(f"[PASS ] {target} -> {schema_file}")
        else:
            failures += 1
            print(f"[FAIL ] {target} -> {schema_file}: {errors[0]}")
    print(f"\nSummary: {checked} checked, {failures} failed.")
    return 1 if failures else 0


def cmd_envelope_validate_input(args):
    with open(args.input, encoding="utf-8-sig") as f:
        env = json.load(f)
    ok, errors = envelope_mod.validate_input_envelope(env)
    if not ok:
        for e in errors:
            print(f"  [FAIL] {e}", file=sys.stderr)
        print("Input Envelope validation FAILED.", file=sys.stderr)
        return 1
    # Explicit UNKNOWN handling (FR-07): missing evidence with no unknowns declared is a defect.
    if not env.get("evidence_refs") and not env.get("unknowns"):
        print("  [WARN] no evidence_refs and no unknowns declared; UNKNOWN must be explicit.", file=sys.stderr)
    print(f"Input Envelope valid (schema_id={env.get('schema_id')}, layer={env.get('layer')}, scope={env.get('scope')}).")
    return 0


def cmd_envelope_run(args):
    with open(args.input, encoding="utf-8-sig") as f:
        env = json.load(f)
    try:
        out = envelope_mod.run_envelope(env)
    except envelope_mod.InputEnvelopeError as exc:
        print(f"error: INPUT_ENVELOPE_INVALID: {exc}", file=sys.stderr)
        for e in (exc.errors or []):
            print(f"  - {e}", file=sys.stderr)
        return 2
    ok, errors = envelope_mod.validate_output_envelope(out)
    if not ok:
        for e in errors:
            print(f"  [FAIL] {e}", file=sys.stderr)
        print("Output Envelope validation FAILED.", file=sys.stderr)
        return 1
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"Observer Output Envelope written to {args.out}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_envelope_check_links(args):
    with open(args.input, encoding="utf-8-sig") as f:
        env = json.load(f)
    known = set()
    if args.known:
        raw = args.known.strip()
        data = None
        # Accept inline JSON ({...} / [...]) directly; otherwise treat as file path.
        if raw[:1] in ("{", "["):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None
        if data is None:
            with open(args.known, encoding="utf-8-sig") as f:
                data = json.load(f)
        # known ids may be a list of objects (with 'id') or a bare list of ids
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    known.add(item["id"])
                elif isinstance(item, str):
                    known.add(item)
        elif isinstance(data, dict):
            known.update(data.get("known_ids", []))
    broken = envelope_mod.check_envelope_links(env, known)
    if broken:
        for kind, ref in broken:
            print(f"  [BROKEN] {kind}: {ref}", file=sys.stderr)
        print(f"{len(broken)} broken reference(s) detected (not silently passed).", file=sys.stderr)
        return 1
    print("No broken references; all declared subject/relationship refs resolve.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="fsengine-govchain",
        description="Generate the Full Spectrum governance object chain from a raw business input.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate governance chain artifacts from a raw-input JSON.")
    g.add_argument("--input", "-i", required=True, help="Path to raw-input JSON (e.g. raw-input.ecommerce.json).")
    g.add_argument("--out", "-o", default="out", help="Output directory for generated artifacts.")
    g.add_argument("--timestamp", default=None,
                   help="Override event timestamp (default deterministic demo timestamp).")
    g.add_argument("--policy", default=None,
                   help="Versioned governance policy JSON; defaults to the vendored approved policy.")
    g.add_argument("--subject", default=None, help="Inline Subject Declaration JSON (v1.1).")
    g.add_argument("--subject-file", default=None, help="Subject Declaration JSON/YAML file (v1.1).")
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("validate", help="Validate generated JSON artifacts against vendored schemas.")
    v.add_argument("dir", nargs="?", help="Directory of JSON artifacts.")
    v.add_argument("--input", "-i", help="A single JSON file to validate instead of a directory.")
    v.set_defaults(func=cmd_validate)

    e = sub.add_parser("envelope", help="v1.2 Observer Input/Output Envelope operations.")
    esub = e.add_subparsers(dest="envelope_cmd", required=True)
    ev = esub.add_parser("validate-input", help="Validate an Input Envelope against the v1.2 schema (FR-01).")
    ev.add_argument("--input", "-i", required=True, help="Path to an Input Envelope JSON.")
    ev.set_defaults(func=cmd_envelope_validate_input)
    er = esub.add_parser("run", help="Run the v1.2 Observer over an Input Envelope and emit the Output Envelope (FR-03).")
    er.add_argument("--input", "-i", required=True, help="Path to an Input Envelope JSON.")
    er.add_argument("--out", "-o", default=None, help="Write the Output Envelope JSON to this path instead of stdout.")
    er.set_defaults(func=cmd_envelope_run)
    el = esub.add_parser("check-links", help="Detect broken subject/relationship references (FR-02 / AC-05).")
    el.add_argument("--input", "-i", required=True, help="Path to an Input Envelope JSON.")
    el.add_argument("--known", "-k", default=None, help="Path to known-id set (list of objects with 'id', or {\"known_ids\":[...]}).")
    el.set_defaults(func=cmd_envelope_check_links)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
