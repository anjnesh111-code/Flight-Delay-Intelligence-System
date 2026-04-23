"""Utility script to fetch weather by airport for feature debugging."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.services.weather_api import WeatherAPIService


async def fetch(airport_iata: str) -> dict:
    """Fetches weather for an airport from live API or simulated fallback.

    Parameters:
        airport_iata: Airport IATA code.

    Returns:
        Weather dictionary.

    Failure modes:
        Service layer catches API failures and returns simulated records.
    """

    service = WeatherAPIService()
    return await service.get_weather_for_airport(airport_iata)


def main() -> None:
    """CLI entrypoint for weather fetch utility."""

    parser = argparse.ArgumentParser(description="Fetch weather by airport IATA code.")
    parser.add_argument("--airport", default="JFK", help="IATA code")
    args = parser.parse_args()
    record = asyncio.run(fetch(args.airport))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

