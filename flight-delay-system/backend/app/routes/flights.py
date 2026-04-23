"""Live flight route handlers."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter(tags=["flights"])


@router.get("/live-flight/{flight_number}")
async def get_live_flight(flight_number: str, request: Request) -> dict:
    """Returns raw normalized flight metadata from live API or simulated fallback.

    Parameters:
        flight_number: Flight identifier supplied by user.
        request: FastAPI request with app state services.

    Returns:
        Flight dictionary with data_source field.

    Failure modes:
        Service layer catches external failures and returns simulated records.
    """

    aviation_service = request.app.state.aviation_service
    record = await aviation_service.get_flight(flight_number)
    return {
        **record,  # backward compatibility for existing clients.
        "status": "success",
        "data": record,
        "meta": {"timestamp_utc": datetime.now(tz=timezone.utc).isoformat(), "flight_number": flight_number.upper()},
    }

