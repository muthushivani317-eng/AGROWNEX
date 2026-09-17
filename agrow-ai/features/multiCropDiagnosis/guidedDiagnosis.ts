import type { PickedImage } from "@/features/disease/types";
import { api } from "@/services/apiClient";
import type { AxiosRequestConfig } from "axios";

export type GuidedPhotoView =
  "whole_plant" | "affected_leaf" | "lesion_closeup" | "leaf_underside";

export type GuidedDecisionStatus =
  | "strong_agreement"
  | "conflict_needs_more_evidence"
  | "unsupported_or_unknown_disease"
  | "insufficient_evidence"
  | "expert_review_required";

export interface GuidedDecision {
  status: GuidedDecisionStatus;
  likely_disease_label: string | null;
  additional_photo_required: boolean;
  requested_photo_view: GuidedPhotoView | null;
  expert_review_required: boolean;
  reason_code: string;
}

export interface GuidedEvidence {
  view: GuidedPhotoView;
  image: PickedImage;
}

export function validateGuidedEvidence(
  views: GuidedPhotoView[],
): "too_many_images" | "duplicate_view" | null {
  if (views.length > 4) return "too_many_images";
  if (new Set(views).size !== views.length) return "duplicate_view";
  return null;
}

export function guidedDecisionCopyKey(status: GuidedDecisionStatus): string {
  return {
    strong_agreement: "disease.guided.agreement",
    conflict_needs_more_evidence: "disease.guided.conflict",
    unsupported_or_unknown_disease: "disease.guided.unknown",
    insufficient_evidence: "disease.guided.insufficient",
    expert_review_required: "disease.guided.expertRequired",
  }[status];
}

export async function submitGuidedDiagnosis(
  crop: string,
  evidence: GuidedEvidence[],
): Promise<GuidedDecision> {
  const validation = validateGuidedEvidence(evidence.map((item) => item.view));
  if (validation || evidence.length === 0) {
    throw new Error(validation ?? "missing_image");
  }
  const form = new FormData();
  form.append("crop", crop);
  for (const item of evidence) {
    form.append("views", item.view);
    form.append("images", {
      uri: item.image.uri,
      type: item.image.mimeType,
      name: `${item.view}-${Date.now()}.jpg`,
    } as unknown as Blob);
  }
  return api.post<GuidedDecision>(
    "/disease-comparisons-controlled/guided-evaluation",
    form,
    { _skipRetry: true } as AxiosRequestConfig,
  );
}
