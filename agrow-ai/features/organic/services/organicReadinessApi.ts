import { httpClient } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

/**
 * Client for backend/app/modules/organic_mvp's readiness assessment
 * endpoints. Deliberately separate from apiOrganicProvider.ts -- organic_mvp
 * is a different backend module (own review/approval workflow for question
 * content) that returns raw payloads, not the { success, data } envelope, so
 * this goes through httpClient directly rather than the `api` helper.
 */

export interface ReadinessQuestionOption {
  points: number;
  risk_flag?: string | null;
  label_ta?: string;
  label_en?: string;
}

export interface ReadinessQuestion {
  id: string;
  title_ta: string;
  title_en?: string;
  options: Record<string, ReadinessQuestionOption>;
}

export interface ReadinessQuestionsResponse {
  /** "ready" once an admin-approved question set exists, else a plain-English reason (e.g. "Pilot setup required"). */
  status: string;
  version: string | null;
  questions: ReadinessQuestion[];
}

export interface ReadinessResult {
  id: string;
  score: number;
  pathway: string;
  recommendation_ta: string;
  recommendation_en?: string | null;
  risk_flags: string[];
  certification_notice: string;
}

export interface ReadinessHistoryEntry {
  id: string;
  score: number | null;
  pathway: string;
  rules_version: string | null;
  risk_flags: string[];
}

export const organicReadinessApi = {
  async getQuestions(): Promise<ReadinessQuestionsResponse> {
    const response = await httpClient.get<ReadinessQuestionsResponse>(
      endpoints.organicMvp.readinessQuestions,
    );
    return response.data;
  },

  async submit(
    farmId: string,
    answers: Record<string, string>,
  ): Promise<ReadinessResult> {
    const response = await httpClient.post<ReadinessResult>(
      endpoints.organicMvp.readiness(farmId),
      { answers },
    );
    return response.data;
  },

  async getHistory(farmId: string): Promise<ReadinessHistoryEntry[]> {
    const response = await httpClient.get<ReadinessHistoryEntry[]>(
      endpoints.organicMvp.readiness(farmId),
    );
    return response.data;
  },
};
