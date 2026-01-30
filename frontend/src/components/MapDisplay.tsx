/**
 * Read-only map that shows a single point (lat/lon). Used to display
 * community location hints to the admin. Uses OpenStreetMap tiles.
 */

import { useRef, useEffect } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

export interface MapDisplayProps {
  latitude: number;
  longitude: number;
  /** Height of the map container (default 200) */
  height?: number;
  /** Zoom level (default 15) */
  zoom?: number;
}

export function MapDisplay({
  latitude,
  longitude,
  height = 200,
  zoom = 15,
}: MapDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const center: L.LatLngTuple = [latitude, longitude];
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
    L.marker(center, { icon }).addTo(map);

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [latitude, longitude, zoom]);

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
