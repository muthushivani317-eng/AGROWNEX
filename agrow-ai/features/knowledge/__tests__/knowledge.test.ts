import { OFFLINE_KNOWLEDGE } from '../knowledge';
import { ORGANIC_INPUTS_GUIDE } from '../organicInputsGuide';
import { en } from '../../../localization/locales/en';
import { ta } from '../../../localization/locales/ta';
import fs from 'node:fs';
import path from 'node:path';

test('bundles every article in English and Tamil with an official HTTPS source', () => {
  expect(OFFLINE_KNOWLEDGE.length).toBeGreaterThanOrEqual(5);
  for (const article of OFFLINE_KNOWLEDGE) {
    for (const key of [article.titleKey, article.summaryKey, article.stepsKey]) {
      const localKey = key.replace('offlineKnowledge.', '') as keyof typeof en.offlineKnowledge;
      expect(en.offlineKnowledge[localKey]).toBeTruthy();
      expect(ta.offlineKnowledge[localKey]).toBeTruthy();
      expect(ta.offlineKnowledge[localKey]).not.toBe(en.offlineKnowledge[localKey]);
    }
    expect(article.sourceUrl).toMatch(/^https:\/\//);
  }
});

test('does not bundle treatment or pesticide dosage claims', () => {
  const text = JSON.stringify({ en: en.offlineKnowledge, ta: ta.offlineKnowledge }).toLowerCase();
  expect(text).not.toMatch(/pesticide|fungicide|insecticide|dosage|ml\/litre/);
});

test('keeps the local library synchronous and handles online source failures', () => {
  const screen = fs.readFileSync(
    path.resolve(__dirname, '..', 'OfflineKnowledgeScreen.tsx'),
    'utf8',
  );
  expect(screen).toContain('articles.map');
  expect(screen).toContain('ORGANIC_INPUTS_GUIDE.map');
  expect(screen).not.toContain('isLoading');
  expect(screen).not.toContain('RefreshControl');
  expect(screen).toContain('Linking.canOpenURL');
  expect(screen).toContain('sourceUnavailableMessage');
  expect(en.offlineKnowledge.sourceUnavailableMessage).toBeTruthy();
  expect(ta.offlineKnowledge.sourceUnavailableMessage).toBeTruthy();
});

test('bundles all 19 organic recipes in both languages with all farmer-facing sections', () => {
  expect(ORGANIC_INPUTS_GUIDE).toHaveLength(19);
  expect(new Set(ORGANIC_INPUTS_GUIDE.map(recipe => recipe.id)).size).toBe(19);
  const counts = { nutrition: 9, protection: 6, growth: 2, soil: 2 };
  for (const [category, count] of Object.entries(counts)) {
    expect(ORGANIC_INPUTS_GUIDE.filter(recipe => recipe.category === category)).toHaveLength(count);
  }
  for (const recipe of ORGANIC_INPUTS_GUIDE) {
    expect(recipe.en.title).toBeTruthy();
    expect(recipe.en.summary).toBeTruthy();
    expect(recipe.ta.title).toMatch(/[\u0B80-\u0BFF]/);
    expect(recipe.ta.summary).toMatch(/[\u0B80-\u0BFF]/);
    for (const section of ['Materials needed', 'Procedure', 'Time to ready', 'Benefits', 'How to use']) {
      expect(recipe.en.body).toContain(section);
    }
    for (const section of ['தேவையான பொருட்கள்', 'செய்முறை', 'தயாராகும் காலம்', 'நன்மைகள்', 'பயன்படுத்தும் முறை']) {
      expect(recipe.ta.body).toContain(section);
    }
    expect(JSON.stringify(recipe)).not.toMatch(/business angle|buyback|resale|starter.culture sales|வணிக வாய்ப்பு|மறுவிற்பனை/i);
    // Translation must retain the source's numeric rates, times and intervals.
    expect(recipe.ta.body.match(/\d+(?:[–.\-]\d+)?%?/g)).toEqual(recipe.en.body.match(/\d+(?:[–.\-]\d+)?%?/g));
  }
});
