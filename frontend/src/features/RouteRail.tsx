import { Route as RouteGlyph } from "lucide-react";
import type { RouteOption, Verdict } from "../api/types";
import { SegmentBar } from "../components/Ledger";
import { LevelChip } from "../components/LevelChip";
import { duration, usMiles } from "../lib/format";

interface RouteRailProps {
  routes: RouteOption[];
  verdict: Verdict | null;
  selected: string | null;
  onSelect: (key: string) => void;
}

export function RouteRail({ routes, verdict, selected, onSelect }: RouteRailProps) {
  const ordered = verdict
    ? [...routes].sort(
        (a, b) => (verdict.order.indexOf(a.key) + 1 || 99) - (verdict.order.indexOf(b.key) + 1 || 99),
      )
    : routes;

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between px-0.5">
        <span className="microlabel">02 / Alternatives</span>
        <span className="font-mono text-[10px] tabular-nums text-dim">{routes.length} loaded</span>
      </div>

      {ordered.length === 0 ? (
        <div className="console-panel flex items-center gap-2 p-3 text-[11px] text-dim">
          <RouteGlyph size={14} aria-hidden />
          No routes on the board yet.
        </div>
      ) : (
        ordered.map((route) => {
          const isBest = verdict?.route === route.key;
          const isSelected = selected === route.key;
          return (
            <button
              key={route.key}
              type="button"
              onClick={() => onSelect(route.key)}
              aria-pressed={isSelected}
              className={
                isSelected
                  ? "w-full rounded-lg border border-signal/60 bg-panel2 p-3 text-left shadow-[0_0_0_1px_rgba(251,191,36,0.15)]"
                  : "w-full rounded-lg border border-line bg-panel p-3 text-left transition hover:border-line2"
              }
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={
                      isBest
                        ? "flex h-8 w-8 items-center justify-center rounded border border-signal/60 bg-signal/15 text-sm font-bold text-signal"
                        : "flex h-8 w-8 items-center justify-center rounded border border-line bg-night/60 text-sm font-bold text-dim"
                    }
                  >
                    {route.key}
                  </span>
                  <div className="leading-tight">
                    <div className="text-[12px] font-semibold text-ink">Route {route.key}</div>
                    <div className="text-[9px] uppercase tracking-[0.14em] text-dim">
                      {route.provider} · {route.timing}
                    </div>
                  </div>
                </div>
                {isBest ? (
                  <span className="rounded bg-signal px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-night">
                    BEST
                  </span>
                ) : null}
              </div>

              <div className="mt-2.5 grid grid-cols-3 gap-2 font-mono text-[11px] tabular-nums">
                <Cell label="Miles" value={usMiles(route.distance_mi)} />
                <Cell label="Drive" value={duration(route.duration_min)} />
                <Cell
                  label="Mean"
                  value={route.ledger.mean_score === null ? "—" : route.ledger.mean_score.toFixed(2)}
                />
              </div>

              <div className="mt-2">
                <SegmentBar ledger={route.ledger} />
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-1">
                {route.ledger.worst ? <LevelChip code={route.ledger.worst} small /> : null}
                {route.ledger.no_go_mi > 0 ? (
                  <span className="rounded border border-nogo/50 bg-nogo/10 px-1 py-0.5 text-[9px] font-bold tracking-wider text-severe">
                    {route.ledger.no_go_mi.toFixed(0)} MI NO-GO
                  </span>
                ) : null}
                {route.ledger.unrated_mi > 0 ? (
                  <span className="rounded border border-line px-1 py-0.5 text-[9px] text-dim">
                    {route.ledger.unrated_mi.toFixed(0)} MI UNRATED
                  </span>
                ) : null}
              </div>
            </button>
          );
        })
      )}
    </section>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="microlabel text-[9px]">{label}</div>
      <div className="mt-0.5 text-ink">{value}</div>
    </div>
  );
}
