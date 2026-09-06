'use client';

import {MoonIcon, SunIcon} from '@heroicons/react/24/outline';
import {ToggleButton} from '@astryxdesign/core/ToggleButton';
import {useThemeMode} from '../providers';

export function ThemeModeToggle() {
  const {mode, setMode} = useThemeMode();

  return (
    <ToggleButton
      label="Dark mode"
      isIconOnly
      size="md"
      icon={<SunIcon />}
      pressedIcon={<MoonIcon />}
      isPressed={mode === 'dark'}
      onPressedChange={next => setMode(next ? 'dark' : 'light')}
    />
  );
}
