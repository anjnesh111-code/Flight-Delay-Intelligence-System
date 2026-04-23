"""Inference wrapper for the trained delay prediction model bundle."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from config import (
    CONFIDENCE_SCORE_MAX,
    CONFIDENCE_SCORE_MIN,
    CONFIDENCE_HIGH_MIN_PROB,
    CONFIDENCE_MEDIUM_MIN_PROB,
    DELAY_PROBABILITY_LOW_THRESHOLD,
    DELAY_PROBABILITY_MEDIUM_THRESHOLD,
    MODEL_BUNDLE_PATH,
    MODERATE_DELAY_MINUTES_THRESHOLD,
    PEAK_HOUR_END,
    PEAK_HOUR_START,
    RISK_HIGH_THRESHOLD,
    RISK_MEDIUM_THRESHOLD,
    SEVERE_DELAY_MINUTES_THRESHOLD,
    SLIGHT_DELAY_MINUTES_THRESHOLD,
    TRAFFIC_HIGH_ROUTE_DELAY,
    TRAFFIC_HIGH_WEATHER_SEVERITY,
    TRAFFIC_MODERATE_ROUTE_DELAY,
    TRAFFIC_MODERATE_WEATHER_SEVERITY,
    WEATHER_BAD_CONDITIONS,
    WEATHER_WARNING_WIND_KPH,
)
from ml.features import build_feature_row, to_next_hour

logger = logging.getLogger(__name__)


@dataclass
class PredictionArtifacts:
    """Container for loaded model artifacts."""

    classifier: Any
    regressor: Any
    feature_columns: list[str]
    encoders: dict[str, dict[str, int]]
    route_avg_delay: dict[str, float]
    analytics_payload: dict[str, Any]


class Predictor:
    """Predictor that serves classification and regression delay outputs.

    Parameters:
        model_path: Optional custom path to a model_bundle.joblib file.

    Returns:
        Ready-to-use predictor instance once initialized.

    Failure modes:
        Raises FileNotFoundError or KeyError if bundle is missing required artifacts.
    """

    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or MODEL_BUNDLE_PATH
        self.artifacts: PredictionArtifacts | None = None

    def load(self) -> None:
        """Loads model bundle into memory once at app startup.

        Parameters:
            None.

        Returns:
            None.

        Failure modes:
            Raises exceptions when model bundle is missing or malformed.
        """

        bundle = joblib.load(self.model_path)
        self.artifacts = PredictionArtifacts(
            classifier=bundle["classifier"],
            regressor=bundle["regressor"],
            feature_columns=bundle["feature_columns"],
            encoders=bundle["encoders"],
            route_avg_delay=bundle["route_avg_delay"],
            analytics_payload=bundle.get("analytics_payload", {}),
        )
        logger.info("Model bundle loaded from %s", self.model_path)

    @property
    def is_loaded(self) -> bool:
        """Reports whether model artifacts are available in memory.

        Parameters:
            None.

        Returns:
            True when loaded, else False.

        Failure modes:
            None.
        """

        return self.artifacts is not None

    def predict(
        self,
        flight_number: str,
        airline_iata: str,
        origin: str,
        destination: str,
        scheduled_departure: datetime | None,
        weather: dict[str, Any],
    ) -> dict[str, Any]:
        """Produces delay probability, delay minutes, category, confidence, and reasons.

        Parameters:
            flight_number: Input flight number.
            airline_iata: Airline IATA code.
            origin: Origin airport.
            destination: Destination airport.
            scheduled_departure: Optional schedule; defaults to next hour UTC when missing.
            weather: Weather payload for feature construction.

        Returns:
            Prediction response dictionary.

        Failure modes:
            Raises RuntimeError if model isn't loaded; caller should handle at API layer.
        """

        if self.artifacts is None:
            raise RuntimeError("Predictor is not loaded")
        schedule = scheduled_departure or to_next_hour(datetime.now(tz=timezone.utc))
        feature_row = build_feature_row(
            airline_iata=airline_iata,
            origin=origin,
            destination=destination,
            scheduled_departure=schedule,
            weather=weather,
            encoders=self.artifacts.encoders,
            route_avg_delay_map=self.artifacts.route_avg_delay,
        )
        features_df = pd.DataFrame([feature_row])[self.artifacts.feature_columns]
        delay_probability = float(self.artifacts.classifier.predict_proba(features_df)[0][1])
        expected_delay = max(0.0, float(self.artifacts.regressor.predict(features_df)[0]))
        category = self._delay_category(expected_delay)
        confidence = self._confidence_label(delay_probability)
        reasons = self._generate_reasons(feature_row, weather)

        risk_level = self._risk_level(delay_probability)
        confidence_score = self._confidence_score(delay_probability)
        traffic_condition = self._traffic_condition(feature_row)
        top_factors = self._top_factors(feature_row, weather)
        recommendation = self._recommendation(
            delay_probability=delay_probability,
            risk_level=risk_level,
            weather=weather,
            departure_hour=int(feature_row["departure_hour"]),
        )

        return {
            "flight_number": flight_number,
            "delay_probability": round(delay_probability, 4),
            "expected_delay_minutes": int(round(expected_delay)),
            "delay_category": category,
            "reasons": reasons,
            "confidence": confidence,
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "traffic_condition": traffic_condition,
            "recommendation": recommendation,
            "top_factors": top_factors,
            "weather": {
                "condition": str(weather.get("condition", "unknown")),
                "wind_kph": round(float(weather.get("wind_kph", 0.0)), 1),
                "visibility_km": round(float(weather.get("visibility_km", 0.0)), 1),
            },
        }

    def get_analytics_payload(self) -> dict[str, Any]:
        """Returns precomputed airline and route analytics payload for charts.

        Parameters:
            None.

        Returns:
            Dictionary with heatmap and leaderboard data.

        Failure modes:
            Returns empty dict when model isn't loaded.
        """

        if self.artifacts is None:
            return {}
        return self.artifacts.analytics_payload

    def _delay_category(self, expected_delay: float) -> str:
        """Maps predicted delay minutes to category labels."""

        if expected_delay >= SEVERE_DELAY_MINUTES_THRESHOLD:
            return "severe"
        if expected_delay >= MODERATE_DELAY_MINUTES_THRESHOLD:
            return "moderate"
        if expected_delay >= SLIGHT_DELAY_MINUTES_THRESHOLD:
            return "slight"
        return "on_time"

    def _confidence_label(self, probability: float) -> str:
        """Maps delay probability to confidence buckets."""

        if probability >= CONFIDENCE_HIGH_MIN_PROB:
            return "high"
        if probability >= CONFIDENCE_MEDIUM_MIN_PROB:
            return "medium"
        return "low"

    def _generate_reasons(self, feature_row: dict[str, float], weather: dict[str, Any]) -> list[str]:
        """Generates human-readable reason strings for UI explainability."""

        reasons: list[str] = []
        if feature_row["weather_severity"] >= DELAY_PROBABILITY_MEDIUM_THRESHOLD * 10:
            reasons.append("weather_score: high")
        elif feature_row["weather_severity"] >= DELAY_PROBABILITY_LOW_THRESHOLD * 10:
            reasons.append("weather_score: medium")
        if 16 <= int(feature_row["departure_hour"]) <= 21:
            reasons.append("departure_hour: peak")
        if feature_row["is_holiday_week"] == 1:
            reasons.append("seasonality: holiday_week")
        if feature_row["route_avg_delay"] >= 25:
            reasons.append("route_risk: historically_delayed")
        if not reasons:
            reasons.append("traffic_pattern: normal")
        return reasons

    def _risk_level(self, probability: float) -> str:
        """Maps delay probability to actionable risk levels."""

        if probability > RISK_HIGH_THRESHOLD:
            return "high"
        if probability >= RISK_MEDIUM_THRESHOLD:
            return "medium"
        return "low"

    def _confidence_score(self, probability: float) -> float:
        """Calculates confidence score from class probability distance.

        Score is higher when prediction is farther from 0.5.
        """

        distance = abs(probability - 0.5) * 2.0
        score = max(CONFIDENCE_SCORE_MIN, min(CONFIDENCE_SCORE_MAX, distance))
        return round(float(score), 4)

    def _traffic_condition(self, feature_row: dict[str, float]) -> str:
        """Infers traffic condition from route, weather, and peak-hour signals."""

        if (
            feature_row["peak_hour"] == 1.0
            or feature_row["weather_severity"] >= TRAFFIC_HIGH_WEATHER_SEVERITY
            or feature_row["route_avg_delay"] >= TRAFFIC_HIGH_ROUTE_DELAY
        ):
            return "high"
        if (
            feature_row["weather_severity"] >= TRAFFIC_MODERATE_WEATHER_SEVERITY
            or feature_row["route_avg_delay"] >= TRAFFIC_MODERATE_ROUTE_DELAY
        ):
            return "moderate"
        return "low"

    def _recommendation(self, delay_probability: float, risk_level: str, weather: dict[str, Any], departure_hour: int) -> str:
        """Builds a decision-oriented recommendation message."""

        condition = str(weather.get("condition", "unknown")).lower()
        wind_kph = float(weather.get("wind_kph", 0.0))
        if delay_probability > RISK_HIGH_THRESHOLD:
            return "High delay risk detected. Consider rebooking or selecting an alternate connection."
        if condition in WEATHER_BAD_CONDITIONS or wind_kph >= WEATHER_WARNING_WIND_KPH:
            return "Weather disruption likely. Monitor gate alerts and keep schedule flexibility."
        if PEAK_HOUR_START <= departure_hour <= PEAK_HOUR_END:
            return "Peak-hour congestion expected. Arrive early and expect slower turnaround."
        if risk_level == "low":
            return "Safe to proceed. No major delay risk signals detected."
        return "Moderate delay risk. Keep buffer time before connections and pickups."

    def _top_factors(self, feature_row: dict[str, float], weather: dict[str, Any]) -> list[str]:
        """Returns top explainability factors influencing prediction."""

        factors: list[tuple[float, str]] = []
        factors.append((feature_row["weather_severity"], f"Weather severity {feature_row['weather_severity']:.1f}/10"))
        factors.append((feature_row["route_avg_delay"] / 10.0, f"Historical route delay {feature_row['route_avg_delay']:.1f} min"))
        if feature_row["peak_hour"] == 1.0:
            factors.append((2.5, "Peak-hour departure congestion"))
        if feature_row["weekend_flag"] == 1.0:
            factors.append((1.2, "Weekend traffic pattern"))
        if feature_row["is_holiday_week"] == 1.0:
            factors.append((2.2, "Holiday week demand pressure"))
        wind_kph = float(weather.get("wind_kph", 0.0))
        factors.append((wind_kph / 20.0, f"Wind speed impact {wind_kph:.1f} kph"))
        factors.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in factors[:3]]

