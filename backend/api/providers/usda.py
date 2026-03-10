"""
USDA FoodData Central provider.

Requires USDA_API_KEY in settings (defaults to DEMO_KEY).
Searches across Survey/FNDDS, Foundation, SR Legacy, and Branded data sets.
Handles both branded (flat) and SR Legacy/Foundation (nested) nutrient formats.
"""

import requests
from django.conf import settings

from .base import FoodProvider
from ..services.normalize import safe_float, make_search_result, make_food_details

TIMEOUT = 8
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
FOOD_URL   = "https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"

# Nutrient numbers that map to our four core macros
_ENERGY  = "208"   # Energy, kcal
_PROTEIN = "203"   # Protein
_CARBS   = "205"   # Carbohydrate, by difference
_FAT     = "204"   # Total lipid (fat)

# All data types — gives broadest coverage including common/generic foods
_DATA_TYPES = ["Survey (FNDDS)", "Foundation", "SR Legacy", "Branded"]


class USDAProvider(FoodProvider):
    source = "usda"

    # ── Public interface ───────────────────────────────────────────────────────

    def search(self, query: str) -> list[dict]:
        params = {
            "query":    query,
            "api_key":  self._key,
            "pageSize": 20,
        }
        # Send dataType as repeated params so all types are searched
        resp = requests.get(
            SEARCH_URL,
            params=params,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()

        foods = resp.json().get("foods") or []
        return [self._norm_search(f) for f in foods]

    def get_details(self, food_id: str) -> dict:
        url  = FOOD_URL.format(fdc_id=food_id)
        resp = requests.get(url, params={"api_key": self._key}, timeout=TIMEOUT)

        if resp.status_code == 404:
            raise ValueError(f"Food not found: {food_id}")
        resp.raise_for_status()

        data = resp.json()
        if not data.get("fdcId"):
            raise ValueError(f"Food not found: {food_id}")

        return self._norm_details(data)

    def search_by_barcode(self, barcode: str) -> dict | None:
        """USDA doesn't have a barcode endpoint; search Branded data as fallback."""
        try:
            resp = requests.get(
                SEARCH_URL,
                params={"query": barcode, "api_key": self._key,
                        "pageSize": 5, "dataType": "Branded"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            foods = resp.json().get("foods") or []
            if foods:
                return self.get_details(str(foods[0]["fdcId"]))
        except Exception:
            pass
        return None

    # ── Private helpers ────────────────────────────────────────────────────────

    @property
    def _key(self) -> str:
        return getattr(settings, "USDA_API_KEY", "DEMO_KEY")

    def _norm_search(self, f: dict) -> dict:
        nutrients = _extract_nutrients(f.get("foodNutrients") or [])
        return make_search_result(
            source=self.source,
            food_id=str(f.get("fdcId") or ""),
            name=f.get("description") or "Unknown",
            brand=f.get("brandOwner") or f.get("brandName") or None,
            serving_hint="per 100g",
            nutrients={
                "caloriesKcal": nutrients.get(_ENERGY),
                "proteinG":     nutrients.get(_PROTEIN),
                "carbsG":       nutrients.get(_CARBS),
                "fatG":         nutrients.get(_FAT),
            },
        )

    def _norm_details(self, f: dict) -> dict:
        nutrients = _extract_nutrients(f.get("foodNutrients") or [])

        # Build native serving sizes from foodPortions (USDA household measures)
        extra_servings = []
        for portion in (f.get("foodPortions") or [])[:4]:
            label = (
                portion.get("portionDescription")
                or (portion.get("measureUnit") or {}).get("name")
                or ""
            )
            grams = safe_float(portion.get("gramWeight"))
            if label and grams:
                extra_servings.append({"label": label, "grams": grams})

        return make_food_details(
            source=self.source,
            food_id=str(f.get("fdcId") or ""),
            name=f.get("description") or "Unknown",
            brand=f.get("brandOwner") or f.get("brandName") or None,
            serving_sizes=extra_servings,
            nutrients={
                "caloriesKcal": nutrients.get(_ENERGY),
                "proteinG":     nutrients.get(_PROTEIN),
                "carbsG":       nutrients.get(_CARBS),
                "fatG":         nutrients.get(_FAT),
            },
            basis="per_100g",
        )


def _extract_nutrients(food_nutrients: list) -> dict[str, float]:
    """
    USDA returns foodNutrients in two formats:

    Branded foods (flat):
        { "nutrientNumber": "208", "value": 250.0, ... }

    Foundation / SR Legacy (nested):
        { "nutrient": { "number": "208", ... }, "amount": 250.0 }

    Returns a dict mapping nutrient number (str) → float amount.
    """
    result: dict[str, float] = {}

    for item in food_nutrients:
        number: str | None = None
        value:  float | None = None

        raw = item.get("nutrientNumber")
        if raw is not None:
            number = str(raw)
            value  = item.get("value")

        if not number:
            nutrient = item.get("nutrient") or {}
            raw = nutrient.get("number")
            if raw is not None:
                number = str(raw)
            value = item.get("amount")

        if number and value is not None:
            try:
                result[number] = float(value)
            except (TypeError, ValueError):
                pass

    return result
