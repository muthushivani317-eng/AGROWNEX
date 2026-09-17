import { useState } from "react";
import { useTranslation } from "react-i18next";
import { View } from "react-native";

import { AgButton, AgCard, AgText } from "@/components/ui";
import type { PickedImage } from "@/features/disease/types";
import { pickFromGallery } from "@/features/disease/utils/pickDiseaseImage";

import {
  guidedDecisionCopyKey,
  submitGuidedDiagnosis,
  type GuidedDecision,
  type GuidedEvidence,
  type GuidedPhotoView,
} from "../guidedDiagnosis";

const OPTIONAL_VIEWS: GuidedPhotoView[] = [
  "whole_plant",
  "lesion_closeup",
  "leaf_underside",
];

export function GuidedDiagnosisCard({
  crop,
  primaryImage,
  onExpertReview,
}: {
  crop: string;
  primaryImage: PickedImage;
  onExpertReview: () => void;
}) {
  const { t } = useTranslation();
  const [extra, setExtra] = useState<GuidedEvidence[]>([]);
  const [decision, setDecision] = useState<GuidedDecision | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);

  const addView = async (view: GuidedPhotoView) => {
    const image = await pickFromGallery({ base64: false });
    if (!image) return;
    setExtra((current) => [
      ...current.filter((item) => item.view !== view),
      { view, image },
    ]);
    setDecision(null);
    setFailed(false);
  };

  const submit = async () => {
    setSubmitting(true);
    setFailed(false);
    try {
      setDecision(
        await submitGuidedDiagnosis(crop, [
          { view: "affected_leaf", image: primaryImage },
          ...extra,
        ]),
      );
    } catch {
      setFailed(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AgCard testID="guided-diagnosis-card" className="mt-4 gap-3">
      <AgText weight="bold">{t("disease.guided.title")}</AgText>
      <AgText variant="bodySmall" color="muted">
        {t("disease.guided.intro")}
      </AgText>
      {OPTIONAL_VIEWS.map((view) => (
        <AgButton
          key={view}
          title={t(
            `disease.guided.views.${view}${extra.some((item) => item.view === view) ? "Added" : ""}`,
          )}
          variant="secondary"
          onPress={() => void addView(view)}
        />
      ))}
      <AgButton
        title={t("disease.guided.compare")}
        loading={submitting}
        disabled={submitting}
        onPress={() => void submit()}
      />
      {failed ? (
        <AgText color="danger">{t("disease.guided.unavailable")}</AgText>
      ) : null}
      {decision ? (
        <View style={{ gap: 8 }}>
          <AgText weight="semibold">
            {t(guidedDecisionCopyKey(decision.status))}
          </AgText>
          {decision.requested_photo_view ? (
            <AgText color="muted">
              {t("disease.guided.requestedView", {
                view: t(
                  `disease.guided.viewNames.${decision.requested_photo_view}`,
                ),
              })}
            </AgText>
          ) : null}
          {decision.status === "strong_agreement" &&
          decision.likely_disease_label ? (
            <AgText color="muted">
              {t("disease.guided.likely", {
                disease: decision.likely_disease_label.replaceAll("_", " "),
              })}
            </AgText>
          ) : null}
          {decision.expert_review_required ||
          decision.status === "unsupported_or_unknown_disease" ? (
            <AgButton
              title={t("disease.guided.askExpert")}
              variant="secondary"
              onPress={onExpertReview}
            />
          ) : null}
        </View>
      ) : null}
      <AgText variant="caption" color="muted">
        {t("disease.guided.safety")}
      </AgText>
    </AgCard>
  );
}
