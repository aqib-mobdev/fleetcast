import { useEffect, useState } from "react";
import { Radar } from "lucide-react";
import { useHealth } from "../hooks/useTrip";

function utcClock(): string {
  return new Date().toISOString().slice(11, 19);
}

export function Header() {
  const { data } = useHealth();
  const [clock, setClock] = useState(utcClock);

  useEffect(() => {
    const id = window.setInterval(() => setClock(utcClock()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const ors = data?.providers.openrouteservice ?? false;

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-night/85 px-3 backdrop-blur sm:px-4">
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-signal text-night shadow-[0_0_18px_-4px_rgba(251,191,36,0.6)]">
          <Radar size={17} aria-hidden />
        </span>
        <div className="leading-tight">
          <div className="text-[13px] font-bold tracking-[0.22em] text-ink">FLEETCAST</div>
          <div className="microlabel">Dispatch weather</div>
        </div>
      </div>

      <div className="hidden items-center gap-2 rounded-md border border-line bg-panel/70 px-2.5 py-1 md:flex">
        <span className="relative flex h-1.5 w-1.5" aria-hidden>
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-clear opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-clear" />
        </span>
        <span className="microlabel">Live</span>
        <span className="font-mono text-[11px] tabular-nums text-dim">{clock} UTC</span>
      </div>

      <div className="flex items-center gap-2">
        <span
          className={
            ors
              ? "rounded border border-ice/30 bg-ice/10 px-2 py-1 text-[10px] font-semibold tracking-wider text-ice"
              : "rounded border border-signal/30 bg-signal/10 px-2 py-1 text-[10px] font-semibold tracking-wider text-signal"
          }
          title={ors ? "Truck profile active" : "OSRM car-profile fallback"}
        >
          {ors ? "ORS · HGV" : "OSRM FALLBACK"}
        </span>
        <span className="hidden text-[10px] tracking-wider text-dim sm:inline">v{data?.version ?? "1.0"}</span>
      </div>
    </header>
  );
}
