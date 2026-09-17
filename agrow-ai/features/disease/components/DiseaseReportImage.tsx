import { Image, type ImageStyle } from 'expo-image';
import { useEffect, useState } from 'react';
import type { StyleProp } from 'react-native';

import { env } from '@/config/env';
import { useAuthStore } from '@/features/auth/store/authStore';

type Props = {
  reportId: string;
  privateImageAvailable?: boolean;
  legacyUrl: string | null;
  style: StyleProp<ImageStyle>;
  className?: string;
};

export function DiseaseReportImage({
  reportId,
  privateImageAvailable,
  legacyUrl,
  style,
  className,
}: Props) {
  const refreshSession = useAuthStore((state) => state.refreshSession);
  const [token, setToken] = useState<string | null>(
    useAuthStore.getState().tokens?.idToken ?? null,
  );
  const [privateFailed, setPrivateFailed] = useState(false);

  useEffect(() => {
    let active = true;
    if (privateImageAvailable) {
      void refreshSession().then((next) => {
        if (active) setToken(next);
      });
    }
    return () => {
      active = false;
    };
  }, [privateImageAvailable, refreshSession]);

  const source = buildDiseaseImageSource({
    reportId,
    privateImageAvailable: privateImageAvailable && !privateFailed,
    legacyUrl,
    token,
  });

  if (!source) return null;
  return (
    <Image
      source={source}
      style={style}
      contentFit="cover"
      className={className}
      onError={() => {
        if (privateImageAvailable && legacyUrl) setPrivateFailed(true);
      }}
    />
  );
}

export function buildDiseaseImageSource({
  reportId,
  privateImageAvailable,
  legacyUrl,
  token,
}: Pick<Props, 'reportId' | 'privateImageAvailable' | 'legacyUrl'> & {
  token: string | null;
}) {
  if (privateImageAvailable && token) {
    return {
      uri: `${env.apiBaseUrl}/disease/${encodeURIComponent(reportId)}/image`,
      headers: { Authorization: `Bearer ${token}` },
    };
  }
  return legacyUrl ? { uri: legacyUrl } : null;
}
