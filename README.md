# WindScope — UK Wind Forecasting & Evaluation

A full-stack dashboard for comparing day-ahead UK wind generation forecasts with actual generation.

WindScope helps a day-ahead electricity trading team evaluate forecast performance over **January 2026**. It visualizes forecast and actual generation, calculates forecast error metrics, and allows users to inspect a selected delivery period.

---

## Live Demo & Links

* **Frontend:** [https://nshvu-eta.vercel.app/](https://nshvu-eta.vercel.app/)
* **Backend API:** [https://nshvu.onrender.com](https://nshvu.onrender.com)
* **API Health Check:** [https://nshvu.onrender.com/api/health](https://nshvu.onrender.com/api/health)
* **API Documentation:** [https://nshvu.onrender.com/docs](https://nshvu.onrender.com/docs)

The dashboard uses Elexon national wind generation data. The evaluation period is **January 1–31, 2026**.

---

## Features

* Interactive hourly chart comparing actual and forecast wind generation.
* Date-range selection for inspecting a delivery period.
* KPI cards for **Mean Absolute Error (MAE)**, **Root Mean Squared Error (RMSE)**, forecast bias, and matched hourly records.
* Summary panel describing the selected period.
* Python API for retrieving processed generation data and metrics.
* Docker-based local development for the frontend and backend.
* Public deployment using Vercel and Render.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, TypeScript, Vite |
| **Styling** | Tailwind CSS v4, custom CSS |
| **Visualization** | Recharts |
| **Icons** | Lucide React |
| **Backend** | Python, FastAPI |
| **Data Processing** | pandas, NumPy |
| **Data Source** | Elexon BMRS |
| **Containerization** | Docker, Docker Compose |
| **Hosting** | Vercel (Frontend), Render (Backend) |

---

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