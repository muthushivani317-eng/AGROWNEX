jest.mock('@/config/internalTestFlags', () => ({ internalTestFlags: { internalFeatureTesting: true } }));
jest.mock('@/localization', () => ({ getLanguage: () => 'ta' }));
jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn(), post: jest.fn() } }));
import { api } from '@/services/apiClient';
import { createQuestion, getQuestion } from '../communityApi';

test('posts community content as Tamil by default', async () => {
  (api.post as jest.Mock).mockResolvedValue({ user_generated: true, expert_verified: false });
  await createQuestion({ title: 'Question title', body: 'Question body long enough' });
  expect(api.post).toHaveBeenCalledWith('/community-controlled', expect.objectContaining({ language: 'ta' }));
});

test('fails closed when a community answer is presented as expert verified', async () => {
  (api.get as jest.Mock).mockResolvedValue({ user_generated: true, expert_verified: false, answers: [{ user_generated: true, expert_verified: true }] });
  await expect(getQuestion('question-1')).rejects.toThrow('COMMUNITY_SAFETY_CONTRACT_INVALID');
});
