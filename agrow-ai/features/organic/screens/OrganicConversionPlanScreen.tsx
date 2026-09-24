import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, ChevronDown, ChevronUp, Plus } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import {
  AgBadge,
  AgButton,
  AgCard,
  AgDatePicker,
  AgEmptyState,
  AgErrorState,
  AgInput,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
  CropSelector,
} from '@/components/ui';
import { COMMON_CROPS } from '@/constants/crops';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';

import {
  useCreateOrganicCropCycle,
  useCreateOrganicPlot,
  useOrganicCropCyclePlan,
  useOrganicCropCycles,
  useOrganicPlots,
} from '../hooks/useOrganicConversion';
import type { OrganicCropCycle, OrganicPlot } from '../services/organicConversionApi';

function cropLabel(cropId: string, language: string): string {
  const crop = COMMON_CROPS.find((c) => c.id === cropId);
  if (!crop) return cropId;
  return language === 'ta' ? crop.ta : crop.en;
}

/**
 * Blueprint's "Conversion Plan" (Phase 2): plot + crop-cycle capture and the
 * resulting week-by-week schedule, on organic_mvp's existing plot/crop-cycle/
 * task-template backend (none of it wired to mobile before this).
 *
 * Deliberately does NOT capture baseline soil values or a target buyer
 * category yet -- the blueprint asks for both, but OrganicPlot/
 * OrganicCropCycle don't have those columns. Adding them is a schema
 * migration, a separate decision, not done silently here.
 *
 * The schedule itself only appears once an agronomist has reviewed a task
 * template for this crop+district and activated it for the cycle -- there
 * is no fallback/invented schedule when that hasn't happened yet.
 */
export function OrganicConversionPlanScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const plotsQuery = useOrganicPlots(farmId);
  const createPlot = useCreateOrganicPlot(farmId);

  const [addingPlot, setAddingPlot] = useState(false);
  const [plotName, setPlotName] = useState('');
  const [plotArea, setPlotArea] = useState('');

  const submitPlot = () => {
    if (!plotName.trim()) return;
    createPlot.mutate(
      {
        name: plotName.trim(),
        area_hectares: plotArea.trim() ? Number(plotArea.trim()) : null,
      },
      {
        onSuccess: () => {
          setAddingPlot(false);
          setPlotName('');
          setPlotArea('');
        },
      },
    );
  };

  return (
    <AgScreen scroll>
      <View className="flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold" className="flex-1">
          {t('organic.conversionPlanTitle')}
        </AgText>
        <AgPressable
          onPress={() => setAddingPlot(!addingPlot)}
          accessibilityRole="button"
          accessibilityLabel={t('organic.addPlot')}
        >
          <Plus size={24} color={colors.primary} />
        </AgPressable>
      </View>
      <AgText color="muted" className="mt-2">
        {t('organic.conversionPlanIntro')}
      </AgText>

      {addingPlot ? (
        <AgCard className="mt-4">
          <AgText weight="bold">{t('organic.addPlot')}</AgText>
          <AgInput
            className="mt-3"
            label={t('organic.plotName')}
            value={plotName}
            onChangeText={setPlotName}
          />
          <AgInput
            className="mt-3"
            label={t('organic.plotAreaHectares')}
            value={plotArea}
            onChangeText={setPlotArea}
            keyboardType="numeric"
          />
          <AgButton
            className="mt-4"
            title={t('common.save')}
            loading={createPlot.isPending}
            onPress={submitPlot}
          />
        </AgCard>
      ) : null}

      {plotsQuery.isLoading ? (
        <AgSkeleton className="mt-4 h-32 w-full" />
      ) : plotsQuery.isError ? (
        <AgErrorState
          message={t('organic.plotsLoadError')}
          onRetry={() => void plotsQuery.refetch()}
        />
      ) : !plotsQuery.data?.length ? (
        <AgEmptyState
          title={t('organic.noPlots')}
          message={t('organic.noPlotsMessage')}
          actionLabel={t('organic.addPlot')}
          onAction={() => setAddingPlot(true)}
        />
      ) : (
        plotsQuery.data.map((plot) => <PlotCard key={plot.id} plot={plot} />)
      )}
    </AgScreen>
  );
}

function PlotCard({ plot }: { plot: OrganicPlot }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const cyclesQuery = useOrganicCropCycles(plot.id);
  const createCycle = useCreateOrganicCropCycle(plot.id);

  const [addingCycle, setAddingCycle] = useState(false);
  const [cropPickerOpen, setCropPickerOpen] = useState(false);
  const [cropId, setCropId] = useState<string | null>(null);
  const [sowingDate, setSowingDate] = useState('');
  const [harvestStart, setHarvestStart] = useState('');
  const [harvestEnd, setHarvestEnd] = useState('');
  const { language } = useLanguage();

  const submitCycle = () => {
    if (!cropId) return;
    createCycle.mutate(
      {
        crop_id: cropId,
        sowing_date: sowingDate || null,
        expected_harvest_start: harvestStart || null,
        expected_harvest_end: harvestEnd || null,
      },
      {
        onSuccess: () => {
          setAddingCycle(false);
          setCropId(null);
          setSowingDate('');
          setHarvestStart('');
          setHarvestEnd('');
        },
      },
    );
  };

  return (
    <AgCard className="mt-3">
      <View className="flex-row items-center justify-between gap-2">
        <AgText weight="bold" className="flex-1">
          {plot.name}
        </AgText>
        {plot.area_hectares ? (
          <AgText variant="caption" color="muted">
            {t('organic.plotAreaValue', { value: plot.area_hectares })}
          </AgText>
        ) : null}
      </View>
      {plot.notice ? (
        <AgText variant="bodySmall" color="muted" className="mt-1">
          {plot.notice}
        </AgText>
      ) : null}

      {cyclesQuery.isLoading ? (
        <AgSkeleton className="mt-3 h-16 w-full" />
      ) : cyclesQuery.isError ? (
        <AgErrorState
          message={t('organic.cropCyclesLoadError')}
          onRetry={() => void cyclesQuery.refetch()}
        />
      ) : (
        (cyclesQuery.data ?? []).map((cycle) => (
          <CropCycleRow key={cycle.id} cycle={cycle} />
        ))
      )}

      {addingCycle ? (
        <View className="mt-3">
          <Pressable
            onPress={() => setCropPickerOpen(true)}
            style={[styles.cropPickerButton, { borderColor: colors.border }]}
          >
            <AgText style={{ color: cropId ? colors.text : colors.textMuted }}>
              {cropId
                ? cropLabel(cropId, language)
                : t('organic.chooseCrop')}
            </AgText>
          </Pressable>
          <CropSelector
            visible={cropPickerOpen}
            selectedCrop={cropId}
            onSelect={(id) => {
              setCropId(id);
              setCropPickerOpen(false);
            }}
            onClose={() => setCropPickerOpen(false)}
          />
          <AgDatePicker
            label={t('organic.sowingDate')}
            placeholder="YYYY-MM-DD"
            value={sowingDate}
            onChange={setSowingDate}
          />
          <View className="mt-3 flex-row gap-3">
            <View className="flex-1">
              <AgDatePicker
                label={t('organic.harvestStart')}
                placeholder="YYYY-MM-DD"
                value={harvestStart}
                onChange={setHarvestStart}
              />
            </View>
            <View className="flex-1">
              <AgDatePicker
                label={t('organic.harvestEnd')}
                placeholder="YYYY-MM-DD"
                value={harvestEnd}
                onChange={setHarvestEnd}
              />
            </View>
          </View>
          <AgButton
            className="mt-4"
            title={t('common.save')}
            disabled={!cropId}
            loading={createCycle.isPending}
            onPress={submitCycle}
          />
        </View>
      ) : (
        <AgButton
          className="mt-3"
          size="sm"
          variant="secondary"
          title={t('organic.addCropCycle')}
          onPress={() => setAddingCycle(true)}
        />
      )}
    </AgCard>
  );
}

function CropCycleRow({ cycle }: { cycle: OrganicCropCycle }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const planQuery = useOrganicCropCyclePlan(expanded ? cycle.id : null);

  return (
    <View style={styles.cycleRow}>
      <Pressable
        onPress={() => setExpanded(!expanded)}
        accessibilityRole="button"
        style={styles.cycleHeader}
      >
        <AgText weight="semibold" className="flex-1">
          {cropLabel(cycle.crop_id, language)}
        </AgText>
        {cycle.sowing_date ? (
          <AgText variant="caption" color="muted">
            {t('organic.sownOn', { date: cycle.sowing_date })}
          </AgText>
        ) : null}
        {expanded ? (
          <ChevronUp size={18} color={colors.textMuted} />
        ) : (
          <ChevronDown size={18} color={colors.textMuted} />
        )}
      </Pressable>
      {expanded ? (
        <View className="mt-2">
          {planQuery.isLoading ? (
            <AgSkeleton className="h-12 w-full" />
          ) : planQuery.isError ? (
            <AgErrorState
              message={t('organic.planLoadError')}
              onRetry={() => void planQuery.refetch()}
            />
          ) : planQuery.data?.status !== 'ready' ||
            !planQuery.data.tasks.length ? (
            <AgText variant="bodySmall" color="muted">
              {planQuery.data?.status ?? t('organic.planAwaitingApproval')}
            </AgText>
          ) : (
            planQuery.data.tasks.map((task) => (
              <View key={task.id} style={styles.taskRow}>
                <View className="flex-row items-center justify-between gap-2">
                  <AgText weight="semibold" variant="bodySmall" className="flex-1">
                    {language === 'ta' ? task.title_ta : (task.title_en ?? task.title_ta)}
                  </AgText>
                  <AgBadge label={task.due_on} tone="neutral" />
                </View>
                <AgText variant="caption" color="muted" className="mt-1">
                  {language === 'ta' ? task.body_ta : (task.body_en ?? task.body_ta)}
                </AgText>
              </View>
            ))
          )}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  cropPickerButton: {
    marginTop: 12,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  cycleRow: {
    marginTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#E4E7E1',
    paddingTop: 10,
  },
  cycleHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  taskRow: {
    marginTop: 8,
    borderRadius: 10,
    backgroundColor: '#F4FAF1',
    padding: 10,
  },
});
