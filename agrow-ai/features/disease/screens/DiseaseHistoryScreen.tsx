import dayjs from 'dayjs';
import { useRouter } from 'expo-router';
import { ArrowLeft, ScanLine } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { FlatList, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useState } from 'react';

import {
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useSelectedFarm } from '@/features/weather';

import { SeverityBadge } from '../components/SeverityBadge';
import { DiseaseReportImage } from '../components/DiseaseReportImage';
import { useDiseaseHistory } from '../hooks/useDisease';
import { formatDiagnosisName } from '../utils/diagnosisName';

export function DiseaseHistoryScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { farms, selected: farm, isLoading: farmsLoading, isError: farmsError, refetch: refetchFarms } = useSelectedFarm();
  const [scope, setScope] = useState<string | 'unassigned' | null>(null);

  const activeScope = scope ?? farm?.id ?? 'unassigned';
  const unassignedOnly = activeScope === 'unassigned';
  const farmId = unassignedOnly ? null : activeScope;
  const { data, isLoading, isError, refetch, isRefetching } = useDiseaseHistory(
    farmId,
    unassignedOnly,
  );

  const header = (
    <View style={{ marginVertical: 8 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
      <Pressable
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel={t('common.back')}
        style={{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }}
      >
        <ArrowLeft size={24} color={colors.text} />
      </Pressable>
      <AgText variant="headingM" weight="bold">
        {t('disease.historyTitle')}
      </AgText>
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scopes}
      >
        {farms.map((item) => {
          const active = activeScope === item.id;
          return (
            <Pressable
              key={item.id}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              onPress={() => setScope(item.id)}
              style={[
                styles.scope,
                {
                  borderColor: active ? colors.primary : colors.border,
                  backgroundColor: active ? `${colors.primary}20` : colors.surface,
                },
              ]}
            >
              <AgText variant="bodySmall" color={active ? 'primary' : 'default'}>
                {item.name}
              </AgText>
            </Pressable>
          );
        })}
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ selected: unassignedOnly }}
          onPress={() => setScope('unassigned')}
          style={[
            styles.scope,
            {
              borderColor: unassignedOnly ? colors.primary : colors.border,
              backgroundColor: unassignedOnly ? `${colors.primary}20` : colors.surface,
            },
          ]}
        >
          <AgText variant="bodySmall" color={unassignedOnly ? 'primary' : 'default'}>
            {t('disease.unassignedFarm')}
          </AgText>
        </Pressable>
      </ScrollView>
    </View>
  );

  if (farmsError) {
    return <AgScreen>{header}<AgErrorState onRetry={() => void refetchFarms()} /></AgScreen>;
  }

  if (farmsLoading || isLoading) {
    return (
      <AgScreen>
        {header}
        <View className="gap-3">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} style={{ height: 80, width: '100%', borderRadius: 16 }} />
          ))}
        </View>
      </AgScreen>
    );
  }

  if (isError) {
    return (
      <AgScreen>
        {header}
        <AgErrorState onRetry={() => void refetch()} />
      </AgScreen>
    );
  }

  const reports = data ?? [];

  return (
    <AgScreen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20 }}>
        <FlatList
          data={reports}
          refreshing={isRefetching}
          onRefresh={() => { void refetchFarms(); void refetch(); }}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={header}
          contentContainerStyle={{ paddingBottom: 32, gap: 8, flexGrow: 1 }}
          renderItem={({ item }) => (
            <AgPressable
              onPress={() => router.push(`/disease/${item.id}`)}
              accessibilityRole="button"
              accessibilityLabel={item.disease ?? t('disease.resultTitle')}
            >
              <AgCard style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                {item.privateImageAvailable || item.imageUrl ? (
                  <DiseaseReportImage
                    reportId={item.id}
                    privateImageAvailable={item.privateImageAvailable}
                    legacyUrl={item.imageUrl}
                    style={{ width: 52, height: 52, borderRadius: 10 }}
                  />
                ) : null}
                <View style={{ flex: 1 }}>
                  <AgText variant="body" weight="semibold" numberOfLines={1}>
                    {item.disease ? formatDiagnosisName(item.disease) : t('disease.cropUnknown')}
                  </AgText>
                  {item.testMode?.display_required ? (
                    <AgText variant="caption" color="danger" className="mt-1" numberOfLines={3}>
                      {item.testMode.banner_text}
                    </AgText>
                  ) : null}
                  <View className="mt-1 flex-row flex-wrap items-center gap-2">
                    <SeverityBadge severity={item.severity} />
                    <AgText variant="caption" color="muted" style={{ flexShrink: 1 }}>
                      {Number.isFinite(item.confidence)
                        ? `${item.confidence}%`
                        : t('disease.confidenceUnavailable')}{' '}
                      ·{' '}
                      {dayjs(item.createdAt).format('YYYY-MM-DD')}
                    </AgText>
                  </View>
                </View>
              </AgCard>
            </AgPressable>
          )}
          ListEmptyComponent={
            <AgEmptyState
              icon={ScanLine}
              title={t('disease.noReportsTitle')}
              message={t('disease.noReportsMessage')}
            />
          }
        />
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  scopes: { gap: 8, paddingTop: 12, paddingBottom: 4 },
  scope: {
    minHeight: 40,
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: 18,
    paddingHorizontal: 14,
  },
});
