import {
  Container,
  Paper,
  Title,
  Text,
  Group,
  Stack,
  Center,
  Button,
  Select,
  Loader,
} from '@mantine/core';
import { Dropzone } from '@mantine/dropzone';
import type { FileRejection, FileWithPath } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import { useMediaQuery } from '@mantine/hooks';
import {
  IconUpload,
  IconX,
  IconPhoto,
  IconAlertCircle,
  IconCamera,
  IconInfoCircle,
} from '@tabler/icons-react';
import { useRef, useState, useEffect } from 'react';
import { validateFile } from '../utils/fileValidation';
import { useUser } from '../hooks/useUser';
import { usePhotoUpload } from '../hooks/usePhotoUpload';
import { PreviewCard } from '../components/PreviewCard';
import { InstructionsModal } from '../components/InstructionsModal';
import { getLocations } from '../services/api';

const MATCH_ALL_VALUE = '__all__';
const SYSTEM_FOLDERS = ['Incidental_Finds', 'Community_Uploads', 'Review_Queue'];

export default function HomePage() {
  const { role } = useUser();
  const isMobile = useMediaQuery('(max-width: 768px)');
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [instructionsOpened, setInstructionsOpened] = useState(false);
  // Admin: backend folder locations for match scope (State = first path segment)
  const [availableLocations, setAvailableLocations] = useState<string[]>([]);
  const [locationsLoading, setLocationsLoading] = useState(false);
  const [selectedMatchSheet, setSelectedMatchSheet] = useState<string>(MATCH_ALL_VALUE);

  // Auto-open instructions on first visit
  useEffect(() => {
    const hasSeenInstructions = localStorage.getItem('hasSeenInstructions');
    if (!hasSeenInstructions) {
      setInstructionsOpened(true);
    }
  }, []);

  // Admin: load backend locations (states = first path segment) for match dropdown
  useEffect(() => {
    if (role !== 'admin') return;
    setLocationsLoading(true);
    getLocations()
      .then((res) => {
        if (!res.success || !res.locations?.length) {
          setAvailableLocations([]);
          return;
        }
        const states = new Set<string>();
        for (const path of res.locations as string[]) {
          const first = (path.split('/')[0] ?? '').trim();
          if (first && !SYSTEM_FOLDERS.includes(first)) states.add(first);
        }
        const list = Array.from(states).sort();
        setAvailableLocations(list);
        setSelectedMatchSheet((prev) =>
          prev === MATCH_ALL_VALUE && list.length ? list[0] : prev,
        );
      })
      .catch(() => setAvailableLocations([]))
      .finally(() => setLocationsLoading(false));
  }, [role]);

  const matchSheetForUpload =
    role === 'admin'
      ? selectedMatchSheet === MATCH_ALL_VALUE
        ? ''
        : selectedMatchSheet
      : undefined;

  const {
    files,
    preview,
    uploadState,
    uploadProgress,
    uploadResponse,
    imageId,
    isDuplicate,
    previousUploadDate,
    isGettingLocation,
    locationPermissionDenied,
    locationHint,
    setLocationHint,
    requestLocationHint,
    collectedToLab,
    setCollectedToLab,
    physicalFlag,
    setPhysicalFlag,
    extraFiles,
    setExtraFiles,
    handleDrop,
    handleUpload,
    handleRemove,
  } = usePhotoUpload({ role, matchSheet: matchSheetForUpload });

  const handleDropWithValidation = (acceptedFiles: FileWithPath[]): void => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];

      // Validation
      const validation = validateFile(file);
      if (!validation.isValid) {
        notifications.show({
          title: 'Invalid File',
          message: validation.error || 'File could not be validated',
          color: 'red',
          icon: <IconAlertCircle size={18} />,
        });
        return;
      }

      handleDrop(acceptedFiles);
    }
  };

  const handleReject = (rejectedFiles: FileRejection[]): void => {
    const rejection = rejectedFiles[0];
    let message = 'File could not be accepted';

    if (rejection.errors[0]?.code === 'file-too-large') {
      message = 'File is too large. Maximum: 5MB';
    } else if (rejection.errors[0]?.code === 'file-invalid-type') {
      message = 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP';
    }

    notifications.show({
      title: 'Upload Rejected',
      message,
      color: 'orange',
      icon: <IconAlertCircle size={18} />,
    });
  };

  const handleCameraClick = (): void => {
    cameraInputRef.current?.click();
  };

  const handleFileSelectClick = (): void => {
    fileInputRef.current?.click();
  };

  const handleCameraChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.target.files?.[0];
    if (file) {
      // Convert File to FileWithPath for consistency
      const fileWithPath = Object.assign(file, { path: file.name }) as FileWithPath;
      handleDropWithValidation([fileWithPath]);
    }
    // Reset input so the same file can be selected again
    if (cameraInputRef.current) {
      cameraInputRef.current.value = '';
    }
  };

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.target.files?.[0];
    if (file) {
      // Convert File to FileWithPath for consistency
      const fileWithPath = Object.assign(file, { path: file.name }) as FileWithPath;
      handleDropWithValidation([fileWithPath]);
    }
    // Reset input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Container size='sm' py={{ base: 'md', sm: 'xl' }} px={{ base: 'xs', sm: 'md' }}>
      <Paper shadow='sm' p={{ base: 'md', sm: 'xl' }} radius='md' withBorder>
        <Stack gap='lg'>
          <Center>
            <Stack gap='xs' align='center' style={{ width: '100%' }}>
              {isMobile ? (
                <Stack gap='xs' align='center' style={{ width: '100%' }}>
                  <Title order={1} ta='center'>
                    Photo Upload
                  </Title>
                  <Button
                    variant='light'
                    size='sm'
                    leftSection={<IconInfoCircle size={16} />}
                    onClick={() => setInstructionsOpened(true)}
                    fullWidth
                  >
                    View Instructions
                  </Button>
                </Stack>
              ) : (
                <Group justify='space-between' style={{ width: '100%' }}>
                  <div style={{ flex: 1 }} />
                  <Title order={1}>Photo Upload</Title>
                  <Group style={{ flex: 1 }} justify='flex-end'>
                    <Button
                      variant='light'
                      size='sm'
                      leftSection={<IconInfoCircle size={16} />}
                      onClick={() => setInstructionsOpened(true)}
                    >
                      View Instructions
                    </Button>
                  </Group>
                </Group>
              )}
              <Text size='sm' c='dimmed' ta='center'>
                Upload a photo to save it in the backend
              </Text>
            </Stack>
          </Center>

          {/* Admin: select which location (backend folder / state) to test against */}
          {role === 'admin' && (
            <Stack gap='xs'>
              <Text size='sm' fw={500}>
                Which location to test against?
              </Text>
              {locationsLoading ? (
                <Group gap='xs'>
                  <Loader size='sm' />
                  <Text size='sm' c='dimmed'>
                    Loading locations…
                  </Text>
                </Group>
              ) : (
                <Select
                  data={[
                    ...availableLocations.map((s) => ({ value: s, label: s })),
                    { value: MATCH_ALL_VALUE, label: 'All locations (exception)' },
                  ]}
                  value={selectedMatchSheet}
                  onChange={(v) => v != null && setSelectedMatchSheet(v)}
                  placeholder={availableLocations.length ? 'Select location' : 'No locations yet'}
                  allowDeselect={false}
                  disabled={uploadState === 'uploading'}
                />
              )}
              <Text size='xs' c='dimmed'>
                Default: only turtles from this location. &quot;All locations&quot; only
                in exceptional cases.
              </Text>
            </Stack>
          )}

          {/* Hidden file inputs for mobile */}
          <input
            ref={cameraInputRef}
            type='file'
            accept='image/*'
            capture='environment'
            style={{ display: 'none' }}
            onChange={handleCameraChange}
            disabled={uploadState === 'uploading'}
          />
          <input
            ref={fileInputRef}
            type='file'
            accept='image/*'
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
            disabled={uploadState === 'uploading'}
          />

          {isMobile ? (
            <Stack gap='md'>
              <Button
                size='lg'
                leftSection={<IconCamera size={20} />}
                onClick={handleCameraClick}
                disabled={uploadState === 'uploading'}
                fullWidth
              >
                Take Photo
              </Button>
              <Button
                size='lg'
                variant='light'
                leftSection={<IconPhoto size={20} />}
                onClick={handleFileSelectClick}
                disabled={uploadState === 'uploading'}
                fullWidth
              >
                Upload Photo
              </Button>
              <Text size='sm' c='dimmed' ta='center' mt='xs'>
                Supported formats: PNG, JPG, JPEG, GIF, WEBP (max. 5MB)
              </Text>
            </Stack>
          ) : (
            <Dropzone
              onDrop={handleDropWithValidation}
              onReject={handleReject}
              maxSize={5 * 1024 * 1024} // 5MB
              accept={{
                'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
              }}
              multiple={false}
              disabled={uploadState === 'uploading'}
            >
              <Group
                justify='center'
                gap='xl'
                mih={220}
                style={{ pointerEvents: 'none' }}
              >
                <Dropzone.Accept>
                  <IconUpload size='3.2rem' stroke={1.5} />
                </Dropzone.Accept>
                <Dropzone.Reject>
                  <IconX size='3.2rem' stroke={1.5} />
                </Dropzone.Reject>
                <Dropzone.Idle>
                  <IconPhoto size='3.2rem' stroke={1.5} />
                </Dropzone.Idle>

                <div>
                  <Text size='xl' inline ta='center'>
                    Drop photo here or click to select
                  </Text>
                  <Text
                    size='sm'
                    c='dimmed'
                    inline
                    mt={7}
                    ta='center'
                    style={{ display: 'block' }}
                  >
                    Supported formats: PNG, JPG, JPEG, GIF, WEBP (max. 5MB)
                  </Text>
                </div>
              </Group>
            </Dropzone>
          )}

          <PreviewCard
            preview={preview}
            files={files}
            uploadState={uploadState}
            uploadProgress={uploadProgress}
            uploadResponse={uploadResponse}
            imageId={imageId}
            isDuplicate={isDuplicate}
            previousUploadDate={previousUploadDate}
            isGettingLocation={isGettingLocation}
            locationPermissionDenied={locationPermissionDenied}
            role={role}
            locationHint={locationHint}
            setLocationHint={setLocationHint}
            requestLocationHint={requestLocationHint}
            collectedToLab={collectedToLab}
            setCollectedToLab={setCollectedToLab}
            physicalFlag={physicalFlag}
            setPhysicalFlag={setPhysicalFlag}
            extraFiles={extraFiles}
            setExtraFiles={setExtraFiles}
            onUpload={handleUpload}
            onRemove={handleRemove}
          />
        </Stack>
      </Paper>

      <InstructionsModal
        opened={instructionsOpened}
        onClose={() => setInstructionsOpened(false)}
      />
    </Container>
  );
}
