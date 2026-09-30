export interface OfflineKnowledgeArticle {
  id: string;
  titleKey: string;
  summaryKey: string;
  stepsKey: string;
  sourceTitle: string;
  sourceUrl: string;
}

/**
 * Bundled, read-only field checklists. These intentionally exclude pesticide
 * names, dosages, diagnoses and generated recommendations. The text remains
 * available without a network connection; links identify the official source
 * family farmers can consult when connectivity is available.
 */
export const OFFLINE_KNOWLEDGE: readonly OfflineKnowledgeArticle[] = [
  {
    id: 'field-scouting',
    titleKey: 'offlineKnowledge.fieldScoutingTitle',
    summaryKey: 'offlineKnowledge.fieldScoutingSummary',
    stepsKey: 'offlineKnowledge.fieldScoutingSteps',
    sourceTitle: 'ICAR agricultural extension resources',
    sourceUrl: 'https://icar.gov.in/',
  },
  {
    id: 'soil-sampling',
    titleKey: 'offlineKnowledge.soilSamplingTitle',
    summaryKey: 'offlineKnowledge.soilSamplingSummary',
    stepsKey: 'offlineKnowledge.soilSamplingSteps',
    sourceTitle: 'Soil Health Card, Government of India',
    sourceUrl: 'https://soilhealth.dac.gov.in/',
  },
  {
    id: 'water-care',
    titleKey: 'offlineKnowledge.waterCareTitle',
    summaryKey: 'offlineKnowledge.waterCareSummary',
    stepsKey: 'offlineKnowledge.waterCareSteps',
    sourceTitle: 'Tamil Nadu Agricultural University Agritech Portal',
    sourceUrl: 'https://agritech.tnau.ac.in/',
  },
  {
    id: 'photo-guide',
    titleKey: 'offlineKnowledge.photoGuideTitle',
    summaryKey: 'offlineKnowledge.photoGuideSummary',
    stepsKey: 'offlineKnowledge.photoGuideSteps',
    sourceTitle: 'AgrowNex field-test capture guidance',
    sourceUrl: 'https://agritech.tnau.ac.in/crop_protection/crop_prot.html',
  },
  {
    id: 'post-harvest',
    titleKey: 'offlineKnowledge.postHarvestTitle',
    summaryKey: 'offlineKnowledge.postHarvestSummary',
    stepsKey: 'offlineKnowledge.postHarvestSteps',
    sourceTitle: 'ICAR post-harvest engineering resources',
    sourceUrl: 'https://icar.gov.in/',
  },
] as const;
