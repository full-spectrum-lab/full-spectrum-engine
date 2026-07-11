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


def cmd_generate(args):
    with open(args.input, encoding="utf-8-sig") as f:
        raw_doc = json.load(f)
    writes, artifacts = write_chain(args.out, raw_doc, timestamp=args.timestamp)
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
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("validate", help="Validate generated JSON artifacts against vendored schemas.")
    v.add_argument("dir", nargs="?", help="Directory of JSON artifacts.")
    v.add_argument("--input", "-i", help="A single JSON file to validate instead of a directory.")
    v.set_defaults(func=cmd_validate)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
