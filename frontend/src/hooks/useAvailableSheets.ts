import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { fetchAvailableSheets } from '../store/slices/availableSheetsSlice';

/**
 * Ensures available sheets (locations/datasheets) are loaded when user is admin.
 * Use in admin pages or components that need the sheets list.
 * Returns sheets from Redux; triggers fetch once when role is admin.
 */
export function useAvailableSheets(role: string | undefined) {
  const dispatch = useAppDispatch();
  const { sheets, loading } = useAppSelector((state) => state.availableSheets);

  useEffect(() => {
    if (role === 'admin') {
      dispatch(fetchAvailableSheets());
    }
  }, [role, dispatch]);

  return { sheets, loading };
}
