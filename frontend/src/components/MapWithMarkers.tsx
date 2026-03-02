/**
 * Read-only map that shows multiple markers (e.g. digital flag positions).
 */

import { useRef, useEffect } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

export interface MarkerItem {
  lat: number;
  lon: number;
  label?: string;
}

export interface MapWithMarkersProps {
  markers: MarkerItem[];
  height?: number;
  zoom?: number;
}

export function MapWithMarkers({
  markers,
  height = 300,
  zoom = 12,
}: MapWithMarkersProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const center: L.LatLngTuple = [39.0, -98.0];
    const map = L.map(containerRef.current).setView(center, zoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: OSM_ATTRIBUTION,
    }).addTo(map);

    const icon = L.icon({
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
    });

    const latLngs: L.LatLng[] = [];
    markers.forEach((m) => {
      const latLng: L.LatLngTuple = [m.lat, m.lon];
      latLngs.push(L.latLng(latLng));
      const marker = L.marker(latLng, { icon }).addTo(map);
      if (m.label) marker.bindTooltip(m.label, { permanent: false });
    });

    if (latLngs.length === 1) {
      map.setView([markers[0].lat, markers[0].lon], 15);
    } else if (latLngs.length > 1) {
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 16 });
    }

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [markers, zoom]);

  return (
    <div
      ref={containerRef}
      style={{
        height: `${height}px`,
        width: '100%',
        borderRadius: 'var(--mantine-radius-md)',
        overflow: 'hidden',
        position: 'relative',
        zIndex: 1,
      }}
    />
  );
}
