import type { UploadedPhoto } from '../types/photo';

/**
 * Format file size in bytes to human-readable string
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 MB")
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format location from photo to display string
 * @param photo - Photo with location data
 * @returns Formatted location string
 */
export function formatLocation(photo: UploadedPhoto): string {
  if (!photo.location) return 'Location not available';
  if (photo.location.address) return photo.location.address;
  return `${photo.location.latitude.toFixed(6)}, ${photo.location.longitude.toFixed(6)}`;
}

/**
 * Get Google Maps URL for photo location
 * @param photo - Photo with location data
 * @returns Google Maps URL or null if no location
 */
export function getGoogleMapsUrl(photo: UploadedPhoto): string | null {
  if (!photo.location) return null;
  return `https://www.google.com/maps?q=${photo.location.latitude},${photo.location.longitude}`;
}

