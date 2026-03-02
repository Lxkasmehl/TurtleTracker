import { createContext, useContext, type ReactNode } from 'react';
import type { useAdminTurtleMatch } from '../../hooks/useAdminTurtleMatch';

export type AdminTurtleMatchContextValue = ReturnType<typeof useAdminTurtleMatch>;

const AdminTurtleMatchContext = createContext<AdminTurtleMatchContextValue | null>(
  null,
);

export function AdminTurtleMatchProvider({
  value,
  children,
}: {
  value: AdminTurtleMatchContextValue;
  children: ReactNode;
}) {
  return (
    <AdminTurtleMatchContext.Provider value={value}>
      {children}
    </AdminTurtleMatchContext.Provider>
  );
}

export function useAdminTurtleMatchContext(): AdminTurtleMatchContextValue {
  const ctx = useContext(AdminTurtleMatchContext);
  if (!ctx) {
    throw new Error(
      'useAdminTurtleMatchContext must be used within AdminTurtleMatchProvider',
    );
  }
  return ctx;
}
