import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { ArrowLeft, Trash2 } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlatList, View } from 'react-native';

import { AgButton, AgCard, AgPressable, AgScreen, AgText } from '@/components/ui';
import { ImageViewer } from '@/features/growth/components/ImageViewer';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';

import {
  plantJournalStorage,
  type PlantJournalEntry,
} from '../services/plantJournalStorage';

export function PlantJournalScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  const [entries, setEntries] = useState(() => plantJournalStorage.list());
  const [viewing, setViewing] = useState<PlantJournalEntry | null>(null);

  const remove = (id: string) => {
    plantJournalStorage.remove(id);
    setEntries(plantJournalStorage.list());
    if (viewing?.id === id) setViewing(null);
  };

  return (
    <AgScreen>
      <View className="mb-4 mt-2 flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="-ml-2 h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold">
          {t('plantIdentifier.journalTitle')}
        </AgText>
      </View>

      <FlatList
        data={entries}
        keyExtractor={(entry) => entry.id}
        contentContainerStyle={{ flexGrow: 1, gap: 12, paddingBottom: 24 }}
        ListEmptyComponent={
          <View className="flex-1 items-center justify-center px-6">
            <AgText color="muted" center>
              {t('plantIdentifier.journalEmpty')}
            </AgText>
          </View>
        }
        renderItem={({ item }) => (
          <AgCard className="flex-row items-center gap-3">
            <AgPressable
              onPress={() => setViewing(item)}
              accessibilityRole="button"
              accessibilityLabel={item.commonName ?? t('plantIdentifier.unknownPlant')}
              className="flex-1 flex-row items-center gap-3"
            >
              <Image
                source={{ uri: item.imageUri }}
                style={{ width: 72, height: 72, borderRadius: 12 }}
                contentFit="cover"
              />
              <View className="flex-1 gap-1">
                <AgText weight="semibold">
                  {item.commonName ?? t('plantIdentifier.unknownPlant')}
                </AgText>
                {item.scientificName ? (
                  <AgText variant="bodySmall" color="muted" style={{ fontStyle: 'italic' }}>
                    {item.scientificName}
                  </AgText>
                ) : null}
                <AgText variant="caption" color="muted">
                  {t('plantIdentifier.savedOn', {
                    date: new Date(item.savedAt).toLocaleDateString(
                      language === 'ta' ? 'ta-IN' : 'en-IN',
                    ),
                  })}
                </AgText>
              </View>
            </AgPressable>
            <AgButton
              title={t('plantIdentifier.deleteEntry')}
              variant="ghost"
              size="sm"
              leftIcon={<Trash2 size={17} color={colors.danger} />}
              onPress={() => remove(item.id)}
            />
          </AgCard>
        )}
      />

      <ImageViewer
        uri={viewing?.imageUri ?? null}
        caption={viewing?.commonName ?? viewing?.scientificName}
        visible={Boolean(viewing)}
        onClose={() => setViewing(null)}
      />
    </AgScreen>
  );
}
