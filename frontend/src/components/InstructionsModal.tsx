import {
  Modal,
  Stack,
  Text,
  Button,
  Group,
  Divider,
  Paper,
  ThemeIcon,
  Image,
  Checkbox,
  ScrollArea,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { IconCamera, IconCheck } from '@tabler/icons-react';
import { useState, useRef } from 'react';
import step1Image from '../assets/step1.jpg';
import step2Image from '../assets/step2.jpg';
import finalResultImage from '../assets/finalresult.jpg';

interface InstructionsModalProps {
  opened: boolean;
  onClose: () => void;
}

export function InstructionsModal({ opened, onClose }: InstructionsModalProps) {
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const viewportRef = useRef<HTMLDivElement>(null);
  const isMobile = useMediaQuery('(max-width: 576px)');

  const handleScroll = () => {
    if (viewportRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = viewportRef.current;
      // Check if scrolled to bottom (with small threshold)
      if (scrollHeight - scrollTop - clientHeight < 10) {
        setHasScrolledToBottom(true);
      }
    }
  };

  const handleClose = () => {
    if (acknowledged && hasScrolledToBottom) {
      localStorage.setItem('hasSeenInstructions', 'true');
      onClose();
    }
  };

  const handleModalClose = () => {
    // Allow closing if acknowledged and scrolled, otherwise prevent
    if (acknowledged && hasScrolledToBottom) {
      handleClose();
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={handleModalClose}
      title='Photo Submission Instructions'
      size={isMobile ? '100%' : '1200px'}
      fullScreen={isMobile}
      centered={!isMobile}
      closeOnClickOutside={acknowledged && hasScrolledToBottom}
      closeOnEscape={acknowledged && hasScrolledToBottom}
      withCloseButton={acknowledged && hasScrolledToBottom}
      styles={{
        title: { fontSize: isMobile ? '1.25rem' : '1.75rem', fontWeight: 700 },
        body: { fontSize: '1rem', padding: 0 },
      }}
    >
      <ScrollArea
        h={isMobile ? '70vh' : 600}
        onScrollPositionChange={handleScroll}
        viewportRef={viewportRef}
        styles={{ viewport: { padding: '0 var(--mantine-spacing-md)' } }}
      >
        <Stack gap='lg' pb='md'>
          {/* Instructions Section */}
          <Stack gap='md'>
            <Group gap='sm'>
              <IconCamera size={28} />
              <Text size='1.5rem' fw={700}>
                How to Photograph a Turtle's Plastron
              </Text>
            </Group>

            <Text size='lg' style={{ lineHeight: 1.6 }}>
              The plastron is the bottom shell of a turtle. Follow these guidelines to
              capture clear, identifiable photos:
            </Text>
          </Stack>

          <Divider />

          {/* Step 1 with Photo */}
          <Paper
            withBorder
            p='xl'
            style={{ borderLeftWidth: 4, borderLeftColor: 'var(--mantine-color-teal-6)' }}
          >
            <Group align='flex-start' gap='xl'>
              <ThemeIcon size={60} radius='xl' variant='filled' color='teal'>
                <Text size='xl' fw={700}>
                  1
                </Text>
              </ThemeIcon>
              <Stack gap='md' style={{ flex: 1 }}>
                <Stack gap='sm'>
                  <Text size='lg' fw={700}>
                    Positioning
                  </Text>
                  <Text size='lg' style={{ lineHeight: 1.6 }}>
                    Gently turn the turtle over or hold it carefully to expose the
                    plastron. Ensure the turtle is safe and comfortable during the
                    process.
                  </Text>
                </Stack>
                <Image
                  src={step1Image}
                  alt='Step 1: Position the turtle'
                  radius='md'
                  maw={300}
                  fit='contain'
                />
              </Stack>
            </Group>
          </Paper>

          {/* Step 2 with Photo */}
          <Paper
            withBorder
            p='xl'
            style={{ borderLeftWidth: 4, borderLeftColor: 'var(--mantine-color-cyan-6)' }}
          >
            <Group align='flex-start' gap='xl'>
              <ThemeIcon size={60} radius='xl' variant='filled' color='cyan'>
                <Text size='xl' fw={700}>
                  2
                </Text>
              </ThemeIcon>
              <Stack gap='md' style={{ flex: 1 }}>
                <Stack gap='sm'>
                  <Text size='lg' fw={700}>
                    Lighting
                  </Text>
                  <Text size='lg' style={{ lineHeight: 1.6 }}>
                    Use natural lighting when possible. Avoid harsh shadows or
                    reflections. The pattern should be clearly visible.
                  </Text>
                </Stack>
                <Image
                  src={step2Image}
                  alt='Step 2: Proper lighting'
                  radius='md'
                  maw={300}
                  fit='contain'
                />
              </Stack>
            </Group>
          </Paper>

          {/* Step 3 */}
          <Paper
            withBorder
            p='xl'
            style={{ borderLeftWidth: 4, borderLeftColor: 'var(--mantine-color-teal-6)' }}
          >
            <Group align='flex-start' gap='xl'>
              <ThemeIcon size={60} radius='xl' variant='filled' color='teal'>
                <Text size='xl' fw={700}>
                  3
                </Text>
              </ThemeIcon>
              <Stack gap='sm' style={{ flex: 1 }}>
                <Text size='lg' fw={700}>
                  Camera Angle
                </Text>
                <Text size='lg' style={{ lineHeight: 1.6 }}>
                  Position your camera directly above and parallel to the plastron. Keep
                  the entire shell in frame with minimal distortion.
                </Text>
              </Stack>
            </Group>
          </Paper>

          {/* Step 4 */}
          <Paper
            withBorder
            p='xl'
            style={{ borderLeftWidth: 4, borderLeftColor: 'var(--mantine-color-cyan-6)' }}
          >
            <Group align='flex-start' gap='xl'>
              <ThemeIcon size={60} radius='xl' variant='filled' color='cyan'>
                <Text size='xl' fw={700}>
                  4
                </Text>
              </ThemeIcon>
              <Stack gap='sm' style={{ flex: 1 }}>
                <Text size='lg' fw={700}>
                  Focus & Clarity
                </Text>
                <Text size='lg' style={{ lineHeight: 1.6 }}>
                  Ensure the photo is sharp and in focus. The scutes (shell plates) and
                  any unique markings should be clearly visible for identification.
                </Text>
              </Stack>
            </Group>
          </Paper>

          {/* Step 5 with Final Result Photo */}
          <Paper
            withBorder
            p='xl'
            style={{ borderLeftWidth: 4, borderLeftColor: 'var(--mantine-color-teal-6)' }}
          >
            <Group align='flex-start' gap='xl'>
              <ThemeIcon size={60} radius='xl' variant='filled' color='teal'>
                <Text size='xl' fw={700}>
                  5
                </Text>
              </ThemeIcon>
              <Stack gap='md' style={{ flex: 1 }}>
                <Stack gap='sm'>
                  <Text size='lg' fw={700}>
                    Background & Final Result
                  </Text>
                  <Text size='lg' style={{ lineHeight: 1.6 }}>
                    Use a plain, contrasting background to make the turtle stand out.
                    Avoid busy patterns or similar colors to the shell. Here's what a good
                    final photo looks like:
                  </Text>
                </Stack>
                <Image
                  src={finalResultImage}
                  alt='Final result: Clear plastron photo'
                  radius='md'
                  maw={300}
                  fit='contain'
                />
              </Stack>
            </Group>
          </Paper>

          {/* Best Practices */}
          <Stack gap='md' mt='md'>
            <Group gap='sm'>
              <IconCheck size={28} color='var(--mantine-color-teal-6)' />
              <Text size='1.5rem' fw={700}>
                Best Practices
              </Text>
            </Group>

            <Paper
              withBorder
              p='lg'
              style={{
                borderLeftWidth: 4,
                borderLeftColor: 'var(--mantine-color-teal-6)',
              }}
            >
              <Text size='lg' style={{ lineHeight: 1.8 }}>
                • Clean the plastron gently if it's dirty to reveal pattern details
              </Text>
            </Paper>

            <Paper
              withBorder
              p='lg'
              style={{
                borderLeftWidth: 4,
                borderLeftColor: 'var(--mantine-color-cyan-6)',
              }}
            >
              <Text size='lg' style={{ lineHeight: 1.8 }}>
                • Take multiple photos from slightly different angles
              </Text>
            </Paper>

            <Paper
              withBorder
              p='lg'
              style={{
                borderLeftWidth: 4,
                borderLeftColor: 'var(--mantine-color-teal-6)',
              }}
            >
              <Text size='lg' style={{ lineHeight: 1.8 }}>
                • Include a scale reference (like a ruler) if possible
              </Text>
            </Paper>

            <Paper
              withBorder
              p='lg'
              style={{
                borderLeftWidth: 4,
                borderLeftColor: 'var(--mantine-color-cyan-6)',
              }}
            >
              <Text size='lg' style={{ lineHeight: 1.8 }}>
                • Handle turtles with care and return them safely to their habitat
              </Text>
            </Paper>
          </Stack>

          {/* Acknowledgment Checkbox */}
          <Paper
            withBorder
            p='xl'
            style={{
              borderLeftWidth: 4,
              borderLeftColor: hasScrolledToBottom
                ? 'var(--mantine-color-teal-6)'
                : 'var(--mantine-color-gray-5)',
            }}
          >
            <Stack gap='md'>
              <Checkbox
                size='lg'
                label={
                  <Text size='lg' fw={600} style={{ lineHeight: 1.6 }}>
                    I have read and understand the photo submission guidelines
                  </Text>
                }
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.currentTarget.checked)}
                disabled={!hasScrolledToBottom}
              />
              {!hasScrolledToBottom && (
                <Text size='md' c='dimmed'>
                  ⬇️ Please scroll to the bottom to continue
                </Text>
              )}
            </Stack>
          </Paper>
        </Stack>
      </ScrollArea>

      {/* Footer Button */}
      <Group
        justify='flex-end'
        p='md'
        style={{ borderTop: '1px solid var(--mantine-color-gray-3)' }}
      >
        <Button
          size='lg'
          onClick={handleClose}
          disabled={!acknowledged || !hasScrolledToBottom}
          leftSection={<IconCheck size={20} />}
        >
          Got it! Let's upload
        </Button>
      </Group>
    </Modal>
  );
}
