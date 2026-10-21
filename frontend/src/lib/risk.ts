import type { CorridorSample, LevelCode, Ledger } from "../api/types";

export const LEVEL_ORDER: LevelCode[] = ["clear", "caution", "warning", "severe", "no_go"];

export const LEVELS: Record<LevelCode, { label: string; short: string; color: string }> = {
  clear: { label: "Clear", short: "CLR", color: "#34d399" },
  caution: { label: "Caution", short: "CTN", color: "#facc15" },
  warning: { label: "Warning", short: "WRN", color: "#fb923c" },
  severe: { label: "Severe", short: "SVR", color: "#f87171" },
  no_go: { label: "No-Go", short: "NOG", color: "#b91c1c" },
  unrated: { label: "Unrated", short: "N/A", color: "#64748b" },
};

export function levelColor(code: LevelCode | null | undefined): string {
  return LEVELS[code ?? "unrated"].color;
}

export function heatWeight(code: LevelCode): number {
  switch (code) {
    case "clear":
      return 0.1;
    case "caution":
      return 0.34;
    case "warning":
      return 0.58;
    case "severe":
      return 0.82;
    case "no_go":
      return 1;
    default:
      return 0;
  }
}

export function ledgerTotal(ledger: Ledger): number {
  return (
    ledger.clear_mi +
    ledger.caution_mi +
    ledger.warning_mi +
    ledger.severe_mi +
    ledger.no_go_mi +
    ledger.unrated_mi
  );
}

export function summarizeHour(samples: CorridorSample[], hour: number): Record<LevelCode, number> {
  const counts: Record<LevelCode, number> = {
    clear: 0,
    caution: 0,
    warning: 0,
    severe: 0,
    no_go: 0,
    unrated: 0,
  };
  for (const sample of samples) {
    const code = sample.levels[hour];
    if (code) counts[code] += 1;
  }
  return counts;
}

export function worstOf(counts: Record<LevelCode, number>): LevelCode | null {
  return [...LEVEL_ORDER].reverse().find((code) => counts[code] > 0) ?? null;
}
