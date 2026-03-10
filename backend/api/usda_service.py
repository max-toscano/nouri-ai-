"""
USDA FoodData Central API service.

All communication with https://api.nal.usda.gov goes here.
The API key is read from Django settings (loaded from .env) and
is never forwarded to the frontend.

Nutrient reference numbers used:
  203 — Protein (g)
  204 — Total lipid / Fat (g)
  205 — Carbohydrate, by difference (g)
  208 — Energy (kcal)
"""

import requests
from django.conf import settings

USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_FOOD_URL   = "https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"

TIMEOUT = 10  # seconds

# USDA nutrient numbers
_ENERGY  = "208"
_PROTEIN = "203"
_CARBS   = "205"
_FAT     = "204"


def search_usda_foods(query: str) -> list[dict]:
    """
    Search USDA FoodData Central and return a normalized list of results.

    Raises:
        requests.RequestException: on network or HTTP errors.
    """
    params = {
        "query":    query,
        "api_key":  settings.USDA_API_KEY,
        "pageSize": 20,
    }

    response = requests.get(USDA_SEARCH_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    data  = response.json()
    foods = data.get("foods", [])

    if not isinstance(foods, list):
        return []

    return [_normalize_search_result(f) for f in foods]


def get_usda_food_details(fdc_id: str) -> dict:
    """
    Fetch a single food item by fdcId and return normalized nutrition details.

    Raises:
        ValueError:                  if the food is not found (404).
        requests.RequestException:   on network or other HTTP errors.
    """
    url    = USDA_FOOD_URL.format(fdc_id=fdc_id)
    params = {"api_key": settings.USDA_API_KEY}

    response = requests.get(url, params=params, timeout=TIMEOUT)

    if response.status_code == 404:
        raise ValueError(f"Food not found for fdcId: {fdc_id}")

    response.raise_for_status()

    data = response.json()

    # Sanity-check that we got a real food object back
    if not data.get("fdcId"):
        raise ValueError(f"Food not found for fdcId: {fdc_id}")

    return _normalize_food_details(data)


# ── Private helpers ────────────────────────────────────────────────────────────

def _normalize_search_result(food: dict) -> dict:
    return {
        "id":         str(food.get("fdcId") or ""),
        "name":       food.get("description") or "Unknown",
        "brand":      food.get("brandOwner") or food.get("brandName") or "",
        "dataSource": "usda",
    }


def _normalize_food_details(food: dict) -> dict:
    nutrients = _extract_nutrients(food.get("foodNutrients") or [])

    return {
        "id":           str(food.get("fdcId") or ""),
        "name":         food.get("description") or "Unknown",
        "brand":        food.get("brandOwner") or food.get("brandName") or "",
        "caloriesKcal": nutrients.get(_ENERGY,  0.0),
        "proteinG":     nutrients.get(_PROTEIN, 0.0),
        "carbsG":       nutrients.get(_CARBS,   0.0),
        "fatG":         nutrients.get(_FAT,     0.0),
        "dataSource":   "usda",
    }


def _extract_nutrients(food_nutrients: list) -> dict:
    """
    USDA returns foodNutrients in two formats depending on food type:

    Branded foods:
        { "nutrientNumber": "208", "nutrientName": "Energy", "value": 250.0, ... }

    Foundation / SR Legacy foods:
        { "nutrient": { "number": "208", "name": "Energy", ... }, "amount": 250.0 }

    Returns a dict mapping nutrient number (str) → float amount.
    """
    result: dict[str, float] = {}

    for item in food_nutrients:
        number: str | None = None
        value:  float | None = None

        # Branded food format
        raw_number = item.get("nutrientNumber")
        if raw_number is not None:
            number = str(raw_number)
            value  = item.get("value")

        # Foundation / SR Legacy format
        if not number:
            nutrient = item.get("nutrient") or {}
            raw_number = nutrient.get("number")
            if raw_number is not None:
                number = str(raw_number)
            value = item.get("amount")

        if number and value is not None:
            try:
                result[number] = float(value)
            except (TypeError, ValueError):
                pass

    return result
