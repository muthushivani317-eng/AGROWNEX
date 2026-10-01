import {
  Bolt,
  ChevronDown,
  ExternalLink,
  Eye,
  FileText,
  Leaf,
  ShieldCheck,
  Sprout,
  TriangleAlert,
  Users,
  Waves,
  type LucideIcon,
} from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { openExternalUrl } from '@/lib/safeLinks';

export type DiseaseRecommendation = {
  canonical_disease_name_en: string;
  canonical_disease_name_ta: string;
  why_it_occurs_en: string[];
  why_it_occurs_ta: string[];
  symptoms_en: string[];
  symptoms_ta: string[];
  immediate_actions_en: string[];
  immediate_actions_ta: string[];
  cultural_management_en: string[];
  cultural_management_ta: string[];
  biological_options_en: string[];
  biological_options_ta: string[];
  nutrient_correction_en: string[];
  nutrient_correction_ta: string[];
  prevention_en: string[];
  prevention_ta: string[];
  escalation_conditions_en: string[];
  escalation_conditions_ta: string[];
  chemical_recommendation_status: string;
  agricultural_disclaimer: string;
  official_sources: Array<{ title: string; url: string }>;
};

type SectionData = { key: string; title: string; items: string[]; icon: LucideIcon };

/** Registry-only display. Content, chemical state and links remain runtime-owned. */
export function RecommendationResultCard({
  recommendation,
  language,
}: {
  recommendation: DiseaseRecommendation;
  language: 'ta' | 'en';
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const ta = language !== 'en';
  const diseaseName = ta
    ? recommendation.canonical_disease_name_ta
    : recommendation.canonical_disease_name_en;
  const sections: SectionData[] = [
    { key: 'why', title: t('disease.whyThisMayOccur'), items: ta ? recommendation.why_it_occurs_ta : recommendation.why_it_occurs_en, icon: Waves },
    { key: 'symptoms', title: t('disease.symptomsToWatch'), items: ta ? recommendation.symptoms_ta : recommendation.symptoms_en, icon: Eye },
    { key: 'actions', title: t('disease.immediateActions'), items: ta ? recommendation.immediate_actions_ta : recommendation.immediate_actions_en, icon: Bolt },
    { key: 'cultural', title: t('disease.culturalManagement'), items: ta ? recommendation.cultural_management_ta : recommendation.cultural_management_en, icon: Sprout },
    { key: 'biological', title: t('disease.biologicalOptions'), items: ta ? recommendation.biological_options_ta : recommendation.biological_options_en, icon: Leaf },
    { key: 'nutrient', title: t('disease.nutrientGuidance'), items: ta ? recommendation.nutrient_correction_ta : recommendation.nutrient_correction_en, icon: Sprout },
    { key: 'prevention', title: t('disease.prevention'), items: ta ? recommendation.prevention_ta : recommendation.prevention_en, icon: ShieldCheck },
    { key: 'expert', title: t('disease.whenToSeekExpertHelp'), items: ta ? recommendation.escalation_conditions_ta : recommendation.escalation_conditions_en, icon: Users },
  ].filter((section) => section.items.length > 0);

  return (
    <View testID="disease-recommendation-result" style={styles.wrapper}>
      <View style={styles.sectionHeader}>
        <View style={[styles.headerIcon, { backgroundColor: `${colors.primary}16` }]}>
          <Leaf size={23} color={colors.primaryLight} />
        </View>
        <View style={styles.headerCopy}>
          <AgText variant="headingS" weight="bold">{t('disease.aboutDisease')}</AgText>
          <AgText variant="bodySmall" color="primary" weight="semibold">{diseaseName}</AgText>
        </View>
      </View>

      {recommendation.agricultural_disclaimer ? (
        <View style={[styles.safetyCard, { backgroundColor: `${colors.primary}0D`, borderColor: `${colors.primary}40` }]}>
          <ShieldCheck size={24} color={colors.primaryLight} />
          <AgText variant="bodySmall" weight="medium" style={styles.safetyText}>
            {recommendation.agricultural_disclaimer}
          </AgText>
        </View>
      ) : null}

      <View style={[styles.sectionsCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
        {sections.map((section, index) => (
          <RecommendationSection
            key={section.key}
            section={section}
            showDivider={index < sections.length - 1}
          />
        ))}
      </View>

      <View style={[styles.chemicalCard, { backgroundColor: `${colors.warning}10`, borderColor: `${colors.warning}45` }]}>
        <View style={[styles.warningIcon, { backgroundColor: `${colors.warning}12` }]}>
          <TriangleAlert size={23} color={colors.warning} />
        </View>
        <View style={styles.chemicalCopy}>
          <AgText variant="bodyLarge" weight="semibold" style={{ color: colors.warning }}>
            {t('disease.chemicalUse')}
          </AgText>
          <AgText variant="bodySmall" weight="medium">{recommendation.chemical_recommendation_status}</AgText>
          <AgText variant="caption" color="muted">{t('disease.verifyOfficialSource').toLocaleUpperCase()}</AgText>
        </View>
      </View>

      {recommendation.official_sources.length > 0 ? (
        <View style={[styles.sourcesCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
          <View style={styles.sourcesHeading}>
            <FileText size={22} color={colors.primaryLight} />
            <AgText variant="bodyLarge" weight="semibold">{t('disease.officialSources')}</AgText>
          </View>
          {recommendation.official_sources.map((source, index) => (
            <Pressable
              key={source.url}
              onPress={() => void openExternalUrl(source.url)}
              accessibilityRole="link"
              accessibilityLabel={source.title}
              style={({ pressed }) => [
                styles.sourceRow,
                index > 0 && { borderTopColor: colors.border, borderTopWidth: StyleSheet.hairlineWidth },
                { opacity: pressed ? 0.68 : 1 },
              ]}
            >
              <AgText variant="bodySmall" color="primary" weight="medium" style={styles.sourceTitle}>
                {source.title}
              </AgText>
              <ExternalLink size={18} color={colors.primaryLight} />
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function RecommendationSection({
  section,
  showDivider,
}: {
  section: SectionData;
  showDivider: boolean;
}) {
  const { colors } = useAppTheme();
  const [expanded, setExpanded] = useState(true);
  const Icon = section.icon;
  return (
    <View style={[styles.recommendationSection, showDivider && { borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth }]}>
      <Pressable
        onPress={() => setExpanded((value) => !value)}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        accessibilityLabel={section.title}
        style={styles.sectionButton}
      >
        <View style={styles.sectionHeadingContent}>
          <View style={[styles.sectionIcon, { backgroundColor: `${colors.primary}12` }]}>
            <Icon size={21} color={colors.primaryLight} />
          </View>
          <AgText variant="bodyLarge" weight="semibold" style={styles.sectionTitle}>
            {section.title}
          </AgText>
          <ChevronDown
            size={20}
            color={colors.primaryLight}
            style={{ transform: [{ rotate: expanded ? '180deg' : '0deg' }] }}
          />
        </View>
      </Pressable>
      {expanded ? (
        <View style={styles.items}>
          {section.items.map((item, index) => (
            <AgText key={`${section.key}-${index}`} variant="bodySmall" color="muted">
              • {item}
            </AgText>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: 14, marginTop: 18 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 11 },
  headerIcon: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  headerCopy: { flex: 1, gap: 1 },
  safetyCard: { minHeight: 74, flexDirection: 'row', alignItems: 'center', gap: 12, borderWidth: 1, borderRadius: 20, padding: 16 },
  safetyText: { flex: 1 },
  sectionsCard: { borderWidth: 1, borderRadius: 22, overflow: 'hidden' },
  recommendationSection: { paddingHorizontal: 14, paddingVertical: 12 },
  sectionButton: { minHeight: 48, justifyContent: 'center' },
  sectionHeadingContent: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
  },
  sectionIcon: { width: 42, height: 42, borderRadius: 13, alignItems: 'center', justifyContent: 'center' },
  sectionTitle: { flex: 1 },
  items: { gap: 7, paddingLeft: 53, paddingBottom: 5 },
  chemicalCard: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, borderWidth: 1, borderRadius: 20, padding: 16 },
  warningIcon: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  chemicalCopy: { flex: 1, gap: 4 },
  sourcesCard: { borderWidth: 1, borderRadius: 20, overflow: 'hidden' },
  sourcesHeading: { minHeight: 58, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 16 },
  sourceRow: { minHeight: 56, flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 10 },
  sourceTitle: { flex: 1 },
});
