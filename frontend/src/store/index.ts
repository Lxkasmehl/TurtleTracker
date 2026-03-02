import { configureStore } from '@reduxjs/toolkit';
import userReducer from './slices/userSlice.js';
import themeReducer from './slices/themeSlice.js';
import availableSheetsReducer from './slices/availableSheetsSlice.js';

export const store = configureStore({
  reducer: {
    user: userReducer,
    theme: themeReducer,
    availableSheets: availableSheetsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
