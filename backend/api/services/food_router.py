"""
Multi-provider search router.

Text search order:   FatSecret → USDA → Open Food Facts  (all run in parallel)
Barcode lookup order: OFF → FatSecret → USDA             (stops at first hit)

Results from all providers are merged and deduplicated before being returned.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..providers.openfoodfacts import OpenFoodFactsProvider
from ..providers.usda import USDAProvider
from ..providers.fatsecret import FatSecretProvider

log = logging.getLogger(__name__)

# Module-level singletons — one per process
_off      = OpenFoodFactsProvider()
_usda     = USDAProvider()
_fatsecret = FatSecretProvider()

_BARCODE_RE = re.compile(r"^\d{8,14}$")


# ── Public API ─────────────────────────────────────────────────────────────────

def search(query: str) -> dict:
    q = query.strip()
    if _BARCODE_RE.match(q):
        return _barcode_search(q)
    return _text_search(q)


def get_provider(source: str):
    """Return the provider instance for a given source name."""
    mapping = {
        "openfoodfacts": _off,
        "usda":          _usda,
        "fatsecret":     _fatsecret,
    }
    provider = mapping.get(source)
    if not provider:
        raise ValueError(f"Unknown provider: '{source}'")
    return provider


def dedupe(results: list[dict]) -> tuple[list[dict], int]:
    """
    Remove near-duplicates based on normalised name + brand.
    Keeps the first occurrence (highest-priority provider).
    Returns (deduped_list, number_removed).
    """
    seen:    set[str]  = set()
    deduped: list[dict] = []

    for item in results:
        key = _dedup_key(item)
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped, len(results) - len(deduped)


# ── Internal search strategies ─────────────────────────────────────────────────

def _text_search(query: str) -> dict:
    order = [
        (_fatsecret, "fatsecret"),
        (_usda,      "usda"),
        (_off,       "openfoodfacts"),
    ]
    attempted  = [name for _, name in order]
    succeeded  = []
    all_items: list[dict] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_safe_search, provider, query): name
            for provider, name in order
        }
        for future in as_completed(futures):
            name    = futures[future]
            results = future.result()   # _safe_search never raises
            if results is not None:
                succeeded.append(name)
                all_items.extend(results)
            else:
                log.warning("Search provider '%s' failed for query: %s", name, query)

    deduped, removed = dedupe(all_items)

    return {
        "query":   query,
        "results": deduped,
        "meta": {
            "providersAttempted": attempted,
            "providersSucceeded": succeeded,
            "dedupedCount":       removed,
        },
    }


def _barcode_search(barcode: str) -> dict:
    order = [
        (_off,       "openfoodfacts"),
        (_fatsecret, "fatsecret"),
        (_usda,      "usda"),
    ]
    attempted: list[str] = []
    succeeded: list[str] = []
    results:   list[dict] = []

    for provider, name in order:
        attempted.append(name)
        try:
            detail = provider.search_by_barcode(barcode)
            if detail:
                succeeded.append(name)
                results.append(_detail_to_search_result(detail))
                break   # stop at first hit
        except Exception as exc:
            log.warning("Barcode lookup failed (%s): %s", name, exc)

    return {
        "query":   barcode,
        "results": results,
        "meta": {
            "providersAttempted": attempted,
            "providersSucceeded": succeeded,
            "dedupedCount":       0,
        },
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_search(provider, query: str) -> list[dict] | None:
    """Call provider.search(); return None (not raise) on any error."""
    try:
        return provider.search(query)
    except Exception as exc:
        log.warning("Provider '%s' search error: %s", provider.source, exc)
        return None


def _dedup_key(item: dict) -> str:
    name  = re.sub(r"[^a-z0-9 ]", "", (item.get("name")  or "").lower().strip())
    brand = re.sub(r"[^a-z0-9 ]", "", (item.get("brand") or "").lower().strip())
    return f"{name}|{brand}"


def _detail_to_search_result(detail: dict) -> dict:
    return {
        "source":          detail["source"],
        "id":              detail["id"],
        "name":            detail["name"],
        "brand":           detail.get("brand"),
        "imageUrl":        detail.get("imageUrl"),
        "matchConfidence": 1.0,
        "servingHint":     None,
    }
