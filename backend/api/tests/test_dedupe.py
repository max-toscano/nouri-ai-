"""
Tests for the dedupe logic in food_router.
"""

from django.test import TestCase

from api.services.food_router import dedupe


def item(source, name, brand=None):
    return {
        "source": source, "id": "1", "name": name, "brand": brand,
        "imageUrl": None, "matchConfidence": 0.5, "servingHint": None,
    }


class DedupeTest(TestCase):

    def test_exact_name_duplicate_removed(self):
        items = [
            item("fatsecret", "Chicken Breast"),
            item("usda",      "Chicken Breast"),
        ]
        result, removed = dedupe(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(removed, 1)
        self.assertEqual(result[0]["source"], "fatsecret")   # first (highest priority) kept

    def test_different_foods_both_kept(self):
        items = [
            item("fatsecret", "Chicken Breast"),
            item("usda",      "Chicken Thigh"),
        ]
        result, removed = dedupe(items)
        self.assertEqual(len(result), 2)
        self.assertEqual(removed, 0)

    def test_different_brands_both_kept(self):
        items = [
            item("fatsecret", "Chicken", "Tyson"),
            item("usda",      "Chicken", "Perdue"),
        ]
        result, removed = dedupe(items)
        self.assertEqual(len(result), 2)

    def test_same_name_no_brand_deduped(self):
        items = [
            item("fatsecret", "Banana", None),
            item("usda",      "Banana", None),
        ]
        result, removed = dedupe(items)
        self.assertEqual(len(result), 1)

    def test_punctuation_ignored(self):
        items = [
            item("fatsecret", "Chicken, Grilled"),
            item("usda",      "Chicken Grilled"),
        ]
        result, removed = dedupe(items)
        self.assertEqual(len(result), 1)

    def test_case_insensitive(self):
        items = [
            item("fatsecret", "Greek Yogurt"),
            item("off",       "GREEK YOGURT"),
        ]
        result, removed = dedupe(items)
        self.assertEqual(len(result), 1)

    def test_empty_list(self):
        result, removed = dedupe([])
        self.assertEqual(result, [])
        self.assertEqual(removed, 0)

    def test_order_preserved(self):
        items = [
            item("fatsecret",    "Apple"),
            item("usda",         "Banana"),
            item("openfoodfacts","Cherry"),
        ]
        result, _ = dedupe(items)
        self.assertEqual([r["name"] for r in result], ["Apple", "Banana", "Cherry"])
