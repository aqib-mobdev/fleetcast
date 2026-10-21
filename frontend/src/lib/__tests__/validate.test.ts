import { describe, expect, it } from "vitest";
import { emptyPlan, validatePlan, type PlanForm } from "../validate";

function form(patch: Partial<PlanForm> = {}): PlanForm {
  return {
    ...emptyPlan(),
    origin: "Los Angeles, CA",
    destination: "Phoenix, AZ",
    depart: "2099-01-01T08:00",
    load: "35000",
    interval: 25,
    ...patch,
  };
}

describe("validatePlan", () => {
  it("requires origin and destination", () => {
    const result = validatePlan(form({ origin: "", destination: "" }));
    expect(result.errors.origin).toBeTruthy();
    expect(result.errors.destination).toBeTruthy();
    expect(result.payload).toBeUndefined();
  });

  it("rejects equal endpoints", () => {
    const result = validatePlan(form({ destination: "los angeles, ca" }));
    expect(result.errors.destination).toMatch(/differ/i);
  });

  it("rejects past departures", () => {
    const result = validatePlan(form({ depart: "2020-01-01T08:00" }));
    expect(result.errors.depart).toMatch(/future/i);
  });

  it("rejects invalid load values", () => {
    expect(validatePlan(form({ load: "90000" })).errors.load).toMatch(/80,000/);
    expect(validatePlan(form({ load: "-1" })).errors.load).toBeTruthy();
    expect(validatePlan(form({ load: "12.5" })).errors.load).toMatch(/whole/i);
  });

  it("builds a UTC payload for a valid plan", () => {
    const result = validatePlan(form({ interval: 10, load: "45000" }));
    expect(result.errors).toEqual({});
    expect(result.payload).toMatchObject({
      origin: "Los Angeles, CA",
      destination: "Phoenix, AZ",
      load_lbs: 45000,
      interval_mi: 10,
    });
    expect(result.payload?.depart_at.endsWith("Z")).toBe(true);
  });
});
