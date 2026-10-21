const timeFmt = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const dayFmt = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function clock(iso: string | null | undefined): string {
  if (!iso) return "--:--";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "--:--" : timeFmt.format(date);
}

export function stamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "—" : dayFmt.format(date).replace(",", "");
}

export function usMiles(miles: number): string {
  return `${miles.toFixed(1)} mi`;
}

export function duration(minutes: number): string {
  const total = Math.max(0, Math.round(minutes));
  const h = Math.floor(total / 60);
  const m = total % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

export function num(value: number | null | undefined, digits = 1, suffix = ""): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(digits)}${suffix}`;
}

export function localInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function defaultDepart(): string {
  const date = new Date(Date.now() + 2 * 60 * 60 * 1000);
  date.setMinutes(Math.ceil(date.getMinutes() / 15) * 15, 0, 0);
  return localInput(date);
}

export function slotLabel(iso: string | null | undefined, index: number): string {
  if (index === 0) return "NOW";
  if (!iso) return `+${index}H`;
  return clock(iso);
}
