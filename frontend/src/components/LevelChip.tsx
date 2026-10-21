import type { LevelCode } from "../api/types";
import { LEVELS } from "../lib/risk";

export function LevelChip({ code, small = false }: { code: LevelCode; small?: boolean }) {
  const meta = LEVELS[code];
  return (
    <span
      className={
        small
          ? "inline-flex items-center gap-1 rounded border px-1 py-0.5 text-[9px] font-bold tracking-wider"
          : "inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-[10px] font-bold tracking-wider"
      }
      style={{ color: meta.color, borderColor: `${meta.color}55`, background: `${meta.color}12` }}
    >
      <span className="h-1 w-1 rounded-full" style={{ background: meta.color }} aria-hidden />
      {meta.label}
    </span>
  );
}
