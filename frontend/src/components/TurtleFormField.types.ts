/**
 * Types for TurtleFormField component
 */

import type { TurtleSheetsData } from '../services/api';

export type TurtleFormFieldType = 'text' | 'select';

export interface TurtleFormFieldProps {
  field: keyof TurtleSheetsData;
  label: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  description?: string;
  type?: TurtleFormFieldType;
  selectData?: string[] | { value: string; label: string }[];
  isFieldModeRestricted: boolean;
  isFieldUnlocked: (field: keyof TurtleSheetsData) => boolean;
  requestUnlock: (field: keyof TurtleSheetsData) => void;
  disabled?: boolean;
  error?: string;
}
