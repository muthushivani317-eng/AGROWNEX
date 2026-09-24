import { useEffect, useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, Check } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import {
  AgBadge,
  AgButton,
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgInput,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { PGS_CHECKLIST_KEYS, type PgsChecklistKey } from '../services/organicPgsApi';
import {
  useOrganicPeerAssignments,
  useOrganicPgsStatus,
  useSubmitPeerAppraisal,
  useUpdatePgsChecklist,
} from '../hooks/useOrganicPgs';

/**
 * Certification Companion (blueprint Phase 6). Mobile UI on top of
 * organic_mvp's existing PGS backend -- no backend changes, same "read the
 * real contract, don't invent one" approach as Phases 3-5.
 *
 * A farmer can only ever submit checklist/evidence input here. The verified
 * state transition, certificate id, issuing authority and validity dates
 * are set exclusively by an agriculture officer via the admin-only
 * POST /admin/organic-mvp/farms/{farm_id}/pgs/review (see
 * backend/app/modules/organic_mvp/router.py::review_pgs). This screen
 * cannot write any of those fields -- mirrors the blueprint's blocking
 * checklist ("no self-assigned PGS labels", "pre-certification never
 * displays as certified").
 *
 * Peer appraisal findings are a free-form dict server-side
 * (AppraisalCompleteIn.findings: dict) -- no structured question set
 * exists in the backend yet, so this captures a single free-text note
 * ({ note: string }) rather than inventing a multi-field form. A real
 * appraisal question set is a product/agronomist decision, same category
 * as the still-open readiness/task-template content gaps from Phases 1-2.
 */
export function OrganicCertificationScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();

  const statusQuery = useOrganicPgsStatus(farmId);
  const updateChecklist = useUpdatePgsChecklist(farmId);
  const peerAssignments = useOrganicPeerAssignments();
  const submitAppraisal = useSubmitPeerAppraisal();

  const [partialConversion, setPartialConversion] = useState(false);
  const [checklist, setChecklist] = useState<Partial<Record<PgsChecklistKey, boolean>>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    if (statusQuery.data) {
      setPartialConversion(statusQuery.data.partial_conversion);
      setChecklist(statusQuery.data.checklist ?? {});
    }
  }, [statusQuery.data]);

  const toggleChecklistItem = (key: PgsChecklistKey) =>
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));

  const saveChecklist = () => {
    updateChecklist.mutate(
      { partial_conversion: partialConversion, checklist },
      {
        onSuccess: () => Alert.alert(t('organic.checklistSaved')),
        onError: () => Alert.alert(t('organic.checklistSaveError')),
      },
    );
  };

  const submitFindings = (appraisalId: string) => {
    const note = notes[appraisalId]?.trim();
    if (!note) return;
    submitAppraisal.mutate(
      { appraisalId, note },
      {
        onSuccess: () => {
          Alert.alert(t('organic.peerReviewSubmitted'));
          setNotes((prev) => ({ ...prev, [appraisalId]: '' }));
        },
        onError: () => Alert.alert(t('organic.peerReviewSubmitError')),
      },
    );
  };

  return (
    <AgScreen scroll>
      <View className="flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold">
          {t('organic.certificationTitle')}
        </AgText>
      </View>

      {statusQuery.isLoading ? (
        <AgSkeleton className="mt-4 h-40 w-full" />
      ) : statusQuery.isError ? (
        <AgErrorState
          message={t('organic.certificationLoadError')}
          onRetry={() => void statusQuery.refetch()}
        />
      ) : statusQuery.data ? (
        <>
          <AgCard className="mt-4">
            <View className="flex-row items-center gap-2">
              <AgText weight="bold">{t(`organic.pgsState.${statusQuery.data.state}`)}</AgText>
            </View>
            {statusQuery.data.certificate_id ? (
              <View className="mt-2">
                <AgBadge label={t('organic.certificateVerified')} tone="success" />
                <AgText variant="bodySmall" color="muted" className="mt-2">
                  {t('organic.certificateIdLabel', { id: statusQuery.data.certificate_id })}
                </AgText>
                {statusQuery.data.issuing_authority ? (
                  <AgText variant="bodySmall" color="muted">
                    {t('organic.issuingAuthorityLabel', {
                      authority: statusQuery.data.issuing_authority,
                    })}
                  </AgText>
                ) : null}
                {statusQuery.data.valid_to ? (
                  <AgText variant="bodySmall" color="muted">
                    {t('organic.validToLabel', { date: statusQuery.data.valid_to })}
                  </AgText>
                ) : null}
              </View>
            ) : null}
            {statusQuery.data.notice ? (
              <AgText variant="bodySmall" color="muted" className="mt-2">
                {statusQuery.data.notice}
              </AgText>
            ) : null}
          </AgCard>

          <AgCard className="mt-3">
            <AgText weight="bold">{t('organic.checklistTitle')}</AgText>
            <AgText variant="caption" color="muted" className="mt-1">
              {t('organic.checklistHint')}
            </AgText>
            <AgPressable
              onPress={() => setPartialConversion(!partialConversion)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: partialConversion }}
              className="mt-3 flex-row items-center gap-2"
            >
              <View
                style={[
                  styles.checkbox,
                  {
                    borderColor: colors.primary,
                    backgroundColor: partialConversion ? colors.primary : 'transparent',
                  },
                ]}
              >
                {partialConversion ? <Check size={14} color="#FFFFFF" /> : null}
              </View>
              <AgText variant="bodySmall" className="flex-1">
                {t('organic.partialConversionLabel')}
              </AgText>
            </AgPressable>
            {PGS_CHECKLIST_KEYS.map((key) => (
              <AgPressable
                key={key}
                onPress={() => toggleChecklistItem(key)}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: Boolean(checklist[key]) }}
                className="mt-3 flex-row items-center gap-2"
              >
                <View
                  style={[
                    styles.checkbox,
                    {
                      borderColor: colors.primary,
                      backgroundColor: checklist[key] ? colors.primary : 'transparent',
                    },
                  ]}
                >
                  {checklist[key] ? <Check size={14} color="#FFFFFF" /> : null}
                </View>
                <AgText variant="bodySmall" className="flex-1">
                  {t(`organic.checklistItem.${key}`)}
                </AgText>
              </AgPressable>
            ))}
            <AgButton
              className="mt-4"
              size="sm"
              title={t('organic.saveChecklist')}
              onPress={saveChecklist}
              loading={updateChecklist.isPending}
            />
          </AgCard>

          <AgCard className="mt-3">
            <AgText weight="bold">{t('organic.peerReviewsTitle')}</AgText>
            {peerAssignments.isLoading ? (
              <AgSkeleton className="mt-2 h-16 w-full" />
            ) : (peerAssignments.data ?? []).length === 0 ? (
              <View className="mt-2">
                <AgEmptyState title={t('organic.peerReviewEmpty')} />
              </View>
            ) : (
              (peerAssignments.data ?? []).map((assignment) => (
                <View key={assignment.id} className="mt-3 border-t border-neutral-200 pt-3">
                  <View className="flex-row items-center gap-2">
                    <AgText weight="bold" className="flex-1">
                      {assignment.farm_name ?? assignment.farm_id ?? assignment.id}
                    </AgText>
                    <AgBadge
                      label={t(`organic.peerReviewStatus.${assignment.status}`)}
                      tone={assignment.status === 'completed' ? 'success' : 'neutral'}
                    />
                  </View>
                  <AgText variant="caption" color="muted" className="mt-1">
                    {t('organic.peerReviewScheduledOn', { date: assignment.scheduled_on })}
                  </AgText>
                  {assignment.status === 'scheduled' ? (
                    <>
                      <AgInput
                        className="mt-2"
                        multiline
                        placeholder={t('organic.peerReviewFindingsLabel')}
                        value={notes[assignment.id] ?? ''}
                        onChangeText={(value) =>
                          setNotes((prev) => ({ ...prev, [assignment.id]: value }))
                        }
                      />
                      <AgButton
                        className="mt-2"
                        size="sm"
                        variant="secondary"
                        title={t('organic.peerReviewSubmit')}
                        onPress={() => submitFindings(assignment.id)}
                        loading={submitAppraisal.isPending}
                      />
                    </>
                  ) : null}
                </View>
              ))
            )}
          </AgCard>
        </>
      ) : null}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 4,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
