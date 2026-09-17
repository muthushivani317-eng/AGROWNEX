import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as service from './communityApi';
const keys = { all: ['community-controlled'] as const, list: ['community-controlled', 'list'] as const, detail: (id: string) => ['community-controlled', 'detail', id] as const };
export const useCommunityQuestions = () => useQuery({ queryKey: keys.list, queryFn: service.listQuestions });
export const useCommunityQuestion = (id: string | null) => useQuery({ queryKey: keys.detail(id ?? ''), enabled: Boolean(id), queryFn: () => service.getQuestion(id as string) });
export function useCreateQuestion() { const client = useQueryClient(); return useMutation({ mutationFn: service.createQuestion, onSuccess: () => client.invalidateQueries({ queryKey: keys.all }) }); }
export function useAnswerQuestion(id: string | null) { const client = useQueryClient(); return useMutation({ mutationFn: (body: string) => service.answerQuestion(id as string, body), onSuccess: () => client.invalidateQueries({ queryKey: keys.detail(id ?? '') }) }); }
export function useReportContent() { const client = useQueryClient(); return useMutation({ mutationFn: ({ type, id }: { type: 'question' | 'answer'; id: string }) => service.reportCommunityContent(type, id), onSuccess: () => client.invalidateQueries({ queryKey: keys.all }) }); }
