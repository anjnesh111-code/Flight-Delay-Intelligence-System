"""Utility script to fetch sample live-flight records for pipeline debugging."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.services.aviation_api import AviationAPIService


async def fetch(flight_number: str) -> dict:
    """Fetches one flight record from AviationStack or fallback simulation.

    Parameters:
        flight_number: Flight number to query.

    Returns:
        Flight record dictionary.

    Failure modes:
        Service layer returns simulated data when external API is unavailable.
    """

    service = AviationAPIService()
    return await service.get_flight(flight_number)


def main() -> None:
    """CLI entrypoint for flight-data fetch utility."""

    parser = argparse.ArgumentParser(description="Fetch one live flight record.")
    parser.add_argument("--flight-number", default="AA123", help="Flight number (e.g., AA123)")
    args = parser.parse_args()
    record = asyncio.run(fetch(args.flight_number))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

