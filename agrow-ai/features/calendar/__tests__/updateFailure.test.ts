import { ApiError } from '@/types';
import { useUpdateEvent } from '../hooks/useCalendar';
import { offlineQueue } from '@/lib/db';
const mockUpdate = jest.fn();
jest.mock('@tanstack/react-query', () => ({ useMutation: (options: unknown) => options }));
jest.mock('@/lib/queryClient', () => ({ queryClient: { invalidateQueries: jest.fn() } }));
jest.mock('@/lib/db', () => ({ offlineQueue: { enqueue: jest.fn().mockResolvedValue(undefined) } }));
jest.mock('../services/calendarProvider', () => ({ getCalendarProvider: () => ({ updateEvent: mockUpdate }) }));
jest.mock('../services/calendarStorage', () => ({ calendarStorage: { update: () => ({ id: 'event-1', status: 'done' }) } }));
beforeEach(() => jest.clearAllMocks());
test.each([401, 403, 422, 500])('does not queue rejected update (%s) as offline success', async (status) => {
  const error = new ApiError({ status, errorCode: 'rejected', message: 'Rejected' });
  mockUpdate.mockRejectedValue(error);
  const mutation = useUpdateEvent() as any;
  await expect(mutation.mutationFn({ id: 'event-1', patch: { status: 'done' } })).rejects.toBe(error);
  expect(offlineQueue.enqueue).not.toHaveBeenCalled();
});
test('queues a genuine network failure', async () => {
  mockUpdate.mockRejectedValue(new ApiError({ status: 0, errorCode: 'NETWORK_ERROR', message: 'Offline' }));
  const mutation = useUpdateEvent() as any;
  await expect(mutation.mutationFn({ id: 'event-1', patch: { status: 'done' } })).resolves.toMatchObject({ status: 'done' });
  expect(offlineQueue.enqueue).toHaveBeenCalledTimes(1);
});
