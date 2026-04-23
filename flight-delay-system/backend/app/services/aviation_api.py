"""AviationStack service with resilient simulated fallback."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import (
    AVIATIONSTACK_API_KEY,
    AVIATIONSTACK_BASE_URL,
    FLIGHT_CACHE_TTL_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SIMULATED_AIRLINE_CODES,
    SIMULATED_AIRPORT_CODES,
)

from .cache import TTLCache

logger = logging.getLogger(__name__)


class AviationAPIService:
    """Fetches flight metadata from AviationStack with graceful fallback behavior.

    Parameters:
        None.

    Returns:
        Service instance with internal 5-minute TTL cache.

    Failure modes:
        External API failures are caught and converted to simulated responses.
    """

    def __init__(self) -> None:
        self.cache = TTLCache(default_ttl_seconds=FLIGHT_CACHE_TTL_SECONDS)

    async def get_flight(self, flight_number: str) -> dict[str, Any]:
        """Returns normalized flight details for a flight number.

        Parameters:
            flight_number: Airline+number code such as AA123.

        Returns:
            Dict with airline_iata, origin, destination, schedule fields and data_source.

        Failure modes:
            On missing key, timeout, HTTP errors, connect errors, or malformed payload,
            returns simulated data and logs the failure reason.
        """

        cache_key = f"flight:{flight_number.upper()}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if not AVIATIONSTACK_API_KEY:
            logger.warning("AviationStack key missing; using simulated flight data.")
            simulated = self._simulated_flight(flight_number, "missing_api_key")
            self.cache.set(cache_key, simulated)
            return simulated

        params = {"access_key": AVIATIONSTACK_API_KEY, "flight_iata": flight_number.upper()}
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.get(AVIATIONSTACK_BASE_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            normalized = self._normalize_live_payload(payload, flight_number)
            self.cache.set(cache_key, normalized)
            return normalized
        except httpx.TimeoutException:
            logger.exception("AviationStack timeout for flight_number=%s", flight_number)
        except httpx.HTTPStatusError as exc:
            logger.exception("AviationStack HTTP error %s for flight_number=%s", exc.response.status_code, flight_number)
        except httpx.ConnectError:
            logger.exception("AviationStack connect error for flight_number=%s", flight_number)
        except ValueError:
            logger.exception("AviationStack returned malformed payload for flight_number=%s", flight_number)

        simulated = self._simulated_flight(flight_number, "api_failure")
        self.cache.set(cache_key, simulated)
        return simulated

    def _normalize_live_payload(self, payload: dict[str, Any], flight_number: str) -> dict[str, Any]:
        """Converts AviationStack response into stable schema.

        Parameters:
            payload: Raw JSON dictionary from AviationStack.
            flight_number: Requested flight number for fallback values.

        Returns:
            Normalized flight dictionary with data_source='live'.

        Failure modes:
            Raises ValueError when payload misses required fields.
        """

        flights = payload.get("data", [])
        if not flights:
            raise ValueError("No flights in payload")
        row = flights[0]
        departure = row.get("departure") or {}
        arrival = row.get("arrival") or {}
        flight_info = row.get("flight") or {}
        airline = row.get("airline") or {}

        origin = (departure.get("iata") or "").upper()
        destination = (arrival.get("iata") or "").upper()
        if not origin or not destination:
            raise ValueError("Missing IATA route")

        scheduled = departure.get("scheduled")
        actual = departure.get("actual")
        if not scheduled:
            raise ValueError("Missing scheduled departure")

        return {
            "flight_number": (flight_info.get("iata") or flight_number).upper(),
            "airline_iata": (airline.get("iata") or flight_number[:2] or "AA").upper(),
            "origin": origin,
            "destination": destination,
            "scheduled_departure": scheduled,
            "actual_departure": actual,
            "data_source": "live",
        }

    def _simulated_flight(self, flight_number: str, reason: str) -> dict[str, Any]:
        """Builds realistic fallback flight data.

        Parameters:
            flight_number: User requested flight number.
            reason: Label for why fallback was chosen.

        Returns:
            Simulated flight dictionary with data_source='simulated'.

        Failure modes:
            No external dependencies; deterministic enough for demo continuity.
        """

        seed_value = sum(ord(char) for char in flight_number.upper())
        random.seed(seed_value)
        airline = (flight_number[:2] or random.choice(SIMULATED_AIRLINE_CODES)).upper()
        if airline not in SIMULATED_AIRLINE_CODES:
            airline = random.choice(SIMULATED_AIRLINE_CODES)

        origin = random.choice(SIMULATED_AIRPORT_CODES)
        destination_choices = [code for code in SIMULATED_AIRPORT_CODES if code != origin]
        destination = random.choice(destination_choices)
        scheduled_dt = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
        simulated = {
            "flight_number": flight_number.upper(),
            "airline_iata": airline,
            "origin": origin,
            "destination": destination,
            "scheduled_departure": scheduled_dt.isoformat(),
            "actual_departure": (scheduled_dt + timedelta(minutes=random.randint(-10, 45))).isoformat(),
            "data_source": "simulated",
            "fallback_reason": reason,
        }
        return simulated

