import { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { AgBadge, AgButton, AgCard, AgErrorState, AgInput, AgPressable, AgScreen, AgSpinner, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useAnswerQuestion, useCommunityQuestion, useCommunityQuestions, useCreateQuestion, useReportContent } from './useCommunity';

export function CommunityScreen() {
  const { t } = useTranslation(); const { colors } = useAppTheme(); const [selected, setSelected] = useState<string | null>(null);
  const [title, setTitle] = useState(''); const [body, setBody] = useState(''); const [crop, setCrop] = useState(''); const [answer, setAnswer] = useState('');
  const list = useCommunityQuestions(); const detail = useCommunityQuestion(selected); const create = useCreateQuestion(); const reply = useAnswerQuestion(selected); const report = useReportContent();
  const fail = () => Alert.alert(t('community.error'));
  return <AgScreen scroll keyboardAvoiding contentContainerStyle={styles.content}>
    <AgBadge label={t('community.testMode')} tone="warning" />
    <AgText variant="headingL" weight="bold">{t('community.title')}</AgText>
    <AgText color="danger">{t('community.disclaimer')}</AgText>
    <AgCard style={styles.gap}><AgText variant="headingS" weight="bold">{t('community.ask')}</AgText><AgInput label={t('community.questionTitle')} value={title} onChangeText={setTitle} /><AgInput label={t('community.details')} value={body} onChangeText={setBody} multiline /><AgInput label={t('community.cropOptional')} value={crop} onChangeText={setCrop} /><AgButton title={t('community.post')} disabled={title.trim().length < 5 || body.trim().length < 10} loading={create.isPending} onPress={() => create.mutate({ title: title.trim(), body: body.trim(), crop: crop.trim() || undefined }, { onSuccess: () => { setTitle(''); setBody(''); setCrop(''); }, onError: fail })} /></AgCard>
    {list.isLoading ? <AgSpinner /> : null}{list.isError ? <AgErrorState message={t('community.loadFailed')} onRetry={() => void list.refetch()} /> : null}
    {list.data?.items.map((item) => <AgPressable key={item.id} onPress={() => setSelected(item.id)}><AgCard style={styles.gap}><AgText weight="bold">{item.title}</AgText><AgText numberOfLines={3}>{item.body}</AgText><AgText color="muted">{item.author_alias} · {t('community.answerCount', { count: item.answer_count })}</AgText></AgCard></AgPressable>)}
    {selected && detail.data ? <AgCard style={styles.gap}><AgText variant="headingS" weight="bold">{detail.data.title}</AgText><AgText>{detail.data.body}</AgText><AgText color="danger">{detail.data.disclaimer}</AgText><AgButton title={t('community.report')} variant="ghost" onPress={() => report.mutate({ type: 'question', id: detail.data!.id })} />
      {detail.data.answers.map((item) => <View key={item.id} style={[styles.answer, { borderColor: colors.border }]}><AgText>{item.body}</AgText><AgText color="muted">{item.author_alias} · {t('community.unverified')}</AgText><AgButton title={t('community.report')} variant="ghost" size="sm" onPress={() => report.mutate({ type: 'answer', id: item.id })} /></View>)}
      <AgInput label={t('community.yourAnswer')} value={answer} onChangeText={setAnswer} multiline /><AgButton title={t('community.reply')} disabled={answer.trim().length < 2} loading={reply.isPending} onPress={() => reply.mutate(answer.trim(), { onSuccess: () => setAnswer(''), onError: fail })} /><AgButton title={t('common.close')} variant="secondary" onPress={() => setSelected(null)} />
    </AgCard> : null}
  </AgScreen>;
}
const styles = StyleSheet.create({ content: { gap: 14, paddingBottom: 32 }, gap: { gap: 10 }, answer: { gap: 6, borderTopWidth: 1, paddingTop: 10 } });
