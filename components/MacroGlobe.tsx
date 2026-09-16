"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { feature } from "topojson-client";
import { MeshPhongMaterial } from "three";
import type { GlobeMethods } from "react-globe.gl";
import worldAtlas from "world-atlas/countries-110m.json";
import { countries, getCountryDeskStatus } from "@/data/countries";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });
const GLOBE_INTRO_DURATION_MS = 1_200;

const numericIsoToIso2: Record<string, string> = {
  "036": "AU", "124": "CA", "156": "CN", "250": "FR", "276": "DE", "364": "IR",
  "356": "IN", "380": "IT", "392": "JP", "410": "KR", "554": "NZ", "578": "NO", "616": "PL", "643": "RU",
  "724": "ES", "752": "SE", "756": "CH", "792": "TR", "804": "UA", "826": "GB", "840": "US",
};

// Change these three values to choose the first region visible on page load.
// latitude: north/south (-90..90), longitude: west/east (-180..180), altitude: zoom (lower = closer).
export const INITIAL_GLOBE_VIEW = { lat: 30, lng: 25, altitude: 1.55 };
// Negative values move the rendered sphere upward inside its frame.
export const GLOBE_VERTICAL_OFFSET_RATIO = 0;

const coordinates: Record<string, [number, number]> = {
  AU: [-25.3, 133.8], CA: [56.1, -106.3], CN: [35.9, 104.2], DE: [51.2, 10.5], FR: [46.2, 2.2],
  GB: [55.4, -3.4], IR: [32.4, 53.7], JP: [36.2, 138.3], NZ: [-40.9, 174.9], RU: [61.5, 105.3],
  UA: [48.4, 31.2], US: [39.8, -98.6],
  CH: [46.8, 8.2], ES: [40.5, -3.7], IN: [20.6, 78.9], IT: [41.9, 12.6], KR: [35.9, 127.8],
  NO: [60.5, 8.5], PL: [51.9, 19.1], SE: [60.1, 18.6], TR: [39.0, 35.2],
};

type GlobePolygon = { id?: string; properties?: { name?: string; iso2?: string } };
type Theme = "light" | "dark";

export default function MacroGlobe() {
  const router = useRouter();
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const frameRef = useRef<HTMLDivElement>(null);
  const [hoveredIso2, setHoveredIso2] = useState<string | null>(null);
  const [frameSize, setFrameSize] = useState({ width: 0, height: 0 });
  const [theme, setTheme] = useState<Theme>("dark");
  const countryByIso2 = useMemo(() => new Map(countries.map((country) => [country.iso2, country])), []);
  const globeMaterial = useMemo(() => new MeshPhongMaterial({ color: theme === "light" ? "#e4e4e7" : "#101014", shininess: 3 }), [theme]);
  const polygons = useMemo(() => {
    const topology = worldAtlas as unknown as { objects: { countries: unknown } };
    const collection = feature(topology as never, topology.objects.countries as never) as unknown as { features: GlobePolygon[] };
    return collection.features.map((polygon) => ({ ...polygon, properties: { ...polygon.properties, iso2: polygon.id ? numericIsoToIso2[polygon.id.padStart(3, "0")] : undefined } }));
  }, []);
  const labels = useMemo(() => countries.flatMap((country) => {
    const location = coordinates[country.iso2];
    return location ? [{ ...country, lat: location[0], lng: location[1] }] : [];
  }), []);
  useEffect(() => {
    if (!frameRef.current) return;
    const observer = new ResizeObserver(([entry]) => setFrameSize({ width: Math.floor(entry.contentRect.width), height: Math.floor(entry.contentRect.height) }));
    observer.observe(frameRef.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const updateTheme = () => setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
    updateTheme();
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);
  const colorFor = (iso2?: string) => {
    if (!iso2 || !countryByIso2.has(iso2)) return theme === "light" ? "rgba(212, 212, 216, 0.72)" : "rgba(39, 39, 42, 0.68)";
    if (hoveredIso2 === iso2) return theme === "light" ? "rgba(24, 24, 27, 0.72)" : "rgba(244, 244, 245, 0.82)";
    return getCountryDeskStatus(iso2) === "live" ? (theme === "light" ? "rgba(24, 24, 27, 0.58)" : "rgba(244, 244, 245, 0.58)") : (theme === "light" ? "rgba(82, 82, 91, 0.32)" : "rgba(161, 161, 170, 0.30)");
  };
  const openCountry = (iso2?: string) => { if (iso2 && countryByIso2.has(iso2)) router.push(`/macro/${iso2.toLowerCase()}`); };
  const setInitialView = useCallback(() => {
    // `onGlobeReady` is raised while the underlying instance is mounting.
    // Deferring one frame guarantees the imperative ref and OrbitControls are
    // both available before the initial camera view is applied.
    requestAnimationFrame(() => globeRef.current?.pointOfView(INITIAL_GLOBE_VIEW, 0));
    // Globe's built-in intro rotates the scene for 1.2 seconds. Reassert the
    // camera target once it completes so the animation cannot leave the
    // globe facing its library default view.
    window.setTimeout(() => globeRef.current?.pointOfView(INITIAL_GLOBE_VIEW, 0), GLOBE_INTRO_DURATION_MS);
  }, []);
  return <section className="macro-globe-section">
    <div className="macro-globe-intro"><div><p className="globe-kicker">01 · INTERACTIVE MACRO MAP</p><h2>Macro globe</h2></div><p>Drag to rotate.</p></div>
    <div className="macro-globe-frame" ref={frameRef}>
      {frameSize.width > 0 && <Globe
        ref={globeRef}
        width={frameSize.width}
        height={frameSize.height}
        globeOffset={[0, Math.round(frameSize.height * GLOBE_VERTICAL_OFFSET_RATIO)]}
        backgroundColor="rgba(0,0,0,0)"
        globeMaterial={globeMaterial}
        animateIn
        onGlobeReady={setInitialView}
        showAtmosphere
        atmosphereColor={theme === "light" ? "#71717a" : "#a1a1aa"}
        atmosphereAltitude={0.11}
        showGraticules
        polygonsData={polygons}
        polygonCapColor={(polygon) => colorFor((polygon as GlobePolygon).properties?.iso2)}
        polygonSideColor={() => theme === "light" ? "rgba(161, 161, 170, 0.18)" : "rgba(24, 24, 27, 0.22)"}
        polygonStrokeColor={() => theme === "light" ? "rgba(82, 82, 91, 0.30)" : "rgba(161, 161, 170, 0.26)"}
        polygonAltitude={(polygon) => (countryByIso2.has((polygon as GlobePolygon).properties?.iso2 ?? "") ? 0.014 : 0.003)}
        polygonLabel={(polygon) => { const iso2 = (polygon as GlobePolygon).properties?.iso2; const country = iso2 ? countryByIso2.get(iso2) : undefined; return country ? `${country.name} · ${getCountryDeskStatus(country.iso2).toUpperCase()}` : ""; }}
        onPolygonHover={(polygon) => setHoveredIso2((polygon as GlobePolygon | null)?.properties?.iso2 ?? null)}
        onPolygonClick={(polygon) => openCountry((polygon as GlobePolygon).properties?.iso2)}
        labelsData={labels}
        labelLat="lat"
        labelLng="lng"
        labelText="iso2"
        labelColor={() => theme === "light" ? "#18181b" : "#f4f4f5"}
        labelSize={0.52}
        labelDotRadius={0.12}
        labelAltitude={0.018}
        onLabelClick={(label) => openCountry((label as { iso2?: string }).iso2)}
      />}
      <div className="globe-overlay" aria-hidden="true"><span>LIVE</span><span>PARTIAL</span><span>{countries.length} ECONOMIES</span></div>
    </div>
  </section>;
}
