import { useState } from 'react';
import { Alert, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, Plus } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { AgButton, AgCard, AgEmptyState, AgErrorState, AgInput, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { PRACTICE_TYPES } from '../constants';
import { useCreateOrganicPractice, useOrganicPractices } from '../hooks/useOrganic';
import { useOrganicSync } from '../hooks/useOrganicSync';
import type { OrganicPracticeType } from '../types';

export function OrganicLogbookScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { colors } = useAppTheme(); const query = useOrganicPractices(farmId); const create = useCreateOrganicPractice(farmId);
  useOrganicSync();
  const [adding, setAdding] = useState(false); const [type, setType] = useState<OrganicPracticeType>('amendment'); const [title, setTitle] = useState(''); const [notes, setNotes] = useState('');
  const submit = () => { if (!title.trim()) return Alert.alert(t('organic.titleRequired')); create.mutate({ type, title: title.trim(), notes: notes.trim() || null, occurredAt: new Date().toISOString() }, { onSuccess: ({ offline }) => { setAdding(false); setTitle(''); setNotes(''); Alert.alert(t(offline ? 'organic.savedOffline' : 'organic.practiceSaved')); } }); };
  return <AgScreen scroll><View className="flex-row items-center gap-2"><AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} className="h-10 w-10 items-center justify-center"><ArrowLeft size={24} color={colors.text}/></AgPressable><AgText variant="headingM" weight="bold" className="flex-1">{t('organic.logbookTitle')}</AgText><AgPressable onPress={() => setAdding(!adding)} accessibilityRole="button" accessibilityLabel={t('organic.addPractice')}><Plus size={24} color={colors.primary}/></AgPressable></View>
  {adding ? <AgCard className="mt-4"><AgText weight="bold">{t('organic.addPractice')}</AgText><View className="mt-3 flex-row flex-wrap gap-2">{PRACTICE_TYPES.map((item) => <AgPressable key={item} onPress={() => setType(item)} className="rounded-full border px-3 py-2" style={{ backgroundColor: type === item ? colors.primary : colors.surface }}><AgText variant="caption" style={{ color: type === item ? '#fff' : colors.text }}>{t(`organic.practice.${item}`)}</AgText></AgPressable>)}</View><AgInput className="mt-4" label={t('organic.practiceTitle')} value={title} onChangeText={setTitle}/><AgInput className="mt-3" label={t('organic.notes')} value={notes} onChangeText={setNotes} multiline/><AgButton className="mt-4" title={t('common.save')} loading={create.isPending} onPress={submit}/></AgCard> : null}
  {query.isLoading ? <><AgSkeleton className="mt-4 h-24 w-full"/><AgSkeleton className="mt-3 h-24 w-full"/></> : query.isError ? <AgErrorState message={t('organic.loadError')} onRetry={() => void query.refetch()}/> : !query.data?.length ? <AgEmptyState title={t('organic.emptyTitle')} message={t('organic.emptyDescription')} actionLabel={t('organic.addPractice')} onAction={() => setAdding(true)}/> : query.data.map((row) => <AgCard key={row.id} className="mt-3"><View className="flex-row justify-between gap-3"><AgText weight="semibold" className="flex-1">{row.title}</AgText>{row.syncStatus === 'pending' ? <AgText variant="caption" color="muted">{t('organic.pendingSync')}</AgText> : null}</View><AgText variant="caption" color="primary" className="mt-1">{t(`organic.practice.${row.type}`)}</AgText><AgText variant="caption" color="muted" className="mt-1">{new Date(row.occurredAt).toLocaleDateString()}</AgText>{row.notes ? <AgText variant="bodySmall" className="mt-2">{row.notes}</AgText> : null}</AgCard>)}</AgScreen>;
}
