
import { useEffect, useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RotateCcw, Wind, AlertCircle } from "lucide-react";
import {
  fetchGenerationData,
  fetchMetrics,
  type GenerationPoint,
  type MetricsResponse,
} from "./api";

const FULL_MONTH_START = "2026-01-01";
const FULL_MONTH_END = "2026-01-31";

const numberFormat = new Intl.NumberFormat("en-GB", {
  maximumFractionDigits: 0,
});


function formatNumber(value: number | null | undefined) {
  return value == null || !Number.isFinite(value)
    ? "—"
    : numberFormat.format(value);
}

function formatDate(date: string) {
  if (!date) return "—";

  return new Date(`${date}T12:00:00`).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatShortDate(value: string) {
  return new Date(value).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  });
}

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

function calculateMetrics(data: GenerationPoint[]): MetricsResponse {
  if (!data.length) {
    return {
      count: 0,
      mae_mw: null,
      rmse_mw: null,
      bias_mw: null,
      average_actual_mw: 0,
      average_forecast_mw: 0,
    };
  }

  const errors = data.map(
    (point) => point.forecast_mw - point.actual_mw,
  );

  const count = errors.length;
  const mae = errors.reduce((sum, error) => sum + Math.abs(error), 0) / count;
  const rmse = Math.sqrt(
    errors.reduce((sum, error) => sum + error * error, 0) / count,
  );
  const bias = errors.reduce((sum, error) => sum + error, 0) / count;

  return {
    count,
    mae_mw: mae,
    rmse_mw: rmse,
    bias_mw: bias,
    average_actual_mw:
      data.reduce((sum, point) => sum + point.actual_mw, 0) / count,
    average_forecast_mw:
      data.reduce((sum, point) => sum + point.forecast_mw, 0) / count,
  };
}

function App() {
  const [startDate, setStartDate] = useState(FULL_MONTH_START);
  const [endDate, setEndDate] = useState(FULL_MONTH_END);
  const [data, setData] = useState<GenerationPoint[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      if (!startDate || !endDate || startDate > endDate) {
        setError("Choose a valid delivery period.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const [generationResponse, metricsResponse] = await Promise.all([
          fetchGenerationData(startDate, endDate),
          fetchMetrics(startDate, endDate),
        ]);

        if (cancelled) return;

        const points = generationResponse.data.map((point) => ({
          ...point,
          actual_mw: Number(point.actual_mw),
          forecast_mw: Number(point.forecast_mw),
          error_mw: Number(point.forecast_mw) - Number(point.actual_mw),
          absolute_error_mw: Math.abs(
            Number(point.forecast_mw) - Number(point.actual_mw),
          ),
        }));

        setData(points);
        setMetrics(metricsResponse);
      } catch (err) {
        if (cancelled) return;

        setData([]);
        setMetrics(null);
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load wind generation data.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [startDate, endDate]);

  const calculated = useMemo(() => calculateMetrics(data), [data]);

  const summaryMetrics = metrics?.count ? metrics : calculated;

  const peakActual = useMemo(
    () => data.reduce((peak, point) =>
      point.actual_mw > (peak?.actual_mw ?? -Infinity) ? point : peak,
    null as GenerationPoint | null),
    [data],
  );

  const chartData = useMemo(
    () =>
      data.map((point) => ({
        ...point,
        chartTime: new Date(point.startTime).getTime(),
        chartLabel: formatShortDate(point.startTime),
      })),
    [data],
  );

  const dateLabel =
    startDate && endDate
      ? `${formatDate(startDate)} — ${formatDate(endDate)}`
      : "Select a delivery period";

  const bias = summaryMetrics.bias_mw;
  const hasData = data.length > 0;

  function resetDates() {
    setStartDate(FULL_MONTH_START);
    setEndDate(FULL_MONTH_END);
  }

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="WindScope home">
          <span className="brand-mark">
            <Wind size={27} strokeWidth={1.8} />
          </span>
          <span className="brand-name">WindScope</span>
        </a>

        <div className="data-status">
          <span className={`status-dot ${error ? "status-error" : ""}`} />
          <span>{error ? "DATA UNAVAILABLE" : "ELEXON DATA"}</span>
        </div>
      </header>

      <section className="hero-section">
        <div className="hero-copy">
          <p className="eyebrow">
            GB WIND <span>·</span> FORECAST EVALUATION <span>·</span> JAN 2026
          </p>

          <h1>
            How close did
            <br />
            the forecast
            <br />
            <span className="headline-accent">blow?</span>
          </h1>
        </div>

        <div className="date-card">
          <p className="eyebrow date-card-title">DELIVERY PERIOD</p>

          <div className="date-fields">
            <label className="date-field">
              <span>From</span>
              <input
                type="date"
                value={startDate}
                max={endDate || FULL_MONTH_END}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </label>

            <label className="date-field">
              <span>To</span>
              <input
                type="date"
                value={endDate}
                min={startDate || FULL_MONTH_START}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </label>
          </div>

          <button className="reset-button" onClick={resetDates} type="button">
            <RotateCcw size={16} strokeWidth={1.7} />
            RESET TO FULL MONTH
          </button>
        </div>
      </section>

      <section className="kpi-strip" aria-label="Forecast accuracy metrics">
        <div className="kpi">
          <p className="eyebrow">MEAN ABS. ERROR</p>
          <div className="kpi-value">
            {loading ? "…" : formatNumber(summaryMetrics.mae_mw)}
            <span className="unit">MW</span>
          </div>
          <p className="kpi-note">&nbsp;</p>
        </div>

        <div className="kpi">
          <p className="eyebrow">RMSE</p>
          <div className="kpi-value">
            {loading ? "…" : formatNumber(summaryMetrics.rmse_mw)}
            <span className="unit">MW</span>
          </div>
          <p className="kpi-note">&nbsp;</p>
        </div>

        <div className="kpi">
          <p className="eyebrow">BIAS</p>
          <div className="kpi-value">
            {loading || bias == null
              ? "…"
              : `${bias > 0 ? "+" : ""}${formatNumber(bias)}`}
            <span className="unit">MW</span>
          </div>
          <p
            className={`kpi-note ${
              bias != null && bias > 0
                ? "bias-positive"
                : bias != null && bias < 0
                  ? "bias-negative"
                  : ""
            }`}
          >
            {bias == null
              ? "\u00a0"
              : bias > 0
                ? "over-forecasting"
                : bias < 0
                  ? "under-forecasting"
                  : "no average bias"}
          </p>
        </div>

        <div className="kpi">
          <p className="eyebrow">HOURLY RECORDS</p>
          <div className="kpi-value">
            {loading ? "…" : formatNumber(summaryMetrics.count || data.length)}
            <span className="unit">hrs</span>
          </div>
          <p className="kpi-note">&nbsp;</p>
        </div>
      </section>

      <section className="chart-card">
        <div className="chart-heading">
          <div>
            <p className="eyebrow">FORECAST VS ACTUAL · HOURLY · MW</p>
            <h2>{dateLabel}</h2>
          </div>

          <div className="chart-legend">
            <span className="legend-item">
              <span className="legend-line actual-line" />
              Actual
            </span>
            <span className="legend-item">
              <span className="legend-line forecast-line" />
              Forecast
            </span>
          </div>
        </div>

        {error ? (
          <div className="chart-message error-message">
            <AlertCircle size={22} />
            <div>
              <strong>Could not load the wind data.</strong>
              <p>{error}</p>
              <p>Check that your Python backend is running on port 8000.</p>
            </div>
          </div>
        ) : loading ? (
          <div className="chart-message">Loading generation data…</div>
        ) : !hasData ? (
          <div className="chart-message">
            No matching hourly records were returned for this period.
          </div>
        ) : (
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={chartData}
                margin={{ top: 16, right: 8, bottom: 2, left: 0 }}
              >
                <defs>
                  <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#087f78" stopOpacity={0.18} />
                    <stop offset="95%" stopColor="#087f78" stopOpacity={0.015} />
                  </linearGradient>
                </defs>

                <CartesianGrid
                  vertical={false}
                  stroke="#dedbd2"
                  strokeDasharray="0"
                />

                <XAxis
                  dataKey="chartTime"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(value) =>
                    formatShortDate(new Date(Number(value)).toISOString())
                  }
                  tick={{
                    fill: "#52616a",
                    fontSize: 12,
                    fontFamily: "JetBrains Mono",
                  }}
                  axisLine={false}
                  tickLine={false}
                  minTickGap={42}
                  tickMargin={12}
                />

                <YAxis
                  domain={[0, "auto"]}
                  tickFormatter={(value) =>
                    value === 0 ? "0k" : `${Math.round(value / 1000)}k`
                  }
                  tick={{ fill: "#52616a", fontSize: 12, fontFamily: "JetBrains Mono" }}
                  axisLine={false}
                  tickLine={false}
                  tickCount={5}
                  width={52}
                />

                <Tooltip
                  labelFormatter={(value) =>
                    formatTimestamp(new Date(Number(value)).toISOString())
                  }
                  formatter={(value, name) => [
                    `${formatNumber(Number(value))} MW`,
                    name === "actual_mw" ? "Actual" : "Forecast",
                  ]}
                  contentStyle={{
                    background: "#fbf9f2",
                    border: "1px solid #d9d5ca",
                    borderRadius: 0,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#52616a", marginBottom: 6 }}
                />

                <Area
                  type="monotone"
                  dataKey="actual_mw"
                  name="actual_mw"
                  stroke="#087f78"
                  strokeWidth={2.3}
                  fill="url(#actualFill)"
                  dot={false}
                  activeDot={{ r: 4, fill: "#087f78", stroke: "#fbf9f2", strokeWidth: 2 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />

                <Line
                  type="monotone"
                  dataKey="forecast_mw"
                  name="forecast_mw"
                  stroke="#fa812b"
                  strokeWidth={2}
                  strokeDasharray="6 5"
                  dot={false}
                  activeDot={{ r: 4, fill: "#fa812b", stroke: "#fbf9f2", strokeWidth: 2 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="bottom-grid">
        <article className="method-card">
          <p className="eyebrow">METHOD</p>
          <p className="method-description">
            Error = forecast − actual generation. A positive bias means the
            model over-forecast wind output for the selected period.
          </p>

          <div className="method-stat">
            <span>Mean abs. error</span>
            <span>{formatNumber(summaryMetrics.mae_mw)} MW</span>
          </div>
          <div className="method-stat">
            <span>RMSE</span>
            <span>{formatNumber(summaryMetrics.rmse_mw)} MW</span>
          </div>
          <div className="method-stat">
            <span>Bias</span>
            <span>
              {bias != null && bias > 0 ? "+" : ""}
              {formatNumber(bias)} MW
            </span>
          </div>
        </article>

        <article className="summary-card">
          <p className="eyebrow summary-eyebrow">SUMMARY</p>

          {loading ? (
            <p className="summary-text">Evaluating the selected period…</p>
          ) : error ? (
            <p className="summary-text">
              The dashboard could not retrieve the selected period.
            </p>
          ) : !hasData ? (
            <p className="summary-text">
              No hourly records are available for this date range.
            </p>
          ) : (
            <p className="summary-text">
              {formatNumber(data.length)} hourly records, peaking at{" "}
              {formatNumber(peakActual?.actual_mw)} MW. Typical forecast miss:{" "}
              {formatNumber(summaryMetrics.mae_mw)} MW.
            </p>
          )}

          <p className="summary-footnote">
            {hasData && !loading
              ? `Selected period: ${formatDate(startDate)} – ${formatDate(endDate)}`
              : ""}
          </p>
        </article>
      </section>

      <footer className="footer">
        <span>WINDSCOPE · UK WIND INTELLIGENCE</span>
        <span>ELEXON BMRS · JAN 2026</span>
      </footer>
    </main>
  );
}

export default App;
