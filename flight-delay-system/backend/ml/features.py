"""Feature engineering for flight delay model inputs."""

from __future__ import annotations

from datetime import datetime, timedelta

from config import (
    DEFAULT_ROUTE_AVG_DELAY_MINUTES,
    DEFAULT_ROUTE_DISTANCE_KM,
    DEFAULT_WEATHER_PENALTY,
    HOLIDAY_WEEKS,
    ROUTE_DISTANCE_KM,
    WEATHER_SEVERITY_MAX,
    WEATHER_SEVERITY_MIN,
)


def is_holiday_week(timestamp: datetime) -> int:
    """Returns whether a datetime falls within a configured US holiday week window.

    Parameters:
        timestamp: Departure datetime.

    Returns:
        1 when in holiday week range, else 0.

    Failure modes:
        None; uses deterministic date calculations.
    """

    for month, day in HOLIDAY_WEEKS:
        holiday = datetime(timestamp.year, month, day, tzinfo=timestamp.tzinfo)
        if abs((timestamp - holiday).days) <= 3:
            return 1
    return 0


def get_route_distance_km(origin: str, destination: str) -> float:
    """Looks up route distance from static route-distance map.

    Parameters:
        origin: Origin airport IATA.
        destination: Destination airport IATA.

    Returns:
        Route distance in km.

    Failure modes:
        Falls back to DEFAULT_ROUTE_DISTANCE_KM when route key is missing.
    """

    key = f"{origin}-{destination}"
    reverse_key = f"{destination}-{origin}"
    return float(ROUTE_DISTANCE_KM.get(key, ROUTE_DISTANCE_KM.get(reverse_key, DEFAULT_ROUTE_DISTANCE_KM)))


def is_peak_hour(timestamp: datetime) -> int:
    """Returns whether departure is in high-traffic peak-hour window.

    Parameters:
        timestamp: Departure datetime.

    Returns:
        1 when hour is in configured peak window, else 0.

    Failure modes:
        None.
    """

    from config import PEAK_HOUR_END, PEAK_HOUR_START

    return 1 if PEAK_HOUR_START <= timestamp.hour <= PEAK_HOUR_END else 0


def is_weekend(timestamp: datetime) -> int:
    """Returns whether departure date is on weekend.

    Parameters:
        timestamp: Departure datetime.

    Returns:
        1 when weekday is Saturday/Sunday, else 0.

    Failure modes:
        None.
    """

    from config import WEEKEND_DAYS

    return 1 if timestamp.weekday() in WEEKEND_DAYS else 0


def weather_severity_score(wind_kph: float, visibility_km: float, weather_penalty: float) -> float:
    """Computes normalized weather severity score on 0-10 scale.

    Parameters:
        wind_kph: Wind speed in km/h.
        visibility_km: Visibility in km.
        weather_penalty: Condition penalty weight.

    Returns:
        Clamped weather severity score in [0, 10].

    Failure modes:
        Applies defaults/clamping for invalid visibility values.
    """

    safe_visibility = max(0.0, visibility_km)
    penalty = weather_penalty if weather_penalty is not None else DEFAULT_WEATHER_PENALTY
    raw = (wind_kph / 10.0) + (10.0 - safe_visibility) + penalty
    return max(WEATHER_SEVERITY_MIN, min(WEATHER_SEVERITY_MAX, raw))


def encode_value(value: str, mapping: dict[str, int]) -> int:
    """Encodes a categorical value using a learned mapping.

    Parameters:
        value: Categorical token.
        mapping: Lookup map from token to integer id.

    Returns:
        Encoded integer id.

    Failure modes:
        Unknown values map to the '<UNK>' bucket if present, else 0.
    """

    normalized = value.upper()
    if normalized in mapping:
        return mapping[normalized]
    if "<UNK>" in mapping:
        return mapping["<UNK>"]
    return 0


def build_feature_row(
    airline_iata: str,
    origin: str,
    destination: str,
    scheduled_departure: datetime,
    weather: dict[str, float | str],
    encoders: dict[str, dict[str, int]],
    route_avg_delay_map: dict[str, float],
) -> dict[str, float]:
    """Builds the exact model feature set used by training and inference.

    Parameters:
        airline_iata: Airline IATA code.
        origin: Origin airport code.
        destination: Destination airport code.
        scheduled_departure: Scheduled departure datetime.
        weather: Weather dictionary containing wind_kph, visibility_km, weather_penalty.
        encoders: Mapping dicts for airline/origin/destination encodings.
        route_avg_delay_map: Historical avg delay map keyed by "ORIGIN-DEST".

    Returns:
        Dict containing the complete feature set.

    Failure modes:
        Unknown categories are mapped to <UNK>/0; unknown routes use default averages.
    """

    route_key = f"{origin}-{destination}"
    weather_penalty = float(weather.get("weather_penalty", DEFAULT_WEATHER_PENALTY))
    wind_kph = float(weather.get("wind_kph", 0.0))
    visibility_km = float(weather.get("visibility_km", 10.0))

    # departure_hour: 0–23 extracted from scheduled departure time.
    departure_hour = float(scheduled_departure.hour)
    # day_of_week: 0–6 where Monday=0.
    day_of_week = float(scheduled_departure.weekday())
    # month: 1–12 calendar month.
    month = float(scheduled_departure.month)
    # airline_encoded: label-encoded airline IATA code.
    airline_encoded = float(encode_value(airline_iata, encoders["airline"]))
    # origin_encoded: label-encoded origin airport IATA code.
    origin_encoded = float(encode_value(origin, encoders["origin"]))
    # dest_encoded: label-encoded destination airport IATA code.
    dest_encoded = float(encode_value(destination, encoders["dest"]))
    # route_avg_delay: historical average delay for this origin→dest route.
    route_avg_delay = float(route_avg_delay_map.get(route_key, DEFAULT_ROUTE_AVG_DELAY_MINUTES))
    # weather_severity: (wind_kph/10) + (10 - visibility_km) + weather_condition_penalty.
    weather_severity = float(weather_severity_score(wind_kph, visibility_km, weather_penalty))
    # is_holiday_week: binary flag for US federal holiday weeks.
    holiday_flag = float(is_holiday_week(scheduled_departure))
    # peak_hour: binary peak-traffic hour flag.
    peak_hour = float(is_peak_hour(scheduled_departure))
    # weekend_flag: binary weekend flag.
    weekend_flag = float(is_weekend(scheduled_departure))
    # distance_km: static airport-pair route distance.
    distance_km = float(get_route_distance_km(origin, destination))

    return {
        "departure_hour": departure_hour,
        "day_of_week": day_of_week,
        "month": month,
        "airline_encoded": airline_encoded,
        "origin_encoded": origin_encoded,
        "dest_encoded": dest_encoded,
        "route_avg_delay": route_avg_delay,
        "weather_severity": weather_severity,
        "is_holiday_week": holiday_flag,
        "peak_hour": peak_hour,
        "weekend_flag": weekend_flag,
        "distance_km": distance_km,
    }


def to_next_hour(timestamp: datetime) -> datetime:
    """Rounds a datetime to the next full hour.

    Parameters:
        timestamp: Input datetime.

    Returns:
        Datetime rounded up to next hour.

    Failure modes:
        None.
    """

    rounded = timestamp.replace(minute=0, second=0, microsecond=0)
    if rounded == timestamp:
        return rounded
    return rounded + timedelta(hours=1)

