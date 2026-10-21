import {
  AlertTriangle,
  ArrowUpRight,
  Compass,
  Gauge,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import type { RouteOption, Stop, TripResponse, Verdict } from "../api/types";
import { LedgerRows, SegmentBar } from "../components/Ledger";
import { LevelChip } from "../components/LevelChip";
import { clock, duration, num, stamp, usMiles } from "../lib/format";

interface InspectorProps {
  trip: TripResponse | null;
  route: RouteOption | null;
  verdict: Verdict | null;
  onFocusStop: (stop: Stop) => void;
}

export function Inspector({ trip, route, verdict, onFocusStop }: InspectorProps) {
  if (!trip || !verdict) return <Guide />;

  return (
    <div className="space-y-3">
      <VerdictPanel verdict={verdict} route={route} />

      {route ? (
        <>
          <section className="console-panel p-3">
            <div className="flex items-center justify-between">
              <span className="microlabel">03 / Route {route.key} ledger</span>
              <span className="text-[10px] uppercase tracking-wider text-dim">{route.profile}</span>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 font-mono text-[11px] tabular-nums">
              <Metric label="Distance" value={usMiles(route.distance_mi)} />
              <Metric label="Drive" value={duration(route.duration_min)} />
              <Metric label="Depart" value={clock(route.depart_at)} />
              <Metric label="Arrive" value={stamp(route.arrive_at)} />
            </div>
            <div className="mt-3">
              <SegmentBar ledger={route.ledger} height="h-2" />
            </div>
            <div className="mt-2.5">
              <LedgerRows ledger={route.ledger} />
            </div>
            <div className="mt-2.5 flex items-center justify-between border-t border-line pt-2 text-[11px]">
              <span className="text-dim">Mean exposure</span>
              <span className="font-mono text-ink">
                {route.ledger.mean_score === null ? "not rated" : `${route.ledger.mean_score.toFixed(2)} / 4.00`}
              </span>
            </div>
          </section>

          <section className="console-panel p-3">
            <div className="flex items-center justify-between">
              <span className="microlabel">04 / Stops</span>
              <span className="font-mono text-[10px] text-dim">
                {route.stops.length} · every {trip.trip.interval_mi} mi
              </span>
            </div>
            <div className="scroll-slim mt-2 max-h-[300px] overflow-y-auto pr-1">
              {route.stops.map((stop) => (
                <button
                  key={stop.n}
                  type="button"
                  onClick={() => onFocusStop(stop)}
                  className="flex w-full items-center justify-between gap-2 border-b border-line/60 py-1.5 text-left last:border-0 hover:bg-panel2/60"
                  title="Center on map"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="w-11 shrink-0 font-mono text-[10px] tabular-nums text-dim">
                      {stop.mile.toFixed(1)}
                    </span>
                    <span className="w-10 shrink-0 font-mono text-[10px] tabular-nums text-dim">
                      {clock(stop.eta)}
                    </span>
                    <span className="truncate text-[11px] text-ink">
                      {stop.weather.available ? (stop.weather.condition ?? "—") : "No data"}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 font-mono text-[10px] tabular-nums text-dim">
                    <span title="Wind mph">{num(stop.weather.wind_mph, 0)}</span>
                    <span title="Rain in/hr">{num(stop.weather.rain_in_hr, 2)}</span>
                    <span title="Snow in/hr">{num(stop.weather.snow_in_hr, 2)}</span>
                    <LevelChip code={stop.risk.code} small />
                  </div>
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-[9px] leading-snug text-dim">
              Wind mph · rain in/hr · snow in/hr. Coloured chip is the combined risk at that ETA.
            </p>
          </section>

          {route.notes.length > 0 || trip.alerts.length > 0 ? (
            <section className="console-panel p-3">
              <div className="microlabel flex items-center gap-1">
                <AlertTriangle size={11} aria-hidden />
                Alerts
              </div>
              <ul className="mt-1.5 space-y-1.5">
                {[...route.notes, ...trip.alerts].map((note, index) => (
                  <li key={index} className="text-[10px] leading-relaxed text-dim">
                    · {note}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      ) : (
        <Guide />
      )}
    </div>
  );
}

function VerdictPanel({ verdict, route }: { verdict: Verdict; route: RouteOption | null }) {
  const safe = verdict.safe && verdict.route;
  return (
    <section
      className={
        safe
          ? "rounded-lg border border-clear/40 bg-clear/[0.06] p-3"
          : "rounded-lg border border-severe/40 bg-severe/[0.06] p-3"
      }
    >
      <div className="flex items-center justify-between">
        <span className="microlabel">Verdict</span>
        {safe ? (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold tracking-wider text-clear">
            <ShieldCheck size={12} aria-hidden /> CLEARED · ROUTE {verdict.route}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold tracking-wider text-severe">
            <ShieldAlert size={12} aria-hidden /> HOLD
          </span>
        )}
      </div>
      <p className="mt-1.5 text-[12px] leading-relaxed text-ink">{verdict.summary}</p>
      {!safe && verdict.fallback ? (
        <div className="mt-2 flex items-center gap-1.5 rounded border border-severe/30 bg-night/40 px-2 py-1 text-[10px] text-dim">
          <ArrowUpRight size={11} aria-hidden />
          Least exposure on the board: Route {verdict.fallback}
          {route ? ` · ${usMiles(route.distance_mi)}` : ""} — reference only.
        </div>
      ) : null}
    </section>
  );
}

function Guide() {
  const steps = [
    { icon: Compass, title: "Set the lane", body: "Origin, destination, departure and load." },
    { icon: Gauge, title: "Read the ledger", body: "Miles are bucketed by the worst endpoint of each interval." },
    { icon: AlertTriangle, title: "Watch No-Go", body: "Any No-Go miles remove a route from the cleared ranking." },
  ];
  return (
    <div className="space-y-3">
      <section className="console-panel p-3">
        <div className="microlabel">How this board works</div>
        <div className="mt-2 space-y-2.5">
          {steps.map((step, index) => (
            <div key={step.title} className="flex gap-2">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded border border-line bg-night/60 text-signal">
                <step.icon size={12} aria-hidden />
              </span>
              <div>
                <div className="text-[11px] font-semibold text-ink">
                  {String(index + 1).padStart(2, "0")} · {step.title}
                </div>
                <p className="text-[10px] leading-relaxed text-dim">{step.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="console-panel p-3 text-[10px] leading-relaxed text-dim">
        Weather is sampled at each stop's projected ETA. The corridor tape is a separate time-slice view of the
        next 48 hours. Truck restrictions still require dispatcher verification.
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="microlabel text-[9px]">{label}</div>
      <div className="mt-0.5 text-ink">{value}</div>
    </div>
  );
}
