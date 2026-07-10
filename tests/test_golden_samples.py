import copy
import json
import unittest
from pathlib import Path

from simulate import load_scenario, run_simulation


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "test-records" / "v0.8-public-beta"


class TestGoldenSamples(unittest.TestCase):
    def test_refund_seed42_matches_golden_sample(self):
        scenario = load_scenario("examples/scenario_refund_conflict.json")
        actual = run_simulation(copy.deepcopy(scenario), seed=42)
        golden = json.loads((GOLDEN_DIR / "golden_refund_seed42.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, golden)

    def test_knowledge_seed42_matches_golden_sample(self):
        scenario = load_scenario("examples/scenario_knowledge_conflict.json")
        actual = run_simulation(copy.deepcopy(scenario), seed=42)
        golden = json.loads((GOLDEN_DIR / "golden_knowledge_seed42.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, golden)

    def test_logistics_coldchain_seed42_matches_golden_sample(self):
        scenario = load_scenario("examples/scenario_logistics_coldchain.json")
        actual = run_simulation(copy.deepcopy(scenario), seed=42)
        golden = json.loads((GOLDEN_DIR / "golden_logistics_coldchain_seed42.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, golden)


if __name__ == "__main__":
    unittest.main()
