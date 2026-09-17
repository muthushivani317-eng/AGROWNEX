import { useState } from 'react';
import { Alert, Share, StyleSheet, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import { useTranslation } from 'react-i18next';
import { AgBadge, AgButton, AgCard, AgChip, AgDatePicker, AgErrorState, AgInput, AgScreen, AgSpinner, AgText } from '@/components/ui';
import { safePublicShareUrl, type TraceEventType } from '../traceabilityApi';
import { useAddTraceEvent, useCreatePublicTraceabilityShare, useInitializeTraceability, useRevokePublicTraceabilityShare, useTraceability } from '../hooks/useTraceability';

const TYPES: TraceEventType[] = ['sowing_recorded', 'input_applied', 'harvested', 'graded', 'packed', 'stored', 'transported', 'handover'];
export function ProduceTraceabilityScreen({ offerId }: { offerId: string }) {
  const { t } = useTranslation(); const trace = useTraceability(offerId); const init = useInitializeTraceability(offerId); const add = useAddTraceEvent(offerId);
  const createShare = useCreatePublicTraceabilityShare(offerId); const revokeShare = useRevokePublicTraceabilityShare(offerId);
  const [type, setType] = useState<TraceEventType>('harvested'); const [date, setDate] = useState(''); const [location, setLocation] = useState(''); const [notes, setNotes] = useState('');
  const [shareClassification, setShareClassification] = useState(true); const [shareEvents, setShareEvents] = useState(false); const [shareUrl, setShareUrl] = useState<string | null>(null);
  const fail = () => Alert.alert(t('traceability.error'));
  return <AgScreen scroll keyboardAvoiding contentContainerStyle={styles.content}>
    <AgBadge label={t('traceability.testMode')} tone="warning" />
    <AgText variant="headingL" weight="bold">{t('traceability.title')}</AgText>
    <AgText color="danger">{t('traceability.notCertificate')}</AgText>
    {trace.isLoading ? <AgSpinner /> : null}
    {trace.isError ? <AgErrorState message={t('traceability.loadFailed')} onRetry={() => void trace.refetch()} /> : null}
    {!trace.data && !trace.isLoading ? <AgButton title={t('traceability.start')} loading={init.isPending} onPress={() => init.mutate(undefined, { onError: fail })} /> : null}
    {trace.data ? <>
      {trace.data.organic_classification ? <AgCard style={styles.gap}><AgText color="muted">{t('organic.produceClassification')}</AgText><AgBadge label={t(`organic.produceClass.${trace.data.organic_classification}`)} tone={trace.data.organic_claim_verification === 'verified' ? 'success' : 'neutral'} /><AgText variant="caption" color="muted">{t(`organic.claimVerification.${trace.data.organic_claim_verification ?? 'not_claimed'}`)}</AgText></AgCard> : null}
      <AgCard style={styles.gap}><AgText variant="headingS" weight="bold">{t('organic.shareTraceability')}</AgText><AgText variant="caption" color="muted">{t('organic.privacyNotice')}</AgText><View style={styles.chips}><AgChip label={t('organic.shareClassification')} selected={shareClassification} onPress={() => setShareClassification((value) => !value)}/><AgChip label={t('traceability.timeline')} selected={shareEvents} onPress={() => setShareEvents((value) => !value)}/></View>{safePublicShareUrl(shareUrl) ? <View accessible accessibilityLabel={t('organic.traceQr')} style={styles.qr}><QRCode value={shareUrl!} size={180}/></View> : null}{safePublicShareUrl(shareUrl) ? <><AgButton title={t('organic.share')} onPress={() => void Share.share({ message: shareUrl! })}/><AgButton variant="danger" title={t('organic.revokeShare')} loading={revokeShare.isPending} onPress={() => revokeShare.mutate(undefined, { onSuccess: () => setShareUrl(null), onError: fail })}/></> : <AgButton title={t('organic.createShare')} disabled={!shareClassification && !shareEvents} loading={createShare.isPending} onPress={() => createShare.mutate({ classification: shareClassification, events: shareEvents }, { onSuccess: (result) => { const url = String(result.share_url); setShareUrl(url); void Share.share({ message: url }); }, onError: fail })}/>} {createShare.isError || revokeShare.isError ? <AgText accessibilityRole="alert" color="danger">{t('organic.shareError')}</AgText> : null}</AgCard>
      <AgCard style={styles.gap}><AgText color="muted">{t('traceability.batch')}</AgText><AgText weight="bold">{trace.data.batch_code}</AgText></AgCard>
      <AgCard style={styles.gap}>
        <AgText variant="headingS" weight="bold">{t('traceability.addEvent')}</AgText>
        <View style={styles.chips}>{TYPES.map((item) => <AgChip key={item} label={t(`traceability.types.${item}`)} selected={type === item} onPress={() => setType(item)} />)}</View>
        <AgDatePicker label={t('traceability.date')} placeholder={t('traceability.selectDate')} value={date} onChange={setDate} />
        <AgInput label={t('traceability.location')} value={location} onChangeText={setLocation} />
        <AgInput label={t('traceability.notes')} value={notes} onChangeText={setNotes} multiline />
        <AgButton title={t('traceability.record')} disabled={!date} loading={add.isPending} onPress={() => add.mutate({ event_type: type, occurred_at: `${date}T12:00:00Z`, location_text: location || undefined, notes: notes || undefined }, { onSuccess: () => { setDate(''); setLocation(''); setNotes(''); }, onError: fail })} />
      </AgCard>
      <AgText variant="headingS" weight="bold">{t('traceability.timeline')}</AgText>
      {trace.data.events.length === 0 ? <AgText color="muted">{t('traceability.empty')}</AgText> : null}
      {trace.data.events.map((event) => <AgCard key={event.id} style={styles.gap}><AgText weight="bold">{t(`traceability.types.${event.event_type}`)}</AgText><AgText color="muted">{event.occurred_at.slice(0, 10)}{event.location_text ? ` · ${event.location_text}` : ''}</AgText>{event.notes ? <AgText>{event.notes}</AgText> : null}<AgText variant="caption" color="muted">{t('traceability.farmerDeclared')}</AgText></AgCard>)}
    </> : null}
  </AgScreen>;
}
const styles = StyleSheet.create({ content: { gap: 14, paddingBottom: 32 }, gap: { gap: 10 }, chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, qr: { width: 180, height: 180, alignSelf: 'center' } });
