export type LevelCode = "clear" | "caution" | "warning" | "severe" | "no_go" | "unrated";

export interface Place {
  label: string;
  lat: number;
  lon: number;
}

export interface Weather {
  available: boolean;
  at: string;
  wind_mph: number | null;
  gust_mph: number | null;
  rain_in_hr: number | null;
  snow_in_hr: number | null;
  temp_f: number | null;
  code: number | null;
  condition: string | null;
  interpolated: boolean;
  reason: string | null;
  source: string | null;
}

export interface Risk {
  code: LevelCode;
  label: string;
  score: number;
  rated: boolean;
  complete: boolean;
  wind: LevelCode | null;
  rain: LevelCode | null;
  snow: LevelCode | null;
  override: string | null;
}

export interface Stop {
  n: number;
  mile: number;
  lat: number;
  lon: number;
  eta: string;
  weather: Weather;
  risk: Risk;
}

export interface Segment {
  from_mi: number;
  to_mi: number;
  code: LevelCode | null;
  path: [number, number][];
}

export interface Ledger {
  clear_mi: number;
  caution_mi: number;
  warning_mi: number;
  severe_mi: number;
  no_go_mi: number;
  unrated_mi: number;
  total_mi: number;
  mean_score: number | null;
  worst: LevelCode | null;
  worst_label: string | null;
  unrated_ratio: number;
}

export interface RouteOption {
  key: string;
  provider: string;
  profile: string;
  timing: string;
  distance_mi: number;
  duration_min: number;
  depart_at: string;
  arrive_at: string;
  stops: Stop[];
  segments: Segment[];
  ledger: Ledger;
  notes: string[];
}

export interface Verdict {
  route: string | null;
  safe: boolean;
  summary: string;
  order: string[];
  fallback: string | null;
}

export interface Trip {
  id: string;
  origin: Place & { query: string };
  destination: Place & { query: string };
  depart_at: string;
  load_lbs: number;
  interval_mi: number;
  generated_at: string;
}

export interface TripResponse {
  trip: Trip;
  routes: RouteOption[];
  verdict: Verdict;
  alerts: string[];
}

export interface CorridorSample {
  lat: number;
  lon: number;
  mile: number;
  offset_mi: number;
  levels: LevelCode[];
  values: { wind_mph: number | null; rain_in_hr: number | null; snow_in_hr: number | null }[];
}

export interface Corridor {
  route: string;
  load_lbs: number;
  start_utc: string;
  hours: string[];
  samples: CorridorSample[];
  notes: string[];
}

export interface Health {
  service: string;
  version: string;
  providers: {
    openrouteservice: boolean;
    osrm: string;
    open_meteo: string;
    nominatim: string;
  };
  clock: string;
}

export interface AnalyzeInput {
  origin: string;
  destination: string;
  depart_at: string;
  load_lbs: number;
  interval_mi: 10 | 25 | 50;
}
