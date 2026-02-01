import {
  Container,
  Title,
  Text,
  Stack,
  Paper,
  TextInput,
  Button,
  Alert,
  Loader,
  Center,
} from '@mantine/core';
import { useState, useEffect } from 'react';
import { IconMail, IconShield, IconAlertCircle, IconCheck } from '@tabler/icons-react';
import { useUser } from '../hooks/useUser';
import { useNavigate } from 'react-router-dom';
import { promoteToAdmin } from '../services/api';
import { notifications } from '@mantine/notifications';

export default function AdminUserManagementPage() {
  const { role, authChecked } = useUser();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authChecked) return;
    if (role !== 'admin') {
      navigate('/');
    }
  }, [authChecked, role, navigate]);

  if (!authChecked) {
    return (
      <Center py='xl'>
        <Loader size='lg' />
      </Center>
    );
  }
  if (role !== 'admin') {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await promoteToAdmin(email);
      notifications.show({
        title: 'Success!',
        message: result.message,
        color: 'green',
        icon: <IconCheck size={18} />,
      });
      setEmail(''); // Clear form
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to promote user to admin';
      setError(errorMessage);
      notifications.show({
        title: 'Error',
        message: errorMessage,
        color: 'red',
        icon: <IconAlertCircle size={18} />,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size='sm' py={{ base: 'md', sm: 'xl' }} px={{ base: 'xs', sm: 'md' }}>
      <Paper shadow='sm' p={{ base: 'md', sm: 'xl' }} radius='md' withBorder>
        <Stack gap='lg'>
          <div>
            <Title order={1}>User Management</Title>
            <Text size='sm' c='dimmed' mt='xs'>
              Promote a user to admin by entering their email address. If the user doesn't
              have an account yet, they will receive an invitation email with a
              registration link.
            </Text>
          </div>

          {error && (
            <Alert icon={<IconAlertCircle size={16} />} title='Error' color='red'>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <Stack gap='md'>
              <TextInput
                label='Email Address'
                placeholder='user@example.com'
                leftSection={<IconMail size={16} />}
                value={email}
                onChange={(event) => setEmail(event.currentTarget.value)}
                required
                type='email'
                disabled={loading}
                description='Enter the email address of the user you want to promote to admin'
              />

              <Button
                type='submit'
                leftSection={<IconShield size={16} />}
                disabled={!email || loading}
                loading={loading}
                color='red'
                fullWidth
                size='md'
              >
                {loading ? 'Promoting...' : 'Promote to Admin'}
              </Button>
            </Stack>
          </form>

          <Alert icon={<IconAlertCircle size={16} />} title='How it works' color='blue'>
            <Text size='sm'>
              <strong>Existing users:</strong> If the user already has an account, they
              will be promoted immediately and receive a notification email.
              <br />
              <br />
              <strong>New users:</strong> If the user doesn't have an account yet, they
              will receive an invitation email with a registration link. When they
              register using that link, their account will be created with admin
              privileges.
            </Text>
          </Alert>
        </Stack>
      </Paper>
    </Container>
  );
}
