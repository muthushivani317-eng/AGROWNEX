import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Alert } from 'react-native';

import { AgOfflineBanner, AgScreen, AgText } from '@/components/ui';

import { ConsultationForm } from '../components/ConsultationForm';
import { ExpertBackHeader } from '../components/ExpertBackHeader';
import { useCreateConsultation } from '../hooks/useConsultations';
import type { ConsultationInput } from '../types';

/** Ask a verified expert: crop → issue → photos → description → submit. */
export function CreateConsultationScreen({ expertId }: { expertId?: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const create = useCreateConsultation();

  const onSubmit = (input: ConsultationInput) => {
    create.mutate(input, {
      onSuccess: (consultation) => {
        router.replace({
          pathname: '/consultations/[id]',
          params: { id: consultation.id },
        });
      },
      onError: () => Alert.alert(t('experts.submitFailed')),
    });
  };

  return (
    <AgScreen scroll>
      <AgOfflineBanner />
      <ExpertBackHeader title={t('experts.createTitle')} />
      <AgText variant="bodySmall" color="muted" className="mb-3 mt-1">
        {t('experts.createSubtitle')}
      </AgText>
      <ConsultationForm
        submitting={create.isPending}
        onSubmit={onSubmit}
        presetExpertId={expertId ?? null}
      />
    </AgScreen>
  );
}
