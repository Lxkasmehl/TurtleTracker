/**
 * Turtle API – photo upload, review queue, matching
 */

import { getToken, removeToken, TURTLE_API_BASE_URL } from './config';
import type { TurtleSheetsData } from './sheets';

export interface TurtleMatch {
  turtle_id: string;
  location: string;
  distance: number;
  file_path: string;
  filename: string;
}

export interface UploadPhotoResponse {
  success: boolean;
  request_id?: string;
  matches?: TurtleMatch[];
  uploaded_image_path?: string;
  message: string;
}

/** Location hint from community (never stored in sheets, queue/display only) */
export interface LocationHint {
  latitude: number;
  longitude: number;
  source: 'gps' | 'manual';
}

export interface ReviewQueueItem {
  request_id: string;
  uploaded_image: string;
  metadata: {
    finder?: string;
    email?: string;
    uploaded_at?: number;
    state?: string;
    location?: string;
    location_hint_lat?: number;
    location_hint_lon?: number;
    location_hint_source?: 'gps' | 'manual';
  };
  candidates: Array<{
    rank: number;
    turtle_id: string;
    score: number;
    image_path: string;
  }>;
  status: string;
}

export interface ReviewQueueResponse {
  success: boolean;
  items: ReviewQueueItem[];
}

export interface ApproveReviewRequest {
  match_turtle_id?: string;
  new_location?: string;
  new_turtle_id?: string;
  uploaded_image_path?: string;
  sheets_data?: TurtleSheetsData;
}

export interface ApproveReviewResponse {
  success: boolean;
  message: string;
}

// Upload photo (Admin or Community)
export const uploadTurtlePhoto = async (
  file: File,
  _role: 'admin' | 'community',
  _email: string,
  location?: { state: string; location: string },
  locationHint?: LocationHint,
  matchSheet?: string,
): Promise<UploadPhotoResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  if (location) {
    formData.append('state', location.state);
    formData.append('location', location.location);
  }
  if (matchSheet !== undefined) {
    formData.append('match_sheet', matchSheet);
  }
  if (locationHint) {
    formData.append('location_hint_lat', String(locationHint.latitude));
    formData.append('location_hint_lon', String(locationHint.longitude));
    formData.append('location_hint_source', locationHint.source);
  }

  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${TURTLE_API_BASE_URL}/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    if (response.status === 401) {
      removeToken();
      throw new Error('Authentication failed. Please try again.');
    }
    const error = await response.json().catch(() => ({ error: 'Upload failed' }));
    const message = error.error || 'Upload failed';
    const details = error.details as string | undefined;
    if (details && import.meta.env.DEV) {
      console.error('Upload error details:', details);
    }
    throw new Error(message);
  }

  return await response.json();
};

// Get review queue (Admin only)
export const getReviewQueue = async (): Promise<ReviewQueueResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${TURTLE_API_BASE_URL}/review-queue`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to load review queue');
  }

  return await response.json();
};

// Approve review item (Admin only)
export const approveReview = async (
  requestId: string,
  data: ApproveReviewRequest,
): Promise<ApproveReviewResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${TURTLE_API_BASE_URL}/review/${requestId}/approve`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to approve review');
  }

  return await response.json();
};

// Delete review queue item (Admin only)
export const deleteReviewItem = async (
  requestId: string,
): Promise<{ success: boolean; message: string }> => {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(
    `${TURTLE_API_BASE_URL}/review/${encodeURIComponent(requestId)}`,
    {
      method: 'DELETE',
      headers,
    },
  );
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ error: 'Failed to delete' }));
    throw new Error(error.error || 'Failed to delete review item');
  }
  return await response.json();
};

// Get image URL helper
export const getImageUrl = (imagePath: string): string => {
  if (imagePath.startsWith('http')) {
    return imagePath;
  }
  const encodedPath = encodeURIComponent(imagePath);
  return `${TURTLE_API_BASE_URL.replace('/api', '')}/api/images?path=${encodedPath}`;
};
