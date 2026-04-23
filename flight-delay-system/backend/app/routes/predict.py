"""Prediction route handlers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import PredictRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["prediction"])


@router.post("/predict")
async def predict_delay(payload: PredictRequest, request: Request) -> dict:
    """Predicts delay risk and expected delay minutes for a flight.

    Parameters:
        payload: Validated prediction request model.
        request: FastAPI request containing app state dependencies.

    Returns:
        Backward-compatible prediction payload enriched with status/data/meta envelope.

    Failure modes:
        Raises 503 if model was not loaded during startup.
    """

    predictor = request.app.state.predictor
    aviation_service = request.app.state.aviation_service
    weather_service = request.app.state.weather_service

    if not predictor.is_loaded:
        raise HTTPException(status_code=503, detail="Prediction model is still warming up. Try again shortly.")

    flight_data = await aviation_service.get_flight(payload.flight_number)
    origin = payload.departure_airport or flight_data["origin"]
    destination = flight_data["destination"]
    airline_iata = flight_data["airline_iata"]
    scheduled_value = payload.scheduled_departure or _parse_schedule(flight_data.get("scheduled_departure"))
    weather = await weather_service.get_weather_for_airport(origin)

    prediction = predictor.predict(
        flight_number=payload.flight_number,
        airline_iata=airline_iata,
        origin=origin,
        destination=destination,
        scheduled_departure=scheduled_value,
        weather=weather,
    )

    source = "live" if flight_data.get("data_source") == "live" and weather.get("data_source") == "live" else "simulated"
    prediction["data_source"] = source
    response_payload = {
        **prediction,  # backward compatibility for existing clients.
        "status": "success",
        "data": prediction,
        "meta": {
            "timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
            "decision_engine": "v1",
            "data_source": source,
        },
    }
    logger.info(
        "prediction_completed flight=%s risk=%s prob=%.3f source=%s",
        payload.flight_number,
        prediction.get("risk_level"),
        prediction.get("delay_probability", 0.0),
        source,
    )
    return response_payload


def _parse_schedule(raw_schedule: str | None) -> datetime | None:
    """Parses ISO departure schedule string into datetime.

    Parameters:
        raw_schedule: Optional datetime string from AviationStack payload.

    Returns:
        Parsed datetime or None.

    Failure modes:
        Returns None for missing or malformed timestamps.
    """

    if not raw_schedule:
        return None
    try:
        return datetime.fromisoformat(raw_schedule.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Failed to parse scheduled_departure=%s", raw_schedule)
        return None

