import { useEffect } from 'react';
import { useAppDispatch } from '../store/hooks';
import { setUser, setAuthChecked } from '../store/slices/userSlice';
import { getToken, getCurrentUser, removeToken } from '../services/api';

interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * Component that checks for existing authentication token on app startup
 * and restores user session if valid
 */
export default function AuthProvider({ children }: AuthProviderProps) {
  const dispatch = useAppDispatch();

  useEffect(() => {
    let cancelled = false;

    const markAuthChecked = () => {
      if (!cancelled) {
        dispatch(setAuthChecked(true));
      }
    };

    // Fallback: if auth backend is slow/unreachable, still allow UI to proceed after a short delay
    const fallbackId = setTimeout(markAuthChecked, 4000);

    const checkAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const user = await getCurrentUser();
          if (!cancelled) {
            if (user) {
              dispatch(setUser(user));
            } else {
              removeToken();
            }
          }
        } catch (error) {
          if (!cancelled) {
            console.error('Unexpected error during auth check:', error);
            removeToken();
          }
        }
      }
      clearTimeout(fallbackId);
      markAuthChecked();
    };

    checkAuth();
    return () => {
      cancelled = true;
      clearTimeout(fallbackId);
    };
  }, [dispatch]);

  return <>{children}</>;
}

