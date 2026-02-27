/**
 * Hook for TurtleSheetsDataForm: state, effects, and submit/create-sheet logic
 */

import React, { useState, useEffect } from 'react';
import { notifications } from '@mantine/notifications';
import { IconCheck, IconX } from '@tabler/icons-react';
import type { TurtleSheetsData } from '../services/api';
import { listSheets, createSheet } from '../services/api';
import type { TurtleSheetsDataFormProps } from '../components/TurtleSheetsDataForm.types';

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
}

export function useTurtleSheetsDataForm(
  props: TurtleSheetsDataFormProps,
): UseTurtleSheetsDataFormReturn {
  const {
    initialData,
    sheetName: initialSheetName,
    onSave,
    mode,
    onCombinedSubmit,
    addOnlyMode = false,
    initialAvailableSheets,
  } = props;

  const [formData, setFormData] = useState<TurtleSheetsData>(initialData || {});
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [availableSheets, setAvailableSheets] = useState<string[]>(
    initialAvailableSheets ?? [],
  );
  const [selectedSheetName, setSelectedSheetName] = useState<string>(
    initialSheetName || '',
  );
  const [loadingSheets, setLoadingSheets] = useState(false);
  const [showCreateSheetModal, setShowCreateSheetModal] = useState(false);
  const [newSheetName, setNewSheetName] = useState('');
  const [creatingSheet, setCreatingSheet] = useState(false);
  const [unlockedFields, setUnlockedFields] = useState<Set<keyof TurtleSheetsData>>(
    new Set(),
  );
  const [additionalNotes, setAdditionalNotes] = useState('');
  const [additionalDatesRefound, setAdditionalDatesRefound] = useState('');
  const [unlockConfirmField, setUnlockConfirmField] = useState<
    keyof TurtleSheetsData | null
  >(null);

  const isFieldModeRestricted = addOnlyMode && mode === 'edit';
  const isFieldUnlocked = (field: keyof TurtleSheetsData) => unlockedFields.has(field);
  const requestUnlock = (field: keyof TurtleSheetsData) => setUnlockConfirmField(field);
  const confirmUnlock = () => {
    if (unlockConfirmField) {
      setUnlockedFields((prev) => new Set(prev).add(unlockConfirmField));
      setUnlockConfirmField(null);
    }
  };

  useEffect(() => {
    if (initialData) {
      setFormData(initialData);
      setAdditionalNotes('');
      setAdditionalDatesRefound('');
      setUnlockedFields(new Set());
    }
    if (initialSheetName) {
      setSelectedSheetName(initialSheetName);
    }
  }, [initialData, initialSheetName]);

  useEffect(() => {
    if (initialAvailableSheets != null && initialAvailableSheets.length > 0) {
      setAvailableSheets(initialAvailableSheets);
      setLoadingSheets(false);
      return;
    }

    let cancelled = false;

    const loadSheets = async () => {
      setLoadingSheets(true);
      try {
        const response = await listSheets();
        if (cancelled) return;
        if (response.success && response.sheets) {
          const sheets = response.sheets;
          setAvailableSheets(sheets);
          setSelectedSheetName((current) => {
            if (!current && !initialSheetName && sheets.length > 0) {
              return sheets[0];
            }
            return current;
          });
        }
      } catch (error) {
        if (cancelled) return;
        console.error('Failed to load sheets:', error);
        setAvailableSheets([]);
      } finally {
        if (!cancelled) setLoadingSheets(false);
      }
    };

    loadSheets();
    return () => {
      cancelled = true;
    };
  }, [initialSheetName, initialAvailableSheets]);

  const handleCreateNewSheet = async (sheetName: string) => {
    if (!sheetName?.trim()) {
      notifications.show({
        title: 'Error',
        message: 'Please enter a sheet name',
        color: 'red',
      });
      return;
    }

    setCreatingSheet(true);
    try {
      const response = await createSheet({ sheet_name: sheetName.trim() });
      if (response.success) {
        const sheetsResponse = await listSheets();
        if (sheetsResponse.success && sheetsResponse.sheets) {
          setAvailableSheets(sheetsResponse.sheets);
        }
        setSelectedSheetName(sheetName.trim());
        setShowCreateSheetModal(false);
        setNewSheetName('');
        notifications.show({
          title: 'Success',
          message: `Sheet "${sheetName}" created successfully`,
          color: 'green',
        });
      } else {
        throw new Error(response.error || 'Failed to create sheet');
      }
    } catch (error) {
      console.error('Error creating sheet:', error);
      notifications.show({
        title: 'Error',
        message: error instanceof Error ? error.message : 'Failed to create sheet',
        color: 'red',
      });
    } finally {
      setCreatingSheet(false);
    }
  };

  const handleChange = (field: keyof TurtleSheetsData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const validate = (): boolean => {
    setErrors({});
    return true;
  };

  const handleSubmit = async () => {
    if (!selectedSheetName) {
      notifications.show({
        title: 'Validation Error',
        message: 'Please select a sheet',
        color: 'red',
        icon: React.createElement(IconX, { size: 18 }),
      });
      return;
    }

    if (!validate()) {
      notifications.show({
        title: 'Validation Error',
        message: 'Please fix the errors in the form',
        color: 'red',
        icon: React.createElement(IconX, { size: 18 }),
      });
      return;
    }

    setLoading(true);
    try {
      let dataToSave = formData;
      if (isFieldModeRestricted) {
        const mergedNotes = [formData.notes, additionalNotes]
          .filter(Boolean)
          .join('\n\n');
        const existingDates = (formData.dates_refound || '')
          .split(/[\s,]+/)
          .filter(Boolean);
        const newDates = additionalDatesRefound.split(/[\s,]+/).filter(Boolean);
        const mergedDatesRefound = [...existingDates, ...newDates].join(', ');
        dataToSave = {
          ...formData,
          ...(mergedNotes !== (formData.notes || '') ? { notes: mergedNotes } : {}),
          ...(mergedDatesRefound !== (formData.dates_refound || '')
            ? { dates_refound: mergedDatesRefound }
            : {}),
        };
      }
      if (onCombinedSubmit) {
        await onCombinedSubmit(dataToSave, selectedSheetName);
      } else {
        await onSave(dataToSave, selectedSheetName);
        notifications.show({
          title: 'Success!',
          message: `Turtle data ${mode === 'create' ? 'created' : 'updated'} successfully`,
          color: 'green',
          icon: React.createElement(IconCheck, { size: 18 }),
        });
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: error instanceof Error ? error.message : 'Failed to save turtle data',
        color: 'red',
        icon: React.createElement(IconX, { size: 18 }),
      });
    } finally {
      setLoading(false);
    }
  };

  return {
    formData,
    loading,
    errors,
    availableSheets,
    selectedSheetName,
    setSelectedSheetName,
    loadingSheets,
    showCreateSheetModal,
    setShowCreateSheetModal,
    newSheetName,
    setNewSheetName,
    creatingSheet,
    additionalNotes,
    setAdditionalNotes,
    additionalDatesRefound,
    setAdditionalDatesRefound,
    unlockConfirmField,
    setUnlockConfirmField,
    isFieldModeRestricted,
    isFieldUnlocked,
    requestUnlock,
    confirmUnlock,
    handleChange,
    handleCreateNewSheet,
    handleSubmit,
  };
}
