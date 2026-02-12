import { useMemo } from 'react';
import type { UploadedPhoto } from '../types/photo';
import { generateFileHash } from '../utils/fileValidation';

export interface PhotoGroup {
  representative: UploadedPhoto;
  photos: UploadedPhoto[];
  isDuplicate: boolean;
}

function getDuplicatePhotosByImageId(
  photos: UploadedPhoto[],
  imageId: string
): UploadedPhoto[] {
  const photo = photos.find((p) => p.imageId === imageId);
  if (!photo) return [];
  const fileHash = generateFileHash({
    name: photo.fileName,
    size: photo.fileSize,
    type: photo.fileType,
  });
  return photos.filter((p) => {
    const h = generateFileHash({
      name: p.fileName,
      size: p.fileSize,
      type: p.fileType,
    });
    return h === fileHash;
  });
}

/**
 * Groups photos by duplicate file hash (same file name/size/type).
 */
export function usePhotoGroups(photos: UploadedPhoto[]): PhotoGroup[] {
  return useMemo<PhotoGroup[]>(() => {
    const groups: PhotoGroup[] = [];
    const processed = new Set<string>();

    photos.forEach((photo) => {
      if (processed.has(photo.imageId)) return;
      const duplicates = getDuplicatePhotosByImageId(photos, photo.imageId);
      duplicates.sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
      duplicates.forEach((p) => processed.add(p.imageId));
      groups.push({
        representative: duplicates[0],
        photos: duplicates,
        isDuplicate: duplicates.length > 1,
      });
    });

    groups.sort(
      (a, b) =>
        new Date(b.representative.timestamp).getTime() -
        new Date(a.representative.timestamp).getTime()
    );
    return groups;
  }, [photos]);
}
