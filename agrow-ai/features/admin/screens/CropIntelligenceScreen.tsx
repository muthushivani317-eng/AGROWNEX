import { Sprout } from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';

import { AgButton, AgCard, AgErrorState, AgInput, AgScreen, AgSkeleton, AgText } from '@/components/ui';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { DistributionBars } from '../components/DistributionBars';
import { SampleNotice } from '../components/SampleNotice';
import { useCropIntelligence } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';
import type { CropIntelligenceFilter, CropIntelligenceGroup } from '../types';

function Fact({ value, label }: { value: string | number; label: string }) {
  return (
    <AgCard variant="compact" className="min-w-[46%] flex-1 gap-1">
      <AgText variant="headingS" weight="bold">{value}</AgText>
      <AgText variant="caption" color="muted">{label}</AgText>
    </AgCard>
  );
}

function GroupDetails({ title, items }: { title: string; items: CropIntelligenceGroup[] }) {
  return (
    <AgCard className="gap-3">
      <AgText variant="label" weight="semibold">{title}</AgText>
      {items.map((item) => (
        <View key={item.label} className="gap-1 border-b border-border pb-2">
          <AgText variant="bodySmall" weight="semibold">{item.label}</AgText>
          <AgText variant="caption" color="muted">
            {item.farmerCount} farmers · {item.farmCount} farms · {item.knownAreaHectares.toLocaleString()} known ha
          </AgText>
          <AgText variant="caption" color="muted">
            Area reported for {item.farmsWithArea} of {item.farmCount} farms
          </AgText>
        </View>
      ))}
      {!items.length ? <AgText variant="caption" color="muted">No registered farms match.</AgText> : null}
    </AgCard>
  );
}

export function CropIntelligenceScreen() {
  const [draft, setDraft] = useState({ crop: '', district: '', village: '', days: '30' });
  const [filter, setFilter] = useState<CropIntelligenceFilter>({ harvestDays: 30 });
  const query = useCropIntelligence(filter);

  if (isAccessError(query.error)) return <AccessDenied message={query.error.message} />;
  const data = query.data;

  return (
    <AgScreen scroll>
      <AdminHeader
        icon={Sprout}
        title="Crop intelligence"
        subtitle="Registered farms, recorded stages, upcoming harvests and produce offered for sale."
        back
      />

      <AgCard className="mt-4 gap-3">
        <AgText variant="label" weight="semibold">Supply question</AgText>
        <AgInput label="Crop" placeholder="e.g. Banana" value={draft.crop}
          onChangeText={(crop) => setDraft((value) => ({ ...value, crop }))} />
        <AgInput label="District" placeholder="e.g. Tirunelveli" value={draft.district}
          onChangeText={(district) => setDraft((value) => ({ ...value, district }))} />
        <AgInput label="Village (optional)" value={draft.village}
          onChangeText={(village) => setDraft((value) => ({ ...value, village }))} />
        <AgInput label="Harvest within days" keyboardType="number-pad" value={draft.days}
          onChangeText={(days) => setDraft((value) => ({ ...value, days }))} />
        <AgButton title="Run crop overview" onPress={() => setFilter({
          crop: draft.crop.trim() || undefined,
          district: draft.district.trim() || undefined,
          village: draft.village.trim() || undefined,
          harvestDays: Math.min(365, Math.max(1, Number(draft.days) || 30)),
        })} />
      </AgCard>

      {query.isLoading ? (
        <View className="mt-4 gap-3"><AgSkeleton className="h-40 w-full rounded-card" /></View>
      ) : query.isError || !data ? (
        <View className="mt-4"><AgErrorState onRetry={() => void query.refetch()} /></View>
      ) : (
        <View className="mt-4 gap-3">
          <SampleNotice visible={Boolean(data.isSample)} />
          <AgCard className="gap-2">
            <AgText variant="label" weight="semibold">Direct answer</AgText>
            <AgText variant="headingS" weight="bold">
              {data.summary.harvestWindowFarmerCount} farmers match the harvest window
            </AgText>
            <AgText variant="caption" color="muted">
              Based only on submitted or planned produce listings dated {data.harvestWindow.fromDate} to {data.harvestWindow.toDate}.
            </AgText>
          </AgCard>

          <View className="flex-row flex-wrap gap-3">
            <Fact value={data.summary.farmerCount} label="Registered farmers" />
            <Fact value={data.summary.farmCount} label="Registered farms" />
            <Fact value={`${data.summary.knownAreaHectares.toLocaleString()} ha`} label="Known cultivated area" />
            <Fact value={data.summary.saleListingCount} label="Active sale listings" />
          </View>

          <AgCard className="gap-1">
            <AgText variant="label" weight="semibold">Coverage and confidence</AgText>
            <AgText variant="bodySmall">
              Area supplied for {data.summary.farmsWithArea} of {data.summary.farmCount} farms.
            </AgText>
            <AgText variant="bodySmall">
              Crop stage recorded for {data.summary.recordedStageFarms} farms.
            </AgText>
            <AgText variant="caption" color="muted">
              Missing acreage and stages are not estimated. Harvest counts require a dated sale listing.
            </AgText>
          </AgCard>

          <DistributionBars title="Registered farms by crop"
            items={data.byCrop.map((item) => ({ label: item.label, count: item.farmCount }))} />
          <GroupDetails title="Crop acreage coverage" items={data.byCrop} />
          <DistributionBars title="Registered farms by district / village"
            items={data.byLocation.map((item) => ({ label: item.label, count: item.farmCount }))} />
          <GroupDetails title="District and village acreage coverage" items={data.byLocation} />
          <DistributionBars title="Available crop-stage evidence"
            items={data.cropStages.map((item) => ({ label: item.label, count: item.farmCount }))} />

          <AgCard className="gap-2">
            <AgText variant="label" weight="semibold">Produce currently offered</AgText>
            {data.offeredQuantities.length ? data.offeredQuantities.map((item) => (
              <View key={item.unit} className="flex-row justify-between">
                <AgText variant="bodySmall">{item.unit}</AgText>
                <AgText variant="bodySmall" weight="semibold">{item.quantity.toLocaleString()}</AgText>
              </View>
            )) : <AgText variant="caption" color="muted">No active offers match these filters.</AgText>}
            <AgText variant="caption" color="muted">Units remain separate; unlike units are never added together.</AgText>
          </AgCard>
        </View>
      )}
    </AgScreen>
  );
}
