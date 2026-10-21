import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Inspector } from "../Inspector";
import { makeTrip, makeVerdict } from "../../test/factories";

describe("Inspector", () => {
  it("shows a cleared verdict for a safe route", () => {
    const trip = makeTrip();
    render(
      <Inspector
        trip={trip}
        route={trip.routes[0]}
        verdict={makeVerdict()}
        onFocusStop={vi.fn()}
      />,
    );
    expect(screen.getByText(/cleared · route a/i)).toBeInTheDocument();
    expect(screen.getByText(/route a avoids severe conditions/i)).toBeInTheDocument();
    expect(screen.getByText("04 / Stops")).toBeInTheDocument();
  });

  it("shows a hold verdict and the least-exposure reference", () => {
    const trip = makeTrip();
    render(
      <Inspector
        trip={trip}
        route={trip.routes[1]}
        verdict={makeVerdict({
          route: null,
          safe: false,
          summary: "Every alternative includes No-Go conditions.",
          fallback: "B",
        })}
        onFocusStop={vi.fn()}
      />,
    );
    expect(screen.getByText("HOLD")).toBeInTheDocument();
    expect(screen.getByText(/least exposure on the board: route b/i)).toBeInTheDocument();
    expect(screen.getByText(/every alternative includes/i)).toBeInTheDocument();
  });

  it("focuses a stop on click", async () => {
    const user = userEvent.setup();
    const onFocusStop = vi.fn();
    const trip = makeTrip();
    const route = trip.routes[0];
    render(<Inspector trip={trip} route={route} verdict={makeVerdict()} onFocusStop={onFocusStop} />);

    const rows = screen.getAllByTitle("Center on map");
    await user.click(rows[1]);
    expect(onFocusStop).toHaveBeenCalledWith(route.stops[1]);
  });

  it("renders the guide when there is no trip", () => {
    render(<Inspector trip={null} route={null} verdict={null} onFocusStop={vi.fn()} />);
    expect(screen.getByText(/how this board works/i)).toBeInTheDocument();
    expect(screen.getByText(/set the lane/i)).toBeInTheDocument();
  });
});
