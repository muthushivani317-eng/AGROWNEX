import { MapPin, Sprout, User } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgBadge, AgCard, AgErrorState, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { formatIndianPhone } from '@/utils/format';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { formatShortDate } from '../components/adminMeta';
import { useAdminFarmerDetail } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';

const ACTIVITY_KEYS: { key: string; labelKey: string }[] = [
  { key: 'disease', labelKey: 'admin.activity.disease' },
  { key: 'soil', labelKey: 'admin.activity.soil' },
  { key: 'ai_chats', labelKey: 'admin.activity.aiChats' },
  { key: 'memory', labelKey: 'admin.activity.memory' },
  { key: 'notifications', labelKey: 'admin.activity.notifications' },
];

/** Read-only detail for one farmer — profile, farms and cross-module activity counts. */
export function FarmerDetailScreen({ userId }: { userId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const query = useAdminFarmerDetail(userId);

  if (isAccessError(query.error)) return <AccessDenied message={query.error.message} />;

  const data = query.data;
  const location = data
    ? [data.village, data.block, data.district].filter(Boolean).join(', ')
    : '';

  return (
    <AgScreen scroll>
      <AdminHeader icon={User} title={t('admin.farmerDetail')} back />

      {query.isLoading ? (
        <View className="mt-4 gap-3">
          <AgSkeleton className="h-28 w-full rounded-card" />
          <AgSkeleton className="h-24 w-full rounded-card" />
        </View>
      ) : query.isError || !data ? (
        <AgErrorState onRetry={() => void query.refetch()} />
      ) : (
        <View className="mt-4 gap-3">
          <AgCard variant="elevated" className="gap-1">
            <AgBadge label={data.farmerRef ?? data.userId} tone="info" />
            <AgText variant="headingS" weight="bold">
              {data.fullName ?? '—'}
            </AgText>
            {data.phoneNumber ? (
              <AgText variant="body" color="muted">
                {formatIndianPhone(data.phoneNumber)}
              </AgText>
            ) : null}
            {location ? (
              <View className="mt-1 flex-row items-center gap-1">
                <MapPin size={14} color={colors.textMuted} />
                <AgText variant="caption" color="muted">
                  {location}
                </AgText>
              </View>
            ) : null}
            {data.primaryCrop ? (
              <View className="mt-1 flex-row items-center gap-1">
                <Sprout size={14} color={colors.textMuted} />
                <AgText variant="caption" color="muted">
                  {data.primaryCrop}
                </AgText>
              </View>
            ) : null}
          </AgCard>

          <AgText variant="label" weight="semibold" color="muted" className="mt-1">
            {t('admin.farms')} · {data.farms.length}
          </AgText>
          {data.farms.length === 0 ? (
            <AgText variant="caption" color="muted">
              {t('admin.noFarms')}
            </AgText>
          ) : (
            data.farms.map((farm) => (
              <AgCard key={farm.id} className="flex-row items-center justify-between gap-2">
                <View className="flex-1">
                  <AgText variant="body" weight="semibold">
                    {farm.name}
                  </AgText>
                  <AgText variant="caption" color="muted">
                    {[farm.crop, farm.areaHectares ? `${farm.areaHectares} ha` : null]
                      .filter(Boolean)
                      .join(' · ')}
                    {` · ${formatShortDate(farm.createdAt)}`}
                  </AgText>
                </View>
                <AgBadge label={farm.status} tone="neutral" />
              </AgCard>
            ))
          )}

          <AgText variant="label" weight="semibold" color="muted" className="mt-1">
            {t('admin.activityTitle')}
          </AgText>
          <AgCard className="flex-row flex-wrap gap-x-6 gap-y-3">
            {ACTIVITY_KEYS.map(({ key, labelKey }) => (
              <View key={key} className="gap-0.5">
                <AgText variant="headingS" weight="bold">
                  {data.counts[key] ?? 0}
                </AgText>
                <AgText variant="caption" color="muted">
                  {t(labelKey)}
                </AgText>
              </View>
            ))}
          </AgCard>
        </View>
      )}
    </AgScreen>
  );
}
