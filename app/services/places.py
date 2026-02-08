"""Google Places search for finding service providers."""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PlaceResult:
    name: str
    address: str
    phone: str | None
    rating: float | None
    total_ratings: int
    place_id: str


async def search_places(
    query: str,
    latitude: float | None = None,
    longitude: float | None = None,
    radius: float = 5000.0,
    max_results: int = 5,
) -> list[PlaceResult]:
    """Search Google Places API (New) for businesses matching the query."""
    if not settings.google_places_api_key:
        logger.warning("Google Places API key not configured")
        return []

    request_body: dict = {"textQuery": query, "maxResultCount": max_results}
    if latitude is not None and longitude is not None:
        request_body["locationBias"] = {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius,
            }
        }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.google_places_api_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.internationalPhoneNumber,places.rating,places.userRatingCount,places.id",
            },
            json=request_body,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for place in data.get("places", []):
        phone = place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber")
        results.append(PlaceResult(
            name=place.get("displayName", {}).get("text", "Unknown"),
            address=place.get("formattedAddress", ""),
            phone=phone,
            rating=place.get("rating"),
            total_ratings=place.get("userRatingCount", 0),
            place_id=place.get("id", ""),
        ))

    logger.info("Places search '%s' returned %d results", query, len(results))
    return results
