"""
Abstract base class that every food provider must implement.

Each provider is responsible for:
  - Searching foods by text query
  - Fetching full nutrition details by provider-specific ID
  - Looking up a product by barcode (optional; return None if unsupported)
"""

from abc import ABC, abstractmethod


class FoodProvider(ABC):
    # Override in each subclass — used as the "source" field in responses
    source: str = ""

    @abstractmethod
    def search(self, query: str) -> list[dict]:
        """
        Search for foods matching query.
        Returns a list of normalized search-result dicts.
        Must NOT raise — return [] on any error (caller logs separately).
        """

    @abstractmethod
    def get_details(self, food_id: str) -> dict:
        """
        Fetch full nutrition details for a single food by provider-specific ID.
        Raises ValueError if the food is not found.
        Raises requests.RequestException on network / HTTP errors.
        """

    def search_by_barcode(self, barcode: str) -> dict | None:
        """
        Look up a product by barcode.
        Return a normalized detail dict, or None if not found / not supported.
        Default implementation returns None; override where supported.
        """
        return None
