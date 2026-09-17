import { useRouter } from 'expo-router';
import { ChevronRight, Eye, Link2, MapPin, Sparkles, Tag } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { RefreshControl, ScrollView, View } from 'react-native';

import {
  AgCard,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { relativeTimeKey } from '@/features/home/utils/time';
import { useAppTheme } from '@/hooks/useAppTheme';

import { ImportanceBadge } from '../components/ImportanceBadge';
import { MemoryBackHeader } from '../components/MemoryBackHeader';
import { sourceIcon } from '../components/sourceMeta';
import {
  LINK_LABEL_KEY,
  OBSERVATION_LABEL_KEY,
  SEASON_LABEL_KEY,
  SOURCE_LABEL_KEY,
} from '../constants';
import { useMemoryDetail } from '../hooks/useMemory';
import type { FarmMemory } from '../types';

/** A single memory in full: what happened, how it was known, and its related memories. */
export function MemoryDetailScreen({ id }: { id: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const query = useMemoryDetail(id);
  const memory = query.data;

  return (
    <AgScreen padded={false}>
      <ScrollView
        className="flex-1 px-5"
        contentContainerClassName="pb-24 gap-3"
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={colors.primary}
          />
        }
      >
        <MemoryBackHeader title={t('memory.detailTitle')} />

        {query.isLoading ? (
          <View className="gap-3">
            {[0, 1].map((i) => (
              <AgSkeleton key={i} className="h-28 w-full rounded-card" />
            ))}
          </View>
        ) : query.isError || !memory ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : (
          <MemoryDetail memory={memory} />
        )}
      </ScrollView>
    </AgScreen>
  );
}

function MemoryDetail({ memory }: { memory: FarmMemory }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const Icon = sourceIcon(memory.sourceModule);
  const rt = relativeTimeKey(memory.occurredAt);
  const ObservationIcon = memory.observation === 'observed' ? Eye : Sparkles;

  const rows: { label: string; value: string }[] = [
    { label: t('memory.source'), value: t(SOURCE_LABEL_KEY[memory.sourceModule] ?? memory.sourceModule) },
    ...(memory.crop ? [{ label: t('memory.crop'), value: memory.crop }] : []),
    ...(memory.season
      ? [{ label: t('memory.season'), value: t(SEASON_LABEL_KEY[memory.season] ?? memory.season) }]
      : []),
    ...(memory.confidence != null
      ? [{ label: t('memory.confidence'), value: `${memory.confidence}%` }]
      : []),
    { label: t('memory.when'), value: t(rt.key, rt.params) },
  ];

  return (
    <>
      <AgCard className="gap-3">
        <View className="flex-row items-start gap-3">
          <View className="h-11 w-11 items-center justify-center rounded-md bg-primary/10">
            <Icon size={22} color={colors.primary} />
          </View>
          <View className="flex-1">
            <AgText variant="body" weight="bold">
              {t(`${memory.summary}.title`, { defaultValue: t('memory.eventFallback') })}
            </AgText>
            <AgText variant="bodySmall" color="muted" className="mt-0.5">
              {t(`${memory.summary}.message`, { defaultValue: '', ...(memory.params ?? {}) })}
            </AgText>
          </View>
        </View>

        <View className="flex-row items-center gap-2">
          <ImportanceBadge importance={memory.importance} />
          <View className="flex-row items-center gap-1">
            <ObservationIcon size={13} color={colors.textMuted} />
            <AgText variant="caption" color="muted">
              {t(OBSERVATION_LABEL_KEY[memory.observation])}
            </AgText>
          </View>
          {memory.location ? (
            <View className="flex-row items-center gap-1">
              <MapPin size={13} color={colors.textMuted} />
              <AgText variant="caption" color="muted">
                {memory.location}
              </AgText>
            </View>
          ) : null}
        </View>
      </AgCard>

      <AgCard className="gap-2">
        {rows.map((row) => (
          <View key={row.label} className="flex-row justify-between">
            <AgText variant="bodySmall" color="muted">
              {row.label}
            </AgText>
            <AgText variant="bodySmall" weight="semibold">
              {row.value}
            </AgText>
          </View>
        ))}
      </AgCard>

      {memory.tags.length > 0 ? (
        <AgCard className="gap-2">
          <View className="flex-row items-center gap-1">
            <Tag size={14} color={colors.textMuted} />
            <AgText variant="label" weight="semibold" color="muted">
              {t('memory.tags')}
            </AgText>
          </View>
          <View className="flex-row flex-wrap gap-1.5">
            {memory.tags.map((tag) => (
              <View key={tag} className="rounded-full bg-border/50 px-2.5 py-1">
                <AgText variant="caption" color="muted">
                  #{tag}
                </AgText>
              </View>
            ))}
          </View>
        </AgCard>
      ) : null}

      {memory.links.length > 0 ? (
        <View className="gap-2">
          <View className="flex-row items-center gap-1">
            <Link2 size={14} color={colors.textMuted} />
            <AgText variant="label" weight="semibold" color="muted">
              {t('memory.related')}
            </AgText>
          </View>
          {memory.links.map((link) => {
            const otherId = link.fromMemoryId === memory.id ? link.toMemoryId : link.fromMemoryId;
            return (
              <AgPressable
                key={link.id}
                onPress={() => router.push({ pathname: '/memory/[id]', params: { id: otherId } })}
                accessibilityRole="button"
                accessibilityLabel={t(LINK_LABEL_KEY[link.linkType])}
              >
                <AgCard className="flex-row items-center justify-between">
                  <AgText variant="bodySmall">{t(LINK_LABEL_KEY[link.linkType])}</AgText>
                  <ChevronRight size={18} color={colors.textMuted} />
                </AgCard>
              </AgPressable>
            );
          })}
        </View>
      ) : null}

      <AgText variant="caption" color="muted" className="mt-1 px-1">
        {t('memory.disclaimer')}
      </AgText>
    </>
  );
}
