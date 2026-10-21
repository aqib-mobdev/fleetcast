import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  AttributionControl,
  Map as MapLibre,
  NavigationControl,
  Popup,
  ScaleControl,
  setWorkerUrl,
  type GeoJSONSource,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Corridor, LevelCode, RouteOption, Stop } from "../api/types";
import { LEVELS, heatWeight, levelColor } from "../lib/risk";
import { clock, num, stamp } from "../lib/format";

setWorkerUrl(workerUrl);

const EMPTY = { type: "FeatureCollection" as const, features: [] };

const DARK_STYLE = "https://tiles.openfreemap.org/styles/dark";

interface MapStageProps {
  tripId: string | null;
  routes: RouteOption[];
  selected: RouteOption | null;
  corridor: Corridor | null;
  slot: number;
  heat: boolean;
  focus: { lon: number; lat: number; nonce: number } | null;
  children?: ReactNode;
}

function boundsFor(routes: RouteOption[]): [[number, number], [number, number]] | null {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const route of routes) {
    for (const [lon, lat] of route.stops.map((stop) => [stop.lon, stop.lat])) {
      minLon = Math.min(minLon, lon);
      minLat = Math.min(minLat, lat);
      maxLon = Math.max(maxLon, lon);
      maxLat = Math.max(maxLat, lat);
    }
  }
  return Number.isFinite(minLon)
    ? [
        [minLon, minLat],
        [maxLon, maxLat],
      ]
    : null;
}

export function MapStage({ tripId, routes, selected, corridor, slot, heat, focus, children }: MapStageProps) {
  const holder = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibre | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const currentRoute = useRef<RouteOption | null>(null);
  const lastTrip = useRef<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    currentRoute.current = selected;
  }, [selected]);

  useEffect(() => {
    if (!holder.current || mapRef.current) return;
    const map = new MapLibre({
      container: holder.current,
      style: DARK_STYLE,
      center: [-116.5, 34.2],
      zoom: 6,
      attributionControl: false,
    });
    mapRef.current = map;

    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new ScaleControl({ unit: "imperial", maxWidth: 80 }), "bottom-right");
    map.addControl(new AttributionControl({ compact: true }), "bottom-right");

    map.on("load", () => {
      map.addSource("heat", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "heat-layer",
        type: "heatmap",
        source: "heat",
        layout: { visibility: "none" },
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "weight"], 0, 0, 1, 1],
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 5, 0.9, 11, 1.6],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 5, 30, 9, 46, 13, 64],
          "heatmap-opacity": 0.55,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(52,211,153,0)",
            0.15,
            "rgba(52,211,153,0.35)",
            0.35,
            "rgba(250,204,21,0.45)",
            0.55,
            "rgba(251,146,60,0.6)",
            0.78,
            "rgba(248,113,113,0.75)",
            1,
            "rgba(185,28,28,0.9)",
          ],
        },
      });

      map.addSource("routes", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "route-halo",
        type: "line",
        source: "routes",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": "#000000",
          "line-width": ["case", ["get", "selected"], 9, 6],
          "line-opacity": 0.45,
        },
      });
      map.addLayer({
        id: "route-line",
        type: "line",
        source: "routes",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": [
            "match",
            ["get", "code"],
            "clear",
            LEVELS.clear.color,
            "caution",
            LEVELS.caution.color,
            "warning",
            LEVELS.warning.color,
            "severe",
            LEVELS.severe.color,
            "no_go",
            LEVELS.no_go.color,
            LEVELS.unrated.color,
          ],
          "line-width": ["case", ["get", "selected"], 5.5, 3],
          "line-opacity": ["case", ["get", "selected"], 1, 0.38],
        },
      });

      map.addSource("stops", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "stop-dots",
        type: "circle",
        source: "stops",
        paint: {
          "circle-radius": 4.5,
          "circle-color": [
            "match",
            ["get", "code"],
            "clear",
            LEVELS.clear.color,
            "caution",
            LEVELS.caution.color,
            "warning",
            LEVELS.warning.color,
            "severe",
            LEVELS.severe.color,
            "no_go",
            LEVELS.no_go.color,
            LEVELS.unrated.color,
          ],
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#070b14",
        },
      });

      map.on("click", "stop-dots", (event: MapLayerMouseEvent) => {
        const index = Number(event.features?.[0]?.properties?.index);
        const route = currentRoute.current;
        const stop = route?.stops.find((candidate) => candidate.n === index);
        if (!route || !stop) return;
        popupRef.current?.remove();
        popupRef.current = new Popup({ closeButton: true, maxWidth: "290px", offset: 10 })
          .setLngLat([stop.lon, stop.lat])
          .setDOMContent(popupBody(route.key, stop))
          .addTo(map);
      });
      map.on("mouseenter", "stop-dots", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "stop-dots", () => {
        map.getCanvas().style.cursor = "";
      });

      setReady(true);
    });

    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, []);

  useEffect(() => {
    const observer = new ResizeObserver(() => mapRef.current?.resize());
    if (holder.current) observer.observe(holder.current);
    return () => observer.disconnect();
  }, []);

  const routeFeatures = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: routes.flatMap((route) =>
        route.segments.map((segment) => ({
          type: "Feature" as const,
          geometry: { type: "LineString" as const, coordinates: segment.path },
          properties: {
            code: segment.code ?? "unrated",
            selected: route.key === selected?.key,
          },
        })),
      ),
    }),
    [routes, selected],
  );

  const stopFeatures = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: (selected?.stops ?? []).map((stop) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [stop.lon, stop.lat] },
        properties: { code: stop.risk.code, index: stop.n },
      })),
    }),
    [selected],
  );

  const heatFeatures = useMemo(() => {
    if (!corridor) return EMPTY;
    const features = corridor.samples.flatMap((sample) => {
      const code = sample.levels[slot] as LevelCode | undefined;
      if (!code) return [];
      const weight = heatWeight(code);
      if (weight <= 0) return [];
      return [
        {
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [sample.lon, sample.lat] },
          properties: { weight, level: code },
        },
      ];
    });
    return { type: "FeatureCollection" as const, features };
  }, [corridor, slot]);

  useEffect(() => {
    if (!ready) return;
    (mapRef.current?.getSource("routes") as GeoJSONSource | undefined)?.setData(routeFeatures);
  }, [ready, routeFeatures]);

  useEffect(() => {
    if (!ready) return;
    (mapRef.current?.getSource("stops") as GeoJSONSource | undefined)?.setData(stopFeatures);
  }, [ready, stopFeatures]);

  useEffect(() => {
    if (!ready) return;
    (mapRef.current?.getSource("heat") as GeoJSONSource | undefined)?.setData(heatFeatures);
  }, [ready, heatFeatures]);

  useEffect(() => {
    if (!ready) return;
    mapRef.current?.setLayoutProperty("heat-layer", "visibility", heat && corridor ? "visible" : "none");
  }, [ready, heat, corridor]);

  useEffect(() => {
    if (!ready) return;
    const map = mapRef.current;
    if (!map) return;
    const tripChanged = lastTrip.current !== tripId;
    lastTrip.current = tripId;
    const target = tripChanged ? boundsFor(routes) : selected ? boundsFor([selected]) : boundsFor(routes);
    if (target) {
      map.fitBounds(target, {
        padding: { top: 70, bottom: 110, left: 60, right: 60 },
        duration: 650,
        maxZoom: tripChanged ? 9.5 : 11.5,
      });
    }
  }, [ready, tripId, selected, routes]);

  useEffect(() => {
    if (!ready || !focus) return;
    const map = mapRef.current;
    if (!map) return;
    map.flyTo({ center: [focus.lon, focus.lat], zoom: Math.max(map.getZoom(), 9.5), duration: 650 });
  }, [ready, focus]);

  return (
    <div className="relative h-full w-full">
      <div ref={holder} className="h-full w-full" aria-label="Dispatch map" role="application" />
      {children}
    </div>
  );
}

function popupBody(routeKey: string, stop: Stop): HTMLElement {
  const root = document.createElement("div");
  root.className = "w-[270px] text-[#e6edf9]";

  const head = document.createElement("div");
  head.className = "border-b border-[#1e293b] px-3 py-2";
  const eyebrow = document.createElement("div");
  eyebrow.className = "text-[9px] font-semibold uppercase tracking-[0.16em] text-[#8a9ab3]";
  eyebrow.textContent = `Route ${routeKey} · mile ${stop.mile.toFixed(1)}`;
  const titleRow = document.createElement("div");
  titleRow.className = "mt-0.5 flex items-center justify-between gap-2";
  const title = document.createElement("div");
  title.className = "text-[13px] font-semibold";
  title.textContent = stop.weather.available ? (stop.weather.condition ?? "Forecast") : "Weather unavailable";
  const chip = document.createElement("span");
  chip.className = "rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider";
  chip.style.color = levelColor(stop.risk.code);
  chip.style.background = `${levelColor(stop.risk.code)}22`;
  chip.textContent = LEVELS[stop.risk.code].label;
  titleRow.append(title, chip);
  const eta = document.createElement("div");
  eta.className = "mt-0.5 text-[10px] text-[#8a9ab3]";
  eta.textContent = `ETA ${stamp(stop.eta)} · ${clock(stop.eta)}`;
  head.append(eyebrow, titleRow, eta);
  root.append(head);

  if (!stop.weather.available) {
    const empty = document.createElement("div");
    empty.className = "px-3 py-2 text-[10px] text-[#8a9ab3]";
    empty.textContent = stop.weather.reason ?? "No forecast at this ETA.";
    root.append(empty);
    return root;
  }

  const grid = document.createElement("div");
  grid.className = "grid grid-cols-2 gap-x-2 gap-y-1 px-3 py-2 text-[10px]";
  const rows: [string, string][] = [
    ["Wind", `${num(stop.weather.wind_mph, 1)} mph`],
    ["Gusts", `${num(stop.weather.gust_mph, 1)} mph`],
    ["Rain", `${num(stop.weather.rain_in_hr, 2)} in/hr`],
    ["Snow", `${num(stop.weather.snow_in_hr, 2)} in/hr`],
    ["Temp", `${num(stop.weather.temp_f, 0)} °F`],
    ["Risk", String(stop.risk.score)],
  ];
  for (const [label, value] of rows) {
    const key = document.createElement("span");
    key.className = "text-[#8a9ab3]";
    key.textContent = label;
    const val = document.createElement("span");
    val.className = "text-right font-mono tabular-nums";
    val.textContent = value;
    grid.append(key, val);
  }
  root.append(grid);

  if (stop.risk.override) {
    const note = document.createElement("div");
    note.className = "border-t border-[#fbbf2433] bg-[#fbbf2412] px-3 py-1.5 text-[9px] text-[#fbbf24]";
    note.textContent = stop.risk.override;
    root.append(note);
  }

  const foot = document.createElement("div");
  foot.className = "border-t border-[#1e293b] px-3 py-1.5 text-[9px] text-[#8a9ab3]";
  foot.textContent = `Open-Meteo · forecast ${clock(stop.weather.at)}${stop.weather.interpolated ? " · interpolated" : ""}`;
  root.append(foot);
  return root;
}
