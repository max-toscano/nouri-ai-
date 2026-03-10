"""
Tests for USDA nutrient extraction (_extract_nutrients).
Covers branded (flat) format, SR Legacy (nested) format, mixed, and edge cases.
"""

from django.test import TestCase

from api.providers.usda import _extract_nutrients


class USDANormalizeTest(TestCase):

    def test_branded_format(self):
        nutrients = [
            {"nutrientNumber": "208", "nutrientName": "Energy",  "value": 250.0},
            {"nutrientNumber": "203", "nutrientName": "Protein", "value": 25.0},
        ]
        result = _extract_nutrients(nutrients)
        self.assertEqual(result["208"], 250.0)
        self.assertEqual(result["203"], 25.0)

    def test_sr_legacy_format(self):
        nutrients = [
            {"nutrient": {"number": "208", "name": "Energy"},           "amount": 120.0},
            {"nutrient": {"number": "204", "name": "Total lipid (fat)"}, "amount": 3.5},
        ]
        result = _extract_nutrients(nutrients)
        self.assertEqual(result["208"], 120.0)
        self.assertEqual(result["204"], 3.5)

    def test_mixed_formats(self):
        nutrients = [
            {"nutrientNumber": "208", "value": 300.0},
            {"nutrient": {"number": "203"}, "amount": 20.0},
        ]
        result = _extract_nutrients(nutrients)
        self.assertEqual(result["208"], 300.0)
        self.assertEqual(result["203"], 20.0)

    def test_empty_list_returns_empty_dict(self):
        self.assertEqual(_extract_nutrients([]), {})

    def test_invalid_value_skipped(self):
        nutrients = [{"nutrientNumber": "208", "value": "not_a_number"}]
        result = _extract_nutrients(nutrients)
        self.assertNotIn("208", result)

    def test_none_value_skipped(self):
        nutrients = [{"nutrientNumber": "208", "value": None}]
        result = _extract_nutrients(nutrients)
        self.assertNotIn("208", result)

    def test_missing_number_skipped(self):
        nutrients = [{"nutrientName": "Energy", "value": 200.0}]
        result = _extract_nutrients(nutrients)
        self.assertEqual(result, {})
