import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouteRail } from "../RouteRail";
import { makeRoute, makeVerdict } from "../../test/factories";

describe("RouteRail", () => {
  it("marks only the verdict route as best and lists every alternative", () => {
    render(
      <RouteRail
        routes={[makeRoute("A"), makeRoute("B")]}
        verdict={makeVerdict({ route: "B", order: ["B", "A"] })}
        selected="B"
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getAllByText("BEST")).toHaveLength(1);
    expect(screen.getByText("Route A")).toBeInTheDocument();
    expect(screen.getByText("Route B")).toBeInTheDocument();
    expect(screen.getByText("2 loaded")).toBeInTheDocument();
  });

  it("selects a route tile", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <RouteRail
        routes={[makeRoute("A"), makeRoute("B")]}
        verdict={makeVerdict()}
        selected="A"
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole("button", { name: /route b/i }));
    expect(onSelect).toHaveBeenCalledWith("B");
  });

  it("flags No-Go and unrated exposure", () => {
    render(
      <RouteRail
        routes={[
          makeRoute("A", {
            ledger: {
              ...makeRoute("A").ledger,
              no_go_mi: 28,
              unrated_mi: 12,
            },
          }),
        ]}
        verdict={makeVerdict({ route: "A" })}
        selected="A"
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText(/28 MI NO-GO/i)).toBeInTheDocument();
    expect(screen.getByText(/12 MI UNRATED/i)).toBeInTheDocument();
  });

  it("shows an empty state", () => {
    render(<RouteRail routes={[]} verdict={null} selected={null} onSelect={vi.fn()} />);
    expect(screen.getByText(/no routes on the board yet/i)).toBeInTheDocument();
  });
});
