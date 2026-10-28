# WindScope — UK Wind Forecasting & Evaluation

**A full-stack dashboard for comparing day-ahead UK wind generation forecasts with actual generation.**

WindScope helps a day-ahead electricity trading team evaluate forecast performance over January 2026. It visualizes forecast and actual generation, calculates forecast error metrics, and allows users to inspect a selected delivery period.

## Live Demo

- **Frontend:** https://nshvu-eta.vercel.app/
- **Backend API:** https://nshvu.onrender.com
- **API health check:** https://nshvu.onrender.com/api/health
- **API documentation:** https://nshvu.onrender.com/docs

The dashboard uses Elexon national wind generation data. The evaluation period is January 1–31, 2026.

## Features

- Interactive hourly chart comparing actual and forecast wind generation.
- Date-range selection for inspecting a delivery period.
- KPI cards for Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), forecast bias, and matched hourly records.
- Summary panel describing the selected period.
- Python API for retrieving processed generation data and metrics.
- Docker-based local development for the frontend and backend.
- Public deployment using Vercel and Render.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Styling | Tailwind CSS v4, custom CSS |
| Visualization | Recharts |
| Icons | Lucide React |
| Backend | Python, FastAPI |
| Data processing | pandas, NumPy |
| Data source | Elexon BMRS |
| Containerization | Docker, Docker Compose |
| Frontend hosting | Vercel |
| Backend hosting | Render |

## Architecture

```text
Elexon BMRS API
      |
      v
Python data fetching
      |
      v
Data processing
  - Filter January 2026
  - Select forecast vintage
  - Aggregate actual generation hourly
  - Match delivery timestamps
  - Calculate forecast errors
      |
      v
Processed CSV data
      |
      v
FastAPI backend
  /api/data
  /api/metrics
  /api/daily-metrics
  /api/health
      |
      v
React + TypeScript dashboard
      |
      v
Vercel deployment
```

## Data Sources

WindScope uses Elexon BMRS national generation data:

- **FUELHH:** actual generation records filtered to `fuelType=WIND`. Relevant fields include `startTime` and `generation`.
- **WINDFOR:** wind generation forecasts. Relevant fields include `startTime`, `publishTime`, and `generation`.

The delivery period is January 2026. Forecast publication timestamps are important because an evaluation for day-ahead trading should use only information available by the relevant purchasing decision time.

## Data Processing Methodology

The processing pipeline prepares actual and forecast generation for comparison.

1. **Filter the evaluation period:** retain delivery records belonging to January 2026.
2. **Process actual generation:** convert generation values to numeric MW values, resolve duplicate records, and aggregate half-hourly actual observations into hourly averages. The implementation requires two half-hour intervals for a complete hourly aggregate.
3. **Select forecast vintages:** for each delivery hour, select the latest forecast publication timestamp at or before the configured cutoff. The current implementation uses 16:00 UK time on the preceding calendar day; this cutoff must be confirmed against the assignment's decision-time requirement.
4. **Match delivery timestamps:** join hourly actuals and selected forecasts on their delivery timestamps.
5. **Calculate errors:** compute forecast error and absolute error for each matched hour.

The resulting processed dataset contains the hourly actual and forecast generation values used by the API and dashboard.

### Evaluation Assumptions and Limitations

- The 16:00 UK day-ahead cutoff is an implementation assumption that should be verified against the intended purchasing decision time.
- Actual and forecast timestamps must use consistent timezone handling and delivery-interval conventions.
- The forecast `generation` field must be confirmed to use MW, comparable to the actual-generation values.
- Duplicate resolution and incomplete-hour exclusion should be checked against the raw source records.
- Complete timestamp coverage does not by itself prove that the forecast vintage was available at decision time.
- Forecast accuracy metrics describe the selected records and should not be interpreted as independently audited trading-time accuracy until these assumptions have been verified.

## Forecast Accuracy Metrics

Let \(F_t\) be forecast generation and \(A_t\) be actual generation for matched hour \(t\). Define the error as:

\[
e_t = F_t - A_t
\]

### Mean Absolute Error (MAE)

\[
MAE = \frac{1}{n}\sum_{t=1}^{n}|e_t|
\]

Measures the average absolute forecast error in MW. Lower is better.

### Root Mean Squared Error (RMSE)

\[
RMSE = \sqrt{\frac{1}{n}\sum_{t=1}^{n}e_t^2}
\]

Penalizes larger errors more heavily. Lower is better.

### Forecast Bias

\[
Bias = \frac{1}{n}\sum_{t=1}^{n}e_t
\]

- Positive bias: forecasts tend to overestimate generation.
- Negative bias: forecasts tend to underestimate generation.
- Bias near zero: average errors cancel out, which does not necessarily mean individual forecasts are accurate.

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Backend root endpoint |
| `GET /api/health` | Health check |
| `GET /api/data?start_date=2026-01-01&end_date=2026-01-02` | Matched hourly generation data |
| `GET /api/metrics?start_date=2026-01-01&end_date=2026-01-31` | Aggregate error metrics |
| `GET /api/daily-metrics` | Daily evaluation metrics |
| `GET /docs` | Interactive FastAPI documentation |

The data endpoint returns the selected period, record count, and hourly records containing actual generation, forecast generation, forecast error, and absolute error.

## Project Structure

```text
uk-wind-forecasting/
├── backend/
│   ├── main.py
│   ├── data_fetcher.py
│   ├── processor.py
│   ├── metrics.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── data/
│       ├── actuals.json
│       ├── forecasts.json
│       ├── processed.csv
│       └── daily_metrics.csv
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Run Locally

### Prerequisites

- Python 3.11 or a compatible Python version
- Node.js and npm
- Docker Desktop with Docker Compose (for containerized execution)

### Option 1: Run with Docker

From the project root:

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- Backend health check: http://localhost:8000/api/health
- API documentation: http://localhost:8000/docs

Stop the containers with `Ctrl+C`. To stop and remove them from another terminal, run:

```bash
docker compose down
```

### Option 2: Run without Docker

Start the backend in one terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend development server uses `VITE_API_BASE_URL` to identify the backend. For local development, set it to:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Keep local environment files out of Git. Use `.env.example` to document placeholder configuration.

### Production Build

From the `frontend` directory:

```bash
npm ci
npm run build
```

Vite generates the production frontend in `frontend/dist`.

## Deployment

- **Frontend:** deployed to Vercel.
- **Backend:** deployed to Render using Docker.
- **API configuration:** the frontend uses `VITE_API_BASE_URL` to call the deployed backend.
- **CORS:** the backend must allow the deployed Vercel origin as well as the required local development origins.

Live application: https://nshvu-eta.vercel.app/

## AI Tools

AI assistance was used during development to help with implementation, debugging, UI development, Docker configuration, documentation, and deployment troubleshooting. The project uses explicit data-processing code and metric formulas for its calculations; AI assistance does not independently validate forecast accuracy.

## Future Improvements

- Verify the forecast publication cutoff against the precise trading decision time.
- Add explicit timestamp normalization and validation for all source records.
- Report missing and duplicate records before and after processing.
- Add tests for forecast-vintage selection and hourly aggregation.
- Include daily and time-of-day error breakdowns.
- Add automated data-quality checks and reproducible evaluation reports.
- Improve production monitoring and API error reporting.

## Summary

WindScope provides an interactive way to inspect hourly UK wind generation forecasts against actual generation for January 2026. It combines a React dashboard, a Python API, data-processing scripts, and containerized deployment. Its forecast accuracy results should be interpreted alongside the documented forecast-cutoff and data-alignment assumptions.
