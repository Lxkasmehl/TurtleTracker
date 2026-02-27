/**
 * Single form field with optional lock/unlock (add-only mode) and text or select input
 */

import { TextInput, Select, Group, Button } from '@mantine/core';
import { IconLockOpen } from '@tabler/icons-react';
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

export function TurtleFormField({
  field,
  label,
  placeholder,
  value,
  onChange,
  description,
  type = 'text',
  selectData = [],
  isFieldModeRestricted,
  isFieldUnlocked,
  requestUnlock,
  disabled,
  error,
}: TurtleFormFieldProps) {
  const locked = isFieldModeRestricted && !isFieldUnlocked(field);

  if (locked) {
    return (
      <>
        <Group gap='xs' mb={4}>
          <Button
            variant='subtle'
            size='compact-xs'
            leftSection={<IconLockOpen size={14} />}
            onClick={() => requestUnlock(field)}
          >
            Unlock editing
          </Button>
        </Group>
        <TextInput
          label={label}
          value={value}
          disabled
          description={description}
          error={error}
        />
      </>
    );
  }

  if (type === 'select') {
    const data = Array.isArray(selectData) && typeof selectData[0] === 'string'
      ? (selectData as string[]).map((v) => ({ value: v, label: v }))
      : (selectData as { value: string; label: string }[]);
    return (
      <Select
        label={label}
        placeholder={placeholder}
        data={data}
        value={value}
        onChange={(v) => onChange(v || '')}
        description={description}
        disabled={disabled}
        error={error}
      />
    );
  }

  return (
    <TextInput
      label={label}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      description={description}
      disabled={disabled}
      error={error}
    />
  );
}
