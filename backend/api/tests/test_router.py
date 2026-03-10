"""
Tests for the food_router: fallback behavior when a provider fails,
and that all providers are called on a normal text search.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

import api.services.food_router as router


def _item(source, name, brand=None):
    return {
        "source": source, "id": "1", "name": name, "brand": brand,
        "imageUrl": None, "matchConfidence": 0.5, "servingHint": None,
    }


class RouterFallbackTest(TestCase):

    @patch.object(router, "_fatsecret")
    @patch.object(router, "_usda")
    @patch.object(router, "_off")
    def test_continues_when_fatsecret_fails(self, mock_off, mock_usda, mock_fatsecret):
        mock_fatsecret.search.side_effect = Exception("FatSecret down")
        mock_usda.search.return_value     = [_item("usda", "Chicken Breast")]
        mock_off.search.return_value      = []

        result = router.search("chicken breast")

        self.assertIn("usda", result["meta"]["providersSucceeded"])
        self.assertNotIn("fatsecret", result["meta"]["providersSucceeded"])
        self.assertIn("fatsecret", result["meta"]["providersAttempted"])
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["source"], "usda")

    @patch.object(router, "_fatsecret")
    @patch.object(router, "_usda")
    @patch.object(router, "_off")
    def test_all_providers_called_on_text_search(self, mock_off, mock_usda, mock_fatsecret):
        mock_fatsecret.search.return_value = []
        mock_usda.search.return_value      = []
        mock_off.search.return_value       = []

        router.search("apple")

        mock_fatsecret.search.assert_called_once_with("apple")
        mock_usda.search.assert_called_once_with("apple")
        mock_off.search.assert_called_once_with("apple")

    @patch.object(router, "_fatsecret")
    @patch.object(router, "_usda")
    @patch.object(router, "_off")
    def test_all_providers_fail_returns_empty(self, mock_off, mock_usda, mock_fatsecret):
        mock_fatsecret.search.side_effect = Exception("down")
        mock_usda.search.side_effect      = Exception("down")
        mock_off.search.side_effect       = Exception("down")

        result = router.search("xyz")

        self.assertEqual(result["results"], [])
        self.assertEqual(result["meta"]["providersSucceeded"], [])

    @patch.object(router, "_fatsecret")
    @patch.object(router, "_usda")
    @patch.object(router, "_off")
    def test_barcode_query_stops_at_first_hit(self, mock_off, mock_usda, mock_fatsecret):
        detail = {"source": "openfoodfacts", "id": "12345678", "name": "Test Bar",
                  "brand": None, "imageUrl": None, "servingSizes": [], "nutrients": {},
                  "basis": "per_100g"}
        mock_off.search_by_barcode.return_value      = detail
        mock_fatsecret.search_by_barcode.return_value = None
        mock_usda.search_by_barcode.return_value      = None

        result = router.search("12345678")

        mock_off.search_by_barcode.assert_called_once()
        mock_fatsecret.search_by_barcode.assert_not_called()   # stopped after OFF hit
        self.assertEqual(len(result["results"]), 1)
