"""
External API calls — all Open Food Facts communication lives here.
Views must not call requests directly; they call these functions instead.
"""

import requests

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

TIMEOUT = 10  # seconds


def search_foods(query: str) -> list[dict]:
    """
    Search Open Food Facts and return a normalized list of results.
    Raises requests.RequestException on network / HTTP errors.
    """
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 20,
    }

    response = requests.get(OFF_SEARCH_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()
    products = data.get("products", [])

    if not isinstance(products, list):
        return []

    return [_normalize_search_result(p) for p in products]


def get_food_details(barcode: str) -> dict:
    """
    Fetch a single product by barcode and return normalized nutrition details.
    Raises ValueError if the product is not found.
    Raises requests.RequestException on network / HTTP errors.
    """
    url = OFF_PRODUCT_URL.format(barcode=barcode)
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()

    if data.get("status") != 1 or not data.get("product"):
        raise ValueError(f"Product not found for barcode: {barcode}")

    return _normalize_product_details(data["product"], barcode)


# ── Private helpers ────────────────────────────────────────────────────────────

def _normalize_search_result(product: dict) -> dict:
    n = product.get("nutriments") or {}
    return {
        "id": product.get("code") or "",
        "name": product.get("product_name") or product.get("generic_name") or "Unknown",
        "brand": product.get("brands") or "",
        "imageUrl": product.get("image_front_small_url") or product.get("image_url") or "",
        "caloriesKcal": _num(n.get("energy-kcal_100g") or n.get("energy-kcal")),
        "proteinG":     _num(n.get("proteins_100g")      or n.get("proteins")),
        "carbsG":       _num(n.get("carbohydrates_100g") or n.get("carbohydrates")),
        "fatG":         _num(n.get("fat_100g")           or n.get("fat")),
    }


def _normalize_product_details(product: dict, barcode: str) -> dict:
    n = product.get("nutriments") or {}

    return {
        "id": product.get("code") or barcode,
        "name": product.get("product_name") or product.get("generic_name") or "Unknown",
        "brand": product.get("brands") or "",
        "imageUrl": product.get("image_front_url") or product.get("image_url") or "",
        "caloriesKcal": _num(n.get("energy-kcal_100g") or n.get("energy-kcal")),
        "proteinG":     _num(n.get("proteins_100g")       or n.get("proteins")),
        "carbsG":       _num(n.get("carbohydrates_100g")  or n.get("carbohydrates")),
        "fatG":         _num(n.get("fat_100g")            or n.get("fat")),
        "servingSize":  product.get("serving_size"),
    }


def _num(value) -> float:
    """Safely coerce a nutriment value to float, defaulting to 0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
