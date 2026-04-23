"""Data preprocessing helper for Kaggle flight delay dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def preprocess_csv(input_path: Path, output_path: Path) -> Path:
    """Preprocesses flights.csv into a compact modeling subset.

    Parameters:
        input_path: Path to raw Kaggle flights.csv file.
        output_path: Path where cleaned CSV should be written.

    Returns:
        Output path of processed CSV.

    Failure modes:
        Propagates IO and parsing errors if file paths are invalid.
    """

    required = ["FL_DATE", "MONTH", "DAY_OF_WEEK", "OP_CARRIER", "ORIGIN", "DEST", "CRS_DEP_TIME", "DEP_DELAY"]
    frame = pd.read_csv(input_path, low_memory=False)
    cleaned = frame[required].dropna()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    """CLI entrypoint for preprocessing script."""

    parser = argparse.ArgumentParser(description="Preprocess raw flight delay data.")
    parser.add_argument("--input", required=True, help="Path to raw flights.csv")
    parser.add_argument("--output", required=True, help="Path for cleaned output csv")
    args = parser.parse_args()
    output = preprocess_csv(Path(args.input), Path(args.output))
    print(f"Wrote preprocessed file to {output}")


if __name__ == "__main__":
    main()

