import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from 'react-native';

import { AgErrorState, AgScreen, AgSkeleton } from '@/components/ui';
import { ApiError } from '@/types';

import { ProduceBackHeader } from '../components/ProduceBackHeader';
import { ProduceForm } from '../components/ProduceForm';
import { useProduceDetail, useUpdateProduce } from '../hooks/useProduce';
import { ProduceError } from '../services/produceProvider';
import type { ProduceInput } from '../types';
import { PRODUCE_COLORS as C } from '../produceTheme';

function errorKeyFor(error: unknown): string {
  if (error instanceof ProduceError) return 'produce.errorGeneric';
  if (error instanceof ApiError) {
    if (error.errorCode === 'invalid_produce') return 'produce.errorInvalid';
    if (error.errorCode === 'invalid_produce_status') return 'produce.errorStatus';
    if (error.isNetwork) return 'common.offlineMessage';
  }
  return 'errors.generic';
}

/** Edit Produce screen (docs: Edit Produce). */
export function EditProduceScreen({ offerId }: { offerId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { data: offer, isLoading, isError, refetch } = useProduceDetail(offerId);
  const update = useUpdateProduce(offerId);
  const [errorKey, setErrorKey] = useState<string | undefined>();

  const onSubmit = (input: ProduceInput) => {
    setErrorKey(undefined);
    update.mutate(input, {
      onSuccess: ({ offline }) => {
        if (offline) Alert.alert(t('produce.savedOffline'));
        router.back();
      },
      onError: (error) => setErrorKey(errorKeyFor(error)),
    });
  };

  if (isLoading) {
    return (
      <AgScreen scroll backgroundColor={C.bg}>
        <AgSkeleton className="h-8 w-40 rounded-md" />
        <AgSkeleton className="mt-4 h-64 w-full rounded-card" />
      </AgScreen>
    );
  }

  if (isError || !offer) {
    return (
      <AgScreen backgroundColor={C.bg}>
        <ProduceBackHeader title={t('produce.editTitle')} />
        <AgErrorState onRetry={() => void refetch()} />
      </AgScreen>
    );
  }

  return (
    <AgScreen
      scroll
      backgroundColor={C.bg}
      contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 40 }}
    >
      <ProduceBackHeader title={t('produce.editTitle')} />
      <ProduceForm
        mode="edit"
        initial={offer}
        submitting={update.isPending}
        errorKey={errorKey}
        onSubmit={onSubmit}
      />
    </AgScreen>
  );
}
