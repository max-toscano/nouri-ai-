"""
DB-backed cache for food detail responses.
TTL: 7 days.  Cache key: (source, food_id).
"""

import json
import logging
from datetime import timedelta

from django.utils import timezone

log = logging.getLogger(__name__)

CACHE_TTL = timedelta(days=7)


def get_cached(source: str, food_id: str) -> dict | None:
    """Return cached data if it exists and is not expired; otherwise None."""
    from api.models import FoodCache   # local import avoids circular issues at startup

    try:
        entry = FoodCache.objects.get(source=source, food_id=food_id)
    except FoodCache.DoesNotExist:
        return None

    if timezone.now() - entry.updated_at > CACHE_TTL:
        entry.delete()
        return None

    try:
        return json.loads(entry.data)
    except (json.JSONDecodeError, TypeError):
        entry.delete()
        return None


def set_cached(source: str, food_id: str, data: dict) -> None:
    """Upsert a cache entry."""
    from api.models import FoodCache

    try:
        FoodCache.objects.update_or_create(
            source=source,
            food_id=food_id,
            defaults={"data": json.dumps(data), "updated_at": timezone.now()},
        )
    except Exception as exc:
        log.warning("Cache write failed for %s/%s: %s", source, food_id, exc)
