'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type {TooltipContentProps} from 'recharts';
import {Section} from '@astryxdesign/core/Section';
import {Text} from '@astryxdesign/core/Text';
import {VStack} from '@astryxdesign/core/Layout';

export interface ChargeSlotDto {
  start: string;
  end: string;
  price_gbp_per_kwh: number;
  carbon_gco2_per_kwh: number | null;
}

interface ChargeTimelineProps {
  slots: ChargeSlotDto[];
  /** Recommended window start (ISO). */
  start: string;
  /** Recommended window end (ISO). */
  end: string;
  optimizeFor: 'cost' | 'carbon';
}

/** 24 hours of half-hour slots. Slides to cover the recommended window. */
const MAX_CELLS = 48;
const MS_PER_HOUR = 3_600_000;
const TICK_COUNT = 6;
const CHART_HEIGHT = 220;

function metricOf(slot: ChargeSlotDto, optimizeFor: 'cost' | 'carbon'): number | null {
  return optimizeFor === 'cost' ? slot.price_gbp_per_kwh : slot.carbon_gco2_per_kwh;
}

function formatValue(value: number, optimizeFor: 'cost' | 'carbon'): string {
  return optimizeFor === 'cost'
    ? `£${value.toFixed(2)}/kWh`
    : `${Math.round(value)} gCO₂/kWh`;
}

function formatTime(iso: string | number, withWeekday = false): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return String(iso);
  }
  return date.toLocaleString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    ...(withWeekday ? {weekday: 'short'} : {}),
  });
}

function isSameDay(a: string | number, b: string | number): boolean {
  const dateA = new Date(a);
  const dateB = new Date(b);
  if (Number.isNaN(dateA.getTime()) || Number.isNaN(dateB.getTime())) {
    return true;
  }
  return dateA.toDateString() === dateB.toDateString();
}

function ChartTooltip({
  active,
  payload,
  optimizeFor,
  firstTimestamp,
}: TooltipContentProps & {
  optimizeFor: 'cost' | 'carbon';
  firstTimestamp: number;
}) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const point = payload[0];
  const timestamp = typeof point.payload?.timestamp === 'number' ? point.payload.timestamp : null;
  const value = typeof point.value === 'number' ? point.value : null;
  if (timestamp === null || value === null) {
    return null;
  }

  return (
    <Section padding={2}>
      <VStack gap={0.5}>
        <Text type="supporting" color="secondary" hasTabularNumbers>
          {formatTime(timestamp, !isSameDay(timestamp, firstTimestamp))}
        </Text>
        <Text type="body" weight="semibold" hasTabularNumbers>
          {formatValue(value, optimizeFor)}
        </Text>
      </VStack>
    </Section>
  );
}

export function ChargeTimeline({slots, start, end, optimizeFor}: ChargeTimelineProps) {
  const windowStart = Date.parse(start);
  const windowEnd = Date.parse(end);

  const isInWindow = (slot: ChargeSlotDto): boolean => {
    const slotStart = Date.parse(slot.start);
    const slotEnd = Date.parse(slot.end);
    return (
      Number.isFinite(slotStart) &&
      Number.isFinite(slotEnd) &&
      slotStart >= windowStart &&
      slotEnd <= windowEnd
    );
  };

  // The recommendation is picked from every slot the backend returns (~100),
  // so a blind head-slice can cut the winning window off the chart. Slide the
  // MAX_CELLS viewport instead so it always contains the whole window.
  let firstWindowIdx = -1;
  let lastWindowIdx = -1;
  slots.forEach((slot, index) => {
    if (!isInWindow(slot)) {
      return;
    }
    if (firstWindowIdx === -1) {
      firstWindowIdx = index;
    }
    lastWindowIdx = index;
  });

  const sliceEnd =
    lastWindowIdx === -1 ? MAX_CELLS : Math.max(MAX_CELLS, lastWindowIdx + 1);
  const sliceStart = Math.max(
    0,
    Math.min(firstWindowIdx === -1 ? 0 : firstWindowIdx, sliceEnd - MAX_CELLS),
  );
  const visible = slots.slice(sliceStart, sliceEnd);
  if (visible.length === 0) {
    return null;
  }
  const windowIsVisible = lastWindowIdx !== -1;

  const points = visible.map(slot => ({
    timestamp: Date.parse(slot.start),
    value: metricOf(slot, optimizeFor),
  }));

  const firstTimestamp = points[0].timestamp;
  const lastTimestamp = Date.parse(visible[visible.length - 1].end);

  const ticks = Array.from({length: TICK_COUNT}, (_, i) =>
    Math.round(firstTimestamp + ((lastTimestamp - firstTimestamp) * i) / (TICK_COUNT - 1)),
  );

  const hasNoData = points.some(point => point.value === null);
  const missingCount = points.filter(point => point.value === null).length;

  const spanHours = Number.isFinite(lastTimestamp - firstTimestamp)
    ? Math.round((lastTimestamp - firstTimestamp) / MS_PER_HOUR)
    : Math.round(visible.length / 2);
  const spanLabel =
    sliceStart === 0
      ? `Next ${spanHours} hours`
      : `${spanHours} hours from ${formatTime(firstTimestamp)}`;

  const yAxisLabel = optimizeFor === 'cost' ? '£/kWh' : 'gCO₂/kWh';

  const windowSentence = windowIsVisible
    ? `Your recommended window is ${formatTime(start)} to ${formatTime(end)}, ` +
      'highlighted on the chart.'
    : 'Your recommended window is not covered by the slots shown.';
  const ariaLabel =
    `${visible.length} half-hour slots from ${formatTime(firstTimestamp)} to ` +
    `${formatTime(lastTimestamp, !isSameDay(firstTimestamp, lastTimestamp))}, ` +
    `charted by ${optimizeFor === 'cost' ? 'price' : 'carbon intensity'}. ` +
    (hasNoData ? `${missingCount} slots have no data and appear as a gap. ` : '') +
    windowSentence;

  return (
    <VStack gap={2} width="100%">
      <Text type="supporting" color="secondary">
        {spanLabel}
      </Text>

      <VStack width="100%" aria-label={ariaLabel} role="img">
        <VStack width="100%" aria-hidden>
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <AreaChart data={points} margin={{top: 8, right: 8, left: 0, bottom: 0}}>
              <CartesianGrid
                stroke="var(--color-border-emphasized)"
                horizontal
                vertical={false}
              />
              <XAxis
                dataKey="timestamp"
                type="number"
                domain={[firstTimestamp, lastTimestamp]}
                ticks={ticks}
                tickFormatter={value =>
                  formatTime(value, !isSameDay(value, firstTimestamp))
                }
                stroke="var(--color-text-secondary)"
                tick={{fill: 'var(--color-text-secondary)', fontSize: 12}}
              />
              <YAxis
                width={48}
                label={{
                  value: yAxisLabel,
                  angle: -90,
                  position: 'insideLeft',
                  fill: 'var(--color-text-secondary)',
                  fontSize: 12,
                }}
                stroke="var(--color-text-secondary)"
                tick={{fill: 'var(--color-text-secondary)', fontSize: 12}}
              />
              <ReferenceArea
                x1={windowStart}
                x2={windowEnd}
                fill="var(--color-accent)"
                fillOpacity={0.16}
                stroke="none"
              />
              <RechartsTooltip
                content={props => (
                  <ChartTooltip
                    {...props}
                    optimizeFor={optimizeFor}
                    firstTimestamp={firstTimestamp}
                  />
                )}
              />
              <Area
                type="monotone"
                dataKey="value"
                connectNulls={false}
                stroke="var(--color-data-blue-4)"
                fill="var(--color-data-blue-4)"
                fillOpacity={0.15}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </VStack>
      </VStack>
    </VStack>
  );
}
