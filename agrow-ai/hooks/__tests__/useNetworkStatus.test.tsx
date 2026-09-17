import React from 'react';
import { AppState } from 'react-native';
import TestRenderer, { act } from 'react-test-renderer';
import { useNetworkStatus } from '../useNetworkStatus';

describe('connectivity probe recovery', () => {
  const originalFetch = global.fetch;
  let tree: TestRenderer.ReactTestRenderer | undefined;
  let latest: ReturnType<typeof useNetworkStatus>;
  let foreground: (state: string) => void;
  const remove = jest.fn();
  function Probe() { latest = useNetworkStatus(); return null; }
  beforeEach(() => {
    jest.useFakeTimers();
    jest.spyOn(AppState, 'addEventListener').mockImplementation((_, listener) => {
      foreground = listener as (state: string) => void;
      return { remove };
    });
  });
  afterEach(async () => {
    if (tree) await act(async () => tree!.unmount());
    tree = undefined;
    global.fetch = originalFetch;
    jest.restoreAllMocks();
    jest.useRealTimers();
  });
  it('times out a stalled probe, avoids overlap, and recovers on the next check', async () => {
    const fetchMock = jest.fn().mockImplementationOnce((_, options) => new Promise((_, reject) => {
      options.signal.addEventListener('abort', () => reject(new Error('aborted')));
    })).mockResolvedValue({ status: 204, ok: true });
    global.fetch = fetchMock;
    await act(async () => { tree = TestRenderer.create(<Probe />); });
    await act(async () => { foreground('active'); });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => { jest.advanceTimersByTime(8_000); });
    expect(latest!).toEqual({ isConnected: false, checking: false });
    await act(async () => { jest.advanceTimersByTime(12_000); });
    expect(latest!).toEqual({ isConnected: true, checking: false });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
  it('aborts a pending probe and removes listeners when unmounted', async () => {
    let signal!: AbortSignal;
    global.fetch = jest.fn().mockImplementation((_, options) => new Promise((_, reject) => {
      signal = options.signal;
      signal.addEventListener('abort', () => reject(new Error('aborted')));
    }));
    await act(async () => { tree = TestRenderer.create(<Probe />); });
    await act(async () => tree!.unmount());
    tree = undefined;
    expect(signal.aborted).toBe(true);
    expect(remove).toHaveBeenCalled();
    const callsAfterUnmount = (global.fetch as jest.Mock).mock.calls.length;
    await act(async () => { jest.advanceTimersByTime(40_000); });
    expect(global.fetch).toHaveBeenCalledTimes(callsAfterUnmount);
  });
});
