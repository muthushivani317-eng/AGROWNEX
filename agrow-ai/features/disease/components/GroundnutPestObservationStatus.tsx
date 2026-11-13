import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgBadge, AgCard, AgText } from '@/components/ui';

import type { GroundnutPestObservation } from '../types';

const feedbackText: Record<NonNullable<GroundnutPestObservation['feedback']>, string> = {
  monitor_field_conditions: 'Continue monitoring field conditions.',
  submit_clearer_photo: 'Submit a clearer photograph for another review.',
  seek_in_person_field_assessment: 'Arrange an in-person field assessment.',
  no_actionable_conclusion_from_photo: 'No actionable conclusion can be made from this photograph.',
};

export function GroundnutPestObservationStatus({
  observation,
  compact = false,
}: {
  observation: GroundnutPestObservation;
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const reviewed = observation.reviewStatus === 'reviewed';
  const body = (
    <View style={{ gap: 6 }} testID="groundnut-pest-observation-status">
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <AgText weight="semibold">
          {t('disease.pestObservation.title', {
            defaultValue: 'Groundnut pest-damage observation',
          })}
        </AgText>
        <AgBadge
          label={t(
            reviewed
              ? 'disease.pestObservation.reviewed'
              : 'disease.pestObservation.pending',
            { defaultValue: reviewed ? 'Reviewed' : 'Pending expert review' },
          )}
          tone={reviewed ? 'success' : 'warning'}
        />
      </View>
      {!compact ? (
        <>
          <AgText variant="bodySmall" color="muted">
            {t('disease.pestObservation.extent', { defaultValue: 'Reported extent' })}:{' '}
            {observation.damageExtent} ·{' '}
            {t('disease.pestObservation.spread', { defaultValue: 'Reported spread' })}:{' '}
            {observation.spreadSpeed}
          </AgText>
          {reviewed && observation.feedback ? (
            <AgText variant="bodySmall">
              {t('disease.pestObservation.feedback', { defaultValue: 'KVK feedback' })}:{' '}
              {feedbackText[observation.feedback]}
            </AgText>
          ) : (
            <AgText variant="bodySmall" color="muted">
              {t('disease.pestObservation.pendingBody', {
                defaultValue: 'Your consented photograph is waiting for KVK review.',
              })}
            </AgText>
          )}
          <AgText variant="caption" color="muted">
            {t('disease.pestObservation.noDiagnosis', {
              defaultValue: 'This observation and feedback do not identify a pest or confirm a diagnosis.',
            })}
          </AgText>
        </>
      ) : null}
    </View>
  );
  return compact ? body : <AgCard style={{ marginTop: 16 }}>{body}</AgCard>;
}
