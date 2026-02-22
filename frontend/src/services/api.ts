/**
 * API Service for backend communication
 */

// Auth Backend API URL - Node.js/Express server runs on port 3001
const AUTH_API_BASE_URL =
  import.meta.env.VITE_AUTH_API_URL || 'http://localhost:3001/api';

// Turtle Backend API URL - Flask server runs on port 5000
const TURTLE_API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export interface User {
  id: number;
  email: string;
  name: string | null;
  role: 'community' | 'admin';
}

export interface AuthResponse {
  success: boolean;
  token: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
  token?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// Get stored token from localStorage
export const getToken = (): string | null => {
  return localStorage.getItem('auth_token');
};

// Store token in localStorage
export const setToken = (token: string): void => {
  localStorage.setItem('auth_token', token);
};

// Remove token from localStorage
export const removeToken = (): void => {
  localStorage.removeItem('auth_token');
};

// Make authenticated API request to Auth Backend
export const apiRequest = async (
  endpoint: string,
  options: RequestInit = {},
): Promise<Response> => {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${AUTH_API_BASE_URL}${endpoint}`, {
    ...options,
    headers: headers as HeadersInit,
  });

  return response;
};

// Register new user
export const register = async (data: RegisterRequest): Promise<AuthResponse> => {
  const response = await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Registration failed');
  }

  const result = await response.json();
  if (result.success && result.token) {
    setToken(result.token);
  }
  return result;
};

// Login
export const login = async (data: LoginRequest): Promise<AuthResponse> => {
  const response = await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Login failed');
  }

  const result = await response.json();
  if (result.success && result.token) {
    setToken(result.token);
  }
  return result;
};

// Get current user
export const getCurrentUser = async (): Promise<User | null> => {
  const token = getToken();
  if (!token) {
    return null;
  }

  const response = await apiRequest('/auth/me');

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      removeToken();
      return null;
    }
    const error = await response.json();
    throw new Error(error.error || 'Failed to get user');
  }

  const result = await response.json();
  return result.user;
};

// Logout
export const logout = async (): Promise<void> => {
  try {
    await apiRequest('/auth/logout', {
      method: 'POST',
    });
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    removeToken();
  }
};

// Google OAuth URL
export const getGoogleAuthUrl = (): string => {
  return `${AUTH_API_BASE_URL.replace('/api', '')}/api/auth/google`;
};

// Get invitation details by token
export interface InvitationDetails {
  success: boolean;
  invitation: {
    email: string;
    expires_at: string;
  };
}

export const getInvitationDetails = async (token: string): Promise<InvitationDetails> => {
  const response = await apiRequest(`/auth/invitation/${token}`, {
    method: 'GET',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get invitation details');
  }

  return await response.json();
};

// Promote user to admin (admin only)
export interface PromoteToAdminResponse {
  success: boolean;
  message: string;
  user: {
    id: number;
    email: string;
    role: 'admin';
  };
}

export const promoteToAdmin = async (email: string): Promise<PromoteToAdminResponse> => {
  const response = await apiRequest('/admin/promote-to-admin', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to promote user to admin');
  }

  return await response.json();
};

// --- Turtle Photo Upload & Matching API ---

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
    /** Hint only – never stored in sheets */
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
  _role: 'admin' | 'community', // Used by frontend for navigation logic, not sent to backend
  _email: string, // Used by frontend, not sent to backend
  location?: { state: string; location: string },
  /** Optional: coordinates as hint only (never stored in sheets) */
  locationHint?: LocationHint,
  /** Admin only: sheet name (location) to test against; '' or undefined = test against all locations */
  matchSheet?: string,
): Promise<UploadPhotoResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  // Note: role and email are no longer sent in form data - they come from JWT token
  // These parameters are kept for API compatibility and frontend logic, but backend extracts them from JWT

  if (location) {
    formData.append('state', location.state);
    formData.append('location', location.location);
  }
  // Admin: which location/datasheet to match against (empty = all)
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
      // 401 should not happen for uploads anymore since auth is optional
      // but keep this for backwards compatibility
      throw new Error('Authentication failed. Please try again.');
    }
    const error = await response.json().catch(() => ({ error: 'Upload failed' }));
    const message = error.error || 'Upload failed';
    // Include backend details in dev for debugging (e.g. 500 traceback)
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

  const response = await fetch(`${TURTLE_API_BASE_URL}/review/${requestId}/approve`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to approve review');
  }

  return await response.json();
};

// Delete review queue item (Admin only) – no processing, removes packet
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
    const error = await response.json().catch(() => ({ error: 'Failed to delete' }));
    throw new Error(error.error || 'Failed to delete review item');
  }
  return await response.json();
};

// Get image URL helper
export const getImageUrl = (imagePath: string): string => {
  // Convert file path to API endpoint
  if (imagePath.startsWith('http')) {
    return imagePath;
  }
  // For local paths, encode them as query parameter
  const encodedPath = encodeURIComponent(imagePath);
  return `${TURTLE_API_BASE_URL.replace('/api', '')}/api/images?path=${encodedPath}`;
};

// --- Google Sheets API ---

export interface TurtleSheetsData {
  primary_id?: string;
  sheet_name?: string; // Which Google Sheets tab this turtle belongs to
  transmitter_id?: string;
  id?: string;
  id2?: string;
  pit?: string;
  pic_in_2024_archive?: string;
  adopted?: string;
  ibutton?: string;
  dna_extracted?: string;
  date_1st_found?: string;
  species?: string;
  name?: string;
  sex?: string;
  ibutton_last_set?: string;
  last_assay_date?: string;
  dates_refound?: string;
  general_location?: string;
  location?: string;
  notes?: string;
  transmitter_put_on_by?: string;
  transmitter_on_date?: string;
  transmitter_type?: string;
  transmitter_lifespan?: string;
  radio_replace_date?: string;
  old_frequencies?: string;
}

export interface GetTurtleSheetsDataResponse {
  success: boolean;
  data?: TurtleSheetsData;
  message?: string;
  exists?: boolean; // Whether the turtle exists in Google Sheets
}

export interface ListSheetsResponse {
  success: boolean;
  sheets?: string[];
  error?: string;
}

export interface GetLocationsResponse {
  success: boolean;
  locations?: string[]; // e.g. ["Kansas/Wichita", "Kansas/Lawrence", "Nebraska/Topeka", "Incidental_Finds", "Community_Uploads"]
  error?: string;
}

export interface GeneratePrimaryIdRequest {
  state: string;
  location?: string;
}

export interface GeneratePrimaryIdResponse {
  success: boolean;
  primary_id?: string;
  error?: string;
}

export interface GenerateTurtleIdRequest {
  sex: string; // M, F, J, or U
  sheet_name: string; // Sheet (tab) the turtle belongs to; sequence is scoped to this sheet
}

export interface GenerateTurtleIdResponse {
  success: boolean;
  id?: string;
  error?: string;
}

export interface CreateTurtleSheetsDataRequest {
  sheet_name: string;
  state?: string;
  location?: string;
  turtle_data: TurtleSheetsData;
}

export interface CreateTurtleSheetsDataResponse {
  success: boolean;
  primary_id?: string;
  message?: string;
  error?: string;
}

export interface UpdateTurtleSheetsDataRequest {
  sheet_name: string;
  state?: string;
  location?: string;
  turtle_data: Partial<TurtleSheetsData>;
}

export interface UpdateTurtleSheetsDataResponse {
  success: boolean;
  message?: string;
  error?: string;
}

// Get turtle data from Google Sheets
// sheetName is optional - if not provided, the backend will automatically find the sheet containing the turtle
export const getTurtleSheetsData = async (
  primaryId: string,
  sheetName?: string,
  state?: string,
  location?: string,
): Promise<GetTurtleSheetsDataResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const params = new URLSearchParams();
  if (sheetName) {
    params.append('sheet_name', sheetName);
  }
  if (state) {
    params.append('state', state);
  }
  if (location) {
    params.append('location', location);
  }

  const response = await fetch(
    `${TURTLE_API_BASE_URL}/sheets/turtle/${primaryId}${params.toString() ? `?${params.toString()}` : ''}`,
    {
      method: 'GET',
      headers,
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get turtle data from sheets');
  }

  return await response.json();
};

// Create turtle data in Google Sheets
export const createTurtleSheetsData = async (
  data: CreateTurtleSheetsDataRequest,
): Promise<CreateTurtleSheetsDataResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${TURTLE_API_BASE_URL}/sheets/turtle`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to create turtle data in sheets');
  }

  return await response.json();
};

// Update turtle data in Google Sheets
export const updateTurtleSheetsData = async (
  primaryId: string,
  data: UpdateTurtleSheetsDataRequest,
): Promise<UpdateTurtleSheetsDataResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${TURTLE_API_BASE_URL}/sheets/turtle/${primaryId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to update turtle data in sheets');
  }

  return await response.json();
};

// Generate a new primary ID
export const generatePrimaryId = async (
  data: GeneratePrimaryIdRequest,
  timeoutMs: number = 15000,
): Promise<GeneratePrimaryIdResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Create an AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${TURTLE_API_BASE_URL}/sheets/generate-primary-id`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to generate primary ID');
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    }
    throw error;
  }
};

// Generate the next biology ID (ID column) based on sex: M/F/J/U + sequence number
export const generateTurtleId = async (
  data: GenerateTurtleIdRequest,
  timeoutMs: number = 10000,
): Promise<GenerateTurtleIdResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${TURTLE_API_BASE_URL}/sheets/generate-id`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to generate turtle ID');
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    }
    throw error;
  }
};

// List all available sheets (longer timeout: backend may retry Google API on first timeout)
export const listSheets = async (
  timeoutMs: number = 25000,
): Promise<ListSheetsResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Create an AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${TURTLE_API_BASE_URL}/sheets/sheets`, {
      method: 'GET',
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to list sheets');
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    }
    throw error;
  }
};

// List backend location paths (State/Location) for community upload and manual upload
export const getLocations = async (): Promise<GetLocationsResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(`${TURTLE_API_BASE_URL}/locations`, {
    method: 'GET',
    headers,
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to load locations');
  }
  return await response.json();
};

// Create a new sheet with headers
export interface CreateSheetRequest {
  sheet_name: string;
}

export interface CreateSheetResponse {
  success: boolean;
  message?: string;
  sheets?: string[];
  error?: string;
}

export const createSheet = async (
  data: CreateSheetRequest,
): Promise<CreateSheetResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${TURTLE_API_BASE_URL}/sheets/sheets`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to create sheet');
  }

  return await response.json();
};

// List all turtle names across sheets (for duplicate-name validation)
export interface TurtleNameEntry {
  name: string;
  primary_id: string;
}

export interface ListTurtleNamesResponse {
  success: boolean;
  names: TurtleNameEntry[];
  error?: string;
}

export const getTurtleNames = async (): Promise<ListTurtleNamesResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${TURTLE_API_BASE_URL}/sheets/turtle-names`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to list turtle names');
  }

  return await response.json();
};

// List all turtles from Google Sheets
export interface ListTurtlesResponse {
  success: boolean;
  turtles: TurtleSheetsData[];
  count: number;
  error?: string;
}

export const listAllTurtlesFromSheets = async (
  sheetName?: string,
): Promise<ListTurtlesResponse> => {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const params = new URLSearchParams();
  if (sheetName) {
    params.append('sheet', sheetName);
  }

  const response = await fetch(
    `${TURTLE_API_BASE_URL}/sheets/turtles?${params.toString()}`,
    {
      method: 'GET',
      headers,
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to list turtles from sheets');
  }

  return await response.json();
};
