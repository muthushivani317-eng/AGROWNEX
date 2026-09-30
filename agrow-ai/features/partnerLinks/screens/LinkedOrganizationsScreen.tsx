import { useRouter } from 'expo-router';
import { ArrowLeft, Building2 } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Alert, View } from 'react-native';

import {
  AgBadge,
  AgButton,
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSpinner,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import {
  useApprovePartnerLink,
  useMyPartnerLinks,
  useRevokePartnerLink,
} from '../hooks/usePartnerLinks';
import type { PartnerLinkRequest, PartnerOrgKind } from '../types';

const KIND_LABEL_KEY: Record<PartnerOrgKind, string> = {
  fpo: 'partnerLinks.kindFpo',
  kvk: 'partnerLinks.kindKvk',
  agri_community: 'partnerLinks.kindAgriCommunity',
};

function LinkRow({ link }: { link: PartnerLinkRequest }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const approve = useApprovePartnerLink();
  const revoke = useRevokePartnerLink();
  const busy = approve.isPending || revoke.isPending;

  const confirmApprove = () => {
    Alert.alert(
      t('partnerLinks.approveConfirmTitle'),
      t('partnerLinks.approveConfirmMessage', { name: link.organizationName }),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('partnerLinks.approve'),
          onPress: () => approve.mutate(link.id, {
            onError: () => Alert.alert(t('partnerLinks.approveFailed')),
          }),
        },
      ],
    );
  };

  const confirmRevoke = () => {
    const isWaiting = link.status === 'join_requested';
    const isMember = link.status === 'active';
    Alert.alert(
      isWaiting ? t('partnerLinks.cancelConfirmTitle') : t('partnerLinks.leaveConfirmTitle'),
      isWaiting ? t('partnerLinks.cancelConfirmMessage', { name: link.organizationName }) : t('partnerLinks.leaveConfirmMessage', { name: link.organizationName }),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: isWaiting ? t('partnerLinks.cancelRequest') : isMember ? t('partnerLinks.leave') : t('partnerLinks.reject'),
          style: 'destructive',
          onPress: () => revoke.mutate(link.id, {
            onError: () => Alert.alert(t('partnerLinks.revokeFailed')),
          }),
        },
      ],
    );
  };

  return (
    <AgCard className="mb-3 gap-3">
      <View className="flex-row items-center gap-3">
        <View className="h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <Building2 size={19} color={colors.primary} />
        </View>
        <View className="flex-1">
          <AgText variant="body" weight="semibold">
            {link.organizationName}
          </AgText>
          <AgText variant="caption" color="muted">
            {t(KIND_LABEL_KEY[link.organizationKind])}
          </AgText>
        </View>
        <AgBadge
          label={
            link.status === 'pending'
              ? t('partnerLinks.statusPending')
              : link.status === 'join_requested'
                ? t('partnerLinks.statusWaiting')
              : link.status === 'active'
                ? t('partnerLinks.statusActive')
                : t('partnerLinks.statusRevoked')
          }
          tone={
            link.status === 'pending'
              ? 'warning'
              : link.status === 'join_requested'
                ? 'warning'
              : link.status === 'active'
                ? 'success'
                : 'neutral'
          }
        />
      </View>

      {link.status === 'pending' && link.initiatedBy === 'organization' ? (
        <View className="flex-row gap-2">
          <AgButton
            title={t('partnerLinks.approve')}
            onPress={confirmApprove}
            loading={approve.isPending}
            disabled={busy}
            variant="success"
            size="sm"
            className="flex-1"
          />
          <AgButton
            title={t('partnerLinks.reject')}
            onPress={confirmRevoke}
            loading={revoke.isPending}
            disabled={busy}
            variant="outline"
            size="sm"
            className="flex-1"
          />
        </View>
      ) : link.status === 'active' || link.status === 'join_requested' ? (
        <AgButton
          title={link.status === 'join_requested' ? t('partnerLinks.cancelRequest') : t('partnerLinks.leave')}
          onPress={confirmRevoke}
          loading={revoke.isPending}
          disabled={busy}
          variant="outline"
          size="sm"
        />
      ) : null}
    </AgCard>
  );
}

export function LinkedOrganizationsScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { data: links, isLoading, isError, refetch } = useMyPartnerLinks();

  return (
    <AgScreen scroll>
      <View className="mt-2 flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="-ml-2 h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold">
          {t('partnerLinks.title')}
        </AgText>
      </View>
      <AgText variant="body" color="muted" className="mb-4 mt-1">
        {t('partnerLinks.subtitle')}
      </AgText>

      {isLoading ? (
        <View className="mt-12">
          <AgSpinner />
        </View>
      ) : isError ? (
        <AgErrorState message={t('partnerLinks.loadFailed')} onRetry={() => refetch()} />
      ) : !links || links.length === 0 ? (
        <AgEmptyState
          icon={Building2}
          title={t('partnerLinks.emptyTitle')}
          message={t('partnerLinks.emptyMessage')}
          actionLabel={t('common.retry')}
          onAction={() => refetch()}
        />
      ) : (
        links.map((link) => <LinkRow key={link.id} link={link} />)
      )}
    </AgScreen>
  );
}
