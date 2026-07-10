import copy
import unittest

from simulate import load_scenario, run_simulation


class TestSimulationDeterminism(unittest.TestCase):
    def test_same_seed_produces_identical_refund_output(self):
        scenario = load_scenario("examples/scenario_refund_conflict.json")

        first = run_simulation(copy.deepcopy(scenario), seed=42)
        second = run_simulation(copy.deepcopy(scenario), seed=42)

        self.assertEqual(first, second)
        self.assertEqual(first["timestamp"], "2026-07-04T00:00:00Z")
        self.assertTrue(first["runestone"]["runestone_id"].startswith("RS_"))
        self.assertTrue(first["causal_chain"]["causal_chain_id"].startswith("CC_"))

    def test_different_seed_keeps_structure_but_changes_path(self):
        scenario = load_scenario("examples/scenario_refund_conflict.json")

        seed_42 = run_simulation(copy.deepcopy(scenario), seed=42)
        seed_43 = run_simulation(copy.deepcopy(scenario), seed=43)

        self.assertEqual(seed_42["simulation_id"], seed_43["simulation_id"])
        self.assertEqual(set(seed_42.keys()), set(seed_43.keys()))
        self.assertNotEqual(
            seed_42["runestone"]["runestone_id"],
            seed_43["runestone"]["runestone_id"],
        )


if __name__ == "__main__":
    unittest.main()
