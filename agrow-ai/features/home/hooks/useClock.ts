import { useEffect, useState } from 'react';

/** A Date that ticks on an interval (default 30s — enough for a HH:mm clock). */
export function useClock(intervalMs = 30_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
