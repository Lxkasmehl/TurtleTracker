/**
 * File validation for photo uploads (size, type).
 * Used before sending files to the real backend API.
 */

const MAX_SIZE = 5 * 1024 * 1024; // 5MB
const VALID_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/gif',
  'image/webp',
];

export function validateFile(file: File): { isValid: boolean; error?: string } {
  if (file.size > MAX_SIZE) {
    return {
      isValid: false,
      error: `File is too large. Maximum: ${(MAX_SIZE / 1024 / 1024).toFixed(0)}MB`,
    };
  }
  if (!VALID_TYPES.includes(file.type)) {
    return {
      isValid: false,
      error: 'Invalid file type. Allowed: JPEG, PNG, GIF, WEBP',
    };
  }
  return { isValid: true };
}

/**
 * Simple hash for duplicate detection (filename + size + type).
 * Used when grouping photos by "same file".
 */
export function generateFileHash(
  file: File | { name: string; size: number; type: string }
): string {
  return `${file.name}_${file.size}_${file.type}`;
}
