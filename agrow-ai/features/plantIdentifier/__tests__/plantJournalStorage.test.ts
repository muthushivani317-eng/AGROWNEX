import {
  plantJournalStorage,
  type PlantJournalEntry,
} from '../services/plantJournalStorage';

const first: PlantJournalEntry = {
  id: 'journal-test-1',
  imageUri: 'file://plant-1.jpg',
  commonName: 'Neem',
  scientificName: 'Azadirachta indica',
  family: 'Meliaceae',
  confidence: 0.94,
  savedAt: '2026-08-09T10:00:00.000Z',
  latitude: 11.0,
  longitude: 77.0,
};

const second: PlantJournalEntry = {
  ...first,
  id: 'journal-test-2',
  imageUri: 'file://plant-2.jpg',
  commonName: 'Banana',
  savedAt: '2026-08-10T10:00:00.000Z',
};

describe('plantJournalStorage', () => {
  beforeEach(() => {
    plantJournalStorage.remove(first.id);
    plantJournalStorage.remove(second.id);
  });

  afterAll(() => {
    plantJournalStorage.remove(first.id);
    plantJournalStorage.remove(second.id);
  });

  it('adds and lists entries newest first', () => {
    plantJournalStorage.add(first);
    plantJournalStorage.add(second);

    const entries = plantJournalStorage
      .list()
      .filter((entry) => entry.id === first.id || entry.id === second.id);
    expect(entries.map((entry) => entry.id)).toEqual([second.id, first.id]);
  });

  it('replaces an entry with the same id and removes it', () => {
    plantJournalStorage.add(first);
    plantJournalStorage.add({ ...first, commonName: 'Updated neem' });

    expect(
      plantJournalStorage.list().find((entry) => entry.id === first.id)?.commonName,
    ).toBe('Updated neem');

    plantJournalStorage.remove(first.id);
    expect(plantJournalStorage.list().some((entry) => entry.id === first.id)).toBe(false);
  });
});
