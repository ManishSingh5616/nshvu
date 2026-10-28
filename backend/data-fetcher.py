
import json
import sys
from pathlib import Path

import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ACTUALS_PUBLISH_FROM = "2026-01-01T00:00:00Z"
ACTUALS_PUBLISH_TO = "2026-02-01T00:30:00Z"

FORECASTS_PUBLISH_FROM = "2025-12-30T00:00:00Z"
FORECASTS_PUBLISH_TO = "2026-01-31T23:59:59Z"

TIMEOUT_SECONDS = 120

SESSION = requests.Session()
SESSION.headers.update({"accept": "application/json"})



def fetch_dataset(
    dataset: str,
    publish_from: str,
    publish_to: str,
    wind_only: bool = False,
) -> list[dict]:

    url = f"{BASE_URL}/{dataset}/stream"

    params = {
        "publishDateTimeFrom": publish_from,
        "publishDateTimeTo": publish_to,
    }

    if wind_only:
        params["fuelType"] = "WIND"

    print(f"\nDownloading {dataset}...")
    print(f"Publication range: {publish_from} to {publish_to}")

    try:
        response = SESSION.get(
            url,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to download {dataset}: {exc}"
        ) from exc

    try:
        records = response.json()
    except requests.exceptions.JSONDecodeError:
        
        records = []

        for line in response.text.splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON returned by {dataset}."
                    ) from exc

    if isinstance(records, dict):
        records = records.get("data", [records])

    if not isinstance(records, list):
        raise ValueError(
            f"Unexpected response format from {dataset}: "
            f"{type(records).__name__}"
        )

    if not all(isinstance(record, dict) for record in records):
        raise ValueError(
            f"{dataset} returned records that are not JSON objects."
        )

    print(f"Downloaded {len(records):,} records from {dataset}.")

    return records



def save_json(filename: str, records: list[dict]) -> None:

    output_path = DATA_DIR / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)

    print(f"Saved {len(records):,} records to {output_path}")


def main() -> None:
    try:
        # 1. Download actual wind generation.
        actuals = fetch_dataset(
            dataset="FUELHH",
            publish_from=ACTUALS_PUBLISH_FROM,
            publish_to=ACTUALS_PUBLISH_TO,
            wind_only=True,
        )

        # Defensive filtering in case the API returns other fuel types.
        actuals = [
            record
            for record in actuals
            if str(record.get("fuelType", "")).upper() == "WIND"
        ]

        save_json("actuals.json", actuals)

        # 2. Download wind forecasts, retaining all publication vintages.
        forecasts = fetch_dataset(
            dataset="WINDFOR",
            publish_from=FORECASTS_PUBLISH_FROM,
            publish_to=FORECASTS_PUBLISH_TO,
        )

        save_json("forecasts.json", forecasts)

        print("\n" + "=" * 45)
        print("DOWNLOAD SUMMARY")
        print("=" * 45)
        print(f"Actual wind records: {len(actuals):,}")
        print(f"Forecast records:    {len(forecasts):,}")
        print(f"Output directory:    {DATA_DIR}")
        print("\nDownload completed successfully.")

    except (RuntimeError, ValueError, OSError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
