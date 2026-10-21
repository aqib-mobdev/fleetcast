import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ArrowRight, Loader2, MapPin, Navigation, RadioTower } from "lucide-react";
import type { AnalyzeInput } from "../api/types";
import { ApiError } from "../api/client";
import { useDebounced } from "../hooks/useDebounced";
import { usePlaces } from "../hooks/useTrip";
import { defaultDepart } from "../lib/format";
import { emptyPlan, validatePlan, type PlanErrors, type PlanForm } from "../lib/validate";

interface PlanFormProps {
  busy: boolean;
  serverError: ApiError | null;
  onSubmit: (input: AnalyzeInput) => void;
}

const LANES = [
  { origin: "Los Angeles, CA", destination: "Phoenix, AZ" },
  { origin: "Chicago, IL", destination: "Detroit, MI" },
  { origin: "Dallas, TX", destination: "Atlanta, GA" },
];

const LOAD_STEPS = [0, 20_000, 35_000, 44_000];

export function PlanForm({ busy, serverError, onSubmit }: PlanFormProps) {
  const [form, setForm] = useState<PlanForm>({ ...emptyPlan(), depart: defaultDepart() });
  const [errors, setErrors] = useState<PlanErrors>({});

  function update<K extends keyof PlanForm>(key: K, value: PlanForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined, form: undefined }));
  }

  const shown: PlanErrors = serverError?.field
    ? { ...errors, [serverError.field as keyof PlanForm]: serverError.message }
    : errors;

  function submit() {
    const result = validatePlan(form);
    setErrors(result.errors);
    if (result.payload) onSubmit(result.payload);
  }

  return (
    <section className="console-panel p-3">
      <div className="mb-3 flex items-center justify-between">
        <span className="microlabel">01 / Trip plan</span>
        <RadioTower size={14} className="text-signal" aria-hidden />
      </div>

      <div className="space-y-2.5">
        <PlaceField
          label="Origin"
          icon={<MapPin size={13} />}
          value={form.origin}
          placeholder="Los Angeles, CA"
          error={shown.origin}
          onChange={(value) => update("origin", value)}
        />
        <PlaceField
          label="Destination"
          icon={<Navigation size={13} />}
          value={form.destination}
          placeholder="Phoenix, AZ"
          error={shown.destination}
          onChange={(value) => update("destination", value)}
        />

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label htmlFor="depart" className="microlabel mb-1 block">
              Depart
            </label>
            <input
              id="depart"
              type="datetime-local"
              value={form.depart}
              onChange={(event) => update("depart", event.target.value)}
              className="w-full rounded-md border border-line bg-panel2 px-2 py-1.5 text-[12px] text-ink outline-none focus:border-signal/60"
            />
            {shown.depart ? <p className="mt-1 text-[10px] text-severe">{shown.depart}</p> : null}
          </div>
          <div>
            <label htmlFor="load" className="microlabel mb-1 block">
              Load / lb
            </label>
            <input
              id="load"
              type="number"
              min={0}
              max={80_000}
              step={500}
              value={form.load}
              onChange={(event) => update("load", event.target.value)}
              className="w-full rounded-md border border-line bg-panel2 px-2 py-1.5 font-mono text-[12px] tabular-nums text-ink outline-none focus:border-signal/60"
            />
            {shown.load ? <p className="mt-1 text-[10px] text-severe">{shown.load}</p> : null}
          </div>
        </div>

        <div>
          <input
            type="range"
            className="fader"
            min={0}
            max={80_000}
            step={500}
            value={Number(form.load) || 0}
            aria-label="Load weight slider"
            onChange={(event) => update("load", event.target.value)}
          />
          <div className="mt-1.5 flex flex-wrap gap-1">
            {LOAD_STEPS.map((step) => (
              <button
                key={step}
                type="button"
                onClick={() => update("load", String(step))}
                className={
                  Number(form.load) === step
                    ? "rounded border border-signal/60 bg-signal/10 px-1.5 py-0.5 text-[10px] font-semibold text-signal"
                    : "rounded border border-line px-1.5 py-0.5 text-[10px] text-dim hover:border-line2 hover:text-ink"
                }
              >
                {step === 0 ? "Empty" : `${step / 1000}k`}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="microlabel mb-1 block">Checkpoint spacing</span>
          <div className="grid grid-cols-3 gap-1 rounded-md border border-line bg-night/50 p-1" role="group" aria-label="Checkpoint spacing">
            {([10, 25, 50] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={form.interval === value}
                onClick={() => update("interval", value)}
                className={
                  form.interval === value
                    ? "rounded bg-signal px-2 py-1 text-[11px] font-bold text-night"
                    : "rounded px-2 py-1 text-[11px] font-medium text-dim hover:text-ink"
                }
              >
                {value} mi
              </button>
            ))}
          </div>
        </div>

        {shown.form ? <p className="text-[11px] text-severe">{shown.form}</p> : null}
        {serverError && !serverError.field ? (
          <p className="rounded border border-severe/40 bg-severe/10 px-2 py-1.5 text-[11px] text-severe">
            {serverError.message}
          </p>
        ) : null}

        <button
          type="button"
          onClick={submit}
          disabled={busy}
          className={
            busy
              ? "flex w-full items-center justify-center gap-2 rounded-md bg-signal/60 px-3 py-2 text-[12px] font-bold tracking-wide text-night"
              : "flex w-full items-center justify-center gap-2 rounded-md bg-signal px-3 py-2 text-[12px] font-bold tracking-wide text-night transition hover:bg-[#ffc94a] active:translate-y-px"
          }
        >
          {busy ? <Loader2 size={14} className="animate-spin" aria-hidden /> : <ArrowRight size={14} aria-hidden />}
          {busy ? "Reading forecasts…" : "Run corridor analysis"}
        </button>

        <div className="flex flex-wrap gap-1 pt-0.5">
          <span className="microlabel mr-1">Demo lanes</span>
          {LANES.map((lane) => (
            <button
              key={lane.origin}
              type="button"
              onClick={() => {
                update("origin", lane.origin);
                update("destination", lane.destination);
              }}
              className="rounded border border-line bg-panel2 px-1.5 py-0.5 text-[10px] text-dim hover:border-signal/40 hover:text-signal"
            >
              {lane.origin.split(",")[0]} → {lane.destination.split(",")[0]}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function PlaceField({
  label,
  icon,
  value,
  placeholder,
  error,
  onChange,
}: {
  label: string;
  icon: ReactNode;
  value: string;
  placeholder: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  const debounced = useDebounced(value, 350);
  const { data, isLoading } = usePlaces(debounced);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const places = data?.places ?? [];

  useEffect(() => {
    function close(event: MouseEvent) {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div ref={wrapRef} className="relative">
      <label htmlFor={id} className="microlabel mb-1 flex items-center gap-1">
        <span className="text-dim">{icon}</span>
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type="text"
          autoComplete="off"
          role="combobox"
          aria-expanded={open && places.length > 0}
          value={value}
          placeholder={placeholder}
          onChange={(event) => {
            onChange(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          className={
            error
              ? "w-full rounded-md border border-severe/60 bg-panel2 px-2.5 py-2 text-[13px] text-ink outline-none placeholder:text-dim/50"
              : "w-full rounded-md border border-line bg-panel2 px-2.5 py-2 text-[13px] text-ink outline-none placeholder:text-dim/50 focus:border-signal/50"
          }
        />
        {isLoading ? (
          <Loader2 size={12} className="absolute right-2 top-1/2 -translate-y-1/2 animate-spin text-dim" aria-hidden />
        ) : null}
      </div>
      {error ? <p className="mt-1 text-[10px] text-severe">{error}</p> : null}

      {open && places.length > 0 ? (
        <ul className="absolute z-30 mt-1 max-h-56 w-full overflow-auto rounded-md border border-line bg-panel py-1 shadow-2xl">
          {places.map((place) => (
            <li key={place.label}>
              <button
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onChange(place.label);
                  setOpen(false);
                }}
                className="block w-full px-2.5 py-1.5 text-left text-[11px] leading-snug text-dim hover:bg-panel2 hover:text-ink"
              >
                {place.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
