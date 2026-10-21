import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Timeline } from "../Timeline";
import { makeCorridor } from "../../test/factories";

function renderTimeline(overrides: Partial<Parameters<typeof Timeline>[0]> = {}) {
  const props = {
    corridor: makeCorridor(),
    slot: 0,
    onSlot: vi.fn(),
    visible: true,
    onVisible: vi.fn(),
    loading: false,
    error: null,
    onRetry: vi.fn(),
    ...overrides,
  };
  render(<Timeline {...props} />);
  return props;
}

describe("Timeline", () => {
  it("shows a 0-48h tape starting now", () => {
    renderTimeline();
    const slider = screen.getByRole("slider", { name: /forecast hour/i });
    expect(slider).toHaveValue("0");
    expect(slider).toHaveAttribute("max", "48");
    expect(screen.getByText("NOW")).toBeInTheDocument();
    expect(screen.getByText(/\+48h/i)).toBeInTheDocument();
  });

  it("reports slider changes", () => {
    const props = renderTimeline();
    fireEvent.change(screen.getByRole("slider", { name: /forecast hour/i }), { target: { value: "24" } });
    expect(props.onSlot).toHaveBeenCalledWith(24);
  });

  it("summarizes the selected hour", () => {
    renderTimeline({ slot: 24 });
    expect(screen.getByText(/NOG 3/)).toBeInTheDocument();
    expect(screen.getByText(/worst no-go/i)).toBeInTheDocument();
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuetext", "24 hours from now");
  });

  it("toggles the heat layer", async () => {
    const user = userEvent.setup();
    const props = renderTimeline();
    await user.click(screen.getByRole("switch", { name: /toggle corridor heatmap/i }));
    expect(props.onVisible).toHaveBeenCalledWith(false);
  });

  it("renders loading and retry states", async () => {
    const user = userEvent.setup();
    renderTimeline({ corridor: undefined, loading: true });
    expect(screen.getByText(/building 48-hour corridor/i)).toBeInTheDocument();

    const retry = vi.fn();
    renderTimeline({ corridor: undefined, error: "Forecast failed", onRetry: retry });
    expect(screen.getByText("Forecast failed")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(retry).toHaveBeenCalled();
  });

  it("explains when the heat is hidden", () => {
    renderTimeline({ visible: false });
    expect(screen.getByText(/heat hidden/i)).toBeInTheDocument();
  });
});
