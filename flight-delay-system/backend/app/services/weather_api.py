"""OpenWeatherMap service with resilient simulated fallback."""

from __future__ import annotations

import logging
import random
from typing import Any

import httpx

from config import (
    AIRPORT_COORDINATES,
    DEFAULT_WEATHER_PENALTY,
    OPENWEATHER_API_KEY,
    OPENWEATHER_BASE_URL,
    REQUEST_TIMEOUT_SECONDS,
    SIMULATED_WEATHER_CHOICES,
    WEATHER_CACHE_TTL_SECONDS,
    WEATHER_CONDITION_PENALTY,
)

from .cache import TTLCache

logger = logging.getLogger(__name__)


class WeatherAPIService:
    """Fetches weather by airport and falls back to simulated weather on failure.

    Parameters:
        None.

    Returns:
        Service instance with 15-minute cache.

    Failure modes:
        Handles missing keys, network errors, and malformed responses gracefully.
    """

    def __init__(self) -> None:
        self.cache = TTLCache(default_ttl_seconds=WEATHER_CACHE_TTL_SECONDS)

    async def get_weather_for_airport(self, airport_iata: str) -> dict[str, Any]:
        """Gets weather conditions for an airport.

        Parameters:
            airport_iata: IATA code (e.g., JFK).

        Returns:
            Dict containing condition, wind_kph, visibility_km, penalty and data_source.

        Failure modes:
            Returns simulated data on API timeouts, status failures, connect failures,
            missing coordinates, or malformed payload.
        """

        code = airport_iata.upper()
        cache_key = f"weather:{code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        coords = AIRPORT_COORDINATES.get(code)
        if coords is None:
            logger.warning("Unknown airport coordinates for %s; using simulated weather.", code)
            simulated = self._simulated_weather(code, "unknown_airport")
            self.cache.set(cache_key, simulated)
            return simulated

        if not OPENWEATHER_API_KEY:
            logger.warning("OpenWeather API key missing; using simulated weather.")
            simulated = self._simulated_weather(code, "missing_api_key")
            self.cache.set(cache_key, simulated)
            return simulated

        params = {"lat": coords[0], "lon": coords[1], "appid": OPENWEATHER_API_KEY, "units": "metric"}
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.get(OPENWEATHER_BASE_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            normalized = self._normalize_live_payload(payload)
            self.cache.set(cache_key, normalized)
            return normalized
        except httpx.TimeoutException:
            logger.exception("OpenWeather timeout for airport=%s", code)
        except httpx.HTTPStatusError as exc:
            logger.exception("OpenWeather HTTP error %s for airport=%s", exc.response.status_code, code)
        except httpx.ConnectError:
            logger.exception("OpenWeather connect error for airport=%s", code)
        except ValueError:
            logger.exception("OpenWeather malformed payload for airport=%s", code)

        simulated = self._simulated_weather(code, "api_failure")
        self.cache.set(cache_key, simulated)
        return simulated

    def _normalize_live_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalizes OpenWeather response to backend weather schema.

        Parameters:
            payload: Raw weather API payload.

        Returns:
            Weather dictionary with data_source='live'.

        Failure modes:
            Raises ValueError if required weather fields are missing.
        """

        weather = payload.get("weather", [])
        wind = payload.get("wind", {})
        if not weather:
            raise ValueError("Missing weather array")
        condition = (weather[0].get("main") or "clouds").lower()
        wind_mps = float(wind.get("speed", 0.0))
        visibility_m = float(payload.get("visibility", 10_000))
        visibility_km = max(0.0, visibility_m / 1000.0)
        penalty = WEATHER_CONDITION_PENALTY.get(condition, DEFAULT_WEATHER_PENALTY)
        return {
            "condition": condition,
            "wind_kph": wind_mps * 3.6,
            "visibility_km": visibility_km,
            "weather_penalty": penalty,
            "data_source": "live",
        }

    def _simulated_weather(self, airport_iata: str, reason: str) -> dict[str, Any]:
        """Creates realistic simulated weather for zero-key operation.

        Parameters:
            airport_iata: Airport code used for deterministic randomization.
            reason: Label describing fallback trigger.

        Returns:
            Simulated weather dictionary with data_source='simulated'.

        Failure modes:
            None; uses local deterministic random generation.
        """

        random.seed(sum(ord(ch) for ch in airport_iata))
        condition, wind_kph, visibility_km = random.choice(SIMULATED_WEATHER_CHOICES)
        jitter = random.uniform(-3.0, 3.0)
        wind = max(2.0, wind_kph + jitter)
        visibility = max(1.0, visibility_km + random.uniform(-1.0, 1.0))
        penalty = WEATHER_CONDITION_PENALTY.get(condition, DEFAULT_WEATHER_PENALTY)
        return {
            "condition": condition,
            "wind_kph": wind,
            "visibility_km": visibility,
            "weather_penalty": penalty,
            "data_source": "simulated",
            "fallback_reason": reason,
        }

