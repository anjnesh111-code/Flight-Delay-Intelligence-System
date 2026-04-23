"""Central configuration for the flight delay system.

All constants used across backend modules are defined here to avoid magic numbers.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Flight Delay Prediction API"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent
MODEL_BUNDLE_PATH = BASE_DIR / "ml" / "model_bundle.joblib"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

AVIATIONSTACK_BASE_URL = "http://api.aviationstack.com/v1/flights"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

REQUEST_TIMEOUT_SECONDS = 8.0

FLIGHT_CACHE_TTL_SECONDS = 5 * 60
WEATHER_CACHE_TTL_SECONDS = 15 * 60

DELAY_PROBABILITY_LOW_THRESHOLD = 0.30
DELAY_PROBABILITY_MEDIUM_THRESHOLD = 0.60

SEVERE_DELAY_MINUTES_THRESHOLD = 60
MODERATE_DELAY_MINUTES_THRESHOLD = 30
SLIGHT_DELAY_MINUTES_THRESHOLD = 10

CONFIDENCE_HIGH_MIN_PROB = 0.70
CONFIDENCE_MEDIUM_MIN_PROB = 0.45
RISK_HIGH_THRESHOLD = 0.70
RISK_MEDIUM_THRESHOLD = 0.45
CONFIDENCE_SCORE_MIN = 0.05
CONFIDENCE_SCORE_MAX = 0.99

PEAK_HOUR_START = 16
PEAK_HOUR_END = 21
WEEKEND_DAYS = {5, 6}

TRAFFIC_HIGH_WEATHER_SEVERITY = 7.0
TRAFFIC_MODERATE_WEATHER_SEVERITY = 4.0
TRAFFIC_HIGH_ROUTE_DELAY = 28.0
TRAFFIC_MODERATE_ROUTE_DELAY = 18.0

WEATHER_BAD_CONDITIONS = {"thunderstorm", "snow", "rain"}
WEATHER_WARNING_WIND_KPH = 30.0

AIRLINE_SCORE_ON_TIME_WEIGHT = 0.70
AIRLINE_SCORE_DELAY_WEIGHT = 0.30
AIRLINE_DELAY_SCORE_MULTIPLIER = 2.0

SIMULATED_AIRLINE_CODES = ["AA", "UA", "DL", "WN", "B6", "AS", "NK", "F9"]
SIMULATED_AIRPORT_CODES = ["JFK", "LAX", "SFO", "ORD", "ATL", "DFW", "DEN", "SEA", "MIA", "BOS"]

AIRPORT_COORDINATES = {
    "JFK": (40.6413, -73.7781),
    "LAX": (33.9416, -118.4085),
    "SFO": (37.6213, -122.3790),
    "ORD": (41.9742, -87.9073),
    "ATL": (33.6407, -84.4277),
    "DFW": (32.8998, -97.0403),
    "DEN": (39.8561, -104.6737),
    "SEA": (47.4502, -122.3088),
    "MIA": (25.7959, -80.2870),
    "BOS": (42.3656, -71.0096),
    "PHX": (33.4342, -112.0116),
    "LAS": (36.0840, -115.1537),
}

ROUTE_DISTANCE_KM = {
    "JFK-LAX": 3983,
    "JFK-SFO": 4162,
    "JFK-ORD": 1188,
    "JFK-ATL": 1221,
    "JFK-MIA": 1757,
    "LAX-SFO": 543,
    "LAX-SEA": 1546,
    "LAX-DEN": 1386,
    "LAX-ORD": 2805,
    "SFO-SEA": 1093,
    "SFO-ORD": 2964,
    "ORD-ATL": 975,
    "ATL-MIA": 959,
    "ATL-DFW": 1172,
    "DFW-DEN": 1036,
    "DFW-SEA": 2679,
    "DEN-SEA": 1647,
    "BOS-ATL": 1513,
    "BOS-MIA": 2028,
    "LAS-SEA": 1402,
    "PHX-DEN": 970,
}

DEFAULT_ROUTE_DISTANCE_KM = 1500
DEFAULT_ROUTE_AVG_DELAY_MINUTES = 18.0

WEATHER_CONDITION_PENALTY = {
    "clear": 0.0,
    "clouds": 1.0,
    "mist": 2.5,
    "rain": 4.0,
    "snow": 6.0,
    "thunderstorm": 8.0,
}
DEFAULT_WEATHER_PENALTY = 2.0

WEATHER_SEVERITY_MIN = 0.0
WEATHER_SEVERITY_MAX = 10.0

SIMULATED_WEATHER_CHOICES = [
    ("clear", 8.0, 10.0),
    ("clouds", 14.0, 9.0),
    ("rain", 24.0, 6.0),
    ("thunderstorm", 38.0, 4.0),
]

HOLIDAY_WEEKS = {
    (1, 1),
    (1, 15),
    (2, 19),
    (5, 27),
    (7, 4),
    (9, 2),
    (10, 14),
    (11, 11),
    (11, 28),
    (12, 25),
}

TRAINING_SAMPLE_ROWS = 50_000
TRAINING_RANDOM_SEED = 42
TRAINING_TEST_SIZE = 0.2
XGB_CLASSIFIER_PARAMS = {
    "n_estimators": 120,
    "max_depth": 5,
    "learning_rate": 0.08,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "random_state": TRAINING_RANDOM_SEED,
    "eval_metric": "logloss",
}
XGB_REGRESSOR_PARAMS = {
    "n_estimators": 160,
    "max_depth": 5,
    "learning_rate": 0.07,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "random_state": TRAINING_RANDOM_SEED,
}

