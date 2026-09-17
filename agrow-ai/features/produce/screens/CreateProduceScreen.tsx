import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from 'react-native';

import { AgScreen } from '@/components/ui';
import { ApiError } from '@/types';

import { ProduceBackHeader } from '../components/ProduceBackHeader';
import { ProduceForm } from '../components/ProduceForm';
import { useCreateProduce } from '../hooks/useProduce';
import { ProduceError } from '../services/produceProvider';
import type { ProduceInput } from '../types';
import { PRODUCE_COLORS as C } from '../produceTheme';

function errorKeyFor(error: unknown): string {
  if (error instanceof ProduceError) return 'produce.errorGeneric';
  if (error instanceof ApiError) {
    if (error.errorCode === 'invalid_produce') return 'produce.errorInvalid';
    if (error.errorCode === 'farm_not_found') return 'produce.errorFarmMissing';
    if (error.isNetwork) return 'common.offlineMessage';
  }
  return 'errors.generic';
}

/** Create Produce screen (docs: Create Produce). */
export function CreateProduceScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const create = useCreateProduce();
  const [errorKey, setErrorKey] = useState<string | undefined>();

  const onSubmit = (input: ProduceInput) => {
    setErrorKey(undefined);
    create.mutate(input, {
      onSuccess: ({ offline }) => {
        if (offline) Alert.alert(t('produce.savedOffline'));
        router.back();
      },
      onError: (error) => setErrorKey(errorKeyFor(error)),
    });
  };

  return (
    <AgScreen
      scroll
      backgroundColor={C.bg}
      contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 40 }}
    >
      <ProduceBackHeader title={t('produce.createTitle')} />
      <ProduceForm
        mode="create"
        submitting={create.isPending}
        errorKey={errorKey}
        showPhotos
        onSubmit={onSubmit}
      />
    </AgScreen>
  );
}
