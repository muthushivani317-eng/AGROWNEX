jest.mock('@/services/apiClient', () => ({ httpClient: { post: jest.fn() } }));

import { submitBananaFeedback } from '../bananaV3Api';
import { httpClient } from '@/services/apiClient';

const mockPost = httpClient.post as jest.Mock;

test('feedback sends the prediction request ID and mobile source context', async () => {
  mockPost.mockResolvedValueOnce({ data: {} });
  await submitBananaFeedback({
    prediction_request_id: '00000000-0000-4000-8000-000000000001',
    farmer_selected_outcome: 'UNSURE',
    consent: true,
    source_context: 'agrowai_mobile_app',
  });
  expect(mockPost).toHaveBeenCalledWith(
    '/disease/banana/feedback',
    expect.objectContaining({
      prediction_request_id: '00000000-0000-4000-8000-000000000001',
      source_context: 'agrowai_mobile_app',
    }),
    expect.objectContaining({ _skipRetry: true }),
  );
});
