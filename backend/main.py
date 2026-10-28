
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_FILE = DATA_DIR / "processed.csv"
DAILY_METRICS_FILE = DATA_DIR / "daily_metrics.csv"

app = FastAPI(
    title="UK Wind Forecasting API",
    description="January 2026 wind generation and forecast evaluation",
    version="1.0.0",
)

# Allow the Vite development server to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_processed_data() -> pd.DataFrame:
    if not PROCESSED_FILE.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Processed data not found. "
                "Run backend/processor.py first."
            ),
        )

    try:
        df = pd.read_csv(PROCESSED_FILE)
    except (OSError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to read processed data.",
        ) from exc

    required = {
        "startTime",
        "actual_mw",
        "forecast_mw",
    }

    missing = required - set(df.columns)

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Processed CSV is missing columns: {sorted(missing)}",
        )

    df["startTime"] = pd.to_datetime(
        df["startTime"], utc=True, errors="coerce"
    )

    for column in ["actual_mw", "forecast_mw"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    df["absolute_error_mw"] = df["error_mw"].abs()
    df["squared_error_mw"] = df["error_mw"] ** 2

    df = df.dropna(
        subset=["startTime", "actual_mw", "forecast_mw"]
    )

    # Keep only January 2026 delivery timestamps.
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    end = pd.Timestamp("2026-02-01T00:00:00Z")

    df = df[(df["startTime"] >= start) & (df["startTime"] < end)]

    if df["startTime"].duplicated().any():
        raise HTTPException(
            status_code=500,
            detail="Processed data contains duplicate hourly timestamps.",
        )

    return df.sort_values("startTime")


@app.get("/")
def root():
    return {
        "name": "UK Wind Forecasting API",
        "status": "running",
        "period": "January 2026",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/data")
def get_generation_data(
    start_date: str = Query("2026-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query("2026-01-31", pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    # Dates are interpreted as UTC delivery dates.
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    if start_date < "2026-01-01" or end_date > "2026-01-31":
        raise HTTPException(
            status_code=400,
            detail="Dates must fall within January 2026.",
        )

    df = load_processed_data()

    start = pd.Timestamp(f"{start_date}T00:00:00Z")
    end = pd.Timestamp(f"{end_date}T00:00:00Z") + pd.Timedelta(days=1)

    df = df[(df["startTime"] >= start) & (df["startTime"] < end)]

    records = []
    for row in df.itertuples(index=False):
        records.append({
            "startTime": row.startTime.isoformat(),
            "actual_mw": float(row.actual_mw),
            "forecast_mw": float(row.forecast_mw),
            "error_mw": float(row.error_mw),
            "absolute_error_mw": float(row.absolute_error_mw),
        })

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "count": len(records),
        "data": records,
    }


@app.get("/api/metrics")
def get_metrics(
    start_date: str = Query("2026-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query("2026-01-31", pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    if start_date < "2026-01-01" or end_date > "2026-01-31":
        raise HTTPException(
            status_code=400,
            detail="Dates must fall within January 2026.",
        )

    df = load_processed_data()

    start = pd.Timestamp(f"{start_date}T00:00:00Z")
    end = pd.Timestamp(f"{end_date}T00:00:00Z") + pd.Timedelta(days=1)

    df = df[(df["startTime"] >= start) & (df["startTime"] < end)]

    if df.empty:
        return {
            "count": 0,
            "mae_mw": None,
            "rmse_mw": None,
            "bias_mw": None,
        }

    errors = df["forecast_mw"] - df["actual_mw"]

    return {
        "count": int(len(df)),
        "mae_mw": float(errors.abs().mean()),
        "rmse_mw": float((errors.pow(2).mean()) ** 0.5),
        "bias_mw": float(errors.mean()),
        "average_actual_mw": float(df["actual_mw"].mean()),
        "average_forecast_mw": float(df["forecast_mw"].mean()),
    }


@app.get("/api/daily-metrics")
def get_daily_metrics():
    if not DAILY_METRICS_FILE.exists():
        raise HTTPException(
            status_code=503,
            detail="Daily metrics not found. Run backend/metrics.py first.",
        )

    try:
        df = pd.read_csv(DAILY_METRICS_FILE)
    except (OSError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to read daily metrics.",
        ) from exc

    return {"data": df.where(pd.notna(df), None).to_dict(orient="records")}
