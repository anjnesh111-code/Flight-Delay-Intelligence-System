"""Analytics route handlers."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

from config import AIRLINE_DELAY_SCORE_MULTIPLIER, AIRLINE_SCORE_DELAY_WEIGHT, AIRLINE_SCORE_ON_TIME_WEIGHT

router = APIRouter(tags=["analytics"])


@router.get("/airlines/performance")
async def airline_performance(request: Request) -> dict:
    """Returns aggregated delay analytics for dashboard visualizations.

    Parameters:
        request: FastAPI request with predictor instance.

    Returns:
        Backward-compatible analytics payload enriched with ranking and score metrics.

    Failure modes:
        Returns empty collections when model artifacts are unavailable.
    """

    predictor = request.app.state.predictor
    base_payload = predictor.get_analytics_payload() or {}
    airline_rows = base_payload.get("airline_performance", [])
    enriched_airlines = _enrich_airlines(airline_rows)
    best_airline = enriched_airlines[0]["airline_iata"] if enriched_airlines else None
    worst_airline = enriched_airlines[-1]["airline_iata"] if enriched_airlines else None

    enriched_payload = {
        "hourly_heatmap": base_payload.get("hourly_heatmap", []),
        "airline_performance": enriched_airlines,
        "top_delayed_routes": base_payload.get("top_delayed_routes", []),
        "best_airline_today": best_airline,
        "worst_airline_today": worst_airline,
    }

    return {
        **enriched_payload,  # backward compatibility for existing clients.
        "status": "success",
        "data": enriched_payload,
        "meta": {"timestamp_utc": datetime.now(tz=timezone.utc).isoformat(), "record_count": len(enriched_airlines)},
    }


def _enrich_airlines(airline_rows: list[dict]) -> list[dict]:
    """Adds airline score and ranking metadata to each airline row.

    Parameters:
        airline_rows: Existing airline performance rows.

    Returns:
        Sorted rows with airline_score and ranking fields.

    Failure modes:
        Missing values default to zeros and still return stable output.
    """

    scored: list[dict] = []
    for row in airline_rows:
        on_time_pct = float(row.get("on_time_pct", 0.0))
        avg_delay = float(row.get("avg_delay", 0.0))
        delay_score_component = max(0.0, 100.0 - min(100.0, avg_delay * AIRLINE_DELAY_SCORE_MULTIPLIER))
        airline_score = (on_time_pct * AIRLINE_SCORE_ON_TIME_WEIGHT) + (delay_score_component * AIRLINE_SCORE_DELAY_WEIGHT)
        scored.append({**row, "airline_score": round(airline_score, 2)})

    scored.sort(key=lambda item: item.get("airline_score", 0.0), reverse=True)
    for index, row in enumerate(scored, start=1):
        row["ranking"] = index
    return scored

