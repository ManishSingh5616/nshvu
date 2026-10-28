
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
UK_TZ = ZoneInfo("Europe/London")

DELIVERY_START = pd.Timestamp("2026-01-01T00:00:00Z")
DELIVERY_END = pd.Timestamp("2026-02-01T00:00:00Z")

EXPECTED_HALF_HOURLY_INTERVALS = 31 * 48
EXPECTED_HOURLY_INTERVALS = 31 * 24

DECISION_HOUR_UK = 16



def load_json(filename: str) -> pd.DataFrame:

    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist. Run data_fetcher.py first."
        )

    with path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(f"{filename} must contain a JSON array.")

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError(
            f"{filename} contains no records. Check the API response "
            "and publication-time filters."
        )

    return df


def parse_timestamp(
    df: pd.DataFrame,
    column: str,
) -> pd.DataFrame:

    if column not in df.columns:
        raise ValueError(
            f"Required timestamp '{column}' is missing. "
            f"Available columns: {list(df.columns)}"
        )

    df = df.copy()
    df[column] = pd.to_datetime(
        df[column],
        utc=True,
        errors="coerce",
    )

    return df



def load_actuals() -> pd.DataFrame:
    """Load half-hourly actual wind generation."""

    actuals = load_json("actuals.json")

    required = {"startTime", "publishTime", "fuelType", "generation"}
    missing = required - set(actuals.columns)

    if missing:
        raise ValueError(
            f"Actuals are missing required columns: {sorted(missing)}"
        )

    actuals = parse_timestamp(actuals, "startTime")
    actuals = parse_timestamp(actuals, "publishTime")

    actuals["generation"] = pd.to_numeric(
        actuals["generation"],
        errors="coerce",
    )

    actuals = actuals[
        actuals["fuelType"].astype(str).str.upper().eq("WIND")
    ].copy()

    actuals = actuals.dropna(
        subset=["startTime", "publishTime", "generation"]
    )

    # Filter by delivery time, not publication time.
    actuals = actuals[
        (actuals["startTime"] >= DELIVERY_START)
        & (actuals["startTime"] < DELIVERY_END)
    ].copy()

    # Retain the most recently published version of each interval.
    actuals = actuals.sort_values("publishTime")
    actuals = actuals.drop_duplicates(
        subset=["startTime"],
        keep="last",
    )

    return actuals[["startTime", "generation"]].rename(
        columns={"generation": "actual_mw"}
    )



def load_forecasts() -> pd.DataFrame:
    """Load forecast records with their publication timestamps."""

    forecasts = load_json("forecasts.json")

    required = {"startTime", "publishTime", "generation"}
    missing = required - set(forecasts.columns)

    if missing:
        raise ValueError(
            f"Forecasts are missing required columns: {sorted(missing)}"
        )

    forecasts = parse_timestamp(forecasts, "startTime")
    forecasts = parse_timestamp(forecasts, "publishTime")

    forecasts["generation"] = pd.to_numeric(
        forecasts["generation"],
        errors="coerce",
    )

    forecasts = forecasts.dropna(
        subset=["startTime", "publishTime", "generation"]
    )

    # Keep January delivery timestamps only.
    forecasts = forecasts[
        (forecasts["startTime"] >= DELIVERY_START)
        & (forecasts["startTime"] < DELIVERY_END)
    ].copy()

    forecasts = forecasts.rename(
        columns={"generation": "forecast_mw"}
    )

    # Remove duplicate copies of the same published forecast.
    forecasts = forecasts.drop_duplicates(
        subset=["startTime", "publishTime"],
        keep="last",
    )

    return forecasts[
        ["startTime", "publishTime", "forecast_mw"]
    ]



def get_decision_cutoff(start_time: pd.Timestamp) -> pd.Timestamp:
    """
    Illustrative rule: 16:00 UK time on the preceding calendar day.

    Confirm the client's required purchasing decision cutoff before
    treating this assumption as the final evaluation methodology.
    """

    delivery_local = start_time.tz_convert(UK_TZ)
    previous_date = delivery_local.date() - pd.Timedelta(days=1)

    cutoff_local = pd.Timestamp(
        f"{previous_date.isoformat()} {DECISION_HOUR_UK:02d}:00:00",
        tz=UK_TZ,
    )

    return cutoff_local.tz_convert("UTC")


def select_forecasts(forecasts: pd.DataFrame) -> pd.DataFrame:
    """
    Select the latest forecast published by the decision cutoff
    for each delivery timestamp.
    """

    columns = ["startTime", "publishTime", "forecast_mw"]

    if forecasts.empty:
        return pd.DataFrame(columns=columns)

    selected_rows = []

    for start_time, group in forecasts.groupby("startTime", sort=True):
        cutoff = get_decision_cutoff(start_time)

        eligible = group[group["publishTime"] <= cutoff]

        if eligible.empty:
            continue

        selected = eligible.loc[eligible["publishTime"].idxmax()]
        selected_rows.append(selected)

    if not selected_rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(selected_rows)[columns].reset_index(drop=True)



def aggregate_actuals_hourly(
    actuals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate hourly average generation from half-hourly actuals.

    An hour is retained only when both half-hourly intervals are
    present. This prevents incomplete hours from being treated as
    complete hourly observations.
    """

    if actuals.empty:
        return pd.DataFrame(columns=["startTime", "actual_mw"])

    actuals = actuals.copy()

    actuals["hour"] = actuals["startTime"].dt.floor("h")

    grouped = actuals.groupby("hour")["actual_mw"].agg(
        actual_mw="mean",
        interval_count="count",
    )

    # Require two half-hourly readings per hour.
    grouped = grouped[grouped["interval_count"] == 2]

    hourly = grouped.reset_index().rename(
        columns={"hour": "startTime"}
    )

    return hourly[["startTime", "actual_mw"]]



def process_data() -> pd.DataFrame:
    print("Loading actual generation...")
    actuals = load_actuals()

    print("Loading forecasts...")
    forecasts = load_forecasts()

    print("Selecting eligible day-ahead forecasts...")
    selected_forecasts = select_forecasts(forecasts)

    print("Aggregating half-hourly actuals to hourly averages...")
    hourly_actuals = aggregate_actuals_hourly(actuals)

    print("Merging actuals and forecasts...")

    # Exact hourly timestamp matching; no forecast interpolation.
    merged = hourly_actuals.merge(
        selected_forecasts,
        on="startTime",
        how="inner",
        validate="one_to_one",
    )

    merged["error_mw"] = (
        merged["forecast_mw"] - merged["actual_mw"]
    )

    merged["absolute_error_mw"] = merged["error_mw"].abs()

    merged["squared_error"] = merged["error_mw"] ** 2

    merged["delivery_date"] = (
        merged["startTime"]
        .dt.tz_convert(UK_TZ)
        .dt.strftime("%Y-%m-%d")
    )

    merged = merged.sort_values("startTime").reset_index(drop=True)

    output_path = DATA_DIR / "processed.csv"
    merged.to_csv(output_path, index=False)

    # --------------------------------------------------
    # Coverage diagnostics
    # --------------------------------------------------

    expected_hourly = pd.date_range(
        start=DELIVERY_START,
        end=DELIVERY_END,
        freq="h",
        inclusive="left",
    )

    actual_hour_set = set(hourly_actuals["startTime"])
    forecast_hour_set = set(selected_forecasts["startTime"])
    matched_hour_set = set(merged["startTime"])

    print("\n" + "=" * 48)
    print("JANUARY 2026 DATA PROCESSING SUMMARY")
    print("=" * 48)

    print(f"Raw actual records:              {len(actuals):,}")
    print(f"Raw forecast records:            {len(forecasts):,}")
    print(f"Selected forecast intervals:     {len(selected_forecasts):,}")
    print(f"Complete hourly actuals:         {len(hourly_actuals):,}")
    print(f"Expected half-hour intervals:    {EXPECTED_HALF_HOURLY_INTERVALS:,}")
    print(f"Expected hourly intervals:       {EXPECTED_HOURLY_INTERVALS:,}")
    print(f"Expected UTC hour timestamps:    {len(expected_hourly):,}")
    print(f"Hours with actuals:               {len(actual_hour_set):,}")
    print(f"Hours with selected forecasts:    {len(forecast_hour_set):,}")
    print(f"Matched evaluation hours:         {len(matched_hour_set):,}")

    coverage = (
        len(matched_hour_set) / len(expected_hourly) * 100
        if len(expected_hourly)
        else 0.0
    )

    print(f"Matched hourly coverage:          {coverage:.2f}%")
    print(f"Saved processed data:             {output_path}")

    if merged.empty:
        print(
            "\nWARNING: No matched intervals. Check forecast timestamps, "
            "publication cutoff, and downloaded date ranges."
        )
    elif len(merged) < len(expected_hourly):
        print(
            "\nWARNING: Evaluation coverage is incomplete. "
            "Investigate missing actuals and eligible forecasts."
        )

    return merged


if __name__ == "__main__":
    process_data()
