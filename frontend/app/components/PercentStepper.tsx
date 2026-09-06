'use client';

import {useId} from 'react';
import {MinusIcon, PlusIcon} from '@heroicons/react/24/outline';
import {VStack, HStack} from '@astryxdesign/core/Layout';
import {Text} from '@astryxdesign/core/Text';
import {IconButton} from '@astryxdesign/core/IconButton';

interface PercentStepperProps {
  label: string;
  /** `null` is treated as "not yet set" and resolves to `min`. */
  value: number | null;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  step?: number;
}

export function PercentStepper({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 5,
}: PercentStepperProps) {
  const labelId = useId();
  const current = value ?? min;
  const clamp = (next: number): number => Math.min(max, Math.max(min, next));

  return (
    <VStack gap={2}>
      <Text id={labelId} type="label" color="secondary">
        {label}
      </Text>
      <HStack
        role="group"
        aria-labelledby={labelId}
        gap={3}
        vAlign="center"
        justify="between"
        padding={2}
        style={{
          backgroundColor: 'var(--color-background-muted)',
          borderRadius: 'var(--radius-full)',
        }}>
        <IconButton
          label={`Decrease ${label}`}
          icon={<MinusIcon />}
          variant="ghost"
          size="lg"
          isDisabled={current <= min}
          onClick={() => onChange(clamp(current - step))}
        />
        <Text
          role="status"
          aria-live="polite"
          type="display-3"
          weight="bold"
          hasTabularNumbers
          justify="center">{`${current}%`}</Text>
        <IconButton
          label={`Increase ${label}`}
          icon={<PlusIcon />}
          variant="ghost"
          size="lg"
          isDisabled={current >= max}
          onClick={() => onChange(clamp(current + step))}
        />
      </HStack>
    </VStack>
  );
}
