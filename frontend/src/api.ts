
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export type GenerationPoint = {
  startTime: string;
  actual_mw: number;
  forecast_mw: number;
  error_mw: number;
  absolute_error_mw: number;
};

export type GenerationResponse = {
  period: {
    start_date: string;
    end_date: string;
  };
  count: number;
  data: GenerationPoint[];
};

export type MetricsResponse = {
  count: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  average_actual_mw?: number;
  average_forecast_mw?: number;
};

export async function fetchGenerationData(
  startDate: string,
  endDate: string
): Promise<GenerationResponse> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });

  const response = await fetch(
    `${API_BASE_URL}/api/data?${params.toString()}`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch generation data (${response.status})`);
  }

  return response.json();
}

export async function fetchMetrics(
  startDate: string,
  endDate: string
): Promise<MetricsResponse> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });

  const response = await fetch(
    `${API_BASE_URL}/api/metrics?${params.toString()}`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch metrics (${response.status})`);
  }

  return response.json();
}
