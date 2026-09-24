import { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, Plus, X } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { AgBadge, AgButton, AgCard, AgEmptyState, AgErrorState, AgInput, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { captureFromCamera, pickFromGallery } from '@/features/disease/utils/pickDiseaseImage';
import { PRACTICE_TYPES } from '../constants';
import { useCreateOrganicPractice, useOrganicPractices, useUploadOrganicEvidence } from '../hooks/useOrganic';
import { useOrganicSync } from '../hooks/useOrganicSync';
import type { OrganicEvidenceInput, OrganicOutcomeStatus, OrganicPracticeType } from '../types';

const OUTCOME_STATUSES: OrganicOutcomeStatus[] = ['not_reported', 'improved', 'no_change', 'worse', 'unknown'];
const OUTCOME_BADGE_TONE: Record<OrganicOutcomeStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  not_reported: 'neutral', improved: 'success', no_change: 'neutral', worse: 'danger', unknown: 'neutral',
};

export function OrganicLogbookScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { colors } = useAppTheme();
  const query = useOrganicPractices(farmId); const create = useCreateOrganicPractice(farmId);
  const uploadEvidence = useUploadOrganicEvidence(farmId);
  useOrganicSync();
  const [adding, setAdding] = useState(false); const [type, setType] = useState<OrganicPracticeType>('amendment');
  const [title, setTitle] = useState(''); const [notes, setNotes] = useState('');
  const [quantity, setQuantity] = useState(''); const [unit, setUnit] = useState('');
  const [treatedArea, setTreatedArea] = useState(''); const [expense, setExpense] = useState('');
  const [outcomeStatus, setOutcomeStatus] = useState<OrganicOutcomeStatus>('not_reported');
  const [pendingEvidence, setPendingEvidence] = useState<OrganicEvidenceInput | null>(null);

  const reset = () => {
    setAdding(false); setTitle(''); setNotes(''); setQuantity(''); setUnit('');
    setTreatedArea(''); setExpense(''); setOutcomeStatus('not_reported'); setPendingEvidence(null);
  };

  const attachPhoto = () => {
    Alert.alert(t('organic.attachPhoto'), undefined, [
      { text: t('organic.camera'), onPress: async () => {
        const picked = await captureFromCamera({ base64: false });
        if (picked) uploadEvidence.mutate({ fileUri: picked.uri, mimeType: picked.mimeType }, {
          onSuccess: (attestation) => setPendingEvidence({ evidenceType: 'photo', uploadAttestationId: attestation.id, uploadReceipt: attestation.upload_receipt, retentionConsent: true }),
          onError: () => Alert.alert(t('organic.evidenceUploadError')),
        });
      } },
      { text: t('organic.gallery'), onPress: async () => {
        const picked = await pickFromGallery({ base64: false });
        if (picked) uploadEvidence.mutate({ fileUri: picked.uri, mimeType: picked.mimeType }, {
          onSuccess: (attestation) => setPendingEvidence({ evidenceType: 'photo', uploadAttestationId: attestation.id, uploadReceipt: attestation.upload_receipt, retentionConsent: true }),
          onError: () => Alert.alert(t('organic.evidenceUploadError')),
        });
      } },
      { text: t('common.cancel'), style: 'cancel' },
    ]);
  };

  const submit = () => {
    if (!title.trim()) return Alert.alert(t('organic.titleRequired'));
    if (Boolean(quantity.trim()) !== Boolean(unit.trim())) return Alert.alert(t('organic.quantityUnitRequiredTogether'));
    create.mutate({
      type, title: title.trim(), notes: notes.trim() || null, occurredAt: new Date().toISOString(),
      quantity: quantity.trim() ? Number(quantity) : null,
      unit: unit.trim() || null,
      treatedAreaHectares: treatedArea.trim() ? Number(treatedArea) : null,
      expenseAmountInr: expense.trim() ? Number(expense) : null,
      outcomeStatus,
      evidence: pendingEvidence ? [pendingEvidence] : [],
    }, { onSuccess: ({ offline }) => { reset(); Alert.alert(t(offline ? 'organic.savedOffline' : 'organic.practiceSaved')); } });
  };

  return <AgScreen scroll><View className="flex-row items-center gap-2"><AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} className="h-10 w-10 items-center justify-center"><ArrowLeft size={24} color={colors.text}/></AgPressable><AgText variant="headingM" weight="bold" className="flex-1">{t('organic.logbookTitle')}</AgText><AgPressable onPress={() => setAdding(!adding)} accessibilityRole="button" accessibilityLabel={t('organic.addPractice')}><Plus size={24} color={colors.primary}/></AgPressable></View>
  {adding ? <AgCard className="mt-4">
    <AgText weight="bold">{t('organic.addPractice')}</AgText>
    <View style={styles.practiceOptions}>{PRACTICE_TYPES.map((item) => <AgPressable key={item} onPress={() => setType(item)} accessibilityRole="radio" accessibilityState={{ checked: type === item }} style={[styles.practiceOption, { backgroundColor: type === item ? '#E8F4E7' : colors.surface, borderColor: type === item ? colors.primary : '#D8DDD9' }]}><AgText variant="caption" style={{ color: type === item ? '#14552D' : colors.text }}>{t(`organic.practice.${item}`)}</AgText></AgPressable>)}</View>
    <AgInput className="mt-4" label={t('organic.practiceTitle')} value={title} onChangeText={setTitle}/>
    <AgInput className="mt-3" label={t('organic.notes')} value={notes} onChangeText={setNotes} multiline/>
    <View className="mt-3 flex-row gap-3">
      <AgInput className="flex-1" label={t('organic.quantityLabel')} value={quantity} onChangeText={setQuantity} keyboardType="numeric"/>
      <AgInput className="flex-1" label={t('organic.unitLabel')} value={unit} onChangeText={setUnit}/>
    </View>
    <View className="mt-3 flex-row gap-3">
      <AgInput className="flex-1" label={t('organic.treatedAreaLabel')} value={treatedArea} onChangeText={setTreatedArea} keyboardType="numeric"/>
      <AgInput className="flex-1" label={t('organic.costLabel')} value={expense} onChangeText={setExpense} keyboardType="numeric"/>
    </View>
    <AgText variant="caption" color="muted" className="mt-3">{t('organic.outcomeLabel')}</AgText>
    <View style={styles.practiceOptions}>{OUTCOME_STATUSES.map((item) => <AgPressable key={item} onPress={() => setOutcomeStatus(item)} accessibilityRole="radio" accessibilityState={{ checked: outcomeStatus === item }} style={[styles.practiceOption, { backgroundColor: outcomeStatus === item ? '#E8F4E7' : colors.surface, borderColor: outcomeStatus === item ? colors.primary : '#D8DDD9' }]}><AgText variant="caption" style={{ color: outcomeStatus === item ? '#14552D' : colors.text }}>{t(`organic.outcomeStatus.${item}`)}</AgText></AgPressable>)}</View>
    {pendingEvidence ? <View className="mt-3 flex-row items-center gap-2"><AgText variant="bodySmall" color="primary">{t('organic.photoAttached')}</AgText><AgPressable onPress={() => setPendingEvidence(null)} accessibilityRole="button" accessibilityLabel={t('organic.removePhoto')}><X size={16} color={colors.textMuted}/></AgPressable></View>
      : <AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.attachPhoto')} loading={uploadEvidence.isPending} onPress={attachPhoto}/>}
    <AgButton className="mt-4" title={t('common.save')} loading={create.isPending} onPress={submit}/>
  </AgCard> : null}
  {query.isLoading ? <><AgSkeleton className="mt-4 h-24 w-full"/><AgSkeleton className="mt-3 h-24 w-full"/></> : query.isError ? <AgErrorState message={t('organic.loadError')} onRetry={() => void query.refetch()}/> : !query.data?.length ? <AgEmptyState title={t('organic.emptyTitle')} message={t('organic.emptyDescription')} actionLabel={t('organic.addPractice')} onAction={() => setAdding(true)}/> : query.data.map((row) => <AgCard key={row.id} className="mt-3">
    <View className="flex-row justify-between gap-3"><AgText weight="semibold" className="flex-1">{row.title}</AgText>{row.syncStatus === 'pending' ? <AgText variant="caption" color="muted">{t('organic.pendingSync')}</AgText> : null}</View>
    <AgText variant="caption" color="primary" className="mt-1">{t(`organic.practice.${row.type}`)}</AgText>
    <AgText variant="caption" color="muted" className="mt-1">{new Date(row.occurredAt).toLocaleDateString()}</AgText>
    {row.notes ? <AgText variant="bodySmall" className="mt-2">{row.notes}</AgText> : null}
    {row.quantity != null ? <AgText variant="caption" color="muted" className="mt-1">{t('organic.quantityValue', { quantity: row.quantity, unit: row.unit })}</AgText> : null}
    {row.treatedAreaHectares != null ? <AgText variant="caption" color="muted" className="mt-1">{t('organic.treatedAreaValue', { area: row.treatedAreaHectares })}</AgText> : null}
    {row.expenseAmountInr != null ? <AgText variant="caption" color="muted" className="mt-1">{t('organic.costValue', { amount: row.expenseAmountInr })}</AgText> : null}
    <View className="mt-2 flex-row flex-wrap gap-2">
      {row.outcomeStatus !== 'not_reported' ? <AgBadge label={t(`organic.outcomeStatus.${row.outcomeStatus}`)} tone={OUTCOME_BADGE_TONE[row.outcomeStatus]}/> : null}
      {row.evidence.length > 0 ? <AgBadge label={t('organic.evidenceCount', { count: row.evidence.length })} tone="neutral"/> : null}
    </View>
  </AgCard>)}</AgScreen>;
}

const styles = StyleSheet.create({
  practiceOptions: { marginTop: 12, flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  practiceOption: { borderWidth: 1, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 8 },
});
