"""
Shared normalization helpers used by all providers.
"""

import re

_STANDARD_SERVINGS = [
    {"label": "100 g",  "grams": 100.0},
    {"label": "1 oz",   "grams": 28.3495},
]


def safe_float(value, default=None) -> float | None:
    """Coerce value to float; return default if not possible."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_serving_grams(serving_str: str | None) -> float | None:
    """
    Extract gram weight from a serving size string like "30g" or "1 cup (240g)".
    Returns None if no gram value is found.
    """
    if not serving_str:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", str(serving_str), re.I)
    return float(m.group(1)) if m else None


def standard_servings(extra: list[dict] | None = None) -> list[dict]:
    """
    Return the two standard serving sizes (100g + 1oz), optionally
    prepended with provider-native servings.
    Avoids duplicating entries that are already close to 100g or 28g.
    """
    result = list(extra or [])
    for std in _STANDARD_SERVINGS:
        if not any(abs(s["grams"] - std["grams"]) < 2 for s in result):
            result.append(std)
    return result


def make_search_result(
    source: str,
    food_id: str,
    name: str,
    brand: str | None = None,
    image_url: str | None = None,
    match_confidence: float = 0.5,
    serving_hint: str | None = None,
    nutrients: dict | None = None,
) -> dict:
    n = nutrients or {}
    return {
        "source":          source,
        "id":              str(food_id),
        "name":            name or "Unknown",
        "brand":           brand or None,
        "imageUrl":        image_url or None,
        "matchConfidence": match_confidence,
        "servingHint":     serving_hint,
        # Preview nutrition (per 100g where available; null if unknown)
        "caloriesKcal":    n.get("caloriesKcal"),
        "proteinG":        n.get("proteinG"),
        "carbsG":          n.get("carbsG"),
        "fatG":            n.get("fatG"),
    }


def make_food_details(
    source: str,
    food_id: str,
    name: str,
    brand: str | None = None,
    image_url: str | None = None,
    serving_sizes: list[dict] | None = None,
    nutrients: dict | None = None,
    basis: str = "unknown",
) -> dict:
    n = nutrients or {}
    return {
        "source":       source,
        "id":           str(food_id),
        "name":         name or "Unknown",
        "brand":        brand or None,
        "imageUrl":     image_url or None,
        "servingSizes": standard_servings(serving_sizes),
        "nutrients": {
            "caloriesKcal": n.get("caloriesKcal"),
            "proteinG":     n.get("proteinG"),
            "carbsG":       n.get("carbsG"),
            "fatG":         n.get("fatG"),
        },
        "basis": basis,
    }
