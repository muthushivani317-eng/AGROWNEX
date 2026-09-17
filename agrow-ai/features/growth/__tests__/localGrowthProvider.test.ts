jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localGrowthProvider } from '../services/localGrowthProvider';
import { GrowthError } from '../services/growthProvider';
import { growthStorage } from '../services/growthStorage';
import type { UploadGrowthInput } from '../types';

function input(overrides: Partial<UploadGrowthInput> = {}): UploadGrowthInput {
  return {
    imageBase64: 'x',
    mimeType: 'image/jpeg',
    imageUri: 'file://photo.jpg',
    farmId: 'farm-1',
    crop: 'paddy',
    language: 'ta',
    captureMethod: 'camera',
    ...overrides,
  };
}

describe('localGrowthProvider', () => {
  beforeEach(() => growthStorage.clear());

  it('creates a session, image and timeline entry on first upload', async () => {
    const result = await localGrowthProvider.upload(input());
    expect(result.session.imageCount).toBe(1);
    expect(result.image.weekNumber).toBe(1);
    expect(result.image.analysis?.growthStage).toBe('vegetative');
    expect(result.timelineEntry.healthDelta).toBeNull(); // first entry
    expect(result.session.currentGrowthStage).toBe('vegetative');
  });

  it('reuses the active session and increments the week', async () => {
    const first = await localGrowthProvider.upload(input());
    const second = await localGrowthProvider.upload(input());
    expect(second.session.id).toBe(first.session.id);
    expect(second.session.imageCount).toBe(2);
    expect(second.image.weekNumber).toBe(2);
  });

  it('lists history newest first', async () => {
    await localGrowthProvider.upload(input());
    await localGrowthProvider.upload(input());
    const history = await localGrowthProvider.history();
    expect(history).toHaveLength(2);
    expect(history[0].weekNumber).toBe(2); // newest first
  });

  it('builds an ordered timeline with health deltas', async () => {
    await localGrowthProvider.upload(input());
    await localGrowthProvider.upload(input());
    const { timeline, session } = await localGrowthProvider.timeline();
    expect(session.imageCount).toBe(2);
    expect(timeline.map((e) => e.weekNumber)).toEqual([1, 2]);
    // Same mock health each week → delta 0 on the second entry.
    expect(timeline[1].healthDelta).toBe(0);
  });

  it('returns the latest uploaded photo', async () => {
    await localGrowthProvider.upload(input());
    const latest = await localGrowthProvider.latest();
    expect(latest).not.toBeNull();
    expect(latest?.weekNumber).toBe(1);
  });

  it('returns full session detail', async () => {
    const first = await localGrowthProvider.upload(input());
    const detail = await localGrowthProvider.session(first.session.id);
    expect(detail.images).toHaveLength(1);
    expect(detail.timeline).toHaveLength(1);
  });

  it('deletes an image', async () => {
    const first = await localGrowthProvider.upload(input());
    await localGrowthProvider.deleteImage(first.image.id);
    expect(await localGrowthProvider.history()).toHaveLength(0);
  });

  it('throws when there is no session for the timeline', async () => {
    await expect(localGrowthProvider.timeline()).rejects.toBeInstanceOf(GrowthError);
  });
});
