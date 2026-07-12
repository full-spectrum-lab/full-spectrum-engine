import json
import os
import unittest
import tempfile

from src.governance_chain import build_chain
from src.governance_chain import validator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KINDS = ("governance-event", "canonical-context", "cell-manifest", "output-envelope", "enterprise-writeback")


class TestGovernanceChainAdapters(unittest.TestCase):
    def test_all_adapters_match_golden_and_schema(self):
        for adapter_id in ("ecommerce", "logistics", "knowledge_conflict"):
            with self.subTest(adapter=adapter_id):
                path = os.path.join(ROOT, "examples", "governance_chain", f"raw-input.{adapter_id}.json")
                with open(path, encoding="utf-8-sig") as handle:
                    raw = json.load(handle)
                artifacts, _, _ = build_chain(raw)
                for kind in KINDS:
                    schema_name = validator.map_schema_for_filename(kind + ".json")
                    ok, errors = validator.validate_instance(artifacts[kind], validator.load_schema(schema_name))
                    self.assertTrue(ok, errors)
                    golden = os.path.join(ROOT, "tests", "fixtures", f"expected_{adapter_id}_chain", f"{kind}.{adapter_id}.json")
                    with open(golden, encoding="utf-8-sig") as handle:
                        self.assertEqual(artifacts[kind], json.load(handle))

                relationships = artifacts["enterprise-writeback"]["relationships"]
                self.assertTrue(any(item["target_type"] == "output_envelope" for item in relationships))
                self.assertEqual(artifacts["output-envelope"]["policy_evaluation"]["policy_version"], "1.0.0")

    def test_replay_with_explicit_policy_version(self):
        source = os.path.join(ROOT, "src", "governance_chain", "policies", "governance-rules.v1.json")
        with open(source, encoding="utf-8-sig") as handle:
            policy = json.load(handle)
        policy["version"] = "1.0.0-replay"
        policy["rules"][0]["risk_level"] = "critical"
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = os.path.join(tmp, "replay-policy.json")
            with open(policy_path, "w", encoding="utf-8") as handle:
                json.dump(policy, handle)
            input_path = os.path.join(ROOT, "examples", "governance_chain", "raw-input.ecommerce.json")
            with open(input_path, encoding="utf-8-sig") as handle:
                raw = json.load(handle)
            artifacts, _, _ = build_chain(raw, policy_path=policy_path)
        self.assertEqual(artifacts["enterprise-writeback"]["risk_level"], "critical")
        self.assertEqual(artifacts["output-envelope"]["policy_evaluation"]["policy_version"], "1.0.0-replay")


if __name__ == "__main__":
    unittest.main()
