import { RefreshCw, Waves } from "lucide-react";
import type { Corridor } from "../api/types";
import { LEVELS, LEVEL_ORDER, summarizeHour, worstOf } from "../lib/risk";
import { slotLabel } from "../lib/format";

interface TimelineProps {
  corridor: Corridor | undefined;
  slot: number;
  onSlot: (slot: number) => void;
  visible: boolean;
  onVisible: (visible: boolean) => void;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function Timeline({ corridor, slot, onSlot, visible, onVisible, loading, error, onRetry }: TimelineProps) {
  const hours = corridor?.hours ?? [];
  const max = Math.max(0, hours.length - 1);
  const active = Math.min(slot, max);
  const counts = corridor ? summarizeHour(corridor.samples, active) : null;
  const worst = counts ? worstOf(counts) : null;

  return (
    <div className="pointer-events-auto absolute bottom-3 left-1/2 z-10 w-[min(780px,calc(100%-1.5rem))] -translate-x-1/2 rounded-lg border border-line bg-panel/95 p-2.5 shadow-2xl backdrop-blur">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Waves size={13} className="text-ice" aria-hidden />
          <span className="microlabel">Corridor tape</span>
          {corridor ? (
            <span className="rounded border border-line px-1 py-0.5 font-mono text-[9px] text-dim">
              ROUTE {corridor.route}
            </span>
          ) : null}
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={visible}
          aria-label="Toggle corridor heatmap"
          onClick={() => onVisible(!visible)}
          className="flex items-center gap-1.5 text-[9px] font-semibold tracking-wider text-dim hover:text-ink"
        >
          HEAT
          <span
            className={
              visible
                ? "relative h-4 w-7 rounded-full bg-ice/80 transition"
                : "relative h-4 w-7 rounded-full bg-line transition"
            }
          >
            <span
              className={
                visible
                  ? "absolute left-3.5 top-0.5 h-3 w-3 rounded-full bg-night transition-all"
                  : "absolute left-0.5 top-0.5 h-3 w-3 rounded-full bg-dim transition-all"
              }
            />
          </span>
        </button>
      </div>

      {loading ? (
        <div className="mt-2 flex items-center gap-2 text-[10px] text-dim">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ice" />
          Building 48-hour corridor…
        </div>
      ) : error ? (
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-[10px] text-severe">{error}</span>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1 rounded border border-line px-1.5 py-0.5 text-[10px] text-dim hover:text-ink"
          >
            <RefreshCw size={10} aria-hidden /> retry
          </button>
        </div>
      ) : corridor && visible ? (
        <>
          <div className="mt-1.5 flex items-end justify-between">
            <span className="font-mono text-[13px] font-semibold tabular-nums text-signal">
              {slotLabel(hours[active], active)}
            </span>
            <span className="font-mono text-[10px] tabular-nums text-dim">
              +{active}h / +{max}h
            </span>
          </div>
          <input
            type="range"
            className="fader mt-1.5"
            min={0}
            max={max}
            step={1}
            value={active}
            aria-label="Forecast hour"
            aria-valuetext={`${active} hours from now`}
            onChange={(event) => onSlot(Number(event.target.value))}
          />
          <div className="mt-1 flex items-center justify-between">
            <div className="flex flex-wrap gap-1">
              {counts
                ? LEVEL_ORDER.filter((code) => counts[code] > 0).map((code) => (
                    <span
                      key={code}
                      className="inline-flex items-center gap-1 rounded border border-line px-1 py-0.5 font-mono text-[9px] text-dim"
                    >
                      <span className="h-1 w-1 rounded-full" style={{ background: LEVELS[code].color }} />
                      {LEVELS[code].short} {counts[code]}
                    </span>
                  ))
                : null}
            </div>
            {worst ? (
              <span className="font-mono text-[9px] uppercase tracking-wider" style={{ color: LEVELS[worst].color }}>
                worst {LEVELS[worst].label}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[9px] leading-snug text-dim">
            {corridor.samples.length} samples · heat is interpolated between them; each slot uses its own hour.
          </p>
        </>
      ) : (
        <p className="mt-2 text-[10px] text-dim">Heat hidden. Route colours and stop weather stay live.</p>
      )}
    </div>
  );
}
