import { lazy, Suspense, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import type { AnalyzeInput, Stop, TripResponse } from "./api/types";
import { ApiError } from "./api/client";
import { Header } from "./components/Header";
import { MapLegend } from "./components/MapLegend";
import { PlanForm } from "./features/PlanForm";
import { RouteRail } from "./features/RouteRail";
import { Inspector } from "./features/Inspector";
import { Timeline } from "./features/Timeline";
import { useAnalysis, useCorridor } from "./hooks/useTrip";

const MapStage = lazy(() =>
  import("./features/MapStage").then((module) => ({ default: module.MapStage })),
);

export default function App() {
  const { trigger, data, isMutating, error } = useAnalysis();
  const [selected, setSelected] = useState<string | null>(null);
  const [slot, setSlot] = useState(0);
  const [heat, setHeat] = useState(true);
  const [focus, setFocus] = useState<{ lon: number; lat: number; nonce: number } | null>(null);

  const trip: TripResponse | null = data ?? null;
  const selectedRoute = useMemo(
    () => trip?.routes.find((candidate) => candidate.key === selected) ?? null,
    [trip, selected],
  );
  const corridor = useCorridor(trip?.trip.id, selected);
  const maxSlot = Math.max(0, (corridor.data?.hours.length ?? 1) - 1);
  const activeSlot = Math.min(slot, maxSlot);

  async function analyze(input: AnalyzeInput) {
    const result = await trigger(input).catch(() => null);
    if (!result) return;
    setSelected(result.verdict.route ?? result.routes[0]?.key ?? null);
    setSlot(0);
    setFocus(null);
  }

  function pickRoute(key: string) {
    setSelected(key);
    setSlot(0);
  }

  const failure =
    error instanceof ApiError
      ? error
      : error
        ? new ApiError("Analysis failed. Try again.", "unknown", 0)
        : null;

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto grid w-full max-w-[1720px] gap-3 p-3 lg:h-[calc(100vh-3.5rem)] lg:grid-cols-[320px_minmax(0,1fr)_360px] lg:overflow-hidden">
        <aside className="scroll-slim space-y-3 lg:overflow-y-auto lg:pr-0.5">
          <PlanForm busy={isMutating} serverError={failure} onSubmit={analyze} />
          <RouteRail
            routes={trip?.routes ?? []}
            verdict={trip?.verdict ?? null}
            selected={selected}
            onSelect={pickRoute}
          />
        </aside>

        <section className="relative min-h-[460px] overflow-hidden rounded-lg border border-line lg:min-h-0">
          <Suspense fallback={<div className="h-full w-full animate-pulse bg-deck" />}>
          <MapStage
            tripId={trip?.trip.id ?? null}
            routes={trip?.routes ?? []}
            selected={selectedRoute}
            corridor={corridor.data ?? null}
            slot={activeSlot}
            heat={heat}
            focus={focus}
          >
            <MapLegend />
            {trip ? (
              <Timeline
                corridor={corridor.data ?? undefined}
                slot={activeSlot}
                onSlot={setSlot}
                visible={heat}
                onVisible={setHeat}
                loading={corridor.isLoading}
                error={corridor.error instanceof Error ? corridor.error.message : null}
                onRetry={() => void corridor.mutate()}
              />
            ) : (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <div className="rounded border border-line bg-panel/90 px-3 py-1.5 text-[11px] tracking-wide text-dim">
                  SET A LANE TO PLOT THE CORRIDOR
                </div>
              </div>
            )}
            {isMutating ? (
              <div className="absolute inset-0 z-20 flex items-center justify-center bg-night/70 backdrop-blur-sm">
                <div className="flex items-center gap-2 rounded border border-line bg-panel px-3 py-2 text-[12px] text-ink">
                  <Loader2 size={14} className="animate-spin text-signal" aria-hidden />
                  Building risk board…
                </div>
              </div>
            ) : null}
          </MapStage>
          </Suspense>
        </section>

        <aside className="scroll-slim lg:overflow-y-auto lg:pl-0.5">
          <Inspector
            trip={trip}
            route={selectedRoute}
            verdict={trip?.verdict ?? null}
            onFocusStop={(stop: Stop) => setFocus({ lon: stop.lon, lat: stop.lat, nonce: Date.now() })}
          />
        </aside>
      </main>
    </div>
  );
}
