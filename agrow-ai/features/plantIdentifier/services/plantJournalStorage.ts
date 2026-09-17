import { appStorage } from '@/lib/storage';

const PLANT_JOURNAL_KEY = 'agrowai.plantIdentifier.journal';

export interface PlantJournalEntry {
  id: string;
  imageUri: string;
  commonName: string | null;
  scientificName: string | null;
  family: string | null;
  confidence: number;
  savedAt: string;
  latitude: number | null;
  longitude: number | null;
}

function readEntries(): PlantJournalEntry[] {
  return appStorage.getJSON<PlantJournalEntry[]>(PLANT_JOURNAL_KEY) ?? [];
}

function writeEntries(entries: PlantJournalEntry[]): void {
  appStorage.setJSON(PLANT_JOURNAL_KEY, entries);
}

function byNewest(a: PlantJournalEntry, b: PlantJournalEntry): number {
  return b.savedAt.localeCompare(a.savedAt);
}

export const plantJournalStorage = {
  add(entry: PlantJournalEntry): void {
    const entries = readEntries();
    const index = entries.findIndex((item) => item.id === entry.id);
    if (index >= 0) entries[index] = entry;
    else entries.unshift(entry);
    writeEntries(entries);
  },

  list(): PlantJournalEntry[] {
    return [...readEntries()].sort(byNewest);
  },

  remove(id: string): void {
    writeEntries(readEntries().filter((entry) => entry.id !== id));
  },
};
