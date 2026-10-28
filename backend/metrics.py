
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).parent / "data"
PROCESSED_FILE = DATA_DIR / "processed.csv"
DAILY_OUTPUT_FILE = DATA_DIR / "daily_metrics.csv"

EXPECTED_HOURLY_INTERVALS = 31 * 24



def load_processed_data() -> pd.DataFrame:
    """Load and validate the processed evaluation dataset."""

    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"{PROCESSED_FILE} not found. Run processor.py first."
        )

    df = pd.read_csv(PROCESSED_FILE)

    required_columns = [
        "startTime",
        "actual_mw",
        "forecast_mw",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df["startTime"] = pd.to_datetime(
        df["startTime"], utc=True, errors="coerce"
    )

    for column in ["actual_mw", "forecast_mw"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(
        subset=["startTime", "actual_mw", "forecast_mw"]
    ).copy()

    if df.empty:
        raise ValueError("No valid evaluation records found.")

    if df["startTime"].duplicated().any():
        duplicates = int(df["startTime"].duplicated().sum())
        raise ValueError(
            f"Found {duplicates} duplicate delivery timestamps. "
            "Fix processor.py before calculating metrics."
        )

    start = pd.Timestamp("2026-01-01T00:00:00Z")
    end = pd.Timestamp("2026-02-01T00:00:00Z")

    df = df[
        (df["startTime"] >= start)
        & (df["startTime"] < end)
    ].copy()

    if df.empty:
        raise ValueError("No January 2026 records remain.")

    # Recalculate errors from the source values so that stale
    # error columns cannot affect the results.
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    df["absolute_error_mw"] = df["error_mw"].abs()
    df["squared_error"] = df["error_mw"] ** 2

    df = df.sort_values("startTime").reset_index(drop=True)

    return df


def calculate_metrics(df: pd.DataFrame) -> dict:
    """Calculate monthly wind forecast accuracy metrics."""

    actual = df["actual_mw"].to_numpy(dtype=float)
    forecast = df["forecast_mw"].to_numpy(dtype=float)

    errors = forecast - actual
    absolute_errors = np.abs(errors)

    mae = np.mean(absolute_errors)
    rmse = np.sqrt(np.mean(errors ** 2))
    bias = np.mean(errors)

    average_actual = np.mean(actual)
    average_forecast = np.mean(forecast)

    relative_mae = (
        mae / abs(average_actual) * 100
        if average_actual != 0
        else None
    )

    expected = EXPECTED_HOURLY_INTERVALS
    matched = len(df)

    return {
        "period": "2026-01",
        "interval_minutes": 60,
        "expected_intervals": expected,
        "matched_intervals": matched,
        "coverage_percent": round(
            matched / expected * 100, 2
        ),
        "mae_mw": round(float(mae), 2),
        "rmse_mw": round(float(rmse), 2),
        "bias_mw": round(float(bias), 2),
        "average_actual_mw": round(
            float(average_actual), 2
        ),
        "average_forecast_mw": round(
            float(average_forecast), 2
        ),
        "maximum_absolute_error_mw": round(
            float(np.max(absolute_errors)), 2
        ),
        "relative_mae_percent": (
            round(float(relative_mae), 2)
            if relative_mae is not None
            else None
        ),
    }


def calculate_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate accuracy metrics for each delivery date."""

    data = df.copy()

    # Use the UK delivery date for daily reporting.
    data["delivery_date"] = (
        data["startTime"]
        .dt.tz_convert("Europe/London")
        .dt.strftime("%Y-%m-%d")
    )

    rows = []

    for delivery_date, group in data.groupby(
        "delivery_date", sort=True
    ):
        actual = group["actual_mw"].to_numpy(dtype=float)
        forecast = group["forecast_mw"].to_numpy(dtype=float)

        errors = forecast - actual

        rows.append({
            "date": delivery_date,
            "interval_count": len(group),
            "average_actual_mw": round(
                float(np.mean(actual)), 2
            ),
            "average_forecast_mw": round(
                float(np.mean(forecast)), 2
            ),
            "mae_mw": round(
                float(np.mean(np.abs(errors))), 2
            ),
            "rmse_mw": round(
                float(np.sqrt(np.mean(errors ** 2))), 2
            ),
            "bias_mw": round(
                float(np.mean(errors)), 2
            ),
        })

    return pd.DataFrame(rows)



def main() -> None:
    print("Loading processed data...")
    df = load_processed_data()

    print("Calculating monthly metrics...")
    metrics = calculate_metrics(df)

    print("\nMONTHLY WIND FORECAST EVALUATION")
    print("=" * 45)

    for key, value in metrics.items():
        print(f"{key}: {value}")

    print("\nCalculating daily metrics...")
    daily_metrics = calculate_daily_metrics(df)
    daily_metrics.to_csv(DAILY_OUTPUT_FILE, index=False)

    print(f"\nDaily metrics saved to: {DAILY_OUTPUT_FILE}")
    print(f"Delivery days represented: {len(daily_metrics)}")

    if metrics["matched_intervals"] != EXPECTED_HOURLY_INTERVALS:
        print(
            "\nWARNING: Coverage is incomplete. Investigate missing "
            "delivery intervals before presenting the evaluation."
        )

    print(
        "\nMethodology note: results use the forecast selection and "
        "hourly aggregation rules defined in processor.py. Verify "
        "the decision cutoff and forecast resolution before treating "
        "these results as final."
    )


if __name__ == "__main__":
    main()
