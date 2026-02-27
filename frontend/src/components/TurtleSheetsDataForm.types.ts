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
  onSave: (data: TurtleSheetsData, sheetName: string, backendLocationPath?: string) => Promise<void>;
  onCancel?: () => void;
  mode: 'create' | 'edit';
  hideSubmitButton?: boolean;
  onCombinedSubmit?: (data: TurtleSheetsData, sheetName: string, backendLocationPath?: string) => Promise<void>;
  addOnlyMode?: boolean;
  initialAvailableSheets?: string[];
  /** When true, use backend locations (State/Location) instead of Google Sheet tabs. For community upload new turtle: sheet = State, path = State/Location. */
  useBackendLocations?: boolean;
}

export interface TurtleSheetsDataFormRef {
  submit: () => Promise<void>;
}
