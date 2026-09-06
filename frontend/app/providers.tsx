'use client';

import {createContext, useContext, useMemo, useState} from 'react';
import type {ReactNode} from 'react';
import {Theme} from '@astryxdesign/core';
import {teslaTheme} from './theme/tesla';

export type ThemeMode = 'light' | 'dark';

interface ThemeModeContextValue {
  mode: ThemeMode;
  setMode: (next: ThemeMode) => void;
}

const ThemeModeContext = createContext<ThemeModeContextValue | null>(null);

export function useThemeMode(): ThemeModeContextValue {
  const value = useContext(ThemeModeContext);
  if (value === null) {
    throw new Error('useThemeMode must be used inside <AppThemeProvider>');
  }
  return value;
}

export function AppThemeProvider({children}: {children: ReactNode}) {
  const [mode, setMode] = useState<ThemeMode>('light');
  const value = useMemo<ThemeModeContextValue>(() => ({mode, setMode}), [mode]);

  return (
    <ThemeModeContext.Provider value={value}>
      <Theme theme={teslaTheme} mode={mode}>
        {children}
      </Theme>
    </ThemeModeContext.Provider>
  );
}
