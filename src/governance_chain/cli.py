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


def _load_json_file(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


# ----------------------------------------------------------------
# v1.3 profile subcommand group (FR-01)
# ----------------------------------------------------------------
def cmd_profile_validate(args):
    from src.governance_chain.profiles.registry import ProfileRegistry
    obj = _load_json_file(args.input)
    reg = ProfileRegistry()  # schema-only validation; no fixture load needed
    ok, errors = reg.validate(obj)
    if not ok:
        for e in errors:
            print(f"  [FAIL] {e}", file=sys.stderr)
        print("Profile validation FAILED.", file=sys.stderr)
        return 1
    print(f"Profile valid (profile_type={obj.get('profile_type')}, "
          f"id={obj.get('id')}@{obj.get('version')}).")
    return 0


def cmd_profile_list(args):
    from src.governance_chain.profiles.registry import get_default_registry
    reg = get_default_registry()
    ids = reg.list_ids()
    print(f"{len(ids)} profile id(s):")
    for pid in ids:
        for ver in reg.all_versions(pid):
            print(f"  - {pid}@{ver}")
    return 0


def cmd_profile_show(args):
    from src.governance_chain.profiles.registry import get_default_registry
    reg = get_default_registry()
    try:
        obj = reg.get(args.id, args.version)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
        print(f"Profile written to {args.out}")
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


def cmd_profile_run(args):
    env = _load_json_file(args.input)
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
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(out, handle, ensure_ascii=False, indent=2)
        print(f"Observer Output Envelope written to {args.out}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


# ----------------------------------------------------------------
# v1.3 policy subcommand group (FR-02)
# ----------------------------------------------------------------
def cmd_policy_validate(args):
    from src.governance_chain.policy import load_policy
    try:
        policy = load_policy(args.input)
    except Exception as exc:  # noqa: BLE001
        print(f"error: policy invalid: {exc}", file=sys.stderr)
        return 1
    print(f"Policy valid: policy_id={policy.get('policy_id')} "
          f"version={policy.get('version')}")
    return 0


def cmd_policy_list(args):
    from src.governance_chain.policy import load_policy
    policy = load_policy()
    print(f"default policy: policy_id={policy.get('policy_id')} "
          f"version={policy.get('version')} source={policy.get('source')}")
    return 0


def cmd_policy_show(args):
    from src.governance_chain.policy import load_policy
    policy = load_policy()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(policy, handle, ensure_ascii=False, indent=2)
        print(f"Policy written to {args.out}")
    else:
        print(json.dumps(policy, ensure_ascii=False, indent=2))
    return 0


# ----------------------------------------------------------------
# v1.4 replay subcommand group (FR-01 / FR-05 / FR-06 / FR-07 / FR-09)
# ----------------------------------------------------------------
def _default_v14_store():
    from src.governance_chain import replay_store as rs_mod

    return rs_mod.get_default_store()


def cmd_replay_record(args):
    from src.governance_chain import evaluation_event as ee_mod
    from src.governance_chain import replay_store as rs_mod

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    env = _load_json_file(args.input)
    try:
        out = ee_mod.record_evaluation(
            env, store=store, clock=args.clock or None,
            externalize_input=args.externalize,
        )
    except ee_mod.EventIntegrityError as exc:
        print(f"error: EVENT_INTEGRITY: {exc}", file=sys.stderr)
        return 2
    print(f"recorded event_id={out['replay_ref']['event_id']}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(out, handle, ensure_ascii=False, indent=2)
        print(f"Audited Output Envelope written to {args.out}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_replay_replay(args):
    from src.governance_chain import replay as replay_mod
    from src.governance_chain import replay_bundle as rb_mod
    from src.governance_chain import replay_store as rs_mod
    from src.governance_chain.replay_bundle import ReplayDependencyError

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    engine = replay_mod.ReplayEngine(store)
    if args.bundle:
        bundle = rb_mod.ReplayBundle.from_dict(_load_json_file(args.bundle))
    elif args.event:
        ev = store.get(args.event)
        if ev is None:
            print(f"error: event {args.event} not found", file=sys.stderr)
            return 2
        bundle = rb_mod.ReplayBundle.from_event(ev)
    else:
        print("error: provide --bundle or --event", file=sys.stderr)
        return 2
    try:
        new_event = engine.replay(
            bundle, policy_version=args.policy or None, replay_mode=args.mode
        )
    except ReplayDependencyError as exc:
        print(f"error: REPLAY_DEPENDENCY: {exc}", file=sys.stderr)
        return 2
    print(
        f"replayed new event_id={new_event['event_id']} "
        f"type={new_event['event_type']} mode={new_event['replay_mode']}"
    )
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(new_event, handle, ensure_ascii=False, indent=2)
        print(f"Replay event written to {args.out}")
    else:
        print(json.dumps(new_event, ensure_ascii=False, indent=2))
    return 0


def cmd_replay_audit_export(args):
    from src.governance_chain import audit as audit_mod
    from src.governance_chain import replay_store as rs_mod

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    events = store.list_events(limit=10 ** 9)
    path = audit_mod.AuditExporter.export_range(events, args.out)
    print(f"exported {len(events)} event(s) to {path}")
    return 0


def cmd_replay_audit_verify(args):
    from src.governance_chain import audit as audit_mod
    from src.governance_chain import replay_store as rs_mod

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    ok, tampered = audit_mod.IntegrityChecker.verify_chain(store)
    if ok:
        print("INTEGRITY OK: chain verified, no tamper points")
        return 0
    print(f"INTEGRITY FAIL: {len(tampered)} tamper point(s):", file=sys.stderr)
    for t in tampered:
        print(f"  - {t}", file=sys.stderr)
    return 1


def cmd_replay_audit_events(args):
    from src.governance_chain import replay_store as rs_mod

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    events = store.list_events(limit=args.limit, offset=args.offset)
    for e in events:
        prev = (e.get("previous_event_hash") or "")[:12]
        print(f"{e['event_id']} {e['event_type']} {e.get('replay_mode')} prev={prev}")
    return 0


def cmd_replay_retention_backup(args):
    from src.governance_chain import replay_store as rs_mod

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    path = store.backup(args.path)
    print(f"backup written to {path}")
    return 0


def cmd_replay_retention_restore(args):
    from src.governance_chain import replay_store as rs_mod

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    try:
        store.restore(args.path)
    except FileNotFoundError:
        print(f"error: backup not found: {args.path}", file=sys.stderr)
        return 2
    print(f"restored from {args.path}")
    return 0


def cmd_replay_retention_cleanup(args):
    from src.governance_chain import replay_store as rs_mod

    store = rs_mod.EvaluationEventStore(args.store) if args.store else _default_v14_store()
    n = store.cleanup(args.before)
    print(f"cleanup removed {n} trailing OPERATION event(s)")
    return 0


# ================================================================
# v1.5 enterprise_pilot subcommand group (ADDITIVE; 不改动既有子命令)
# ================================================================
def cmd_pilot_config_check(args):
    from src.enterprise_pilot import ConfigSecretManager, split_config_secrets
    cfg = ConfigSecretManager.load_config(args.input)
    _cfg, refs = split_config_secrets(cfg)
    print(f"config_id={cfg.get('config_id')}")
    if refs:
        print("secret references (credentials NOT inlined into repo):")
        for ref in refs:
            print(f"  - {ref}")
    else:
        print("no secret references found")
    return 0


def cmd_pilot_config_resolve(args):
    from src.enterprise_pilot import ConfigSecretManager
    mgr = ConfigSecretManager(config_path=args.input, secret_backend="secret-file",
                               secret_file=args.secret_file)
    try:
        resolved = mgr.load_resolved()
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(resolved, ensure_ascii=False, indent=2))
    return 0


def cmd_pilot_auth_token(args):
    from src.enterprise_pilot import generate_token
    print(generate_token())
    return 0


def cmd_pilot_auth_roles(args):
    from src.enterprise_pilot import ROLE_PERMISSIONS
    for role, perms in ROLE_PERMISSIONS.items():
        print(f"{role}: {sorted(perms)}")
    return 0


def cmd_pilot_desensitize_run(args):
    from src.enterprise_pilot import apply_desensitization
    record = _load_json_file(args.input)
    policy = _load_json_file(args.policy)
    out, mapping = apply_desensitization(record, policy)
    print(json.dumps({"desensitized": out, "mapping": mapping.to_dict()},
                      ensure_ascii=False, indent=2))
    return 0


def cmd_pilot_review_trigger(args):
    from src.governance_chain import evaluation_event as ee_mod
    from src.governance_chain import replay_store as rs_mod
    from src.enterprise_pilot import record_review
    store = rs_mod.EvaluationEventStore(args.store) if args.store else rs_mod.get_default_store()
    env = _load_json_file(args.input)
    try:
        out = ee_mod.record_evaluation(env, store=store)
    except ee_mod.EventIntegrityError as exc:
        print(f"error: EVENT_INTEGRITY: {exc}", file=sys.stderr)
        return 2
    ref = out["replay_ref"]
    rec = record_review(ref, args.action, args.reviewer, source_store=store)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


def cmd_pilot_review_record(args):
    from src.governance_chain import replay_store as rs_mod
    from src.enterprise_pilot import record_review, ReviewBindingError
    store = rs_mod.EvaluationEventStore(args.store) if args.store else rs_mod.get_default_store()
    ref = {"event_id": args.event_id, "event_digest": args.event_digest,
           "bundle_ref": args.bundle_ref}
    try:
        rec = record_review(ref, args.action, args.reviewer, comment=args.comment,
                            source_store=store)
    except ReviewBindingError as exc:
        print(f"error: REVIEW_BINDING_FORGED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


def cmd_pilot_review_list(args):
    from src.enterprise_pilot import ReviewStore
    from src.enterprise_pilot.review import _default_review_store
    rs = ReviewStore(args.review_store) if args.review_store else _default_review_store()
    for rec in rs.list_by_event(args.event_id):
        print(json.dumps(rec, ensure_ascii=False))
    return 0


def cmd_pilot_health(args):
    from src.enterprise_pilot import health
    print(json.dumps(health(), ensure_ascii=False, indent=2))
    return 0


def cmd_pilot_metrics(args):
    from src.enterprise_pilot import metrics_snapshot
    print(json.dumps(metrics_snapshot(), ensure_ascii=False, indent=2))
    return 0


def cmd_pilot_deploy_walkthrough(args):
    from src.enterprise_pilot import run_walkthrough
    result = run_walkthrough(args.repo_root)
    d = result.to_dict()
    print(f"independent={d['independent']} complete={d['complete']}")
    for name, ok in d["checks"]:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if (d["independent"] and d["complete"]) else 1


def cmd_pilot_connector_list(args):
    from src.enterprise_pilot import CONTRACT_KINDS
    for kind in CONTRACT_KINDS:
        print(kind)
    return 0


def cmd_pilot_connector_emit_off(args):
    from src.enterprise_pilot import ConnectorContract
    contract = ConnectorContract(args.name, write_enabled=False)
    payload = json.loads(args.payload) if args.payload else {}
    out = contract.emit(args.kind, payload)
    print(json.dumps(out, ensure_ascii=False, indent=2))
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

    # ---- v1.3 profile subcommand group (additive; FR-01) ----
    pf = sub.add_parser("profile", help="v1.3 Profile operations (validate/list/show/run).")
    pfs = pf.add_subparsers(dest="profile_cmd", required=True)
    pf_validate = pfs.add_parser("validate", help="Validate a Profile JSON against profile.schema.json.")
    pf_validate.add_argument("--input", "-i", required=True, help="Path to a Profile JSON.")
    pf_validate.set_defaults(func=cmd_profile_validate)
    pf_list = pfs.add_parser("list", help="List loaded Profiles (id@version).")
    pf_list.set_defaults(func=cmd_profile_list)
    pf_show = pfs.add_parser("show", help="Show a Profile by id (optionally pinned version).")
    pf_show.add_argument("--id", required=True, help="Profile id.")
    pf_show.add_argument("--version", default=None, help="Profile version (default: latest approved).")
    pf_show.add_argument("--out", "-o", default=None, help="Write the Profile JSON to this path instead of stdout.")
    pf_show.set_defaults(func=cmd_profile_show)
    pf_run = pfs.add_parser("run", help="Run the Observer over an Input Envelope using its profile refs (FR-05).")
    pf_run.add_argument("--input", "-i", required=True, help="Path to an Input Envelope JSON.")
    pf_run.add_argument("--out", "-o", default=None, help="Write the Output Envelope JSON to this path instead of stdout.")
    pf_run.set_defaults(func=cmd_profile_run)

    # ---- v1.3 policy subcommand group (additive; FR-02) ----
    po = sub.add_parser("policy", help="v1.3 Policy operations (validate/list/show).")
    pos = po.add_subparsers(dest="policy_cmd", required=True)
    po_validate = pos.add_parser("validate", help="Validate a governance policy JSON.")
    po_validate.add_argument("--input", "-i", required=True, help="Path to a policy JSON.")
    po_validate.set_defaults(func=cmd_policy_validate)
    po_list = pos.add_parser("list", help="Show the default governance policy metadata.")
    po_list.set_defaults(func=cmd_policy_list)
    po_show = pos.add_parser("show", help="Show the default governance policy.")
    po_show.add_argument("--out", "-o", default=None, help="Write the policy JSON to this path instead of stdout.")
    po_show.set_defaults(func=cmd_policy_show)

    # ---- v1.4 replay subcommand group (additive) ----
    rp_grp = sub.add_parser(
        "replay", help="v1.4 Replay & Audit (record/replay/audit/retention)."
    )
    rps = rp_grp.add_subparsers(dest="replay_cmd", required=True)

    rp_rec = rps.add_parser("record", help="Analyze + record an immutable EvaluationEvent (FR-01).")
    rp_rec.add_argument("--input", "-i", required=True, help="Input Envelope JSON.")
    rp_rec.add_argument("--out", "-o", default=None, help="Write audited Output Envelope JSON.")
    rp_rec.add_argument("--clock", default=None, help="Pinned ISO-8601 clock for determinism.")
    rp_rec.add_argument("--externalize", action="store_true", help="Do not inline input (NFR-03).")
    rp_rec.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_rec.set_defaults(func=cmd_replay_record)

    rp_rep = rps.add_parser("replay", help="Replay a bundle/event into a new REPLAY event (FR-05/FR-06).")
    rp_rep.add_argument("--bundle", default=None, help="ReplayBundle JSON path.")
    rp_rep.add_argument("--event", default=None, help="Source EvaluationEvent id (replay-by-event-id).")
    rp_rep.add_argument("--policy", default=None, help="Override policy version (FR-05).")
    rp_rep.add_argument("--mode", default="EXACT", choices=["EXACT", "SEMANTIC", "EXPLANATORY"])
    rp_rep.add_argument("--out", "-o", default=None, help="Write replay event JSON.")
    rp_rep.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_rep.set_defaults(func=cmd_replay_replay)

    rp_aud = rps.add_parser("audit", help="Audit export / verify / list (FR-09).")
    rp_auds = rp_aud.add_subparsers(dest="audit_cmd", required=True)
    rp_exp = rp_auds.add_parser("export", help="Export the chain as canonical JSONL.")
    rp_exp.add_argument("--out", "-o", required=True, help="Output .jsonl path.")
    rp_exp.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_exp.set_defaults(func=cmd_replay_audit_export)
    rp_ver = rp_auds.add_parser("verify", help="Verify chain integrity (tamper detection).")
    rp_ver.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_ver.set_defaults(func=cmd_replay_audit_verify)
    rp_ev = rp_auds.add_parser("events", help="List recorded events.")
    rp_ev.add_argument("--limit", type=int, default=100)
    rp_ev.add_argument("--offset", type=int, default=0)
    rp_ev.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_ev.set_defaults(func=cmd_replay_audit_events)

    rp_ret = rps.add_parser("retention", help="Backup / restore / cleanup (audited, NFR-04).")
    rp_rets = rp_ret.add_subparsers(dest="retention_cmd", required=True)
    rp_bk = rp_rets.add_parser("backup", help="Back up the audit database.")
    rp_bk.add_argument("--path", required=True, help="Backup .sqlite path.")
    rp_bk.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_bk.set_defaults(func=cmd_replay_retention_backup)
    rp_rs = rp_rets.add_parser("restore", help="Restore the audit database from a backup.")
    rp_rs.add_argument("--path", required=True, help="Backup .sqlite path.")
    rp_rs.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_rs.set_defaults(func=cmd_replay_retention_restore)
    rp_cl = rp_rets.add_parser("cleanup", help="Clean up old audit OPERATION noise (audited).")
    rp_cl.add_argument("--before", required=True, help="ISO-8601 cutoff; remove OPERATION events before this.")
    rp_cl.add_argument("--store", default=None, help="EvaluationEventStore .sqlite path.")
    rp_cl.set_defaults(func=cmd_replay_retention_cleanup)

    # ---- v1.5 enterprise_pilot subcommand group (ADDITIVE) ----
    pilot = sub.add_parser(
        "pilot",
        help="v1.5 企业试点候选（配置/认证/脱敏/复核/健康/指标/部署/连接器）。",
    )
    pss = pilot.add_subparsers(dest="pilot_cmd", required=True)

    pc = pss.add_parser("config", help="配置与秘密分离（C-01）。")
    pcs = pc.add_subparsers(dest="config_cmd", required=True)
    pcc = pcs.add_parser("check", help="检查配置并列出秘密引用（凭证不进仓库）。")
    pcc.add_argument("--input", "-i", required=True, help="配置文件路径。")
    pcc.set_defaults(func=cmd_pilot_config_check)
    pcr = pcs.add_parser("resolve", help="按引用解析秘密后输出（仅本地）。")
    pcr.add_argument("--input", "-i", required=True, help="配置文件路径。")
    pcr.add_argument("--secret-file", default=None, help="secret-file 路径（可选）。")
    pcr.set_defaults(func=cmd_pilot_config_resolve)

    pa = pss.add_parser("auth", help="最小认证 + RBAC（C-02）。")
    pas = pa.add_subparsers(dest="auth_cmd", required=True)
    pas.add_parser("token", help="生成预共享操作员令牌（reference token）。").set_defaults(
        func=cmd_pilot_auth_token
    )
    pas.add_parser("roles", help="打印角色权限矩阵。").set_defaults(func=cmd_pilot_auth_roles)

    pd_ = pss.add_parser("desensitize", help="脱敏（C-03）。")
    pds = pd_.add_subparsers(dest="desensitize_cmd", required=True)
    pdr = pds.add_parser("run", help="对记录应用脱敏策略。")
    pdr.add_argument("--input", "-i", required=True, help="待脱敏记录 JSON。")
    pdr.add_argument("--policy", "-p", required=True, help="脱敏策略 JSON。")
    pdr.set_defaults(func=cmd_pilot_desensitize_run)

    pr = pss.add_parser("review", help="人工复核（C-04，绑定真实 EvaluationEvent）。")
    prs = pr.add_subparsers(dest="review_cmd", required=True)
    prt = prs.add_parser("trigger", help="记录事件并触发一次复核（演示完整链路）。")
    prt.add_argument("--input", "-i", required=True, help="Input Envelope JSON。")
    prt.add_argument("--reviewer", required=True, help="复核人主体 id。")
    prt.add_argument("--action", default="approve",
                     choices=["approve", "reject", "comment"])
    prt.add_argument("--store", default=None, help="EvaluationEventStore .sqlite 路径。")
    prt.set_defaults(func=cmd_pilot_review_trigger)
    prrc = prs.add_parser("record", help="对已有事件记录复核（需 event-id / event-digest）。")
    prrc.add_argument("--event-id", required=True)
    prrc.add_argument("--event-digest", required=True)
    prrc.add_argument("--bundle-ref", default=None)
    prrc.add_argument("--action", default="approve",
                      choices=["approve", "reject", "comment"])
    prrc.add_argument("--reviewer", required=True)
    prrc.add_argument("--comment", default=None)
    prrc.add_argument("--store", default=None, help="EvaluationEventStore .sqlite 路径。")
    prrc.set_defaults(func=cmd_pilot_review_record)
    prl = prs.add_parser("list", help="按事件列出复核记录。")
    prl.add_argument("--event-id", required=True)
    prl.add_argument("--review-store", default=None, help="ReviewStore .sqlite 路径。")
    prl.set_defaults(func=cmd_pilot_review_list)

    pss.add_parser("health", help="健康检查（C-06）。").set_defaults(func=cmd_pilot_health)
    pss.add_parser("metrics", help="指标快照（C-06）。").set_defaults(func=cmd_pilot_metrics)

    pdw = pss.add_parser("deploy", help="部署走查（C-09）。")
    pdws = pdw.add_subparsers(dest="deploy_cmd", required=True)
    pdww = pdws.add_parser("walkthrough", help="非作者部署走查（独立性/完整性）。")
    pdww.add_argument("--repo-root", default=None)
    pdww.set_defaults(func=cmd_pilot_deploy_walkthrough)

    pcon = pss.add_parser("connector", help="企业 Connector 契约（C-08）。")
    pcons = pcon.add_subparsers(dest="connector_cmd", required=True)
    pcons.add_parser("list", help="列出四契约种类。").set_defaults(func=cmd_pilot_connector_list)
    pcone = pcons.add_parser("emit-off", help="写回默认 OFF 方式 emit 契约载荷（绝不写回）。")
    pcone.add_argument("--name", required=True)
    pcone.add_argument("--kind", required=True,
                       choices=["report_export", "warning_event",
                                "review_recommendation", "audit_export"])
    pcone.add_argument("--payload", "-p", default="{}", help="契约载荷 JSON。")
    pcone.set_defaults(func=cmd_pilot_connector_emit_off)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
