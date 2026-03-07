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

/** Props for TurtleSheetsDataFormFields (form grid fragment) */
export interface TurtleSheetsDataFormFieldsProps {
  formData: TurtleSheetsData;
  handleChange: (field: keyof TurtleSheetsData, value: string) => void;
  isFieldModeRestricted: boolean;
  isFieldUnlocked: (field: keyof TurtleSheetsData) => boolean;
  requestUnlock: (field: keyof TurtleSheetsData) => void;
  additionalDatesRefound: string;
  setAdditionalDatesRefound: (v: string) => void;
  additionalNotes: string;
  setAdditionalNotes: (v: string) => void;
  primaryId?: string;
  hintLocationFromCommunity?: string;
  hintCoordinates?: { latitude: number; longitude: number; source?: 'gps' | 'manual' };
  /** Field-level validation errors keyed by field name */
  errors?: Record<string, string>;
  /** In create mode the ID field is always disabled and filled by generate-id (sex + sequence per sheet). */
  mode?: 'create' | 'edit';
}

/** Return type of useTurtleSheetsDataForm hook */
export interface UseTurtleSheetsDataFormReturn {
  formData: TurtleSheetsData;
  loading: boolean;
  errors: Record<string, string>;
  availableSheets: string[];
  selectedSheetName: string;
  setSelectedSheetName: (v: string) => void;
  loadingSheets: boolean;
  showCreateSheetModal: boolean;
  setShowCreateSheetModal: (v: boolean) => void;
  newSheetName: string;
  setNewSheetName: (v: string) => void;
  creatingSheet: boolean;
  additionalNotes: string;
  setAdditionalNotes: (v: string) => void;
  additionalDatesRefound: string;
  setAdditionalDatesRefound: (v: string) => void;
  unlockConfirmField: keyof TurtleSheetsData | null;
  setUnlockConfirmField: (v: keyof TurtleSheetsData | null) => void;
  isFieldModeRestricted: boolean;
  isFieldUnlocked: (field: keyof TurtleSheetsData) => boolean;
  requestUnlock: (field: keyof TurtleSheetsData) => void;
  confirmUnlock: () => void;
  handleChange: (field: keyof TurtleSheetsData, value: string) => void;
  handleCreateNewSheet: (sheetName: string) => Promise<void>;
  handleSubmit: () => Promise<void>;
  /** In create mode, true until existing turtle names have been loaded (for duplicate check). */
  loadingTurtleNames: boolean;
}
