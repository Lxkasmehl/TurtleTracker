/**
 * Inline map for picking a point (lat/lon). Uses OpenStreetMap tiles.
 * Click on the map to set the location; optional lat/lon inputs stay in sync.
 */

import { useRef, useEffect, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

const DEFAULT_CENTER: L.LatLngTuple = [39.5, -98.5]; // USA center
const DEFAULT_ZOOM = 4;

export interface MapPickerProps {
  /** Current selected point (optional) */
  value?: { lat: number; lon: number } | null;
  /** Called when user selects a point (click on map) */
  onChange?: (lat: number, lon: number) => void;
  /** Height of the map container (default 280) */
  height?: number;
  /** Optional: initial center when no value (default USA) */
  center?: L.LatLngTuple;
  /** Optional: zoom when no value */
  zoom?: number;
}

export function MapPicker({
  value,
  onChange,
  height = 280,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
}: MapPickerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  const initMap = useCallback(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current).setView(
      value ? [value.lat, value.lon] : center,
      value ? 15 : zoom
    );
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

    if (value) {
      const marker = L.marker([value.lat, value.lon], { icon, draggable: true }).addTo(map);
      marker.on('dragend', () => {
        const pos = marker.getLatLng();
        onChange?.(pos.lat, pos.lng);
      });
      markerRef.current = marker;
    }

    map.on('click', (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      if (markerRef.current) {
        markerRef.current.setLatLng([lat, lng]);
      } else {
        const marker = L.marker([lat, lng], { icon, draggable: true }).addTo(map);
        marker.on('dragend', () => {
          const pos = marker.getLatLng();
          onChange?.(pos.lat, pos.lng);
        });
        markerRef.current = marker;
      }
      onChange?.(lat, lng);
    });

    mapRef.current = map;
  }, [center, zoom, value, onChange]);

  useEffect(() => {
    initMap();
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        markerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- init map once on mount only
  }, []);

  // Sync marker and view when value changes from outside (e.g. manual lat/lon input)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (value == null) {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      return;
    }

    const latLng: L.LatLngTuple = [value.lat, value.lon];
    if (markerRef.current) {
      markerRef.current.setLatLng(latLng);
    } else {
      const icon = L.icon({
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
      });
      const marker = L.marker(latLng, { icon, draggable: true }).addTo(map);
      marker.on('dragend', () => {
        const pos = marker.getLatLng();
        onChange?.(pos.lat, pos.lng);
      });
      markerRef.current = marker;
    }
    map.setView(latLng, map.getZoom());
  }, [value, onChange]);

  return (
    <div
      ref={containerRef}
      style={{
        height: `${height}px`,
        width: '100%',
        borderRadius: 'var(--mantine-radius-md)',
        overflow: 'hidden',
      }}
    />
  );
}
