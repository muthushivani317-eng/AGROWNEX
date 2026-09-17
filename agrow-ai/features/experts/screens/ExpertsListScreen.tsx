import { useRouter } from 'expo-router';
import { MessageSquarePlus, UserSearch } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlatList, RefreshControl, ScrollView, View } from 'react-native';

import {
  AgChip,
  AgEmptyState,
  AgErrorState,
  AgOfflineBanner,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { ExpertBackHeader } from '../components/ExpertBackHeader';
import { ExpertCard } from '../components/ExpertCard';
import { CATEGORIES, CATEGORY_LABEL_KEY } from '../constants';
import { useExpertList } from '../hooks/useExperts';
import type { ConsultationCategory, Expert } from '../types';

/** Browse verified agricultural experts, filter by category, open a profile. */
export function ExpertsListScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const [category, setCategory] = useState<ConsultationCategory | null>(null);

  const query = useExpertList({ category, pageSize: 50 });
  const items = query.data?.items ?? [];

  const openExpert = (expert: Expert) =>
    router.push({ pathname: '/experts/[id]', params: { id: expert.id } });

  const header = (
    <View className="gap-3 pb-1">
      <ExpertBackHeader title={t('experts.expertsTitle')} />
      <AgText variant="bodySmall" color="muted">
        {t('experts.expertsSubtitle')}
      </AgText>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerClassName="gap-2 pr-4"
      >
        <AgChip
          label={t('experts.filterAll')}
          selected={category === null}
          onPress={() => setCategory(null)}
        />
        {CATEGORIES.map((c) => (
          <AgChip
            key={c}
            label={t(CATEGORY_LABEL_KEY[c])}
            selected={category === c}
            onPress={() => setCategory(category === c ? null : c)}
          />
        ))}
      </ScrollView>
    </View>
  );

  return (
    <AgScreen padded={false}>
      <AgOfflineBanner />
      <View className="flex-1 px-5">
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={header}
          contentContainerClassName="pb-28 gap-3"
          refreshControl={
            <RefreshControl
              refreshing={query.isRefetching}
              onRefresh={() => void query.refetch()}
              tintColor={colors.primary}
            />
          }
          renderItem={({ item }) => <ExpertCard expert={item} onPress={openExpert} />}
          ListEmptyComponent={
            query.isLoading ? (
              <View className="mt-2 gap-3">
                {[0, 1, 2, 3].map((i) => (
                  <AgSkeleton key={i} className="h-24 w-full rounded-card" />
                ))}
              </View>
            ) : query.isError ? (
              <AgErrorState onRetry={() => void query.refetch()} />
            ) : (
              <AgEmptyState
                icon={UserSearch}
                title={t('experts.expertsEmptyTitle')}
                message={t('experts.expertsEmptyMessage')}
              />
            )
          }
        />
      </View>

      <AgPressable
        onPress={() => router.push('/consultations/new')}
        accessibilityRole="button"
        accessibilityLabel={t('experts.ask')}
        className="absolute bottom-6 right-6 h-16 w-16 items-center justify-center rounded-full bg-primary shadow-lg shadow-black/25"
      >
        <MessageSquarePlus size={28} color={colors.onPrimary} />
      </AgPressable>
    </AgScreen>
  );
}
