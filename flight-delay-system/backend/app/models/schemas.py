"""Pydantic models for API request/response payloads."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

FLIGHT_PATTERN = re.compile(r"^[A-Z0-9]{2,3}\d{1,4}$")
AIRPORT_PATTERN = re.compile(r"^[A-Z]{3}$")


class PredictRequest(BaseModel):
    """Schema for prediction requests.

    Parameters:
        flight_number: Required flight code (e.g., AA123).
        departure_airport: Optional departure airport IATA code.
        scheduled_departure: Optional ISO timestamp for departure.

    Returns:
        Validated request model.

    Failure modes:
        Raises validation errors for invalid formats.
    """

    flight_number: str = Field(..., min_length=3, max_length=8)
    departure_airport: str | None = None
    scheduled_departure: datetime | None = None

    @field_validator("flight_number")
    @classmethod
    def validate_flight_number(cls, value: str) -> str:
        """Validates and normalizes flight number format."""

        normalized = value.strip().upper()
        if not FLIGHT_PATTERN.match(normalized):
            raise ValueError("flight_number must look like AA123 or UAL987")
        return normalized

    @field_validator("departure_airport")
    @classmethod
    def validate_airport(cls, value: str | None) -> str | None:
        """Validates and normalizes optional airport IATA code."""

        if value is None:
            return value
        normalized = value.strip().upper()
        if not AIRPORT_PATTERN.match(normalized):
            raise ValueError("departure_airport must be a 3-letter IATA code")
        return normalized


class WeatherInfo(BaseModel):
    """Weather payload in prediction responses."""

    condition: str
    wind_kph: float
    visibility_km: float | None = None

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str) -> str:
        """Validates weather condition token."""

        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("condition cannot be empty")
        return normalized

    @field_validator("wind_kph")
    @classmethod
    def validate_wind_kph(cls, value: float) -> float:
        """Validates wind speed field."""

        if value < 0:
            raise ValueError("wind_kph cannot be negative")
        return value


class PredictResponse(BaseModel):
    """Schema for prediction responses."""

    flight_number: str
    delay_probability: float
    expected_delay_minutes: int
    delay_category: Literal["on_time", "slight", "moderate", "severe"]
    reasons: list[str]
    weather: WeatherInfo
    data_source: Literal["live", "simulated"]
    confidence: Literal["high", "medium", "low"]
    risk_level: Literal["low", "medium", "high"]
    confidence_score: float
    recommendation: str
    traffic_condition: Literal["low", "moderate", "high"]
    top_factors: list[str]

    @field_validator("flight_number")
    @classmethod
    def validate_response_flight_number(cls, value: str) -> str:
        """Validates and normalizes response flight number."""

        normalized = value.strip().upper()
        if not FLIGHT_PATTERN.match(normalized):
            raise ValueError("Invalid response flight_number format")
        return normalized

    @field_validator("delay_probability")
    @classmethod
    def validate_probability(cls, value: float) -> float:
        """Validates delay_probability range."""

        if not 0.0 <= value <= 1.0:
            raise ValueError("delay_probability must be in [0, 1]")
        return value

    @field_validator("expected_delay_minutes")
    @classmethod
    def validate_delay_minutes(cls, value: int) -> int:
        """Validates expected delay minutes."""

        if value < 0:
            raise ValueError("expected_delay_minutes cannot be negative")
        return value

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, value: float) -> float:
        """Validates confidence score range."""

        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence_score must be in [0, 1]")
        return value


class HealthResponse(BaseModel):
    """Schema for health check responses."""

    model_config = {"protected_namespaces": ()}

    status: Literal["ok"]
    model_loaded: bool
    version: str

