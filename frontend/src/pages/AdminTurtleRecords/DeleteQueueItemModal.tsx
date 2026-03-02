import { Button, Group, Modal, Stack, Text } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
interface DeleteQueueItemModalProps {
  opened: boolean;
  onClose: () => void;
  deleting: boolean;
  onConfirm: () => void;
}

export function DeleteQueueItemModal({
  opened,
  onClose,
  deleting,
  onConfirm,
}: DeleteQueueItemModalProps) {
  return (
    <Modal opened={opened} onClose={onClose} title='Remove upload from queue' centered>
      <Stack gap='md'>
        <Text size='sm' c='dimmed'>
          This will permanently delete this upload from the review queue. It will not be
          processed or added to any turtle. Use this for junk or spam only.
        </Text>
        <Text size='sm' fw={500}>
          This cannot be undone.
        </Text>
        <Group justify='flex-end' gap='sm'>
          <Button variant='default' onClick={onClose} disabled={deleting}>
            Cancel
          </Button>
          <Button
            color='red'
            leftSection={<IconTrash size={16} />}
            loading={deleting}
            onClick={onConfirm}
          >
            Delete from queue
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
