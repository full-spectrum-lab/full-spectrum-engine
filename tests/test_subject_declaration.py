import copy
import json
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from src.api.server import create_app
from src.governance_chain import build_chain
from src.subject import SubjectDeclarationError, load_declaration, normalize_declaration, resolve_declarations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(ROOT, "examples", "subjects", "subject-declaration.customer-service.compatible.json")


class SubjectDeclarationTests(unittest.TestCase):
    def setUp(self):
        with open(EXAMPLE, encoding="utf-8-sig") as handle:
            self.compatible = json.load(handle)

    def test_compatible_declaration_gets_deterministic_digest(self):
        first, _ = normalize_declaration(self.compatible)
        second, _ = normalize_declaration(self.compatible)
        self.assertEqual(first["digest"], second["digest"])
        self.assertTrue(first["digest"].startswith("sha256:"))

    def test_tool_mode_has_only_minimum_subject_fields(self):
        tool = copy.deepcopy(self.compatible)
        tool["mode"] = "tool"
        tool["subject"] = {"local_subject_id": "tool-1", "subject_type": "tool"}
        normalized, _ = normalize_declaration(tool)
        self.assertEqual(normalized["mode"], "tool")

    def test_compatible_missing_boundary_fails(self):
        invalid = copy.deepcopy(self.compatible)
        invalid["subject"].pop("boundaries")
        with self.assertRaisesRegex(SubjectDeclarationError, "missing fields") as caught:
            normalize_declaration(invalid)
        self.assertEqual(caught.exception.code, "SUBJECT_REQUIRED_FIELD_MISSING")

    def test_unknown_field_policy_is_separate(self):
        invalid = copy.deepcopy(self.compatible)
        invalid["unexpected"] = True
        with self.assertRaises(SubjectDeclarationError) as caught:
            normalize_declaration(invalid)
        self.assertEqual(caught.exception.code, "SUBJECT_UNKNOWN_FIELD")
        invalid["schema_unknown_field_policy"] = "warn"
        _, warnings = normalize_declaration(invalid)
        self.assertTrue(warnings)

    def test_digest_tamper_fails(self):
        normalized, _ = normalize_declaration(self.compatible)
        normalized["subject"]["capabilities"].append("refund")
        with self.assertRaises(SubjectDeclarationError) as caught:
            normalize_declaration(normalized)
        self.assertEqual(caught.exception.code, "SUBJECT_DIGEST_MISMATCH")

    def test_same_id_conflict_rejected(self):
        other = copy.deepcopy(self.compatible)
        other["declaration_id"] = "other"
        with self.assertRaises(SubjectDeclarationError) as caught:
            resolve_declarations([self.compatible, other])
        self.assertEqual(caught.exception.code, "SUBJECT_DECLARATION_CONFLICT")

    def test_governance_chain_propagates_subject_ref(self):
        with open(os.path.join(ROOT, "examples", "governance_chain", "raw-input.ecommerce.json"), encoding="utf-8-sig") as handle:
            raw = json.load(handle)
        artifacts, _, _ = build_chain(raw, subject_declaration=self.compatible)
        for artifact in artifacts.values():
            self.assertEqual(artifact["subject_ref"]["id"], "cs_ai_01")
            self.assertFalse(artifact["subject_ref"]["external_effect"])

    def test_api_accepts_and_rejects_subject_declaration(self):
        db = os.path.join(tempfile.mkdtemp(), "api.db")
        client = TestClient(create_app(db_path=db))
        scenario_path = os.path.join(ROOT, "examples", "scenario_refund_conflict.json")
        with open(scenario_path, encoding="utf-8-sig") as handle:
            scenario = json.load(handle)
        response = client.post("/api/v1/evaluate", json={"scenario": scenario, "subject_declaration": self.compatible})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subject_ref"]["id"], "cs_ai_01")
        invalid = copy.deepcopy(self.compatible)
        invalid["subject"].pop("boundaries")
        response = client.post("/api/v1/evaluate", json={"scenario": scenario, "subject_declaration": invalid})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["error_code"], "SUBJECT_REQUIRED_FIELD_MISSING")

    def test_load_json_file(self):
        normalized, _ = load_declaration(EXAMPLE)
        self.assertEqual(normalized["subject"]["local_subject_id"], "cs_ai_01")


if __name__ == "__main__":
    unittest.main()
