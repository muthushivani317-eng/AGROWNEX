import { useEffect, useState } from 'react';
import { Alert, Pressable, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, Check } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { AgButton, AgCard, AgErrorState, AgInput, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { ORGANIC_MODES } from '../constants';
import { useOrganicProfile, useSaveOrganicProfile } from '../hooks/useOrganic';
import { useOrganicSync } from '../hooks/useOrganicSync';
import type { OrganicFarmMode } from '../types';

export function OrganicProfileScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { colors } = useAppTheme();
  const query = useOrganicProfile(farmId); const save = useSaveOrganicProfile(farmId);
  useOrganicSync();
  const [mode, setMode] = useState<OrganicFarmMode>('organic_preferred'); const [transitionDate, setTransitionDate] = useState(''); const [goals, setGoals] = useState('');
  useEffect(() => { if (query.data) { setMode(query.data.mode); setTransitionDate(query.data.transitionStartDate ?? ''); setGoals(query.data.goals.join(', ')); } }, [query.data]);
  if (query.isLoading) return <AgScreen><AgSkeleton className="h-10 w-full"/><AgSkeleton className="mt-4 h-64 w-full"/></AgScreen>;
  if (query.isError) return <AgScreen><AgErrorState message={t('organic.loadError')} onRetry={() => void query.refetch()}/></AgScreen>;
  const submit = () => save.mutate({ mode, transitionStartDate: transitionDate.trim() || null, goals: goals.split(',').map((v) => v.trim()).filter(Boolean), preferredPractices: [] }, { onSuccess: ({ offline }) => Alert.alert(t(offline ? 'organic.savedOffline' : 'organic.saved')) });
  return <AgScreen scroll>
    <View className="flex-row items-center gap-2"><AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} className="h-10 w-10 items-center justify-center"><ArrowLeft size={24} color={colors.text}/></AgPressable><AgText variant="headingM" weight="bold">{t('organic.profileTitle')}</AgText></View>
    <AgText color="muted" className="mt-2">{t('organic.profileIntro')}</AgText>
    <AgCard className="mt-5"><AgText variant="label" weight="bold">{t('organic.chooseMode')}</AgText>{ORGANIC_MODES.map((item) => <Pressable key={item} onPress={() => setMode(item)} accessibilityRole="radio" accessibilityState={{ checked: mode === item }} style={[styles.modeOption, mode === item && styles.selectedMode]}><View style={[styles.modeIndicator, { backgroundColor: mode === item ? colors.primary : colors.surface }]}>{mode === item ? <Check size={16} color="#fff"/> : null}</View><View style={styles.modeCopy}><AgText weight="semibold" style={{ color: colors.text }}>{t(`organic.mode.${item}.title`)}</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>{t(`organic.mode.${item}.description`)}</AgText></View></Pressable>)}</AgCard>
    {mode === 'transitioning' ? <AgInput className="mt-4" label={t('organic.transitionDate')} placeholder="YYYY-MM-DD" value={transitionDate} onChangeText={setTransitionDate}/> : null}
    <AgInput className="mt-4" label={t('organic.goals')} placeholder={t('organic.goalsHint')} value={goals} onChangeText={setGoals} multiline/>
    <AgCard className="mt-4"><AgText variant="bodySmall" color="muted">{t('organic.certificationNotice')}</AgText></AgCard>
    <AgButton className="mt-6" title={t('common.save')} loading={save.isPending} onPress={submit}/>
  </AgScreen>;
}

const styles = StyleSheet.create({
  modeOption: { marginTop: 12, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#D8DDD9', borderRadius: 12, padding: 12, backgroundColor: '#FFFFFF' },
  selectedMode: { borderColor: '#19763A', backgroundColor: '#F4FAF1' },
  modeIndicator: { width: 24, height: 24, borderRadius: 12, marginRight: 12, alignItems: 'center', justifyContent: 'center' },
  modeCopy: { flex: 1 },
});
