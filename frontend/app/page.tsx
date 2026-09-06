'use client';

import {useEffect, useState} from 'react';
import {VStack, HStack, Layout, LayoutContent} from '@astryxdesign/core/Layout';
import {Text, Heading} from '@astryxdesign/core/Text';
import {Section} from '@astryxdesign/core/Section';
import {Button} from '@astryxdesign/core/Button';
import {Selector} from '@astryxdesign/core/Selector';
import type {
  SelectorOptionData,
  SelectorOptionType,
} from '@astryxdesign/core/Selector';
import {
  SegmentedControl,
  SegmentedControlItem,
} from '@astryxdesign/core/SegmentedControl';
import {Spinner} from '@astryxdesign/core/Spinner';
import {Icon} from '@astryxdesign/core/Icon';
import {PercentStepper} from './components/PercentStepper';
import {ChargeTimeline} from './components/ChargeTimeline';
import type {ChargeSlotDto} from './components/ChargeTimeline';
import {ThemeModeToggle} from './components/ThemeModeToggle';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface Vehicle {
  name: string;
  make: string;
  battery_capacity_kwh: number;
  ac_charge_rate_kw: number;
  dc_charge_rate_kw: number | null;
  range_km: number;
  charge_port: string;
}

type Vehicles = Record<string, Vehicle>;

type OptimizeFor = 'cost' | 'carbon';

interface RecommendationSuccess {
  status: 'recommendation';
  start: string;
  end: string;
  total_cost_gbp: number;
  average_carbon_gco2_per_kwh: number | null;
  kwh_needed: number;
  /** Optional so an older backend without the `slots` key still type-checks. */
  slots?: ChargeSlotDto[];
}

interface NoChargingNeeded {
  status: 'no_charging_needed';
}

interface RecommendationError {
  status: 'error';
  reason: 'insufficient_data' | 'deadline_unreachable' | 'unknown_vehicle';
  detail: string;
}

type RecommendationResponse =
  | RecommendationSuccess
  | NoChargingNeeded
  | RecommendationError;

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString(undefined, {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatCost(gbp: number): string {
  const formatted = Math.abs(gbp).toFixed(2);
  return gbp < 0 ? `-£${formatted}` : `£${formatted}`;
}

function formatDuration(startIso: string, endIso: string): string {
  const ms = Date.parse(endIso) - Date.parse(startIso);
  if (!Number.isFinite(ms) || ms <= 0) {
    return 'Not available';
  }
  const totalMinutes = Math.round(ms / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) {
    return `${minutes}m`;
  }
  return minutes === 0 ? `${hours}h` : `${hours}h ${minutes}m`;
}

const errorReasonTitle: Record<RecommendationError['reason'], string> = {
  insufficient_data: 'Not enough forecast data',
  deadline_unreachable: "This deadline can't be met",
  unknown_vehicle: 'Unknown vehicle',
};

function ErrorMessage({message}: {message: string}) {
  return (
    <HStack
      gap={2}
      vAlign="center"
      padding={3}
      style={{
        backgroundColor: 'var(--color-background-muted)',
        borderRadius: 'var(--radius-container)',
      }}>
      <Icon icon="error" color="error" size="sm" />
      <Text type="body" color="primary" weight="medium" as="p" role="alert">
        {message}
      </Text>
    </HStack>
  );
}

function HeroStat({value, label}: {value: string; label: string}) {
  return (
    <VStack gap={0.5} hAlign="center">
      <Text type="large" weight="semibold" hasTabularNumbers>
        {value}
      </Text>
      <Text type="supporting" color="secondary">
        {label}
      </Text>
    </VStack>
  );
}

function SpecStat({
  value,
  label,
  hasTabularNumbers = false,
}: {
  value: string;
  label: string;
  hasTabularNumbers?: boolean;
}) {
  return (
    <VStack gap={0.5}>
      <Text type="body" weight="semibold" hasTabularNumbers={hasTabularNumbers}>
        {value}
      </Text>
      <Text type="supporting" color="secondary">
        {label}
      </Text>
    </VStack>
  );
}

function VehicleDetails({vehicle}: {vehicle: Vehicle}) {
  return (
    <VStack gap={3}>
      <Text type="label" color="secondary">
        Vehicle details
      </Text>
      <HStack gap={5} wrap="wrap">
        <SpecStat
          hasTabularNumbers
          value={`${vehicle.battery_capacity_kwh.toFixed(1)} kWh`}
          label="Battery"
        />
        <SpecStat
          hasTabularNumbers
          value={`${vehicle.ac_charge_rate_kw.toFixed(1)} kW`}
          label="AC charging"
        />
        <SpecStat
          hasTabularNumbers
          value={
            vehicle.dc_charge_rate_kw !== null
              ? `${vehicle.dc_charge_rate_kw.toFixed(0)} kW`
              : 'AC only'
          }
          label="DC fast charging"
        />
        <SpecStat
          hasTabularNumbers
          value={`${Math.round(vehicle.range_km)} km`}
          label="Range"
        />
        <SpecStat value={vehicle.charge_port} label="Charge port" />
      </HStack>
    </VStack>
  );
}

function RecommendationHero({
  result,
  optimizeFor,
  isSubmitting,
}: {
  result: RecommendationResponse | null;
  optimizeFor: OptimizeFor;
  isSubmitting: boolean;
}) {
  if (isSubmitting) {
    return (
      <VStack gap={4} hAlign="center">
        <Spinner size="xl" aria-label="Finding your window" />
        <Text
          type="display-2"
          weight="bold"
          textWrap="balance"
          justify="center">
          Finding your window…
        </Text>
      </VStack>
    );
  }

  if (result === null) {
    return (
      <VStack gap={4} hAlign="center">
        <Text type="label" color="secondary">
          Ready when you are
        </Text>
        <Text
          type="display-2"
          weight="bold"
          textWrap="balance"
          justify="center">
          Pick a window
        </Text>
        <Text type="supporting" color="secondary" justify="center">
          Set your battery levels below and we&apos;ll find the best time to
          charge.
        </Text>
      </VStack>
    );
  }

  if (result.status === 'no_charging_needed') {
    return (
      <VStack gap={4} hAlign="center">
        <Text type="display-2" weight="bold" justify="center">
          No charging needed
        </Text>
        <Text type="supporting" color="secondary" justify="center">
          The battery is already at or above the target percentage.
        </Text>
      </VStack>
    );
  }

  if (result.status === 'error') {
    return (
      <VStack gap={4} hAlign="center">
        <Text type="display-3" weight="bold" justify="center">
          {errorReasonTitle[result.reason]}
        </Text>
        <ErrorMessage message={result.detail} />
      </VStack>
    );
  }

  return (
    <VStack gap={4} hAlign="center">
      <Text type="label" color="accent">
        {optimizeFor === 'cost' ? 'Cheapest window' : 'Greenest window'}
      </Text>
      <Text
        type="display-1"
        weight="bold"
        hasTabularNumbers
        textWrap="balance"
        justify="center">
        {`${formatDateTime(result.start)} – ${formatDateTime(result.end)}`}
      </Text>
      <HStack gap={6} justify="center" wrap="wrap">
        <HeroStat
          value={formatDuration(result.start, result.end)}
          label="Charging time"
        />
        <HeroStat value={formatCost(result.total_cost_gbp)} label="Cost" />
        <HeroStat
          value={`${result.kwh_needed.toFixed(2)} kWh`}
          label="Energy"
        />
        <HeroStat
          value={
            result.average_carbon_gco2_per_kwh !== null
              ? `${Math.round(result.average_carbon_gco2_per_kwh)} gCO₂/kWh`
              : 'Not available'
          }
          label="Carbon"
        />
      </HStack>
      {result.slots && result.slots.length > 0 ? (
        <ChargeTimeline
          slots={result.slots}
          start={result.start}
          end={result.end}
          optimizeFor={optimizeFor}
        />
      ) : null}
      {result.total_cost_gbp < 0 ? (
        <Text type="supporting" color="secondary" justify="center">
          A negative cost is real Agile Octopus oversupply pricing — you get
          paid to charge during this window, not a bug.
        </Text>
      ) : null}
    </VStack>
  );
}

export default function ChargingOptimiserPage() {
  const [vehicles, setVehicles] = useState<Vehicles | null>(null);
  const [vehiclesError, setVehiclesError] = useState<string | null>(null);

  const [vehicleId, setVehicleId] = useState<string | undefined>(undefined);
  const [currentPct, setCurrentPct] = useState<number | null>(50);
  const [targetPct, setTargetPct] = useState<number | null>(80);
  const [optimizeFor, setOptimizeFor] = useState<OptimizeFor>('cost');

  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCancelled = false;
    async function loadVehicles() {
      try {
        const response = await fetch(`${API_BASE_URL}/vehicles`);
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        const data: Vehicles = await response.json();
        if (!isCancelled) {
          setVehicles(data);
          const firstId = Object.keys(data)[0];
          if (firstId) {
            setVehicleId(firstId);
          }
        }
      } catch {
        if (!isCancelled) {
          setVehiclesError(
            `Could not load vehicles. Is the backend running at ${API_BASE_URL}?`,
          );
        }
      }
    }
    loadVehicles();
    return () => {
      isCancelled = true;
    };
  }, []);

  const vehicleOptions: SelectorOptionType[] = vehicles
    ? Array.from(
        Object.entries(vehicles)
          .reduce<Map<string, SelectorOptionData[]>>(
            (byMake, [id, vehicle]) => {
              const options = byMake.get(vehicle.make) ?? [];
              options.push({value: id, label: vehicle.name});
              byMake.set(vehicle.make, options);
              return byMake;
            },
            new Map(),
          )
          .entries(),
      )
        .sort(([makeA], [makeB]) => makeA.localeCompare(makeB))
        .map(([make, options]) => ({
          type: 'section' as const,
          title: make,
          options: options
            .slice()
            .sort((a, b) => (a.label ?? '').localeCompare(b.label ?? '')),
        }))
    : [];

  const canSubmit =
    Boolean(vehicleId) && currentPct !== null && targetPct !== null;

  async function handleSubmit() {
    if (!vehicleId || currentPct === null || targetPct === null) {
      setIsSubmitting(false);
      return;
    }
    setSubmitError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_BASE_URL}/recommendation`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          vehicle_id: vehicleId,
          current_pct: currentPct,
          target_pct: targetPct,
          optimize_for: optimizeFor,
          charge_by: null,
        }),
      });
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      const data: RecommendationResponse = await response.json();
      setResult(data);
    } catch {
      setSubmitError(
        'Could not reach the recommendation service. Please try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Layout
      contentWidth={520}
      content={
        <LayoutContent padding={6}>
          <VStack gap={8}>
            <VStack gap={1}>
              <Heading level={1}>EV Charging Optimiser</Heading>
              <Text type="supporting" color="secondary">
                The cheapest and greenest time to charge.
              </Text>
            </VStack>

            <Section padding={6}>
              <RecommendationHero
                result={result}
                optimizeFor={optimizeFor}
                isSubmitting={isSubmitting}
              />
            </Section>

            <Section padding={6}>
              <VStack gap={6}>
                <HStack justify="between" vAlign="center" gap={3}>
                  <Text type="label" color="secondary">
                    Appearance
                  </Text>
                  <ThemeModeToggle />
                </HStack>

                {vehiclesError ? (
                  <ErrorMessage message={vehiclesError} />
                ) : vehicles === null ? (
                  <HStack hAlign="center">
                    <Spinner label="Loading vehicles" />
                  </HStack>
                ) : (
                  <Selector
                    label="Vehicle"
                    options={vehicleOptions}
                    value={vehicleId}
                    onChange={setVehicleId}
                    placeholder="Choose a vehicle"
                    hasSearch
                    searchPlaceholder="Search vehicles..."
                    width="100%"
                  />
                )}

                {vehicleId && vehicles?.[vehicleId] ? (
                  <VehicleDetails vehicle={vehicles[vehicleId]} />
                ) : null}

                <SegmentedControl
                  label="Optimise for"
                  layout="fill"
                  size="lg"
                  value={optimizeFor}
                  onChange={value => setOptimizeFor(value as OptimizeFor)}>
                  <SegmentedControlItem value="cost" label="Cheapest" />
                  <SegmentedControlItem value="carbon" label="Greenest" />
                </SegmentedControl>

                <PercentStepper
                  label="Current battery"
                  value={currentPct}
                  onChange={setCurrentPct}
                />
                <PercentStepper
                  label="Target battery"
                  value={targetPct}
                  onChange={setTargetPct}
                />

                {/*
                  Button runs `clickAction` inside a React transition, so state
                  set there does not paint until the action settles. `onClick`
                  runs at normal priority just before it (and is skipped when
                  the button is disabled or an action is already in flight),
                  so the hero's loading branch is flipped on from there.
                */}
                <Button
                  label="Find my window"
                  variant="primary"
                  size="lg"
                  width="100%"
                  isDisabled={!canSubmit}
                  onClick={() => setIsSubmitting(true)}
                  clickAction={handleSubmit}
                />
              </VStack>
            </Section>

            {submitError ? <ErrorMessage message={submitError} /> : null}
          </VStack>
        </LayoutContent>
      }
    />
  );
}
