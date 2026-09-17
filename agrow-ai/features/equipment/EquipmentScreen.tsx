import { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { AgBadge, AgButton, AgCard, AgChip, AgDatePicker, AgErrorState, AgInput, AgScreen, AgSpinner, AgText } from '@/components/ui';
import { useSelectedFarm } from '@/features/weather';
import type { EquipmentListing, EquipmentType } from './equipmentApi';
import { useCreateEquipment, useDecideEquipment, useEquipment, useEquipmentRequests, useRequestEquipment } from './useEquipment';

const TYPES: EquipmentType[] = ['tractor', 'tiller', 'harvester', 'sprayer', 'pump', 'other'];
export function EquipmentScreen() {
  const { t } = useTranslation(); const farms = useSelectedFarm();
  const listings = useEquipment(); const requests = useEquipmentRequests();
  const create = useCreateEquipment(); const request = useRequestEquipment(); const decide = useDecideEquipment();
  const [name, setName] = useState(''); const [type, setType] = useState<EquipmentType>('tractor');
  const [selected, setSelected] = useState<EquipmentListing | null>(null);
  const [start, setStart] = useState(''); const [end, setEnd] = useState('');
  const fail = () => Alert.alert(t('equipment.error'));
  return <AgScreen scroll keyboardAvoiding contentContainerStyle={styles.content}>
    <AgBadge label={t('equipment.testMode')} tone="warning" />
    <AgText variant="headingL" weight="bold">{t('equipment.title')}</AgText>
    <AgText color="muted">{t('equipment.noPayments')}</AgText>
    <AgCard style={styles.gap}>
      <AgText variant="headingS" weight="bold">{t('equipment.addListing')}</AgText>
      <AgInput label={t('equipment.name')} value={name} onChangeText={setName} />
      <View style={styles.chips}>{TYPES.map((item) => <AgChip key={item} label={t(`equipment.types.${item}`)} selected={type === item} onPress={() => setType(item)} />)}</View>
      <AgButton title={t('equipment.publish')} disabled={name.trim().length < 2} loading={create.isPending} onPress={() => create.mutate({ name: name.trim(), equipment_type: type }, { onSuccess: () => setName(''), onError: fail })} />
    </AgCard>
    <AgText variant="headingS" weight="bold">{t('equipment.available')}</AgText>
    {listings.isLoading ? <AgSpinner /> : null}
    {listings.isError ? <AgErrorState message={t('equipment.loadFailed')} onRetry={() => void listings.refetch()} /> : null}
    {listings.data?.length === 0 ? <AgText color="muted">{t('equipment.empty')}</AgText> : null}
    {listings.data?.map((item) => <AgCard key={item.id} style={styles.gap}>
      <AgText weight="bold">{item.name}</AgText><AgText color="muted">{t(`equipment.types.${item.equipment_type}`)}</AgText>
      <AgButton title={t('equipment.request')} variant="secondary" onPress={() => setSelected(item)} />
    </AgCard>)}
    {selected ? <AgCard style={styles.gap}>
      <AgText weight="bold">{t('equipment.requestFor', { name: selected.name })}</AgText>
      <AgDatePicker label={t('equipment.start')} placeholder={t('equipment.selectDate')} value={start} onChange={setStart} />
      <AgDatePicker label={t('equipment.end')} placeholder={t('equipment.selectDate')} value={end} onChange={setEnd} />
      <AgButton title={t('equipment.send')} disabled={!farms.selected?.id || !start || !end} loading={request.isPending} onPress={() => request.mutate({ listingId: selected.id, farm_id: farms.selected!.id, start_date: start, end_date: end }, { onSuccess: () => { setSelected(null); setStart(''); setEnd(''); }, onError: fail })} />
    </AgCard> : null}
    <AgText variant="headingS" weight="bold">{t('equipment.myRequests')}</AgText>
    {requests.isLoading ? <AgSpinner /> : null}
    {requests.isError ? <AgErrorState message={t('equipment.requestsFailed')} onRetry={() => void requests.refetch()} /> : null}
    {requests.data?.length === 0 ? <AgText color="muted">{t('equipment.noRequests')}</AgText> : null}
    {requests.data?.map((item) => <AgCard key={item.id} style={styles.gap}><AgText weight="bold">{item.equipment_name}</AgText><AgText>{t(`equipment.status.${item.status}`)}</AgText>{item.can_decide ? <View style={styles.actions}><AgButton title={t('equipment.approve')} fullWidth={false} onPress={() => decide.mutate({ requestId: item.id, decision: 'approved' })} /><AgButton title={t('equipment.reject')} variant="danger" fullWidth={false} onPress={() => decide.mutate({ requestId: item.id, decision: 'rejected' })} /></View> : null}</AgCard>)}
  </AgScreen>;
}
const styles = StyleSheet.create({ content: { gap: 14, paddingBottom: 32 }, gap: { gap: 12 }, chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, actions: { flexDirection: 'row', gap: 8 } });
