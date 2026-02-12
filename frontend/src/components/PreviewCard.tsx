import {
  Card,
  Stack,
  Group,
  Grid,
  Image,
  Button,
  Text,
  Badge,
  Alert,
  Progress,
  Center,
  Loader,
  TextInput,
  SegmentedControl,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Transition } from '@mantine/core';
import {
  IconCheck,
  IconAlertCircle,
  IconCloudUpload,
  IconTrash,
  IconClock,
  IconSparkles,
  IconCurrentLocation,
} from '@tabler/icons-react';
import { useState, useEffect, useRef } from 'react';
import type { FileWithPath } from '@mantine/dropzone';
import type { LocationHint } from '../services/api';
import { MapPicker } from './MapPicker';

interface PreviewCardProps {
  preview: string | null;
  files: FileWithPath[];
  uploadState: 'idle' | 'uploading' | 'success' | 'error';
  uploadProgress: number;
  uploadResponse: string | null;
  imageId: string | null;
  isDuplicate: boolean;
  previousUploadDate: string | null;
  isGettingLocation: boolean;
  /** True when the user has denied location permission (show allow-in-settings message). */
  locationPermissionDenied?: boolean;
  role?: string;
  /** Optional location hint (coords) – only in queue, never in sheets */
  locationHint?: LocationHint | null;
  setLocationHint?: (hint: LocationHint | null) => void;
  requestLocationHint?: () => Promise<void>;
  onUpload: () => void;
  onRemove: () => void;
}

export function PreviewCard({
  preview,
  files,
  uploadState,
  uploadProgress,
  uploadResponse,
  imageId,
  isDuplicate,
  previousUploadDate,
  isGettingLocation,
  locationPermissionDenied = false,
  role,
  locationHint,
  setLocationHint,
  requestLocationHint,
  onUpload,
  onRemove,
}: PreviewCardProps) {
  const [stillAtLocation, setStillAtLocation] = useState<'yes' | 'no' | null>(null);
  const [manualLat, setManualLat] = useState('');
  const [manualLon, setManualLon] = useState('');
  const isMobile = useMediaQuery('(max-width: 576px)');

  const prevStillAtLocation = useRef<'yes' | 'no' | null>(null);
  // When user selects "I'm still at the turtle's location", request GPS immediately (once per switch to 'yes')
  useEffect(() => {
    if (
      stillAtLocation === 'yes' &&
      prevStillAtLocation.current !== 'yes' &&
      requestLocationHint
    ) {
      requestLocationHint();
    }
    prevStillAtLocation.current = stillAtLocation;
  }, [stillAtLocation, requestLocationHint]);

  // Default to "Skip" location when starting a new upload so multiple turtles don't share the same pin
  const fileKey = files.length ? files[0]?.name ?? '' : '';
  useEffect(() => {
    setStillAtLocation(null);
    setManualLat('');
    setManualLon('');
    if (setLocationHint) setLocationHint(null);
  }, [fileKey, setLocationHint]);

  if (!preview) return null;

  return (
    <Transition mounted={true} transition='fade' duration={300} timingFunction='ease'>
      {(styles) => (
        <Card shadow='xs' padding='md' radius='md' withBorder style={styles}>
          <Stack gap='md'>
            <Group justify='space-between' align='center'>
              <Text size='lg' fw={500}>
                Preview
              </Text>
              {uploadState === 'success' && (
                <Badge color='green' leftSection={<IconCheck size={14} />} size='lg'>
                  Successfully Uploaded
                </Badge>
              )}
              {uploadState === 'error' && (
                <Badge color='red' leftSection={<IconAlertCircle size={14} />} size='lg'>
                  Error
                </Badge>
              )}
            </Group>

            <Image
              src={preview}
              alt='Uploaded photo'
              radius='md'
              style={{ maxWidth: '100%', height: 'auto' }}
            />

            {files.length > 0 && (
              <Text size='sm' c='dimmed'>
                File: {files[0].name} ({(files[0].size / 1024 / 1024).toFixed(2)} MB)
              </Text>
            )}

            {/* Location hint (only for community members) – coords only, never stored in sheets */}
            {role === 'community' && uploadState === 'idle' && (
              <Stack gap='sm'>
                <Alert color='blue' radius='md'>
                  <Text size='xs'>
                    Optionally share where you found this turtle. This is only shown to
                    admins as a hint and is never saved in the database.
                  </Text>
                </Alert>
                <Stack gap='xs'>
                  <Text size='sm' fw={500}>
                    Exact spot (optional)
                  </Text>
                  <SegmentedControl
                    value={stillAtLocation ?? ''}
                    onChange={(v) => {
                      const val = v === 'yes' || v === 'no' ? v : null;
                      setStillAtLocation(val ?? null);
                      if (setLocationHint) setLocationHint(null);
                      if (val === 'no') {
                        setManualLat('');
                        setManualLon('');
                      }
                    }}
                    data={[
                      { label: 'Skip', value: '' },
                      { label: "I'm still at the turtle's location", value: 'yes' },
                      { label: "I'm not there anymore", value: 'no' },
                    ]}
                    fullWidth
                  />
                  {stillAtLocation === 'yes' && setLocationHint && (
                    <Group gap='xs'>
                      {isGettingLocation ? (
                        <Text
                          size='xs'
                          c='dimmed'
                          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                        >
                          <Loader size={14} />
                          Getting your location…
                        </Text>
                      ) : locationHint?.source === 'gps' ? (
                        <>
                          <Text
                            size='xs'
                            c='dimmed'
                            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                          >
                            <IconCurrentLocation size={14} />
                            Location shared: {locationHint.latitude.toFixed(5)},{' '}
                            {locationHint.longitude.toFixed(5)}
                          </Text>
                          <Button
                            size='xs'
                            variant='subtle'
                            color='gray'
                            onClick={() => setLocationHint(null)}
                          >
                            Clear
                          </Button>
                        </>
                      ) : locationPermissionDenied ? (
                        <Text size='xs' c='dimmed'>
                          Please allow location access in your browser settings first, then
                          try again or choose &quot;I&apos;m not there anymore&quot; to pick a
                          spot on the map.
                        </Text>
                      ) : (
                        <Text size='xs' c='dimmed'>
                          Location not available (check browser permission or try again).
                        </Text>
                      )}
                    </Group>
                  )}
                  {stillAtLocation === 'no' && setLocationHint && (
                    <Stack gap='xs'>
                      <Text size='xs' c='dimmed'>
                        Click on the map to set the spot where you saw the turtle. You can
                        also type coordinates below.
                      </Text>
                      <MapPicker
                        height={isMobile ? 220 : 260}
                        value={
                          locationHint?.source === 'manual' ||
                          (locationHint && stillAtLocation === 'no')
                            ? { lat: locationHint.latitude, lon: locationHint.longitude }
                            : null
                        }
                        onChange={(lat, lon) => {
                          setManualLat(String(lat));
                          setManualLon(String(lon));
                          setLocationHint({
                            latitude: lat,
                            longitude: lon,
                            source: 'manual',
                          });
                        }}
                      />
                      <Grid>
                        <Grid.Col span={{ base: 12, sm: 6 }}>
                          <TextInput
                            size='xs'
                            label='Latitude'
                            placeholder='e.g. 52.52'
                            value={manualLat}
                            onChange={(e) => {
                              setManualLat(e.target.value);
                              const lat = parseFloat(e.target.value);
                              const lon = parseFloat(manualLon);
                              if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
                                setLocationHint({
                                  latitude: lat,
                                  longitude: lon,
                                  source: 'manual',
                                });
                              } else {
                                setLocationHint(null);
                              }
                            }}
                          />
                        </Grid.Col>
                        <Grid.Col span={{ base: 12, sm: 6 }}>
                          <TextInput
                            size='xs'
                            label='Longitude'
                            placeholder='e.g. 13.405'
                            value={manualLon}
                            onChange={(e) => {
                              setManualLon(e.target.value);
                              const lat = parseFloat(manualLat);
                              const lon = parseFloat(e.target.value);
                              if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
                                setLocationHint({
                                  latitude: lat,
                                  longitude: lon,
                                  source: 'manual',
                                });
                              } else {
                                setLocationHint(null);
                              }
                            }}
                          />
                        </Grid.Col>
                      </Grid>
                      {locationHint?.source === 'manual' && (
                        <Button
                          size='xs'
                          variant='subtle'
                          color='gray'
                          onClick={() => setLocationHint(null)}
                        >
                          Clear location
                        </Button>
                      )}
                    </Stack>
                  )}
                </Stack>
              </Stack>
            )}

            {uploadState === 'uploading' && (
              <Stack gap='xs' data-testid='upload-progress'>
                <Group justify='space-between'>
                  <Text size='sm' fw={500}>
                    {isGettingLocation ? 'Getting location...' : 'Uploading...'}
                  </Text>
                  <Text size='sm' c='dimmed'>
                    {uploadProgress}%
                  </Text>
                </Group>
                <Progress value={uploadProgress} size='lg' radius='xl' animated />
                <Center>
                  <Loader size='sm' />
                </Center>
                {isGettingLocation && (
                  <Text size='xs' c='dimmed' ta='center'>
                    Please allow location access to track turtle sightings
                  </Text>
                )}
              </Stack>
            )}

            {uploadState === 'success' && uploadResponse && (
              <Alert
                data-testid='upload-success-alert'
                icon={isDuplicate ? <IconClock size={18} /> : <IconCheck size={18} />}
                title={isDuplicate ? 'Duplicate Photo Detected' : 'Upload Successful!'}
                color={isDuplicate ? 'orange' : 'green'}
                radius='md'
              >
                {uploadResponse}
                {imageId && (
                  <Text size='xs' c='dimmed' mt='xs'>
                    Image ID: {imageId}
                  </Text>
                )}
                {isDuplicate && previousUploadDate && (
                  <Group gap='xs' mt='xs' align='flex-start'>
                    <IconClock size={14} style={{ marginTop: 2 }} />
                    <Text size='xs' c='dimmed'>
                      Previously uploaded on: {previousUploadDate}
                    </Text>
                  </Group>
                )}
                {!isDuplicate && role === 'admin' && (
                  <Group gap='xs' mt='xs' align='flex-start'>
                    <IconSparkles size={14} style={{ marginTop: 2 }} />
                    <Text size='xs' c='dimmed'>
                      This is a new photo that has never been uploaded before
                    </Text>
                  </Group>
                )}
              </Alert>
            )}

            {uploadState === 'error' && uploadResponse && (
              <Alert
                icon={<IconAlertCircle size={18} />}
                title='Upload Failed'
                color='red'
                radius='md'
              >
                {uploadResponse}
              </Alert>
            )}

            <Group justify='flex-end' gap='sm'>
              {uploadState !== 'uploading' && (
                <>
                  {uploadState === 'idle' && (
                    <Button
                      onClick={onUpload}
                      leftSection={<IconCloudUpload size={18} />}
                      size='md'
                      fullWidth
                    >
                      Upload Photo
                    </Button>
                  )}
                  <Button
                    variant='light'
                    color='red'
                    onClick={onRemove}
                    leftSection={<IconTrash size={18} />}
                    size='md'
                    fullWidth={uploadState === 'idle'}
                  >
                    {uploadState === 'idle' ? 'Remove' : 'New Photo'}
                  </Button>
                </>
              )}
            </Group>
          </Stack>
        </Card>
      )}
    </Transition>
  );
}
