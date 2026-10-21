import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlanForm } from "../PlanForm";

vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/client")>();
  return {
    ...actual,
    api: { ...actual.api, places: vi.fn().mockResolvedValue({ places: [] }) },
  };
});

function renderForm(overrides: Partial<Parameters<typeof PlanForm>[0]> = {}) {
  const onSubmit = vi.fn();
  render(<PlanForm busy={false} serverError={null} onSubmit={onSubmit} {...overrides} />);
  return { onSubmit };
}

describe("PlanForm", () => {
  it("shows validation messages for empty endpoints", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderForm();

    await user.click(screen.getByRole("button", { name: /run corridor analysis/i }));

    expect(await screen.findByText(/enter an origin/i)).toBeInTheDocument();
    expect(screen.getByText(/enter a destination/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects an out-of-range load", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderForm();

    fireEvent.change(screen.getByLabelText(/load \/ lb/i), { target: { value: "90000" } });
    await user.type(screen.getByLabelText(/origin/i), "LA");
    await user.type(screen.getByLabelText(/destination/i), "PH");
    await user.click(screen.getByRole("button", { name: /run corridor analysis/i }));

    expect(await screen.findByText(/between 0 and 80,000/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a valid plan with the selected interval", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderForm();

    await user.type(screen.getByLabelText(/origin/i), "LA");
    await user.type(screen.getByLabelText(/destination/i), "PH");
    await user.click(screen.getByRole("button", { name: "10 mi" }));
    await user.click(screen.getByRole("button", { name: /run corridor analysis/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0][0];
    expect(payload).toMatchObject({ origin: "LA", destination: "PH", interval_mi: 10, load_lbs: 35000 });
    expect(payload.depart_at.endsWith("Z")).toBe(true);
  });

  it("fills a demo lane", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: /los angeles → phoenix/i }));
    expect(screen.getByLabelText(/origin/i)).toHaveValue("Los Angeles, CA");
    expect(screen.getByLabelText(/destination/i)).toHaveValue("Phoenix, AZ");
  });

  it("renders a server error without a field", () => {
    const error = Object.assign(new Error("Routing is unavailable"), {
      code: "routing_unavailable",
      status: 502,
      field: null,
    });
    renderForm({ serverError: error });
    expect(screen.getByText("Routing is unavailable")).toBeInTheDocument();
  });
});
