import type { Corridor, Ledger, LevelCode, RouteOption, Stop, TripResponse, Verdict } from "../api/types";

export function makeLedger(overrides: Partial<Ledger> = {}): Ledger {
  const clear = overrides.clear_mi ?? 80;
  const ledger: Ledger = {
    clear_mi: clear,
    caution_mi: 20,
    warning_mi: 0,
    severe_mi: 0,
    no_go_mi: 0,
    unrated_mi: 0,
    total_mi: 100,
    mean_score: 0.2,
    worst: "caution",
    worst_label: "Caution",
    unrated_ratio: 0,
    ...overrides,
  };
  return ledger;
}

export function makeStop(n: number, code: LevelCode = "clear"): Stop {
  const eta = new Date(Date.UTC(2026, 4, 4, 16 + n)).toISOString();
  return {
    n,
    mile: n * 50,
    lat: 34 + n * 0.2,
    lon: -118 + n * 0.5,
    eta,
    weather: {
      available: true,
      at: eta,
      wind_mph: 12.4,
      gust_mph: 18,
      rain_in_hr: 0.04,
      snow_in_hr: 0,
      temp_f: 71,
      code: 2,
      condition: "Partly cloudy",
      interpolated: true,
      reason: null,
      source: "open-meteo",
    },
    risk: {
      code,
      label: code,
      score: code === "clear" ? 0 : code === "caution" ? 1 : code === "warning" ? 2 : code === "severe" ? 3 : 4,
      rated: true,
      complete: true,
      wind: "clear",
      rain: "clear",
      snow: "clear",
      override: null,
    },
  };
}

export function makeRoute(key = "A", overrides: Partial<RouteOption> = {}): RouteOption {
  const stops = [makeStop(0), makeStop(1, "caution"), makeStop(2)];
  return {
    key,
    provider: "osrm",
    profile: "driving",
    timing: "segments",
    distance_mi: 100,
    duration_min: 95,
    depart_at: new Date(Date.UTC(2026, 4, 4, 16)).toISOString(),
    arrive_at: new Date(Date.UTC(2026, 4, 4, 17, 35)).toISOString(),
    stops,
    segments: [
      { from_mi: 0, to_mi: 50, code: "caution", path: [[-118, 34], [-117.5, 34.2]] },
      { from_mi: 50, to_mi: 100, code: "clear", path: [[-117.5, 34.2], [-117, 34.4]] },
    ],
    ledger: makeLedger(),
    notes: [],
    ...overrides,
  };
}

export function makeVerdict(overrides: Partial<Verdict> = {}): Verdict {
  return {
    route: "A",
    safe: true,
    summary: "Route A avoids Severe conditions.",
    order: ["A", "B"],
    fallback: null,
    ...overrides,
  };
}

export function makeTrip(overrides: Partial<TripResponse> = {}): TripResponse {
  return {
    trip: {
      id: "trip-1",
      origin: { query: "Los Angeles, CA", label: "Los Angeles, CA", lat: 34.05, lon: -118.24 },
      destination: { query: "Phoenix, AZ", label: "Phoenix, AZ", lat: 33.45, lon: -112.07 },
      depart_at: new Date(Date.UTC(2026, 4, 4, 16)).toISOString(),
      load_lbs: 34_000,
      interval_mi: 50,
      generated_at: new Date(Date.UTC(2026, 4, 4, 15)).toISOString(),
    },
    routes: [makeRoute("A"), makeRoute("B", { distance_mi: 112, ledger: makeLedger({ warning_mi: 12 }) })],
    verdict: makeVerdict(),
    alerts: [],
    ...overrides,
  };
}

export function makeCorridor(): Corridor {
  const start = Date.UTC(2026, 4, 4, 16);
  const hours = Array.from({ length: 49 }, (_, i) => new Date(start + i * 3_600_000).toISOString());
  const profile = (hour: number): LevelCode => (hour < 8 ? "clear" : hour < 20 ? "warning" : "no_go");
  const samples = [0, 1, 2].map((index) => ({
    lat: 34 + index * 0.3,
    lon: -118 + index * 0.8,
    mile: index * 40,
    offset_mi: index === 0 ? 0 : index === 1 ? -12 : 12,
    levels: hours.map((_, hour) => profile(hour)),
    values: hours.map(() => ({ wind_mph: 10, rain_in_hr: 0.01, snow_in_hr: 0 })),
  }));
  return {
    trip_id: "trip-1",
    route: "A",
    load_lbs: 34_000,
    start_utc: hours[0],
    hours,
    samples,
    notes: ["Heat is interpolated between corridor samples."],
  };
}
