import { LEVELS, LEVEL_ORDER } from "../lib/risk";

export function MapLegend() {
  return (
    <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-lg border border-line bg-panel/90 p-2.5 backdrop-blur">
      <div className="microlabel">Risk key</div>
      <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
        {LEVEL_ORDER.map((code) => (
          <span key={code} className="flex items-center gap-1.5 text-[10px] text-dim">
            <span className="h-1.5 w-1.5 rounded-sm" style={{ background: LEVELS[code].color }} />
            {LEVELS[code].label}
          </span>
        ))}
        <span className="flex items-center gap-1.5 text-[10px] text-dim">
          <span className="h-1.5 w-1.5 rounded-sm" style={{ background: LEVELS.unrated.color }} />
          Unrated
        </span>
      </div>
      <div className="mt-2 border-t border-line pt-1.5">
        <div className="microlabel">Heat</div>
        <div
          className="mt-1 h-1.5 w-40 rounded-sm"
          style={{
            background:
              "linear-gradient(90deg, #34d399 0%, #facc15 38%, #fb923c 62%, #f87171 82%, #b91c1c 100%)",
          }}
        />
      </div>
    </div>
  );
}
