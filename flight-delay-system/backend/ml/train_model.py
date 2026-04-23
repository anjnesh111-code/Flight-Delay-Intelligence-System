"""Training script for the flight delay prediction model bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier, XGBRegressor

from config import (
    APP_VERSION,
    MODEL_BUNDLE_PATH,
    TRAINING_RANDOM_SEED,
    TRAINING_SAMPLE_ROWS,
    TRAINING_TEST_SIZE,
    XGB_CLASSIFIER_PARAMS,
    XGB_REGRESSOR_PARAMS,
)
from ml.features import build_feature_row

RANDOM_GENERATOR = np.random.default_rng(TRAINING_RANDOM_SEED)


def _parse_crs_dep_time(value: int) -> tuple[int, int]:
    """Converts HHMM integer values into hour/minute tuple.

    Parameters:
        value: CRS_DEP_TIME integer from dataset.

    Returns:
        Tuple of (hour, minute).

    Failure modes:
        Invalid values default to 12:00.
    """

    try:
        raw = f"{int(value):04d}"
        hour = min(23, max(0, int(raw[:2])))
        minute = min(59, max(0, int(raw[2:])))
        return hour, minute
    except (TypeError, ValueError):
        return 12, 0


def _fit_encoder(values: pd.Series) -> dict[str, int]:
    """Creates a deterministic label-encoding map with unknown bucket.

    Parameters:
        values: Categorical series.

    Returns:
        Dict mapping category token to integer id.

    Failure modes:
        Empty series still yields '<UNK>' mapping.
    """

    categories = sorted({str(v).upper() for v in values.dropna().tolist()})
    mapping = {"<UNK>": 0}
    mapping.update({value: index + 1 for index, value in enumerate(categories)})
    return mapping


def _synthetic_training_data(row_count: int) -> pd.DataFrame:
    """Generates realistic synthetic training data when Kaggle files are unavailable.

    Parameters:
        row_count: Number of synthetic rows.

    Returns:
        DataFrame compatible with preprocessing pipeline.

    Failure modes:
        None; fully local data generation.
    """

    airlines = np.array(["AA", "UA", "DL", "WN", "B6", "AS", "NK", "F9"])
    airports = np.array(["JFK", "LAX", "SFO", "ORD", "ATL", "DFW", "DEN", "SEA", "MIA", "BOS"])
    base_date = datetime(2015, 1, 1)
    dates = [base_date + timedelta(days=int(RANDOM_GENERATOR.integers(0, 365))) for _ in range(row_count)]
    origins = RANDOM_GENERATOR.choice(airports, size=row_count)
    destinations = []
    for origin in origins:
        choices = airports[airports != origin]
        destinations.append(RANDOM_GENERATOR.choice(choices))
    dep_hours = RANDOM_GENERATOR.integers(0, 24, size=row_count)
    dep_mins = RANDOM_GENERATOR.choice(np.array([0, 10, 15, 20, 30, 40, 45, 50]), size=row_count)
    dep_time = dep_hours * 100 + dep_mins

    route_risk = RANDOM_GENERATOR.normal(16, 8, size=row_count)
    weather_signal = RANDOM_GENERATOR.uniform(0, 10, size=row_count)
    peak_signal = np.where((dep_hours >= 16) & (dep_hours <= 21), 8, 0)
    holiday_signal = np.array([1 if (abs((d - datetime(d.year, 12, 25)).days) <= 3 or abs((d - datetime(d.year, 11, 28)).days) <= 3) else 0 for d in dates])
    dep_delay = np.maximum(0, route_risk + weather_signal * 2 + peak_signal + holiday_signal * 6 + RANDOM_GENERATOR.normal(0, 7, size=row_count))

    dataset = pd.DataFrame(
        {
            "FL_DATE": [d.strftime("%Y-%m-%d") for d in dates],
            "MONTH": [d.month for d in dates],
            "DAY_OF_WEEK": [d.weekday() + 1 for d in dates],
            "OP_CARRIER": RANDOM_GENERATOR.choice(airlines, size=row_count),
            "ORIGIN": origins,
            "DEST": destinations,
            "CRS_DEP_TIME": dep_time.astype(int),
            "DEP_DELAY": dep_delay,
        }
    )
    return dataset


def load_dataset(data_path: Path | None, sample: bool) -> pd.DataFrame:
    """Loads Kaggle dataset or falls back to synthetic data.

    Parameters:
        data_path: Optional local path to flights.csv.
        sample: Whether to downsample to 50k rows.

    Returns:
        Raw dataframe for feature processing.

    Failure modes:
        Missing/unreadable files automatically switch to synthetic fallback data.
    """

    target_rows = TRAINING_SAMPLE_ROWS if sample else 200_000
    if data_path is None or not data_path.exists():
        return _synthetic_training_data(target_rows)

    frame = pd.read_csv(data_path, low_memory=False)
    required_columns = ["FL_DATE", "MONTH", "DAY_OF_WEEK", "OP_CARRIER", "ORIGIN", "DEST", "CRS_DEP_TIME", "DEP_DELAY"]
    frame = frame[required_columns].dropna()
    if sample and len(frame) > TRAINING_SAMPLE_ROWS:
        frame = frame.sample(TRAINING_SAMPLE_ROWS, random_state=TRAINING_RANDOM_SEED)
    return frame


def build_training_frame(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, int]], dict[str, float]]:
    """Transforms raw rows into model-ready features and targets.

    Parameters:
        raw_df: Raw flight rows.

    Returns:
        Tuple of (feature dataframe with labels, categorical encoders, route avg map).

    Failure modes:
        Invalid dates/times are coerced and rows with irrecoverable values are dropped.
    """

    work_df = raw_df.copy().reset_index(drop=True)
    work_df["FL_DATE"] = pd.to_datetime(work_df["FL_DATE"], errors="coerce")
    work_df = work_df.dropna(subset=["FL_DATE", "OP_CARRIER", "ORIGIN", "DEST", "DEP_DELAY"])

    dep_time_components = work_df["CRS_DEP_TIME"].apply(_parse_crs_dep_time)
    work_df["dep_hour"] = dep_time_components.apply(lambda x: x[0])
    work_df["dep_minute"] = dep_time_components.apply(lambda x: x[1])
    work_df["scheduled_departure"] = work_df.apply(
        lambda row: row["FL_DATE"].replace(hour=int(row["dep_hour"]), minute=int(row["dep_minute"]), second=0, microsecond=0),
        axis=1,
    )
    work_df["is_delayed"] = (work_df["DEP_DELAY"] > 15).astype(int)

    route_avg_delay_series = work_df.groupby(["ORIGIN", "DEST"])["DEP_DELAY"].mean()
    route_avg_delay_map = {f"{origin}-{dest}": float(avg) for (origin, dest), avg in route_avg_delay_series.items()}

    encoders = {
        "airline": _fit_encoder(work_df["OP_CARRIER"]),
        "origin": _fit_encoder(work_df["ORIGIN"]),
        "dest": _fit_encoder(work_df["DEST"]),
    }

    weather_condition = RANDOM_GENERATOR.choice(np.array(["clear", "clouds", "rain", "thunderstorm"]), size=len(work_df))
    wind = RANDOM_GENERATOR.uniform(4.0, 42.0, size=len(work_df))
    visibility = RANDOM_GENERATOR.uniform(2.0, 10.0, size=len(work_df))
    condition_penalty = pd.Series(weather_condition).map({"clear": 0.0, "clouds": 1.0, "rain": 4.0, "thunderstorm": 8.0}).fillna(2.0).to_numpy()

    features = []
    for index, row in work_df.iterrows():
        weather = {
            "wind_kph": float(wind[index]),
            "visibility_km": float(visibility[index]),
            "weather_penalty": float(condition_penalty[index]),
        }
        feature_row = build_feature_row(
            airline_iata=str(row["OP_CARRIER"]).upper(),
            origin=str(row["ORIGIN"]).upper(),
            destination=str(row["DEST"]).upper(),
            scheduled_departure=row["scheduled_departure"].to_pydatetime(),
            weather=weather,
            encoders=encoders,
            route_avg_delay_map=route_avg_delay_map,
        )
        features.append(feature_row)

    features_df = pd.DataFrame(features)
    features_df["is_delayed"] = work_df["is_delayed"].to_numpy()
    features_df["dep_delay_minutes"] = work_df["DEP_DELAY"].clip(lower=0).to_numpy()
    return features_df, encoders, route_avg_delay_map


def build_analytics_payload(raw_df: pd.DataFrame) -> dict[str, object]:
    """Generates chart-friendly aggregates for dashboard endpoints.

    Parameters:
        raw_df: Raw flight rows with delay values.

    Returns:
        Dict containing heatmap matrix, airline performance table, and delayed routes.

    Failure modes:
        Empty datasets return zero-filled structures.
    """

    if raw_df.empty:
        return {"hourly_heatmap": [], "airline_performance": [], "top_delayed_routes": []}

    work_df = raw_df.copy()
    work_df["FL_DATE"] = pd.to_datetime(work_df["FL_DATE"], errors="coerce")
    dep_time_components = work_df["CRS_DEP_TIME"].apply(_parse_crs_dep_time)
    work_df["dep_hour"] = dep_time_components.apply(lambda x: x[0])
    work_df["day_of_week"] = work_df["FL_DATE"].dt.weekday.fillna(0).astype(int)
    work_df["on_time"] = (work_df["DEP_DELAY"] <= 15).astype(int)

    heatmap = (
        work_df.groupby(["day_of_week", "dep_hour"])["DEP_DELAY"].mean().reset_index().rename(columns={"DEP_DELAY": "avg_delay"})
    )
    airline = (
        work_df.groupby("OP_CARRIER")
        .agg(avg_delay=("DEP_DELAY", "mean"), on_time_pct=("on_time", "mean"), flights=("DEP_DELAY", "size"))
        .reset_index()
    )
    airline["on_time_pct"] = (airline["on_time_pct"] * 100).round(2)
    delayed_routes = (
        work_df.assign(route=work_df["ORIGIN"] + "-" + work_df["DEST"])
        .groupby("route")["DEP_DELAY"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={"DEP_DELAY": "avg_delay"})
    )
    return {
        "hourly_heatmap": heatmap.to_dict(orient="records"),
        "airline_performance": airline.rename(columns={"OP_CARRIER": "airline_iata"}).to_dict(orient="records"),
        "top_delayed_routes": delayed_routes.to_dict(orient="records"),
    }


def train_and_save(data_path: Path | None, sample: bool, output_path: Path) -> None:
    """Runs end-to-end training and writes model bundle to disk.

    Parameters:
        data_path: Optional path to Kaggle flights.csv.
        sample: Whether to train on 50k rows.
        output_path: Joblib output path.

    Returns:
        None.

    Failure modes:
        Propagates training errors to CLI; caller should inspect stack traces.
    """

    raw_df = load_dataset(data_path, sample=sample)
    features_df, encoders, route_avg_delay_map = build_training_frame(raw_df)

    feature_columns = [
        "departure_hour",
        "day_of_week",
        "month",
        "airline_encoded",
        "origin_encoded",
        "dest_encoded",
        "route_avg_delay",
        "weather_severity",
        "is_holiday_week",
        "peak_hour",
        "weekend_flag",
        "distance_km",
    ]

    x = features_df[feature_columns]
    y_class = features_df["is_delayed"]
    y_reg = features_df["dep_delay_minutes"]

    x_train, x_test, y_class_train, y_class_test, y_reg_train, y_reg_test = train_test_split(
        x,
        y_class,
        y_reg,
        test_size=TRAINING_TEST_SIZE,
        random_state=TRAINING_RANDOM_SEED,
        stratify=y_class,
    )

    classifier = XGBClassifier(**XGB_CLASSIFIER_PARAMS)
    classifier.fit(x_train, y_class_train)
    regressor = XGBRegressor(**XGB_REGRESSOR_PARAMS)
    regressor.fit(x_train, y_reg_train)

    class_predictions = classifier.predict(x_test)
    reg_predictions = regressor.predict(x_test)
    rmse = float(np.sqrt(mean_squared_error(y_reg_test, reg_predictions)))

    print(classification_report(y_class_test, class_predictions, digits=4))
    print(f"RMSE: {rmse:.4f}")

    bundle = {
        "version": APP_VERSION,
        "classifier": classifier,
        "regressor": regressor,
        "feature_columns": feature_columns,
        "encoders": encoders,
        "route_avg_delay": route_avg_delay_map,
        "analytics_payload": build_analytics_payload(raw_df),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output_path)
    print(f"Saved model bundle to {output_path}")


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for training workflow.

    Parameters:
        None.

    Returns:
        Parsed argparse namespace.

    Failure modes:
        Standard argparse validation errors for invalid arguments.
    """

    parser = argparse.ArgumentParser(description="Train and persist flight delay model bundle.")
    parser.add_argument("--data-path", type=str, default="", help="Path to Kaggle flights.csv file")
    parser.add_argument("--sample", action="store_true", help="Train on 50k-row sample")
    parser.add_argument("--output", type=str, default=str(MODEL_BUNDLE_PATH), help="Output path for model bundle")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for model training."""

    args = parse_args()
    data_path = Path(args.data_path) if args.data_path else None
    output_path = Path(args.output)
    train_and_save(data_path=data_path, sample=args.sample, output_path=output_path)


if __name__ == "__main__":
    main()

