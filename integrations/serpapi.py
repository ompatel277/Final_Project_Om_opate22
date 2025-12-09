"""Lightweight SerpAPI client for Google Maps/Local data."""

import logging
import os
from typing import Dict, List, Optional

import requests


logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


class SerpApiClient:
    """Helper around SerpAPI (Google Maps) endpoints."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, params: Dict) -> Dict:
        if not self.is_configured():
            logger.info("SERPAPI_API_KEY not configured; skipping live fetch.")
            return {}

        params = {"api_key": self.api_key, **params}
        try:
            resp = requests.get(SERPAPI_URL, params=params, timeout=12)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("SerpAPI request failed: %s", exc)
            return {}

    def search_restaurants(
        self,
        latitude: float,
        longitude: float,
        query: str = "restaurants",
        radius_meters: int = 8000,
        page_token: Optional[str] = None,
    ) -> List[Dict]:
        """Fetch nearby restaurants using Google Maps results."""

        params: Dict[str, str] = {
            "engine": "google_maps",
            "type": "search",
            "q": query,
            "ll": f"@{latitude},{longitude},14z",
            "hl": "en",
            "google_domain": "google.com",
            "radius": radius_meters,
        }

        if page_token:
            params["next_page_token"] = page_token

        data = self._get(params)
        return data.get("local_results") or data.get("places_results") or []

    def get_place_details(self, place_id: str) -> Dict:
        """Fetch expanded place details and reviews."""

        params = {
            "engine": "google_maps",
            "type": "place",
            "data_id": place_id,
            "hl": "en",
        }

        data = self._get(params)
        return data.get("place_results") or {}