import unittest

from core.seed_matcher import evaluate_soil_ok, find_top_3_seeds


class SeedMatcherTests(unittest.TestCase):
    def test_soil_labels_are_normalized(self):
        seed = {"ideal_soil": "Franco-Sabbioso"}
        self.assertTrue(evaluate_soil_ok(seed, "franco sabbioso"))

    def test_season_is_first_priority(self):
        candidates = find_top_3_seeds(28.0, "summer", "Argilloso")
        self.assertTrue(all("summer" in [s.lower() for s in seed["seasons"]] for seed in candidates))

    def test_soil_is_second_priority(self):
        candidates = find_top_3_seeds(28.0, "summer", "Franco-Argilloso")
        self.assertEqual(candidates[0]["ideal_soil"].lower(), "franco-argilloso")


if __name__ == "__main__":
    unittest.main()
