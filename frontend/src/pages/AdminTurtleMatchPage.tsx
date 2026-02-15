import { Center, Loader } from '@mantine/core';
import { useParams } from 'react-router-dom';
import { useUser } from '../hooks/useUser';
import { useAdminTurtleMatch } from '../hooks/useAdminTurtleMatch';
import { AdminTurtleMatchProvider } from './AdminTurtleMatch/AdminTurtleMatchContext';
import { AdminTurtleMatchView } from './AdminTurtleMatch/AdminTurtleMatchView';

export default function AdminTurtleMatchPage() {
  const { role, authChecked } = useUser();
  const { imageId } = useParams<{ imageId: string }>();
  const hook = useAdminTurtleMatch(role, authChecked, imageId);

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

  return (
    <AdminTurtleMatchProvider value={hook}>
      <AdminTurtleMatchView />
    </AdminTurtleMatchProvider>
  );
}
