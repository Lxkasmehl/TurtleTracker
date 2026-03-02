/**
 * Browser geolocation helpers for community upload location hints.
 * Requires user permission before using location.
 */

import type { PhotoLocation } from '../types/photo';

export interface GetCurrentLocationResult {
  location: PhotoLocation | null;
  permissionDenied?: boolean;
}

export function getGeolocationPermission(): Promise<
  'granted' | 'denied' | 'prompt' | null
> {
  if (typeof navigator?.permissions?.query !== 'function') {
    return Promise.resolve(null);
  }
  return navigator.permissions
    .query({ name: 'geolocation' as PermissionName })
    .then((result) => result.state as 'granted' | 'denied' | 'prompt')
    .catch(() => null);
}

export function getCurrentLocation(): Promise<GetCurrentLocationResult> {
  if (!navigator.geolocation) {
    console.warn('Geolocation is not supported by this browser');
    return Promise.resolve({ location: null });
  }

  return getGeolocationPermission().then((state) => {
    if (state === 'denied') {
      return { location: null, permissionDenied: true };
    }

    return new Promise<GetCurrentLocationResult>((resolve) => {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const location: PhotoLocation = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          };
          try {
            const response = await fetch(
              `https://nominatim.openstreetmap.org/reverse?format=json&lat=${location.latitude}&lon=${location.longitude}&zoom=18&addressdetails=1`,
            );
            if (response.ok) {
              const data = await response.json();
              if (data.display_name) location.address = data.display_name;
            }
          } catch (err) {
            console.warn('Failed to get address from reverse geocoding:', err);
          }
          resolve({ location });
        },
        (error: GeolocationPositionError) => {
          console.warn('Geolocation error:', error);
          resolve({
            location: null,
            permissionDenied: error?.code === 1,
          });
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
      );
    });
  });
}
