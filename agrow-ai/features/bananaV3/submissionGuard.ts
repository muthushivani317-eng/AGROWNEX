export interface SubmissionGuard {
  tryAcquire(): boolean;
  release(): void;
}

export function createSubmissionGuard(): SubmissionGuard {
  let active = false;
  return {
    tryAcquire() {
      if (active) return false;
      active = true;
      return true;
    },
    release() {
      active = false;
    },
  };
}
