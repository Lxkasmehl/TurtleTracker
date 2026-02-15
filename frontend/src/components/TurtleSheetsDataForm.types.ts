/**
 * Types for TurtleSheetsDataForm and related components
 */

import type { TurtleSheetsData } from '../services/api';

export interface TurtleSheetsDataFormProps {
  initialData?: TurtleSheetsData;
  sheetName?: string;
  state?: string;
  location?: string;
  hintLocationFromCommunity?: string;
  hintCoordinates?: { latitude: number; longitude: number; source?: 'gps' | 'manual' };
  primaryId?: string;
  onSave: (data: TurtleSheetsData, sheetName: string) => Promise<void>;
  onCancel?: () => void;
  mode: 'create' | 'edit';
  hideSubmitButton?: boolean;
  onCombinedSubmit?: (data: TurtleSheetsData, sheetName: string) => Promise<void>;
  addOnlyMode?: boolean;
  initialAvailableSheets?: string[];
}

export interface TurtleSheetsDataFormRef {
  submit: () => Promise<void>;
}
