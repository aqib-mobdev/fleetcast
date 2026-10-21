import type { AnalyzeInput } from "../api/types";

export interface PlanForm {
  origin: string;
  destination: string;
  depart: string;
  load: string;
  interval: 10 | 25 | 50;
}

export type PlanErrors = Partial<Record<keyof PlanForm | "form", string>>;

export interface PlanResult {
  errors: PlanErrors;
  payload?: AnalyzeInput;
}

export function emptyPlan(): PlanForm {
  return { origin: "", destination: "", depart: "", load: "35000", interval: 25 };
}

export function validatePlan(form: PlanForm, now = new Date()): PlanResult {
  const errors: PlanErrors = {};

  const origin = form.origin.trim();
  const destination = form.destination.trim();
  if (origin.length < 2) errors.origin = "Enter an origin of at least 2 characters.";
  if (destination.length < 2) errors.destination = "Enter a destination of at least 2 characters.";
  if (origin && destination && origin.toLowerCase() === destination.toLowerCase()) {
    errors.destination = "Destination must differ from origin.";
  }

  const depart = new Date(form.depart);
  if (!form.depart) {
    errors.depart = "Pick a departure time.";
  } else if (Number.isNaN(depart.getTime())) {
    errors.depart = "Departure time is invalid.";
  } else if (depart.getTime() < now.getTime() - 60_000) {
    errors.depart = "Departure must be in the future.";
  }

  const load = Number(form.load);
  if (!Number.isInteger(load)) {
    errors.load = "Load must be a whole number.";
  } else if (load < 0 || load > 80_000) {
    errors.load = "Load must be between 0 and 80,000 lb.";
  }

  if (![10, 25, 50].includes(form.interval)) {
    errors.interval = "Choose a 10, 25, or 50 mile interval.";
  }

  if (Object.keys(errors).length > 0) return { errors };

  return {
    errors,
    payload: {
      origin,
      destination,
      depart_at: depart.toISOString(),
      load_lbs: load,
      interval_mi: form.interval,
    },
  };
}
