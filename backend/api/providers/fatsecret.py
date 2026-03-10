"""
FatSecret Platform API provider.

Auth: OAuth 2.0 client_credentials flow (FatSecret REST API, 2022+).
Token is cached in memory per process and refreshed automatically.

Scope "basic" covers food search and food.get.
"""

import logging
import re
import threading
import time

import requests
from django.conf import settings

from .base import FoodProvider
from ..services.normalize import safe_float, make_search_result, make_food_details

log = logging.getLogger(__name__)

TIMEOUT     = 8
TOKEN_URL   = "https://oauth.fatsecret.com/connect/token"
API_URL     = "https://platform.fatsecret.com/rest/server.api"


class FatSecretProvider(FoodProvider):
    source = "fatsecret"

    def __init__(self):
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    # ── Public interface ───────────────────────────────────────────────────────

    def search(self, query: str) -> list[dict]:
        data = self._call("foods.search", {
            "search_expression": query,
            "max_results":       20,
        })
        container = data.get("foods") or {}
        raw = container.get("food") or []
        if isinstance(raw, dict):   # single result returns a dict, not a list
            raw = [raw]
        return [self._norm_search(f) for f in raw]

    def get_details(self, food_id: str) -> dict:
        data = self._call("food.get.v4", {"food_id": food_id})
        food = data.get("food")
        if not food:
            raise ValueError(f"Food not found: {food_id}")
        return self._norm_details(food)

    def search_by_barcode(self, barcode: str) -> dict | None:
        try:
            data = self._call("food.find_id_for_barcode", {"barcode": barcode})
            fid  = (data.get("food_id") or {}).get("value")
            if fid:
                return self.get_details(str(fid))
        except Exception as exc:
            log.debug("FatSecret barcode lookup failed: %s", exc)
        return None

    # ── OAuth token management ─────────────────────────────────────────────────

    @property
    def _client_id(self) -> str:
        return getattr(settings, "FATSECRET_CLIENT_ID", "")

    @property
    def _client_secret(self) -> str:
        return getattr(settings, "FATSECRET_CLIENT_SECRET", "")

    def _get_token(self) -> str:
        with self._lock:
            if self._token and time.monotonic() < self._expires_at - 60:
                return self._token

            resp = requests.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials", "scope": "basic"},
                auth=(self._client_id, self._client_secret),
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()

            self._token      = body["access_token"]
            self._expires_at = time.monotonic() + body.get("expires_in", 86400)
            return self._token

    def _call(self, method: str, params: dict | None = None) -> dict:
        token   = self._get_token()
        payload = {"method": method, "format": "json", **(params or {})}
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(API_URL, params=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # ── Normalization ──────────────────────────────────────────────────────────

    def _norm_search(self, f: dict) -> dict:
        # food_description: "Per 100g - Calories: 231kcal | Fat: 14.31g | Carbs: 0.37g | Prot: 25.69g"
        desc = f.get("food_description") or ""
        hint = desc.split("|")[0].strip() if desc else None

        return make_search_result(
            source=self.source,
            food_id=str(f.get("food_id") or ""),
            name=f.get("food_name") or "Unknown",
            brand=f.get("brand_name") or None,
            serving_hint=hint or None,
            nutrients=_parse_description_nutrients(desc),
        )

    def _norm_details(self, f: dict) -> dict:
        servings_raw = (f.get("servings") or {}).get("serving") or []
        if isinstance(servings_raw, dict):
            servings_raw = [servings_raw]

        extra_servings: list[dict] = []
        # We'll normalize all macros to per-100g using the first gram-based serving
        nutrients_per_100g: dict | None = None

        for s in servings_raw:
            grams = safe_float(s.get("metric_serving_amount"))
            unit  = (s.get("metric_serving_unit") or "").lower()

            if not (grams and unit == "g"):
                continue

            label = s.get("serving_description") or "serving"
            extra_servings.append({"label": label, "grams": grams})

            # Use the first valid gram-based serving to derive per-100g nutrients
            if nutrients_per_100g is None:
                factor = 100.0 / grams
                nutrients_per_100g = {
                    "caloriesKcal": _scale(s.get("calories"),     factor),
                    "proteinG":     _scale(s.get("protein"),      factor),
                    "carbsG":       _scale(s.get("carbohydrate"), factor),
                    "fatG":         _scale(s.get("fat"),          factor),
                }

        return make_food_details(
            source=self.source,
            food_id=str(f.get("food_id") or ""),
            name=f.get("food_name") or "Unknown",
            brand=f.get("brand_name") or None,
            serving_sizes=extra_servings,
            nutrients=nutrients_per_100g or {},
            basis="per_100g",
        )


def _scale(value, factor: float) -> float | None:
    v = safe_float(value)
    return round(v * factor, 4) if v is not None else None


def _parse_description_nutrients(desc: str) -> dict:
    """
    Parse FatSecret's food_description string for preview macros.
    Format: "Per 100g - Calories: 231kcal | Fat: 14.31g | Carbs: 0.37g | Prot: 25.69g"
    Returns a nutrients dict (values are per 100g when the description says so,
    otherwise left as-is — close enough for a search result preview).
    """
    def _extract(pattern):
        m = re.search(pattern, desc, re.I)
        return safe_float(m.group(1)) if m else None

    return {
        "caloriesKcal": _extract(r"Calories:\s*([\d.]+)"),
        "proteinG":     _extract(r"Prot(?:ein)?:\s*([\d.]+)"),
        "carbsG":       _extract(r"Carbs?:\s*([\d.]+)"),
        "fatG":         _extract(r"Fat:\s*([\d.]+)"),
    }
