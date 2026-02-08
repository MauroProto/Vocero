"""Ranking logic for multi-provider call results.

Scoring: availability (40%) + earliest slot (30%) + Google rating (30%)
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def rank_results(results: list[dict]) -> list[dict]:
    """Score and rank multi-call results. Returns sorted list (best first)."""
    for r in results:
        summary = r.get("summary")
        avail_score = _score_availability(summary)
        slot_score = _score_earliest_slot(summary)
        rating_score = _score_rating(r.get("rating"))

        r["score"] = round(avail_score * 0.4 + slot_score * 0.3 + rating_score * 0.3, 3)
        r["avail_score"] = avail_score
        r["slot_score"] = slot_score
        r["rating_score"] = rating_score

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def _score_availability(summary) -> float:
    """1.0 if booked, 0.6 if slots mentioned, 0.0 if no availability."""
    if summary is None:
        return 0.0
    if summary.booking_confirmed:
        return 1.0
    # If there's a date/time mentioned, slots were available
    if summary.date or summary.time:
        return 0.6
    return 0.0


def _score_earliest_slot(summary) -> float:
    """Score based on how soon the slot is. 0 days = 1.0, 7+ days = 0.0."""
    if summary is None or not summary.date:
        return 0.0
    try:
        slot_date = datetime.strptime(summary.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_away = (slot_date - now).days
        if days_away < 0:
            days_away = 0
        return max(0.0, 1.0 - days_away / 7.0)
    except (ValueError, TypeError):
        return 0.0


def _score_rating(rating: float | None) -> float:
    """Normalize Google 5-star rating to 0-1. No rating = 0.5 (neutral)."""
    if rating is None:
        return 0.5
    return min(rating / 5.0, 1.0)
