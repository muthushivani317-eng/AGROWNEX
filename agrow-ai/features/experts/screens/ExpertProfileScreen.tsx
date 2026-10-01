import { useRouter } from 'expo-router';
import { BadgeCheck, ExternalLink, Phone } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Linking, View } from 'react-native';

import { AgBadge, AgButton, AgCard, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { ExpertBackHeader } from '../components/ExpertBackHeader';
import { expertTypeIcon } from '../components/expertIcon';
import {
  CATEGORY_LABEL_KEY,
  EXPERT_TYPE_LABEL_KEY,
} from '../constants';
import { useExpertDetail } from '../hooks/useExperts';
import type { ConsultationCategory, ExpertType } from '../types';
import { openExternalUrl } from '@/lib/safeLinks';

/** A verified expert desk profile with an "ask this expert" action. */
export function ExpertProfileScreen({ id }: { id: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const query = useExpertDetail(id);
  const expert = query.data;

  if (!expert) {
    return (
      <AgScreen>
        <ExpertBackHeader title={t('experts.profileTitle')} />
        <View className="mt-4 gap-3">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} className="h-24 w-full rounded-card" />
          ))}
        </View>
      </AgScreen>
    );
  }

  const Icon = expertTypeIcon(expert.expertType);
  const typeLabel =
    EXPERT_TYPE_LABEL_KEY[expert.expertType as ExpertType] ?? 'experts.typePrivate';

  return (
    <AgScreen scroll>
      <ExpertBackHeader title={t('experts.profileTitle')} />

      <AgCard className="mt-4 gap-3">
        <View className="flex-row items-center gap-3">
          <View
            className="h-14 w-14 items-center justify-center rounded-full"
            style={{ backgroundColor: `${colors.primary}1A` }}
          >
            <Icon size={26} color={colors.primary} />
          </View>
          <View className="flex-1">
            <View className="flex-row items-center gap-1">
              <AgText variant="headingS" weight="bold" numberOfLines={2} className="flex-1">
                {expert.fullName}
              </AgText>
              {expert.verified ? <BadgeCheck size={18} color={colors.primary} /> : null}
            </View>
            {expert.title ? (
              <AgText variant="caption" color="muted">
                {expert.title}
              </AgText>
            ) : null}
          </View>
        </View>
        <View className="flex-row flex-wrap gap-1.5">
          <AgBadge label={t(typeLabel)} tone="info" />
          {expert.verified ? (
            <AgBadge label={t('experts.verified')} tone="success" />
          ) : null}
        </View>
        {expert.organization ? (
          <AgText variant="bodySmall" color="muted">
            {expert.organization}
          </AgText>
        ) : null}
        {expert.bio ? <AgText variant="body">{expert.bio}</AgText> : null}
      </AgCard>

      {/* Specializations */}
      <View className="mt-4 gap-2">
        <AgText variant="label" weight="semibold" color="muted">
          {t('experts.specializations')}
        </AgText>
        <View className="flex-row flex-wrap gap-1.5">
          {expert.categories.map((c) => (
            <AgBadge
              key={c}
              label={t(
                CATEGORY_LABEL_KEY[c as ConsultationCategory] ?? 'experts.categoryGeneral',
              )}
              tone="neutral"
            />
          ))}
        </View>
      </View>

      {/* Coverage + languages */}
      <AgCard className="mt-4 gap-2">
        <Row label={t('experts.languages')} value={expert.languages.join(', ') || '—'} />
        <Row
          label={t('experts.coverage')}
          value={expert.districts.length ? expert.districts.join(', ') : t('experts.statewide')}
        />
        {expert.contact ? (
          <Row label={t('experts.contact')} value={expert.contact} />
        ) : null}
      </AgCard>

      {expert.contact ? (
        <AgButton
          className="mt-4"
          variant="outline"
          title={t('experts.call')}
          leftIcon={<Phone size={18} color={colors.primary} />}
          onPress={() => void Linking.openURL(`tel:${expert.contact}`)}
        />
      ) : null}

      {expert.source ? (
        <AgButton
          className="mt-2"
          variant="ghost"
          title={t('experts.officialSource')}
          leftIcon={<ExternalLink size={18} color={colors.primary} />}
          onPress={() => void openExternalUrl(expert.source)}
        />
      ) : null}

      <AgButton
        className="mt-4"
        variant="primary"
        title={t('experts.askThisExpert')}
        onPress={() =>
          router.push({ pathname: '/consultations/new', params: { expertId: expert.id } })
        }
      />
    </AgScreen>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row items-start justify-between gap-3">
      <AgText variant="bodySmall" color="muted">
        {label}
      </AgText>
      <AgText variant="bodySmall" weight="semibold" className="flex-1 text-right">
        {value}
      </AgText>
    </View>
  );
}
