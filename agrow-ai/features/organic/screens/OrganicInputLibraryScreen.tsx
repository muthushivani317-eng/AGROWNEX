import { useState } from 'react';
import { Alert, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { ArrowLeft, ArrowRight, BookOpen, CheckCircle2, Filter, Leaf, Search, ShieldCheck, Sprout } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import { AgButton, AgEmptyState, AgErrorState, AgInput, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { useSelectedFarm } from '@/features/weather';
import { useOrganicInputs } from '../hooks/useOrganicInputs';
import { useCreateOrganicPractice } from '../hooks/useOrganic';
import { calculateInputQuantity, practiceTypeForCategory } from '../services/organicInputCalculator';
import type { OrganicInputItem } from '../organicInputTypes';

const CATEGORY_ICONS: Record<string, typeof Sprout> = { biofertilizer: Sprout, biopesticide: ShieldCheck, compost: Leaf, trap: ShieldCheck };

function InputCard({ item, areaHectares, farmId }: { item: OrganicInputItem; areaHectares: number | null; farmId: string | null }) {
  const { t } = useTranslation(); const { isTamil } = useLanguage(); const { colors, isDark } = useAppTheme();
  const calc = calculateInputQuantity(item.guidance, areaHectares); const logPractice = useCreateOrganicPractice(farmId ?? '');
  const Icon = CATEGORY_ICONS[item.category.toLowerCase()] ?? Sprout; const name = isTamil ? item.nameTa : item.nameEn; const purpose = isTamil ? item.purposeTa : item.purposeEn;
  const sourceLabel = item.sourceOrganization.length > 52 ? `${item.sourceOrganization.slice(0, 52)}…` : item.sourceOrganization;
  return <View style={[styles.card, { backgroundColor: isDark ? '#202921' : '#FFFDF9', borderColor: isDark ? '#344539' : '#E4ECE1' }]}>
    <View style={styles.cardTop}>
      <View style={[styles.artPanel, { backgroundColor: isDark ? '#21392A' : '#EAF5E7' }]}><View style={[styles.artGlow, { backgroundColor: isDark ? '#2E5938' : '#D1EBCB' }]} /><Icon size={50} color={colors.primary} strokeWidth={1.5} /></View>
      <View style={styles.cardCopy}>
        <View style={styles.nameRow}><AgText variant="headingS" weight="bold" numberOfLines={2} style={[styles.name, { color: isDark ? colors.text : '#073F2A' }]}>{name}</AgText><View style={[styles.categoryIcon, { backgroundColor: isDark ? '#24452D' : '#EDF7E8' }]}><Leaf size={19} color={colors.primary} /></View></View>
        <View style={[styles.approval, { backgroundColor: item.approved ? (isDark ? '#1B4828' : '#E5F5E3') : (isDark ? '#4A3812' : '#FFF1D2') }]}><CheckCircle2 size={16} color={item.approved ? colors.primary : colors.warning} /><AgText variant="bodySmall" weight="semibold" style={{ color: item.approved ? colors.primary : colors.warning }}>{t(item.approved ? 'organic.catalogueApproved' : 'organic.sourcedNotApproved')}</AgText></View>
        <AgText variant="bodySmall" style={[styles.purpose, { color: colors.textMuted }]}>{purpose}</AgText>
      </View>
    </View>
    <View style={[styles.source, { borderTopColor: isDark ? '#344539' : '#E2EAE0' }]}><View style={[styles.bookIcon, { backgroundColor: isDark ? '#3B311A' : '#FFF5DE' }]}><BookOpen size={21} color="#E87A08" /></View><AgText variant="caption" numberOfLines={2} style={[styles.sourceText, { color: colors.textMuted }]}>{sourceLabel} · {item.documentReference}</AgText><ArrowRight size={20} color={colors.textMuted} /></View>
    {calc ? <View style={[styles.farmDose, { backgroundColor: isDark ? '#193021' : '#F0F8EC' }]}><AgText variant="caption" weight="semibold" style={{ color: colors.primary }}>{t('organic.calculatedForFarm', { area: areaHectares, quantity: calc.quantity, unit: calc.unit })}</AgText>{farmId ? <AgButton size="sm" fullWidth={false} variant="outline" title={t('organic.addToLogbook')} onPress={() => logPractice.mutate({ type: practiceTypeForCategory(item.category), title: name, occurredAt: new Date().toISOString(), quantity: calc.quantity, unit: calc.unit }, { onSuccess: () => Alert.alert(t('organic.practiceSaved')) })} /> : null}</View> : null}
  </View>;
}

export function OrganicInputLibraryScreen() {
  const { t } = useTranslation(); const router = useRouter(); const { colors, isDark } = useAppTheme(); const [search, setSearch] = useState(''); const query = useOrganicInputs(search); const { selected } = useSelectedFarm();
  return <AgScreen scroll padded={false} backgroundColor={isDark ? '#131B15' : '#F7FAF4'} contentContainerStyle={styles.screen}>
    <View style={styles.hero}><Image source={require('@/assets/images/organic-dashboard-landscape.png')} contentFit="cover" contentPosition="right bottom" style={styles.heroLandscape} accessible={false} /><View style={styles.heroShade} /><View style={styles.header}><TouchableOpacity onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} activeOpacity={0.72} style={[styles.backButton, { backgroundColor: isDark ? '#1D3926' : '#EEF7EA' }]}><ArrowLeft size={23} color={isDark ? colors.text : '#0B4A31'} /></TouchableOpacity><View style={[styles.libraryMark, { backgroundColor: isDark ? '#1D3926' : '#F0F8ED' }]}><Leaf size={16} color={colors.primary} /><AgText variant="caption" weight="bold" style={{ color: colors.primary }}>ORGANIC</AgText></View></View><View style={styles.heroCopy}><AgText variant="headingL" weight="bold" style={[styles.heroTitle, { color: isDark ? colors.text : '#073F2A' }]}>{t('organic.inputLibrary')}</AgText><AgText variant="body" style={[styles.heroIntro, { color: colors.textMuted }]}>{t('organic.inputLibraryNotice')}</AgText></View></View>
    <View style={styles.content}><AgInput light={!isDark} fieldBackgroundColor={isDark ? '#202A21' : '#FFFFFF'} fieldBorderColor={isDark ? '#344539' : '#E1EADF'} focusBorderColor={colors.primary} accessibilityLabel={t('organic.searchInputs')} placeholder={t('organic.searchInputs')} value={search} onChangeText={setSearch} leftAccessory={<Search size={25} color={colors.textMuted} />} rightAccessory={<View style={[styles.filter, { backgroundColor: isDark ? '#24452D' : '#EAF7E7' }]}><Filter size={20} color={colors.primary} /></View>} />
    <View style={styles.resultHeader}><View><AgText variant="headingS" weight="bold" style={{ color: colors.text }}>Reviewed inputs</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>{query.data?.length ?? 0} catalogue entries</AgText></View></View>
    {query.isLoading ? <View><AgSkeleton className="h-48 w-full" /><AgSkeleton className="mt-4 h-48 w-full" /></View> : query.isError ? <AgErrorState message={t('organic.inputLibraryError')} onRetry={() => void query.refetch()} /> : !query.data?.length ? <AgEmptyState title={t('organic.inputLibraryEmpty')} message={t('organic.reviewedContentEmpty')} /> : query.data.map((item) => <InputCard key={item.id} item={item} areaHectares={selected?.areaHectares ?? null} farmId={selected?.id ?? null} />)}
    </View>
  </AgScreen>;
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 36 }, hero: { minHeight: 292, overflow: 'hidden' }, heroLandscape: { position: 'absolute', right: -84, bottom: 0, width: '104%', height: 205, opacity: 0.66 }, heroShade: { position: 'absolute', right: 0, bottom: 0, left: 0, height: 205, backgroundColor: 'rgba(247,250,244,0.45)' }, header: { minHeight: 72, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, backButton: { width: 46, height: 46, borderRadius: 15, alignItems: 'center', justifyContent: 'center' }, libraryMark: { minHeight: 32, paddingHorizontal: 11, borderRadius: 16, flexDirection: 'row', alignItems: 'center', gap: 6 }, heroCopy: { paddingHorizontal: 20, paddingTop: 25, maxWidth: 510 }, heroTitle: { letterSpacing: -0.9 }, heroIntro: { marginTop: 8, maxWidth: 375, lineHeight: 24 }, content: { paddingHorizontal: 16, marginTop: -10 }, filter: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' }, resultHeader: { marginTop: 24, marginBottom: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, card: { marginBottom: 16, padding: 16, borderRadius: 24, borderWidth: 1, shadowColor: '#245034', shadowOpacity: 0.08, shadowRadius: 16, shadowOffset: { width: 0, height: 5 }, elevation: 2 }, cardTop: { flexDirection: 'row', alignItems: 'flex-start' }, artPanel: { width: 104, height: 118, borderRadius: 20, overflow: 'hidden', alignItems: 'center', justifyContent: 'center' }, artGlow: { position: 'absolute', width: 90, height: 90, borderRadius: 45, opacity: 0.72, transform: [{ translateX: 22 }, { translateY: -18 }] }, cardCopy: { flex: 1, minWidth: 0, marginLeft: 15 }, nameRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 }, name: { flex: 1, lineHeight: 26, letterSpacing: -0.45 }, categoryIcon: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center' }, approval: { minHeight: 32, marginTop: 9, paddingHorizontal: 10, borderRadius: 16, alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 6 }, purpose: { marginTop: 11, lineHeight: 21 }, source: { marginTop: 15, paddingTop: 13, borderTopWidth: StyleSheet.hairlineWidth, flexDirection: 'row', alignItems: 'center', gap: 11 }, bookIcon: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center' }, sourceText: { flex: 1, lineHeight: 18 }, farmDose: { marginTop: 14, padding: 12, borderRadius: 14, gap: 10 },
});
