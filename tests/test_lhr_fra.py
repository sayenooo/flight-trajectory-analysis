"""Focused checks of dangerous failure modes: false cleaning and wrong geometry."""
import sys
import unittest
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import haversine_distances

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from prepare_lhr_fra import find_short_spikes
from build_lhr_fra_matrix import unit_sphere, hausdorff_km, EARTH_KM


class TrajectoryChecks(unittest.TestCase):
    def test_removes_impossible_single_and_two_point_bursts(self):
        self.assertEqual(find_short_spikes(np.array([[51, 0], [20, 106], [51, .02]]), np.array([0, 5, 10])).tolist(), [False, True, False])
        self.assertEqual(find_short_spikes(np.array([[51, 0], [20, 106], [20, 106.01], [51, .03]]), np.array([0, 5, 6, 12])).tolist(), [False, True, True, False])

    def test_keeps_plausible_turn_and_does_not_bridge_long_gap(self):
        self.assertFalse(find_short_spikes(np.array([[51, 0], [51.01, .02], [51.03, .01]]), np.array([0, 10, 20])).any())
        self.assertFalse(find_short_spikes(np.array([[51, 0], [20, 106], [51, .02]]), np.array([0, 100, 200])).any())

    def test_exact_metric_matches_dense_haversine_across_dateline(self):
        a = np.array([[51, 0], [50, 8], [10, 179.9], [89, 40]])
        b = np.array([[51.1, .1], [50.1, 8.1], [10, -179.9], [88, -140]])
        dense = haversine_distances(np.radians(a), np.radians(b)) * EARTH_KM
        expected = max(dense.min(axis=0).max(), dense.min(axis=1).max())
        self.assertAlmostEqual(hausdorff_km(unit_sphere(a), unit_sphere(b)), expected, places=7)
        self.assertAlmostEqual(hausdorff_km(unit_sphere(a), unit_sphere(a)), 0, places=10)


if __name__ == '__main__':
    unittest.main()
