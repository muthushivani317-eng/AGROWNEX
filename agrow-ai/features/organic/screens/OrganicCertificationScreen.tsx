import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  ArrowRight,
  Award,
  CalendarDays,
  Check,
  ClipboardCheck,
  FileCheck2,
  FileSearch,
  Leaf,
  ShieldCheck,
  Sprout,
  Users,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";

import {
  AgErrorState,
  AgInput,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";

import {
  PGS_CHECKLIST_KEYS,
  type PgsChecklistKey,
} from "../services/organicPgsApi";
import {
  useOrganicPeerAssignments,
  useOrganicPgsStatus,
  useSubmitPeerAppraisal,
  useUpdatePgsChecklist,
} from "../hooks/useOrganicPgs";

const C = {
  bg: "#F6FAF2",
  card: "#FFFFFF",
  green: "#116B36",
  dark: "#093F2E",
  soft: "#EAF6E8",
  text: "#102F2C",
  muted: "#64706D",
  border: "#DCE8DD",
  orange: "#E97710",
  orangeSoft: "#FFF1DA",
} as const;

const CHECKLIST_VISUALS = {
  whole_holding_reviewed: {
    icon: FileSearch,
    color: C.green,
    background: C.soft,
  },
  conversion_plan_recorded: {
    icon: CalendarDays,
    color: C.orange,
    background: C.orangeSoft,
  },
  conversion_completed: { icon: Leaf, color: C.green, background: C.soft },
  no_major_non_compliance: {
    icon: ShieldCheck,
    color: C.orange,
    background: C.orangeSoft,
  },
} satisfies Record<
  PgsChecklistKey,
  { icon: typeof FileSearch; color: string; background: string }
>;

function ChecklistRow({
  checked,
  label,
  onPress,
  icon: Icon,
  iconColor,
  iconBackground,
}: {
  checked: boolean;
  label: string;
  onPress: () => void;
  icon: typeof FileSearch;
  iconColor: string;
  iconBackground: string;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.78}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      accessibilityLabel={label}
      style={styles.checklistRow}
    >
      <View style={[styles.checkbox, checked && styles.checkboxChecked]}>
        {checked ? <Check size={20} color="#FFFFFF" strokeWidth={3} /> : null}
      </View>
      <AgText style={styles.checklistLabel}>{label}</AgText>
      <View style={[styles.rowIcon, { backgroundColor: iconBackground }]}>
        <Icon size={27} color={iconColor} strokeWidth={2.1} />
      </View>
    </TouchableOpacity>
  );
}

/** Farmers submit evidence here; verified certificate fields remain officer-controlled. */
export function OrganicCertificationScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const statusQuery = useOrganicPgsStatus(farmId);
  const updateChecklist = useUpdatePgsChecklist(farmId);
  const peerAssignments = useOrganicPeerAssignments();
  const submitAppraisal = useSubmitPeerAppraisal();
  const [partialConversion, setPartialConversion] = useState(false);
  const [checklist, setChecklist] = useState<
    Partial<Record<PgsChecklistKey, boolean>>
  >({});
  const [notes, setNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    if (statusQuery.data) {
      setPartialConversion(statusQuery.data.partial_conversion);
      setChecklist(statusQuery.data.checklist ?? {});
    }
  }, [statusQuery.data]);

  const saveChecklist = () => {
    updateChecklist.mutate(
      { partial_conversion: partialConversion, checklist },
      {
        onSuccess: () => Alert.alert(t("organic.checklistSaved")),
        onError: () => Alert.alert(t("organic.checklistSaveError")),
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
          Alert.alert(t("organic.peerReviewSubmitted"));
          setNotes((prev) => ({ ...prev, [appraisalId]: "" }));
        },
        onError: () => Alert.alert(t("organic.peerReviewSubmitError")),
      },
    );
  };

  return (
    <AgScreen
      scroll
      padded={false}
      backgroundColor={C.bg}
      contentContainerStyle={styles.screen}
    >
      <View style={styles.hero}>
        <TouchableOpacity
          onPress={() => router.back()}
          activeOpacity={0.75}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          style={styles.backButton}
        >
          <ArrowLeft size={27} color={C.dark} strokeWidth={2.4} />
        </TouchableOpacity>

        <View style={styles.heroContent}>
          <View style={styles.heroCopy}>
            <AgText weight="bold" style={styles.heroTitle}>
              {t("organic.certificationTitle")}
            </AgText>
            <AgText style={styles.heroSubtitle}>
              {t("organic.certificationDashboardHint")}
            </AgText>
          </View>
          <View
            style={styles.heroArtwork}
            accessibilityElementsHidden
            importantForAccessibility="no-hide-descendants"
          >
            <View style={styles.heroSun} />
            <View style={styles.heroLeaf}>
              <Leaf size={39} color="#63A93B" strokeWidth={2} />
            </View>
            <View style={styles.certificatePaper}>
              <View style={styles.paperLine} />
              <View style={styles.paperLine} />
              <View style={[styles.paperLine, styles.paperLineShort]} />
              <FileCheck2 size={35} color={C.green} strokeWidth={1.9} />
            </View>
            <View style={styles.heroAward}>
              <Award size={38} color="#FFFFFF" strokeWidth={1.9} />
            </View>
          </View>
        </View>
      </View>

      {statusQuery.isLoading ? (
        <View style={styles.pagePadding}>
          <AgSkeleton style={styles.statusSkeleton} />
          <AgSkeleton style={styles.checklistSkeleton} />
        </View>
      ) : statusQuery.isError ? (
        <View style={[styles.card, styles.errorCard]}>
          <AgErrorState
            light
            message={t("organic.certificationLoadError")}
            onRetry={() => void statusQuery.refetch()}
          />
        </View>
      ) : statusQuery.data ? (
        <View style={styles.pagePadding}>
          <View style={styles.card}>
            <View style={styles.statusRow}>
              <View style={styles.roundIcon}>
                <FileCheck2 size={31} color={C.green} strokeWidth={2.1} />
              </View>
              <View style={styles.statusCopy}>
                <AgText weight="bold" style={styles.cardTitle}>
                  {t(`organic.pgsState.${statusQuery.data.state}`)}
                </AgText>
                {statusQuery.data.notice ? (
                  <AgText style={styles.description}>
                    {statusQuery.data.notice}
                  </AgText>
                ) : null}
                <View
                  style={[
                    styles.statusPill,
                    statusQuery.data.certificate_id
                      ? styles.verifiedPill
                      : styles.pendingPill,
                  ]}
                >
                  <AgText
                    weight="semibold"
                    style={[
                      styles.pillText,
                      {
                        color: statusQuery.data.certificate_id
                          ? C.green
                          : C.orange,
                      },
                    ]}
                  >
                    {statusQuery.data.certificate_id
                      ? t("organic.certificateVerified")
                      : t("organic.notCertifiedYet")}
                  </AgText>
                </View>
                {statusQuery.data.certificate_id ? (
                  <View style={styles.certificateMeta}>
                    <AgText style={styles.metaText}>
                      {t("organic.certificateIdLabel", {
                        id: statusQuery.data.certificate_id,
                      })}
                    </AgText>
                    {statusQuery.data.issuing_authority ? (
                      <AgText style={styles.metaText}>
                        {t("organic.issuingAuthorityLabel", {
                          authority: statusQuery.data.issuing_authority,
                        })}
                      </AgText>
                    ) : null}
                    {statusQuery.data.valid_to ? (
                      <AgText style={styles.metaText}>
                        {t("organic.validToLabel", {
                          date: statusQuery.data.valid_to,
                        })}
                      </AgText>
                    ) : null}
                  </View>
                ) : null}
              </View>
            </View>
          </View>

          <View style={[styles.card, styles.sectionCard]}>
            <View style={styles.sectionHeader}>
              <View style={styles.roundIcon}>
                <ClipboardCheck size={31} color={C.green} strokeWidth={2.2} />
              </View>
              <View style={styles.sectionCopy}>
                <AgText weight="bold" style={styles.sectionTitle}>
                  {t("organic.checklistTitle")}
                </AgText>
                <AgText style={styles.description}>
                  {t("organic.checklistHint")}
                </AgText>
              </View>
            </View>

            <View style={styles.checklistRows}>
              <ChecklistRow
                checked={partialConversion}
                label={t("organic.partialConversionLabel")}
                onPress={() => setPartialConversion((current) => !current)}
                icon={Sprout}
                iconColor={C.orange}
                iconBackground={C.orangeSoft}
              />
              {PGS_CHECKLIST_KEYS.map((key) => {
                const visual = CHECKLIST_VISUALS[key];
                return (
                  <ChecklistRow
                    key={key}
                    checked={Boolean(checklist[key])}
                    label={t(`organic.checklistItem.${key}`)}
                    onPress={() =>
                      setChecklist((current) => ({
                        ...current,
                        [key]: !current[key],
                      }))
                    }
                    icon={visual.icon}
                    iconColor={visual.color}
                    iconBackground={visual.background}
                  />
                );
              })}
            </View>

            <TouchableOpacity
              onPress={saveChecklist}
              activeOpacity={0.82}
              disabled={updateChecklist.isPending}
              accessibilityRole="button"
              accessibilityState={{ disabled: updateChecklist.isPending }}
              style={[
                styles.saveButton,
                updateChecklist.isPending && styles.disabled,
              ]}
            >
              {updateChecklist.isPending ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <>
                  <AgText weight="bold" style={styles.saveText}>
                    {t("organic.saveChecklist")}
                  </AgText>
                  <ArrowRight size={25} color="#FFFFFF" strokeWidth={2.4} />
                </>
              )}
            </TouchableOpacity>
          </View>

          <View style={[styles.card, styles.peerCard]}>
            <View style={styles.sectionHeader}>
              <View style={styles.roundIcon}>
                <Users size={30} color={C.green} strokeWidth={2.2} />
              </View>
              <AgText
                weight="bold"
                style={[styles.sectionTitle, styles.peerTitle]}
              >
                {t("organic.peerReviewsTitle")}
              </AgText>
            </View>

            {peerAssignments.isLoading ? (
              <AgSkeleton style={styles.peerSkeleton} />
            ) : (peerAssignments.data ?? []).length === 0 ? (
              <View style={styles.emptyState}>
                <View
                  style={styles.emptyArt}
                  accessibilityElementsHidden
                  importantForAccessibility="no-hide-descendants"
                >
                  <View style={styles.emptyCloudLeft} />
                  <View style={styles.emptyCloudRight} />
                  <View style={styles.emptyClipboard}>
                    <ClipboardCheck
                      size={47}
                      color="#4A9B52"
                      strokeWidth={1.8}
                    />
                  </View>
                  <Leaf
                    size={31}
                    color="#72B74C"
                    style={styles.emptyLeafLeft}
                  />
                  <Leaf
                    size={27}
                    color="#3C9347"
                    style={styles.emptyLeafRight}
                  />
                </View>
                <AgText weight="bold" style={styles.emptyTitle}>
                  {t("organic.peerReviewEmpty")}
                </AgText>
                <AgText style={styles.emptyDescription}>
                  {t("organic.peerReviewEmptyHint")}
                </AgText>
              </View>
            ) : (
              <View style={styles.assignments}>
                {(peerAssignments.data ?? []).map((assignment) => (
                  <View key={assignment.id} style={styles.assignmentCard}>
                    <View style={styles.assignmentHeading}>
                      <AgText weight="bold" style={styles.assignmentTitle}>
                        {assignment.farm_name ??
                          assignment.farm_id ??
                          assignment.id}
                      </AgText>
                      <View
                        style={[
                          styles.assignmentStatus,
                          assignment.status === "completed" &&
                            styles.assignmentComplete,
                        ]}
                      >
                        <AgText style={styles.assignmentStatusText}>
                          {t(`organic.peerReviewStatus.${assignment.status}`)}
                        </AgText>
                      </View>
                    </View>
                    <AgText style={styles.scheduleText}>
                      {t("organic.peerReviewScheduledOn", {
                        date: assignment.scheduled_on,
                      })}
                    </AgText>
                    {assignment.status === "scheduled" ? (
                      <>
                        <View style={styles.inputWrapper}>
                          <AgInput
                            light
                            multiline
                            placeholder={t("organic.peerReviewFindingsLabel")}
                            value={notes[assignment.id] ?? ""}
                            onChangeText={(value) =>
                              setNotes((prev) => ({
                                ...prev,
                                [assignment.id]: value,
                              }))
                            }
                            fieldStyle={styles.findingsField}
                            style={styles.findingsInput}
                          />
                        </View>
                        <TouchableOpacity
                          onPress={() => submitFindings(assignment.id)}
                          activeOpacity={0.8}
                          disabled={
                            submitAppraisal.isPending ||
                            !notes[assignment.id]?.trim()
                          }
                          accessibilityRole="button"
                          style={[
                            styles.submitButton,
                            (submitAppraisal.isPending ||
                              !notes[assignment.id]?.trim()) &&
                              styles.disabled,
                          ]}
                        >
                          {submitAppraisal.isPending ? (
                            <ActivityIndicator color={C.green} />
                          ) : (
                            <AgText weight="semibold" style={styles.submitText}>
                              {t("organic.peerReviewSubmit")}
                            </AgText>
                          )}
                        </TouchableOpacity>
                      </>
                    ) : null}
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>
      ) : null}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 40 },
  hero: {
    minHeight: 280,
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 24,
    overflow: "hidden",
  },
  backButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#E8F5E4",
  },
  heroContent: {
    minHeight: 196,
    marginTop: 13,
    flexDirection: "row",
    alignItems: "center",
  },
  heroCopy: { flex: 1, zIndex: 2, paddingRight: 4 },
  heroTitle: {
    color: C.text,
    fontSize: 36,
    lineHeight: 42,
    letterSpacing: -0.8,
  },
  heroSubtitle: {
    maxWidth: 290,
    marginTop: 12,
    color: "#5C6876",
    fontSize: 16,
    lineHeight: 23,
  },
  heroArtwork: {
    width: 132,
    height: 178,
    marginLeft: -20,
    alignSelf: "flex-end",
  },
  heroSun: {
    position: "absolute",
    top: 2,
    right: 13,
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#FFB65A",
  },
  certificatePaper: {
    position: "absolute",
    top: 40,
    right: 18,
    width: 88,
    height: 116,
    borderRadius: 13,
    borderWidth: 2,
    borderColor: C.dark,
    backgroundColor: "#FFFDF4",
    paddingHorizontal: 16,
    paddingTop: 20,
  },
  paperLine: {
    height: 6,
    marginBottom: 8,
    borderRadius: 3,
    backgroundColor: "#E8D7AC",
  },
  paperLineShort: { width: 33, marginBottom: 10 },
  heroLeaf: {
    position: "absolute",
    left: 3,
    bottom: 2,
    transform: [{ rotate: "-28deg" }],
  },
  heroAward: {
    position: "absolute",
    right: 1,
    bottom: 1,
    width: 58,
    height: 58,
    borderRadius: 29,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2E8B42",
    borderWidth: 5,
    borderColor: "#A5D571",
  },
  pagePadding: { paddingHorizontal: 16, gap: 16 },
  card: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.card,
    padding: 20,
    shadowColor: "#234A32",
    shadowOpacity: 0.08,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 7 },
    elevation: 3,
  },
  errorCard: { marginHorizontal: 16, minHeight: 280 },
  statusRow: { flexDirection: "row", alignItems: "flex-start" },
  roundIcon: {
    width: 58,
    height: 58,
    borderRadius: 29,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.soft,
  },
  statusCopy: { flex: 1, marginLeft: 16 },
  cardTitle: { color: C.text, fontSize: 20, lineHeight: 27 },
  description: { marginTop: 5, color: "#667181", fontSize: 15, lineHeight: 22 },
  statusPill: {
    alignSelf: "flex-start",
    marginTop: 12,
    borderRadius: 999,
    paddingHorizontal: 13,
    paddingVertical: 7,
  },
  pendingPill: { backgroundColor: C.orangeSoft },
  verifiedPill: { backgroundColor: C.soft },
  pillText: { fontSize: 13, lineHeight: 17 },
  certificateMeta: { marginTop: 12, gap: 3 },
  metaText: { color: C.muted, fontSize: 13, lineHeight: 19 },
  sectionCard: { padding: 16 },
  sectionHeader: { flexDirection: "row", alignItems: "flex-start" },
  sectionCopy: { flex: 1, marginLeft: 14 },
  sectionTitle: { color: C.text, fontSize: 21, lineHeight: 28 },
  checklistRows: { marginTop: 18, gap: 10 },
  checklistRow: {
    minHeight: 74,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 13,
    paddingVertical: 10,
    flexDirection: "row",
    alignItems: "center",
  },
  checkbox: {
    width: 31,
    height: 31,
    borderRadius: 8,
    borderWidth: 2.5,
    borderColor: C.green,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF",
  },
  checkboxChecked: { backgroundColor: C.green },
  checklistLabel: {
    flex: 1,
    marginHorizontal: 13,
    color: "#273651",
    fontSize: 16,
    lineHeight: 22,
  },
  rowIcon: {
    width: 46,
    height: 46,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  saveButton: {
    minHeight: 60,
    marginTop: 16,
    borderRadius: 18,
    paddingHorizontal: 22,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    backgroundColor: C.green,
  },
  saveText: { color: "#FFFFFF", fontSize: 18, lineHeight: 24 },
  disabled: { opacity: 0.5 },
  peerCard: { padding: 20 },
  peerTitle: { flex: 1, marginLeft: 14, marginTop: 12 },
  peerSkeleton: { height: 150, width: "100%", marginTop: 18, borderRadius: 18 },
  emptyState: { alignItems: "center", paddingTop: 18, paddingBottom: 6 },
  emptyArt: {
    width: 205,
    height: 118,
    alignItems: "center",
    justifyContent: "flex-end",
  },
  emptyCloudLeft: {
    position: "absolute",
    left: 17,
    bottom: 12,
    width: 75,
    height: 32,
    borderRadius: 22,
    backgroundColor: "#E8F6EA",
  },
  emptyCloudRight: {
    position: "absolute",
    right: 15,
    bottom: 10,
    width: 87,
    height: 37,
    borderRadius: 24,
    backgroundColor: "#E1F3E4",
  },
  emptyClipboard: {
    width: 74,
    height: 92,
    borderRadius: 15,
    borderWidth: 2,
    borderColor: "#BEE3C4",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#F3FBF1",
    zIndex: 2,
  },
  emptyLeafLeft: {
    position: "absolute",
    left: 45,
    bottom: 8,
    transform: [{ rotate: "-30deg" }],
  },
  emptyLeafRight: {
    position: "absolute",
    right: 45,
    bottom: 8,
    transform: [{ rotate: "32deg" }],
  },
  emptyTitle: {
    maxWidth: 280,
    marginTop: 7,
    color: C.text,
    fontSize: 20,
    lineHeight: 27,
    textAlign: "center",
  },
  emptyDescription: {
    maxWidth: 290,
    marginTop: 7,
    color: "#687181",
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
  assignments: { marginTop: 16, gap: 12 },
  assignmentCard: {
    borderRadius: 17,
    borderWidth: 1,
    borderColor: C.border,
    padding: 14,
    backgroundColor: "#FBFDF9",
  },
  assignmentHeading: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  assignmentTitle: { flex: 1, color: C.text, fontSize: 16, lineHeight: 22 },
  assignmentStatus: {
    borderRadius: 999,
    paddingHorizontal: 9,
    paddingVertical: 4,
    backgroundColor: C.orangeSoft,
  },
  assignmentComplete: { backgroundColor: C.soft },
  assignmentStatusText: { color: C.green, fontSize: 12, lineHeight: 16 },
  scheduleText: { marginTop: 5, color: C.muted, fontSize: 13, lineHeight: 18 },
  inputWrapper: { marginTop: 12 },
  findingsField: { minHeight: 100, alignItems: "flex-start", paddingTop: 12 },
  findingsInput: { minHeight: 74, textAlignVertical: "top" },
  submitButton: {
    minHeight: 50,
    marginTop: 10,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: C.green,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF",
  },
  submitText: { color: C.green, fontSize: 15, lineHeight: 20 },
  statusSkeleton: { height: 150, width: "100%", borderRadius: 24 },
  checklistSkeleton: { height: 510, width: "100%", borderRadius: 24 },
});
