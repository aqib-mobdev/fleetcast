import type { Ledger } from "../api/types";
import { LEVELS, LEVEL_ORDER, ledgerTotal } from "../lib/risk";

const KEYS = {
  clear: "clear_mi",
  caution: "caution_mi",
  warning: "warning_mi",
  severe: "severe_mi",
  no_go: "no_go_mi",
  unrated: "unrated_mi",
} as const;

export function SegmentBar({ ledger, height = "h-1.5" }: { ledger: Ledger; height?: string }) {
  const total = ledgerTotal(ledger) || 1;
  return (
    <div
      className={`flex w-full overflow-hidden rounded-sm bg-line/60 ${height}`}
      role="img"
      aria-label={LEVEL_ORDER.map(
        (code) => `${LEVELS[code].label} ${ledger[KEYS[code]].toFixed(1)} miles`,
      ).join(", ")}
    >
      {(Object.keys(KEYS) as (keyof typeof KEYS)[]).map((code) => {
        const miles = ledger[KEYS[code]];
        if (miles <= 0) return null;
        return (
          <div
            key={code}
            style={{ width: `${(miles / total) * 100}%`, background: LEVELS[code].color }}
            title={`${LEVELS[code].label}: ${miles.toFixed(1)} mi`}
          />
        );
      })}
    </div>
  );
}

export function LedgerRows({ ledger }: { ledger: Ledger }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-1">
      {LEVEL_ORDER.map((code) => {
        const miles = ledger[KEYS[code]];
        if (miles <= 0) return null;
        return (
          <div key={code} className="flex items-center justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-dim">
              <span className="h-1.5 w-1.5 rounded-sm" style={{ background: LEVELS[code].color }} />
              {LEVELS[code].label}
            </span>
            <span className="font-mono tabular-nums text-ink">{miles.toFixed(1)}</span>
          </div>
        );
      })}
      {ledger.unrated_mi > 0 ? (
        <div className="flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1.5 text-dim">
            <span className="h-1.5 w-1.5 rounded-sm" style={{ background: LEVELS.unrated.color }} />
            Unrated
          </span>
          <span className="font-mono tabular-nums text-ink">{ledger.unrated_mi.toFixed(1)}</span>
        </div>
      ) : null}
    </div>
  );
}
