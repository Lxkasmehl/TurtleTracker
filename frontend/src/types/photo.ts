/**
 * Shared types for photo/location data in the frontend.
 * Used by upload flow, photo cards, and geolocation.
 */

export interface PhotoLocation {
  latitude: number;
  longitude: number;
  address?: string;
  accuracy?: number;
}

export interface UploadedPhoto {
  imageId: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  preview: string;
  timestamp: string;
  uploadDate: string;
  location?: PhotoLocation;
}
