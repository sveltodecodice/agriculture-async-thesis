import unittest

from core.soil_type import select_initial_soil


class SoilSelectionTests(unittest.TestCase):
    def test_three_default_fields_are_distinct(self):
        soils = [
            select_initial_soil(field, "random", 2026)
            for field in ("field_a", "field_b", "field_c")
        ]
        self.assertEqual(len(set(soils)), 3)

    def test_layout_is_reproducible(self):
        first = select_initial_soil("field_a", "random", 2026)
        second = select_initial_soil("field_a", "random", 2026)
        self.assertEqual(first, second)

    def test_explicit_soil_is_preserved(self):
        self.assertEqual(
            select_initial_soil("field_a", "Argilloso", 2026),
            "Argilloso",
        )


if __name__ == "__main__":
    unittest.main()
