import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { api } from "../api/client";
import type { AnalyzeInput, TripResponse } from "../api/types";

export function useHealth() {
  return useSWR("health", () => api.health(), { revalidateOnFocus: false });
}

export function usePlaces(query: string) {
  const text = query.trim();
  return useSWR(
    text.length >= 3 ? `places:${text.toLowerCase()}` : null,
    () => api.places(text),
    { keepPreviousData: true, dedupingInterval: 60_000 },
  );
}

export function useAnalysis() {
  return useSWRMutation<TripResponse, Error, string, AnalyzeInput>(
    "analyze",
    (_key, { arg }) => api.analyze(arg),
  );
}

export function useCorridor(
  tripId: string | undefined,
  route: string | null,
  path: [number, number][] | null,
  loadLbs: number | undefined,
) {
  const ready = tripId && route && path && path.length >= 2 && loadLbs !== undefined;
  return useSWR(
    ready ? `corridor:${tripId}:${route}` : null,
    () => api.corridor(path as [number, number][], loadLbs as number, route as string),
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
}
