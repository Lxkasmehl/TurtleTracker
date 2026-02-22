/**
 * Turtle Sheets Data Form Component
 * Form for entering/editing turtle data that will be synced to Google Sheets
 */

import {
  Stack,
  TextInput,
  Select,
  Textarea,
  Group,
  Button,
  Alert,
  Text,
  Grid,
  Paper,
  Title,
  Loader,
  Modal,
  Anchor,
} from '@mantine/core';
import { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import {
  IconInfoCircle,
  IconCheck,
  IconX,
  IconMapPin,
  IconLockOpen,
} from '@tabler/icons-react';
import { MapDisplay } from './MapDisplay';
import { notifications } from '@mantine/notifications';
import type { TurtleSheetsData, TurtleNameEntry } from '../services/api';
import { listSheets, createSheet, generateTurtleId, getTurtleNames } from '../services/api';

interface TurtleSheetsDataFormProps {
  initialData?: TurtleSheetsData;
  sheetName?: string; // Selected sheet name
  state?: string;
  location?: string;
  /** Shown as help only (e.g. community-indicated location); not used as form field values */
  hintLocationFromCommunity?: string;
  /** Optional coordinates hint from community (never stored in sheets) */
  hintCoordinates?: { latitude: number; longitude: number; source?: 'gps' | 'manual' };
  primaryId?: string;
  onSave: (data: TurtleSheetsData, sheetName: string) => Promise<void>;
  onCancel?: () => void;
  mode: 'create' | 'edit';
  hideSubmitButton?: boolean; // Hide the form's submit button
  onCombinedSubmit?: (data: TurtleSheetsData, sheetName: string) => Promise<void>; // Combined action handler
  /** When true (e.g. field use), only allow adding data; existing values are read-only unless user unlocks per field */
  addOnlyMode?: boolean;
  /** When provided, form uses this list and does not call listSheets() on mount (avoids duplicate API calls) */
  initialAvailableSheets?: string[];
}

export interface TurtleSheetsDataFormRef {
  submit: () => Promise<void>;
}

export const TurtleSheetsDataForm = forwardRef<
  TurtleSheetsDataFormRef,
  TurtleSheetsDataFormProps
>(
  (
    {
      initialData,
      sheetName: initialSheetName,
      hintLocationFromCommunity,
      hintCoordinates,
      primaryId,
      onSave,
      onCancel,
      mode,
      hideSubmitButton = false,
      onCombinedSubmit,
      addOnlyMode = false,
      initialAvailableSheets,
      // state/location accepted for API compatibility but not used as form values – use hintLocationFromCommunity for display
    },
    ref,
  ) => {
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
    /** In addOnlyMode (edit): fields the user has explicitly unlocked for editing */
    const [unlockedFields, setUnlockedFields] = useState<Set<keyof TurtleSheetsData>>(
      new Set(),
    );
    /** In addOnlyMode (edit): additional notes/dates to append (not edit existing) */
    const [additionalNotes, setAdditionalNotes] = useState('');
    const [additionalDatesRefound, setAdditionalDatesRefound] = useState('');
    /** Unlock confirmation: field key we're about to unlock */
    const [unlockConfirmField, setUnlockConfirmField] = useState<
      keyof TurtleSheetsData | null
    >(null);
    /** In create mode: preview of auto-generated ID (gender + sequence number) */
    const [idPreview, setIdPreview] = useState<string>('');
    const [loadingIdPreview, setLoadingIdPreview] = useState(false);
    /** All turtle names across sheets (for duplicate-name validation) */
    const [existingTurtleNames, setExistingTurtleNames] = useState<TurtleNameEntry[]>([]);

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
        // Reset add-only state when switching to another record
        setAdditionalNotes('');
        setAdditionalDatesRefound('');
        setUnlockedFields(new Set());
      }
      if (initialSheetName) {
        setSelectedSheetName(initialSheetName);
      }
    }, [initialData, initialSheetName]);

    // In create mode, fetch next biology ID when sex and sheet are selected (preview only; backend assigns on save)
    useEffect(() => {
      if (mode !== 'create') {
        setIdPreview('');
        return;
      }
      const sheetName = (selectedSheetName || '').trim();
      const sex = (formData.sex || '').trim().toUpperCase();
      if (!sheetName || !sex || !['M', 'F', 'J', 'U'].includes(sex)) {
        setIdPreview('');
        return;
      }
      let cancelled = false;
      setLoadingIdPreview(true);
      generateTurtleId({ sex, sheet_name: sheetName })
        .then((res) => {
          if (!cancelled && res.success && res.id) setIdPreview(res.id);
          else if (!cancelled) setIdPreview('');
        })
        .catch(() => {
          if (!cancelled) setIdPreview('');
        })
        .finally(() => {
          if (!cancelled) setLoadingIdPreview(false);
        });
      return () => {
        cancelled = true;
      };
    }, [mode, formData.sex, selectedSheetName]);

    useEffect(() => {
      // If parent provided sheets, skip API call to avoid duplicate requests
      if (initialAvailableSheets != null && initialAvailableSheets.length > 0) {
        setAvailableSheets(initialAvailableSheets);
        setLoadingSheets(false);
        return;
      }

      let cancelled = false;

      const loadSheets = async () => {
        setLoadingSheets(true);

        try {
          // listSheets() uses a 25s timeout so backend retries (e.g. Google API timeout) can complete
          const response = await listSheets();

          // Check if component was unmounted
          if (cancelled) {
            return;
          }

          if (response.success && response.sheets) {
            const sheets = response.sheets;
            setAvailableSheets(sheets);
            // If no sheet is selected and sheets are available, select the first one
            setSelectedSheetName((current) => {
              if (!current && !initialSheetName && sheets.length > 0) {
                return sheets[0];
              }
              return current;
            });
          }
        } catch (error) {
          // Check if component was unmounted
          if (cancelled) {
            return;
          }

          console.error('Failed to load sheets:', error);
          // Don't show error notification - just log it
          // The form can still work without sheets list (user can type sheet name)
          setAvailableSheets([]);
        } finally {
          if (!cancelled) {
            setLoadingSheets(false);
          }
        }
      };

      loadSheets();

      // Cleanup: cancel if component unmounts
      return () => {
        cancelled = true;
      };
    }, [initialSheetName, initialAvailableSheets]);

    // Load existing turtle names for duplicate-name validation (create mode or when name is editable)
    useEffect(() => {
      let cancelled = false;
      const loadNames = async () => {
        try {
          const res = await getTurtleNames();
          if (!cancelled && res.success && res.names) {
            setExistingTurtleNames(res.names);
          }
        } catch {
          if (!cancelled) setExistingTurtleNames([]);
        }
      };
      loadNames();
      return () => {
        cancelled = true;
      };
    }, []);

    const handleCreateNewSheet = async (sheetName: string) => {
      if (!sheetName || !sheetName.trim()) {
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
          // Reload sheets list
          const sheetsResponse = await listSheets();
          if (sheetsResponse.success && sheetsResponse.sheets) {
            setAvailableSheets(sheetsResponse.sheets);
          }
          // Select the newly created sheet
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
      // Clear error for this field
      if (errors[field]) {
        setErrors((prev) => {
          const newErrors = { ...prev };
          delete newErrors[field];
          return newErrors;
        });
      }
    };

    const validate = (namesForDuplicateCheck?: TurtleNameEntry[]): boolean => {
      const newErrors: Record<string, string> = {};
      const nameVal = (formData.name || '').trim();
      const namesToCheck = namesForDuplicateCheck ?? existingTurtleNames;
      if (nameVal && namesToCheck.length >= 0) {
        const nameLower = nameVal.toLowerCase();
        const isDuplicate = namesToCheck.some(
          (entry) =>
            entry.name.trim().toLowerCase() === nameLower &&
            entry.primary_id !== primaryId,
        );
        if (isDuplicate) {
          newErrors.name =
            'This name is already used by another turtle. Please choose a different name.';
        }
      }
      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async () => {
      if (!selectedSheetName) {
        notifications.show({
          title: 'Validation Error',
          message: 'Please select a sheet',
          color: 'red',
          icon: <IconX size={18} />,
        });
        return;
      }

      // Always fetch fresh names on submit so we never allow a duplicate due to slow initial load
      let namesForValidation: TurtleNameEntry[] = existingTurtleNames;
      if ((formData.name || '').trim()) {
        try {
          const res = await getTurtleNames();
          if (res.success && res.names) {
            namesForValidation = res.names;
            setExistingTurtleNames(res.names);
          }
        } catch {
          // proceed with existing cache
        }
      }

      if (!validate(namesForValidation)) {
        notifications.show({
          title: 'Validation Error',
          message: 'Please fix the errors in the form',
          color: 'red',
          icon: <IconX size={18} />,
        });
        return;
      }

      setLoading(true);
      try {
        let dataToSave = formData;
        if (isFieldModeRestricted) {
          // Merge append-only fields: additional notes and dates refound
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
        // Use combined submit handler if provided, otherwise use normal onSave
        if (onCombinedSubmit) {
          await onCombinedSubmit(dataToSave, selectedSheetName);
        } else {
          await onSave(dataToSave, selectedSheetName);
          notifications.show({
            title: 'Success!',
            message: `Turtle data ${mode === 'create' ? 'created' : 'updated'} successfully`,
            color: 'green',
            icon: <IconCheck size={18} />,
          });
        }
      } catch (error) {
        notifications.show({
          title: 'Error',
          message: error instanceof Error ? error.message : 'Failed to save turtle data',
          color: 'red',
          icon: <IconX size={18} />,
        });
      } finally {
        setLoading(false);
      }
    };

    // Expose submit method via ref
    useImperativeHandle(ref, () => ({
      submit: handleSubmit,
    }));

    return (
      <Paper shadow='sm' p='xl' radius='md' withBorder style={{ position: 'relative' }}>
        {loading && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(255, 255, 255, 0.9)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              borderRadius: 'var(--mantine-radius-md)',
            }}
          >
            <Stack align='center' gap='md'>
              <Loader size='xl' />
              <Text size='lg' fw={500}>
                {mode === 'create' ? 'Creating' : 'Updating'} turtle data...
              </Text>
            </Stack>
          </div>
        )}
        <Stack
          gap='lg'
          style={{ opacity: loading ? 0.3 : 1, pointerEvents: loading ? 'none' : 'auto' }}
        >
          <div>
            <Title order={3}>Turtle Data - Google Sheets</Title>
            <Text size='sm' c='dimmed' mt='xs'>
              {mode === 'create'
                ? 'Enter turtle data to add to Google Sheets'
                : 'Edit turtle data in Google Sheets'}
            </Text>
            {primaryId && (
              <Text size='sm' c='dimmed' mt='xs'>
                Primary ID: <strong>{primaryId}</strong>
              </Text>
            )}
          </div>

          <Alert icon={<IconInfoCircle size={18} />} color='blue' radius='md'>
            <Text size='sm'>
              This data will be synced to Google Sheets. Primary ID is automatically
              generated.
            </Text>
          </Alert>

          {isFieldModeRestricted && (
            <Alert color='yellow' radius='md' title='Add-only mode (field use)'>
              <Text size='sm'>
                You can only add data here; existing values are read-only to avoid
                accidental changes. You can append to Notes and Dates Refound. To edit an
                existing field, use &quot;Unlock editing&quot; above that field and
                confirm.
              </Text>
            </Alert>
          )}

          <Grid gutter='md'>
            {/* Sheet Selection */}
            <Grid.Col span={12}>
              {loadingSheets ? (
                <Group gap='sm'>
                  <Loader size='sm' />
                  <Text size='sm' c='dimmed'>
                    Loading available sheets...
                  </Text>
                </Group>
              ) : isFieldModeRestricted && !isFieldUnlocked('sheet_name') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('sheet_name')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Sheet / Location'
                    value={selectedSheetName}
                    disabled
                    description='Select the Google Sheets tab where this turtle data should be stored'
                  />
                </>
              ) : (
                <Select
                  label='Sheet / Location'
                  placeholder='Select a sheet or create new'
                  data={[
                    ...availableSheets,
                    { value: '__create_new__', label: '+ Create New Sheet' },
                  ]}
                  value={selectedSheetName}
                  onChange={(value) => {
                    if (value === '__create_new__') {
                      setShowCreateSheetModal(true);
                      setSelectedSheetName('');
                    } else {
                      setSelectedSheetName(value || '');
                    }
                  }}
                  required
                  description='Select the Google Sheets tab where this turtle data should be stored'
                  error={!selectedSheetName ? 'Sheet selection is required' : undefined}
                  searchable
                  comboboxProps={{ withinPortal: false }}
                />
              )}
            </Grid.Col>
            {/* Row 1: ID Fields */}
            {primaryId && (
              <Grid.Col span={12}>
                <TextInput
                  label='Primary ID'
                  value={primaryId}
                  disabled
                  description='Automatically generated unique identifier'
                />
              </Grid.Col>
            )}
            <Grid.Col span={{ base: 12, md: 6 }}>
              {mode === 'create' ? (
                <TextInput
                  label='ID'
                  value={loadingIdPreview ? '…' : idPreview || '—'}
                  disabled
                  description='Auto-generated from sex and sequence number for this sheet (assigned on save)'
                />
              ) : isFieldModeRestricted && !isFieldUnlocked('id') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('id')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='ID'
                    value={formData.id || ''}
                    disabled
                    description='Biology ID (gender + sequence number)'
                  />
                </>
              ) : (
                <TextInput
                  label='ID'
                  placeholder='Original ID'
                  value={formData.id || ''}
                  onChange={(e) => handleChange('id', e.target.value)}
                  description='Biology ID (gender + sequence number)'
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('id2') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('id2')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='ID2 (random sequence)'
                    value={formData.id2 || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='ID2 (random sequence)'
                  placeholder='Secondary ID'
                  value={formData.id2 || ''}
                  onChange={(e) => handleChange('id2', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 2: Transmitter Fields */}
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('transmitter_id') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('transmitter_id')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Transmitter ID'
                    value={formData.transmitter_id || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='Transmitter ID'
                  placeholder='Transmitter ID'
                  value={formData.transmitter_id || ''}
                  onChange={(e) => handleChange('transmitter_id', e.target.value)}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('transmitter_type') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('transmitter_type')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Transmitter Type'
                    value={formData.transmitter_type || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='Transmitter Type'
                  placeholder='Transmitter type'
                  value={formData.transmitter_type || ''}
                  onChange={(e) => handleChange('transmitter_type', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 3: Basic Info */}
            <Grid.Col span={{ base: 12, md: 4 }}>
              {isFieldModeRestricted && !isFieldUnlocked('name') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('name')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput label='Name' value={formData.name || ''} disabled />
                </>
              ) : (
                <TextInput
                  label='Name'
                  placeholder='Turtle name'
                  value={formData.name || ''}
                  onChange={(e) => handleChange('name', e.target.value)}
                  onBlur={() => validate()}
                  error={errors.name}
                  description={
                    mode === 'create'
                      ? 'Names must be unique across all location sheets.'
                      : undefined
                  }
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 4 }}>
              {isFieldModeRestricted && !isFieldUnlocked('sex') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('sex')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput label='Sex' value={formData.sex || ''} disabled />
                </>
              ) : (
                <Select
                  label='Sex'
                  placeholder='Select sex'
                  data={['F', 'M', 'J', 'U']}
                  value={formData.sex || ''}
                  onChange={(value) => handleChange('sex', value || '')}
                  comboboxProps={{ withinPortal: false }}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 4 }}>
              {isFieldModeRestricted && !isFieldUnlocked('species') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('species')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput label='Species' value={formData.species || ''} disabled />
                </>
              ) : (
                <TextInput
                  label='Species'
                  placeholder='Species'
                  value={formData.species || ''}
                  onChange={(e) => handleChange('species', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 4: Dates */}
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('date_1st_found') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('date_1st_found')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Date 1st Found'
                    value={formData.date_1st_found || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='Date 1st Found'
                  placeholder='YYYY-MM-DD'
                  value={formData.date_1st_found || ''}
                  onChange={(e) => handleChange('date_1st_found', e.target.value)}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted ? (
                <>
                  <TextInput
                    label='Dates Refound (existing)'
                    value={formData.dates_refound || ''}
                    disabled
                    description='Read-only; add new dates below'
                  />
                  <TextInput
                    label='Add dates refound'
                    placeholder='Comma-separated dates to append'
                    value={additionalDatesRefound}
                    onChange={(e) => setAdditionalDatesRefound(e.target.value)}
                    description='New dates will be appended to the list'
                    mt='xs'
                  />
                </>
              ) : (
                <TextInput
                  label='Dates Refound'
                  placeholder='Comma-separated dates'
                  value={formData.dates_refound || ''}
                  onChange={(e) => handleChange('dates_refound', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 5: Location – only form values; community location shown as hint only when provided */}
            {(hintLocationFromCommunity || hintCoordinates) && (
              <Grid.Col span={12}>
                <Alert
                  variant='light'
                  color='blue'
                  icon={<IconInfoCircle size={16} />}
                  title='Community member indicated'
                >
                  <Stack gap='xs'>
                    {hintLocationFromCommunity && (
                      <Text size='sm'>
                        Location: {hintLocationFromCommunity} (for reference only; not
                        pre-filled)
                      </Text>
                    )}
                    {hintCoordinates && (
                      <>
                        <Text size='sm'>
                          Coordinates: {hintCoordinates.latitude.toFixed(5)},{' '}
                          {hintCoordinates.longitude.toFixed(5)}
                          {hintCoordinates.source && ` (${hintCoordinates.source})`}
                        </Text>
                        <MapDisplay
                          latitude={hintCoordinates.latitude}
                          longitude={hintCoordinates.longitude}
                          height={200}
                          zoom={15}
                        />
                        <Anchor
                          size='sm'
                          href={`https://www.openstreetmap.org/?mlat=${hintCoordinates.latitude}&mlon=${hintCoordinates.longitude}&zoom=17`}
                          target='_blank'
                          rel='noopener noreferrer'
                        >
                          <Group gap={4} wrap='nowrap'>
                            <IconMapPin size={14} />
                            <span>Open in OpenStreetMap</span>
                          </Group>
                        </Anchor>
                      </>
                    )}
                  </Stack>
                </Alert>
              </Grid.Col>
            )}
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('general_location') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('general_location')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='General Location'
                    value={formData.general_location ?? ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='General Location'
                  placeholder='General location'
                  value={formData.general_location ?? ''}
                  onChange={(e) => handleChange('general_location', e.target.value)}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('location') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('location')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput label='Location' value={formData.location ?? ''} disabled />
                </>
              ) : (
                <TextInput
                  label='Location'
                  placeholder='Specific location'
                  value={formData.location ?? ''}
                  onChange={(e) => handleChange('location', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 6: Checkboxes as Selects */}
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('pit') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('pit')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput label='Pit?' value={formData.pit || ''} disabled />
                </>
              ) : (
                <Select
                  label='Pit?'
                  placeholder='Yes/No'
                  data={['Yes', 'No']}
                  value={formData.pit || ''}
                  onChange={(value) => handleChange('pit', value || '')}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('pic_in_2024_archive') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('pic_in_2024_archive')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Pic in 2024 Archive?'
                    value={formData.pic_in_2024_archive || ''}
                    disabled
                  />
                </>
              ) : (
                <Select
                  label='Pic in 2024 Archive?'
                  placeholder='Yes/No'
                  data={['Yes', 'No']}
                  value={formData.pic_in_2024_archive || ''}
                  onChange={(value) => handleChange('pic_in_2024_archive', value || '')}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('adopted') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('adopted')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput label='Adopted?' value={formData.adopted || ''} disabled />
                </>
              ) : (
                <Select
                  label='Adopted?'
                  placeholder='Yes/No'
                  data={['Yes', 'No']}
                  value={formData.adopted || ''}
                  onChange={(value) => handleChange('adopted', value || '')}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('ibutton') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('ibutton')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput label='iButton?' value={formData.ibutton || ''} disabled />
                </>
              ) : (
                <Select
                  label='iButton?'
                  placeholder='Yes/No'
                  data={['Yes', 'No']}
                  value={formData.ibutton || ''}
                  onChange={(value) => handleChange('ibutton', value || '')}
                />
              )}
            </Grid.Col>

            {/* Row 7: More Checkboxes + Last Assay Date */}
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('dna_extracted') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('dna_extracted')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='DNA Extracted?'
                    value={formData.dna_extracted || ''}
                    disabled
                  />
                </>
              ) : (
                <Select
                  label='DNA Extracted?'
                  placeholder='Yes/No'
                  data={['Yes', 'No']}
                  value={formData.dna_extracted || ''}
                  onChange={(value) => handleChange('dna_extracted', value || '')}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('ibutton_last_set') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('ibutton_last_set')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='iButton Last Set'
                    value={formData.ibutton_last_set || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='iButton Last Set'
                  placeholder='Date'
                  value={formData.ibutton_last_set || ''}
                  onChange={(e) => handleChange('ibutton_last_set', e.target.value)}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('last_assay_date') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('last_assay_date')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Last Assay Date'
                    value={formData.last_assay_date || ''}
                    disabled
                    description='Date last brought in for assays'
                  />
                </>
              ) : (
                <TextInput
                  label='Last Assay Date'
                  placeholder='YYYY-MM-DD'
                  value={formData.last_assay_date || ''}
                  onChange={(e) => handleChange('last_assay_date', e.target.value)}
                  description='Date last brought in for assays'
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              {isFieldModeRestricted && !isFieldUnlocked('transmitter_lifespan') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('transmitter_lifespan')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Transmitter Lifespan'
                    value={formData.transmitter_lifespan || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='Transmitter Lifespan'
                  placeholder='Lifespan'
                  value={formData.transmitter_lifespan || ''}
                  onChange={(e) => handleChange('transmitter_lifespan', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 8: Transmitter Dates */}
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('transmitter_on_date') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('transmitter_on_date')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Transmitter On Date'
                    value={formData.transmitter_on_date || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='Transmitter On Date'
                  placeholder='Date'
                  value={formData.transmitter_on_date || ''}
                  onChange={(e) => handleChange('transmitter_on_date', e.target.value)}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('radio_replace_date') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('radio_replace_date')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Radio Replace Date'
                    value={formData.radio_replace_date || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='Radio Replace Date'
                  placeholder='Date'
                  value={formData.radio_replace_date || ''}
                  onChange={(e) => handleChange('radio_replace_date', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 9: Additional Fields */}
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('transmitter_put_on_by') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('transmitter_put_on_by')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='Transmitter Put On By'
                    value={formData.transmitter_put_on_by || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='Transmitter Put On By'
                  placeholder='Name'
                  value={formData.transmitter_put_on_by || ''}
                  onChange={(e) => handleChange('transmitter_put_on_by', e.target.value)}
                />
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              {isFieldModeRestricted && !isFieldUnlocked('old_frequencies') ? (
                <>
                  <Group gap='xs' mb={4}>
                    <Button
                      variant='subtle'
                      size='compact-xs'
                      leftSection={<IconLockOpen size={14} />}
                      onClick={() => requestUnlock('old_frequencies')}
                    >
                      Unlock editing
                    </Button>
                  </Group>
                  <TextInput
                    label='OLD Frequencies'
                    value={formData.old_frequencies || ''}
                    disabled
                  />
                </>
              ) : (
                <TextInput
                  label='OLD Frequencies'
                  placeholder='Frequencies'
                  value={formData.old_frequencies || ''}
                  onChange={(e) => handleChange('old_frequencies', e.target.value)}
                />
              )}
            </Grid.Col>

            {/* Row 10: Notes */}
            <Grid.Col span={12}>
              {isFieldModeRestricted ? (
                <>
                  <Textarea
                    label='Notes (existing)'
                    value={formData.notes || ''}
                    disabled
                    minRows={2}
                    description='Read-only; add new notes below'
                  />
                  <Textarea
                    label='Additional notes'
                    placeholder='New notes to append'
                    value={additionalNotes}
                    onChange={(e) => setAdditionalNotes(e.target.value)}
                    minRows={3}
                    description='New notes will be appended to existing notes'
                    mt='xs'
                  />
                </>
              ) : (
                <Textarea
                  label='Notes'
                  placeholder='Additional notes'
                  value={formData.notes || ''}
                  onChange={(e) => handleChange('notes', e.target.value)}
                  minRows={3}
                />
              )}
            </Grid.Col>
          </Grid>

          {!hideSubmitButton && (
            <Group justify='flex-end' gap='md' mt='md'>
              {onCancel && (
                <Button variant='light' onClick={onCancel}>
                  Cancel
                </Button>
              )}
              <Button onClick={handleSubmit} loading={loading}>
                {mode === 'create' ? 'Create' : 'Update'} Turtle Data
              </Button>
            </Group>
          )}
        </Stack>

        {/* Unlock editing confirmation (add-only / field mode) */}
        <Modal
          opened={unlockConfirmField !== null}
          onClose={() => setUnlockConfirmField(null)}
          title='Unlock editing'
        >
          <Stack gap='md'>
            <Text size='sm' c='dimmed'>
              Editing existing data can affect data integrity and may overwrite or remove
              information. Are you sure you want to allow editing this field?
            </Text>
            <Group justify='flex-end' gap='sm'>
              <Button variant='default' onClick={() => setUnlockConfirmField(null)}>
                Cancel
              </Button>
              <Button leftSection={<IconLockOpen size={16} />} onClick={confirmUnlock}>
                I understand, unlock editing
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal for creating new sheet */}
        <Modal
          opened={showCreateSheetModal}
          onClose={() => {
            setShowCreateSheetModal(false);
            setNewSheetName('');
          }}
          title='Create New Sheet'
        >
          <Stack gap='md'>
            <Text size='sm' c='dimmed'>
              Create a new Google Sheets tab with all required headers.
            </Text>
            <TextInput
              label='Sheet Name'
              placeholder='Enter sheet name (e.g., Location A)'
              value={newSheetName}
              onChange={(e) => setNewSheetName(e.target.value)}
              required
            />
            <Group justify='flex-end' gap='md'>
              <Button
                variant='subtle'
                onClick={() => {
                  setShowCreateSheetModal(false);
                  setNewSheetName('');
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => handleCreateNewSheet(newSheetName)}
                loading={creatingSheet}
                disabled={!newSheetName.trim() || creatingSheet}
              >
                Create Sheet
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Paper>
    );
  },
);
