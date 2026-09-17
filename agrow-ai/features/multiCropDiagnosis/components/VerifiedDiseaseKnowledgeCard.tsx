import { AgCard, AgText } from '@/components/ui';
import { useTranslation } from 'react-i18next';

export interface VerifiedDiseaseKnowledge {
  crop_id: string;
  disease_class_id: string;
  symptoms: string[];
  likely_cause: string;
  recommended_actions: string[];
  prevention: string[];
  remedy_or_management: string[];
  evidence: Array<{
    source_document: string;
    printed_page: string;
    pdf_page_index: number;
    verification_status: 'VERIFIED';
  }>;
  verification_status: 'VERIFIED';
}

export function VerifiedDiseaseKnowledgeCard({ knowledge }: { knowledge: VerifiedDiseaseKnowledge | null }) {
  const { t } = useTranslation();
  if (!knowledge || knowledge.verification_status !== 'VERIFIED' || !knowledge.evidence.length) {
    return <AgCard className="mt-3"><AgText color="muted">{t('diseaseKnowledge.verifyWarning')}</AgText></AgCard>;
  }
  return <AgCard className="mt-3 gap-2">
    <AgText weight="bold">{t('diseaseKnowledge.title')}</AgText>
    <AgText>{t('diseaseKnowledge.symptoms', { value: knowledge.symptoms.join('; ') })}</AgText>
    <AgText>{t('diseaseKnowledge.likelyCause', { value: knowledge.likely_cause })}</AgText>
    <AgText>{t('diseaseKnowledge.recommendedActions', { value: knowledge.recommended_actions.join('; ') })}</AgText>
    <AgText>{t('diseaseKnowledge.prevention', { value: knowledge.prevention.join('; ') })}</AgText>
    <AgText>{t('diseaseKnowledge.remedyManagement', { value: knowledge.remedy_or_management.join('; ') })}</AgText>
    {knowledge.evidence.map((evidence) => <AgText key={`${evidence.source_document}-${evidence.pdf_page_index}`} variant="caption">
      {t('diseaseKnowledge.evidenceReference', {
        source: evidence.source_document,
        printedPage: evidence.printed_page,
        pdfPageIndex: evidence.pdf_page_index,
      })}
    </AgText>)}
  </AgCard>;
}
