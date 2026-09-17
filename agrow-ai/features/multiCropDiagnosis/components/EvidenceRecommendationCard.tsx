import { useState } from 'react';
import { Pressable, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgCard, AgText } from '@/components/ui';

export type RecommendationLanguage = 'ta' | 'en';

interface LocalizedText {
  ta: string | null;
  en: string;
  tamil_review_required: boolean;
}

interface RecommendationItem {
  recommendation_id: string;
  category: string;
  text: LocalizedText;
  source: {
    source_title: string;
    publisher: string | null;
    printed_page: string | null;
    section: string;
  };
}

export interface EvidenceRecommendation {
  verification_label: 'VERIFY AGAINST OFFICIAL SOURCE';
  official_diagnosis: false;
  field_validated: false;
  display_name: LocalizedText;
  items: RecommendationItem[];
}

function localized(value: LocalizedText, language: RecommendationLanguage) {
  if (language === 'ta' && value.ta && !value.tamil_review_required) return value.ta;
  // English is the safe farmer-facing fallback until Tamil is human reviewed.
  // Internal workflow markers must never be rendered in production UI.
  return value.en;
}

export function EvidenceRecommendationCard({
  recommendation,
  language,
}: {
  recommendation: EvidenceRecommendation | null;
  language: RecommendationLanguage;
}) {
  const [expanded, setExpanded] = useState(true);
  const { t } = useTranslation();
  if (!recommendation) {
    return (
      <AgCard className="mt-3">
        <AgText color="muted">{t('disease.verifyQualifiedSource')}</AgText>
      </AgCard>
    );
  }
  return (
    <AgCard className="mt-3 gap-3">
      <Pressable accessibilityRole="button" onPress={() => setExpanded((value) => !value)}>
        <AgText weight="bold">{localized(recommendation.display_name, language)}</AgText>
      </Pressable>
      {expanded && (
        <View className="gap-2">
          {recommendation.items.map((item) => (
            <View key={item.recommendation_id} className="gap-1">
              <AgText>• {localized(item.text, language)}</AgText>
              <AgText variant="caption">
                {item.source.source_title}
                {item.source.publisher ? ` — ${item.source.publisher}` : ''}
                {item.source.printed_page ? `; ${t('disease.sourcePage', { page: item.source.printed_page })}` : ''}
                {`; ${item.source.section}`}
              </AgText>
            </View>
          ))}
          <AgText color="danger">{t('disease.verifyOfficialSource')}</AgText>
        </View>
      )}
    </AgCard>
  );
}
