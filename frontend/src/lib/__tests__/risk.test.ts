import { describe, expect, it } from "vitest";
import { heatWeight, ledgerTotal, LEVELS, LEVEL_ORDER, levelColor, summarizeHour, worstOf } from "../risk";
import { makeCorridor, makeLedger } from "../../test/factories";

describe("risk helpers", () => {
  it("defines a colour for every level", () => {
    for (const code of [...LEVEL_ORDER, "unrated" as const]) {
      expect(LEVELS[code].color).toMatch(/^#[0-9a-f]{6}$/i);
      expect(LEVELS[code].label.length).toBeGreaterThan(2);
    }
    expect(levelColor(null)).toBe(LEVELS.unrated.color);
  });

  it("weights heat monotonically", () => {
    const weights = LEVEL_ORDER.map(heatWeight);
    for (let i = 1; i < weights.length; i += 1) {
      expect(weights[i]).toBeGreaterThan(weights[i - 1]);
    }
    expect(heatWeight("unrated")).toBe(0);
  });

  it("sums ledger miles", () => {
    expect(ledgerTotal(makeLedger())).toBe(100);
  });

  it("summarizes a corridor slot", () => {
    const corridor = makeCorridor();
    const hour0 = summarizeHour(corridor.samples, 0);
    expect(hour0.clear).toBe(3);
    expect(worstOf(hour0)).toBe("clear");

    const hour24 = summarizeHour(corridor.samples, 24);
    expect(hour24.no_go).toBe(3);
    expect(worstOf(hour24)).toBe("no_go");
  });

  it("ignores missing samples for a slot", () => {
    const corridor = makeCorridor();
    const counts = summarizeHour(corridor.samples, 99);
    expect(Object.values(counts).every((value) => value === 0)).toBe(true);
    expect(worstOf(counts)).toBeNull();
  });
});
