'use client';

import {useEffect, useState} from 'react';
import {VStack, HStack, Layout, LayoutContent} from '@astryxdesign/core/Layout';
import {Text, Heading} from '@astryxdesign/core/Text';
import {Card} from '@astryxdesign/core/Card';
import {Button} from '@astryxdesign/core/Button';
import {Selector} from '@astryxdesign/core/Selector';
import type {SelectorOptionType} from '@astryxdesign/core/Selector';
import {NumberInput} from '@astryxdesign/core/NumberInput';
import {
  SegmentedControl,
  SegmentedControlItem,
} from '@astryxdesign/core/SegmentedControl';
import {Banner} from '@astryxdesign/core/Banner';
import {MetadataList, MetadataListItem} from '@astryxdesign/core/MetadataList';
import {Spinner} from '@astryxdesign/core/Spinner';
import {Divider} from '@astryxdesign/core/Divider';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface Vehicle {
  name: string;
  battery_capacity_kwh: number;
  ac_charge_rate_kw: number;
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

const errorReasonTitle: Record<RecommendationError['reason'], string> = {
  insufficient_data: 'Not enough forecast data',
  deadline_unreachable: "This deadline can't be met",
  unknown_vehicle: 'Unknown vehicle',
};

function RecommendationResult({result}: {result: RecommendationResponse}) {
  if (result.status === 'no_charging_needed') {
    return (
      <Banner
        status="info"
        title="No charging needed"
        description="The battery is already at or above the target percentage."
      />
    );
  }

  if (result.status === 'error') {
    return (
      <Banner
        status="error"
        title={errorReasonTitle[result.reason]}
        description={result.detail}
      />
    );
  }

  return (
    <VStack gap={4}>
      <Banner
        status="success"
        title="Recommended charging window"
        description={`${formatDateTime(result.start)} – ${formatDateTime(result.end)}`}
      />
      <MetadataList columns="multi">
        <MetadataListItem label="Estimated cost">
          {formatCost(result.total_cost_gbp)}
        </MetadataListItem>
        <MetadataListItem label="Energy needed">
          {result.kwh_needed.toFixed(2)} kWh
        </MetadataListItem>
        <MetadataListItem label="Avg. carbon intensity">
          {result.average_carbon_gco2_per_kwh !== null
            ? `${Math.round(result.average_carbon_gco2_per_kwh)} gCO₂/kWh`
            : 'Not available'}
        </MetadataListItem>
      </MetadataList>
      {result.total_cost_gbp < 0 ? (
        <Text type="supporting" color="secondary">
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
    ? Object.entries(vehicles).map(([id, vehicle]) => ({
        value: id,
        label: vehicle.name,
      }))
    : [];

  const canSubmit =
    Boolean(vehicleId) && currentPct !== null && targetPct !== null;

  async function handleSubmit() {
    if (!vehicleId || currentPct === null || targetPct === null) {
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
    }
  }

  return (
    <Layout
      contentWidth={640}
      content={
        <LayoutContent padding={6}>
          <VStack gap={6}>
            <VStack gap={1}>
              <Heading level={2}>EV Charging Optimiser</Heading>
              <Text type="body" color="secondary">
                Find the cheapest or greenest time to charge your car.
              </Text>
            </VStack>

            <Card>
              <VStack gap={5}>
                {vehiclesError ? (
                  <Banner status="error" title={vehiclesError} />
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
                  />
                )}

                <HStack gap={4} wrap="wrap">
                  <NumberInput
                    label="Current battery"
                    value={currentPct}
                    onChange={setCurrentPct}
                    min={0}
                    max={100}
                    units="%"
                    width={200}
                  />
                  <NumberInput
                    label="Target battery"
                    value={targetPct}
                    onChange={setTargetPct}
                    min={0}
                    max={100}
                    units="%"
                    width={200}
                  />
                </HStack>

                <SegmentedControl
                  label="Optimise for"
                  value={optimizeFor}
                  onChange={value => setOptimizeFor(value as OptimizeFor)}>
                  <SegmentedControlItem value="cost" label="Cheapest" />
                  <SegmentedControlItem value="carbon" label="Greenest" />
                </SegmentedControl>

                <Button
                  label="Get recommendation"
                  variant="primary"
                  isDisabled={!canSubmit}
                  clickAction={handleSubmit}
                />
              </VStack>
            </Card>

            {submitError ? (
              <Banner status="error" title={submitError} />
            ) : null}

            {result ? (
              <>
                <Divider />
                <RecommendationResult result={result} />
              </>
            ) : null}
          </VStack>
        </LayoutContent>
      }
    />
  );
}
