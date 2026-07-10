#!/usr/bin/env python3
"""Unit tests for the awareness bomb governance mechanism."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.state import CivilizationState, project_to_feasible
from src.governance.bomb import AwarenessBombEngine, BombStage


class TestBomb(unittest.TestCase):
    def test_project_to_feasible(self):
        """Project infeasible state back into feasible space."""
        state = CivilizationState(0.1, 0.9, 0.1)
        self.assertFalse(state.is_feasible())

        projected = project_to_feasible(state)
        self.assertTrue(projected.is_feasible())
        self.assertAlmostEqual(projected.survival, 0.3)
        self.assertAlmostEqual(projected.coordination, 0.8)
        self.assertAlmostEqual(projected.meaning, 0.2)

    def test_bomb_trigger_consecutive_failures(self):
        """Trigger after consecutive infeasible checks."""
        engine = AwarenessBombEngine()
        state = CivilizationState(0.1, 0.9, 0.1)

        for i in range(3):
            triggered, reason = engine.check_trigger(state, purity=0.5, rigidity=0.5)
            if i < 2:
                self.assertFalse(triggered)
            else:
                self.assertTrue(triggered)
                self.assertIn("consecutive", reason.lower())

    def test_bomb_trigger_rigidity(self):
        """Trigger immediately on excessive rigidity."""
        engine = AwarenessBombEngine()
        state = CivilizationState(0.5, 0.5, 0.5)

        triggered, reason = engine.check_trigger(state, purity=0.8, rigidity=0.9)
        self.assertTrue(triggered)
        self.assertIn("rigidity", reason.lower())

    def test_bomb_detonate(self):
        """Detonation should project state and record trigger count."""
        engine = AwarenessBombEngine()
        state = CivilizationState(0.1, 0.9, 0.1)

        detonated = engine.detonate(state, "test detonation")
        self.assertTrue(detonated.is_feasible())
        self.assertEqual(engine.state.stage, BombStage.DETONATED)
        self.assertEqual(engine.state.trigger_count, 1)

    def test_bomb_recover(self):
        """Recovery should move stage from detonation to new equilibrium."""
        engine = AwarenessBombEngine()
        state = CivilizationState(0.5, 0.5, 0.5)

        engine.detonate(state, "test recovery")
        recovered, stage = engine.recover(state, 0)
        self.assertEqual(stage, BombStage.QUANTUM_SUPERPOSITION)

        recovered, stage = engine.recover(state, 10)
        self.assertEqual(stage, BombStage.NEW_EQUILIBRIUM)


if __name__ == "__main__":
    unittest.main()
