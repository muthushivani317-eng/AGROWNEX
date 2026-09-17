import { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgBadge, AgButton, AgCard, AgChip, AgErrorState, AgInput, AgScreen, AgSpinner, AgText } from '@/components/ui';
import { internalTestFlags } from '@/config/internalTestFlags';

import { useAddFarmTeamMember, useFarmTeam, useRemoveFarmTeamMember } from '../hooks/useFarmTeam';
import type { FarmTeamRole } from '../services/farmTeamApi';

const ROLES: FarmTeamRole[] = ['manager', 'field_worker', 'agronomist', 'observer'];

export function FarmTeamScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const [phone, setPhone] = useState('+91');
  const [role, setRole] = useState<FarmTeamRole>('field_worker');
  const team = useFarmTeam(farmId);
  const add = useAddFarmTeamMember(farmId);
  const remove = useRemoveFarmTeamMember(farmId);

  if (!internalTestFlags.internalFeatureTesting) {
    return <AgScreen><AgText>{t('farmTeam.controlledOnly')}</AgText></AgScreen>;
  }
  const submit = () => add.mutate(
    { phone_number: phone.replace(/\s|-/g, ''), role },
    { onSuccess: () => setPhone('+91'), onError: () => Alert.alert(t('farmTeam.addFailed')) },
  );

  return (
    <AgScreen scroll keyboardAvoiding contentContainerStyle={styles.content}>
      <AgBadge label={t('farmTeam.testMode')} tone="warning" />
      <AgText variant="headingL" weight="bold">{t('farmTeam.title')}</AgText>
      <AgText color="muted">{t('farmTeam.rosterOnly')}</AgText>
      <AgCard style={styles.form}>
        <AgInput
          label={t('farmTeam.phone')}
          placeholder={t('farmTeam.phonePlaceholder')}
          keyboardType="phone-pad"
          autoComplete="tel"
          value={phone}
          onChangeText={setPhone}
          required
        />
        <AgText variant="label" weight="semibold">{t('farmTeam.role')}</AgText>
        <View style={styles.roles}>
          {ROLES.map((item) => (
            <AgChip
              key={item}
              label={t(`farmTeam.roles.${item}`)}
              selected={role === item}
              onPress={() => setRole(item)}
            />
          ))}
        </View>
        <AgButton title={t('farmTeam.add')} onPress={submit} loading={add.isPending} disabled={phone.length < 11} />
      </AgCard>
      <AgText variant="headingS" weight="bold">{t('farmTeam.members')}</AgText>
      {team.isLoading ? <AgSpinner /> : null}
      {team.isError ? <AgErrorState message={t('farmTeam.loadFailed')} onRetry={() => void team.refetch()} /> : null}
      {team.data?.length === 0 ? <AgText color="muted">{t('farmTeam.empty')}</AgText> : null}
      {team.data?.map((member) => (
        <AgCard key={member.id} style={styles.member}>
          <View style={styles.memberCopy}>
            <AgText weight="semibold">{member.phone_number}</AgText>
            <AgText color="muted">{t(`farmTeam.roles.${member.role}`)}</AgText>
          </View>
          <AgButton
            title={t('farmTeam.remove')}
            variant="danger"
            size="sm"
            fullWidth={false}
            onPress={() => remove.mutate(member.id)}
            disabled={remove.isPending}
          />
        </AgCard>
      ))}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 14, paddingBottom: 32 },
  form: { gap: 14 },
  roles: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  member: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  memberCopy: { flex: 1, gap: 3 },
});
