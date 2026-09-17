import { apiToOrganicInput, buildOrganicInputQuery } from '../services/organicInputMapper';

describe('organic input catalogue boundary', () => {
  it('preserves sourced-public status without implying approval', () => {
    const item = apiToOrganicInput({ id: 'i1', slug: 'compost', category: 'compost', name_en: 'Compost', name_ta: 'கம்போஸ்ட்', purpose_en: 'Soil amendment', purpose_ta: 'மண் வளம்', guidance: {}, applicable_crops: [], applicable_stages: [], applicable_regions: ['Tamil Nadu'], limitations: {}, source_organization: 'TNAU', document_reference: 'Guide', source_url: 'https://agritech.tnau.ac.in/guide', source_version: '1', content_hash: 'a'.repeat(64), reviewed_at: null, provenance_status: 'sourced_public_reference' });
    expect(item).toMatchObject({ id: 'i1', provenanceStatus: 'sourced_public_reference', approved: false });
  });
  it('maps search filters without client-side approval fields', () => expect(buildOrganicInputQuery(' neem ', 'paddy')).toEqual({ q: 'neem', crop: 'paddy', page: 1, page_size: 50 }));
});
