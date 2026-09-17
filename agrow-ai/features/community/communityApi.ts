import { internalTestFlags } from '@/config/internalTestFlags';
import { getLanguage } from '@/localization';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import type { Paginated } from '@/types';

export interface CommunityQuestion { id: string; author_alias: string; title: string; body: string; crop: string | null; language: string; answer_count: number; created_at: string; user_generated: true; expert_verified: false }
export interface CommunityAnswer { id: string; author_alias: string; body: string; language: string; created_at: string; user_generated: true; expert_verified: false }
export interface CommunityDetail extends CommunityQuestion { answers: CommunityAnswer[]; disclaimer: string; test_mode: true }
function controlled() { if (!internalTestFlags.internalFeatureTesting) throw new Error('CONTROLLED_TEST_BUILD_REQUIRED'); }
function verify<T extends { user_generated: true; expert_verified: false }>(value: T): T { if (value.user_generated !== true || value.expert_verified !== false) throw new Error('COMMUNITY_SAFETY_CONTRACT_INVALID'); return value; }
export async function listQuestions(): Promise<Paginated<CommunityQuestion>> { controlled(); const result = await api.get<Paginated<CommunityQuestion>>(endpoints.community.root); result.items.forEach(verify); return result; }
export async function createQuestion(input: { title: string; body: string; crop?: string }): Promise<CommunityQuestion> { controlled(); return verify(await api.post(endpoints.community.root, { ...input, language: getLanguage() })); }
export async function getQuestion(id: string): Promise<CommunityDetail> { controlled(); const result = verify(await api.get<CommunityDetail>(endpoints.community.byId(id))); result.answers.forEach(verify); return result; }
export async function answerQuestion(id: string, body: string): Promise<CommunityAnswer> { controlled(); return verify(await api.post(endpoints.community.answers(id), { body, language: getLanguage() })); }
export async function reportCommunityContent(target_type: 'question' | 'answer', target_id: string): Promise<void> { controlled(); await api.post(endpoints.community.reports, { target_type, target_id, reason: 'unsafe_advice' }); }
