"""
Open Food Facts provider.

No API key required.
Nutrition values are per 100g (_100g suffix fields preferred).
"""

import requests

from .base import FoodProvider
from ..services.normalize import (
    safe_float, parse_serving_grams, make_search_result, make_food_details,
)

TIMEOUT = 20   # OFF search can be slow; give it more room
SEARCH_URL  = "https://world.openfoodfacts.org/cgi/search.pl"
PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"


class OpenFoodFactsProvider(FoodProvider):
    source = "openfoodfacts"

    # ── Public interface ───────────────────────────────────────────────────────

    def search(self, query: str) -> list[dict]:
        params = {
            "search_terms":  query,
            "search_simple": 1,
            "action":        "process",
            "json":          1,
            "page_size":     20,
        }
        resp = requests.get(SEARCH_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()

        products = resp.json().get("products") or []
        return [self._norm_search(p) for p in products if p.get("code")]

    def get_details(self, food_id: str) -> dict:
        url  = PRODUCT_URL.format(barcode=food_id)
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()

        data = resp.json()
        if data.get("status") != 1 or not data.get("product"):
            raise ValueError(f"Product not found: {food_id}")

        return self._norm_details(data["product"], food_id)

    def search_by_barcode(self, barcode: str) -> dict | None:
        try:
            return self.get_details(barcode)
        except (ValueError, requests.RequestException):
            return None

    # ── Private helpers ────────────────────────────────────────────────────────

    def _norm_search(self, p: dict) -> dict:
        n = p.get("nutriments") or {}
        return make_search_result(
            source=self.source,
            food_id=p.get("code") or "",
            name=p.get("product_name") or p.get("generic_name") or "Unknown",
            brand=p.get("brands") or None,
            image_url=p.get("image_front_small_url") or p.get("image_url") or None,
            serving_hint="per 100g",
            nutrients={
                "caloriesKcal": safe_float(n.get("energy-kcal_100g") or n.get("energy-kcal")),
                "proteinG":     safe_float(n.get("proteins_100g")      or n.get("proteins")),
                "carbsG":       safe_float(n.get("carbohydrates_100g") or n.get("carbohydrates")),
                "fatG":         safe_float(n.get("fat_100g")           or n.get("fat")),
            },
        )

    def _norm_details(self, p: dict, barcode: str) -> dict:
        n = p.get("nutriments") or {}

        extra_servings = []
        native_serving = p.get("serving_size")
        if native_serving:
            grams = parse_serving_grams(native_serving)
            if grams:
                extra_servings.append({"label": native_serving, "grams": grams})

        return make_food_details(
            source=self.source,
            food_id=p.get("code") or barcode,
            name=p.get("product_name") or p.get("generic_name") or "Unknown",
            brand=p.get("brands") or None,
            image_url=p.get("image_front_url") or p.get("image_url") or None,
            serving_sizes=extra_servings,
            nutrients={
                "caloriesKcal": safe_float(n.get("energy-kcal_100g") or n.get("energy-kcal")),
                "proteinG":     safe_float(n.get("proteins_100g")      or n.get("proteins")),
                "carbsG":       safe_float(n.get("carbohydrates_100g") or n.get("carbohydrates")),
                "fatG":         safe_float(n.get("fat_100g")           or n.get("fat")),
            },
            basis="per_100g",
        )
