import { createSubmissionGuard } from '../submissionGuard';

test('duplicate submissions are blocked until the first finishes', () => {
  const guard = createSubmissionGuard();
  expect(guard.tryAcquire()).toBe(true);
  expect(guard.tryAcquire()).toBe(false);
  guard.release();
  expect(guard.tryAcquire()).toBe(true);
});
