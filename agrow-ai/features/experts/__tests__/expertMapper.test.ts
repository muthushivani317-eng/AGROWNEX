import {
  apiToConsultationDetail,
  apiToExpertDetail,
  consultationInputToApi,
  replyInputToApi,
} from '../services/expertMapper';
import type { ApiConsultationDetail, ApiExpertDetail } from '../types';

const apiExpert: ApiExpertDetail = {
  id: 'e1',
  full_name: 'TNAU Plant Health Clinic',
  expert_type: 'tnau',
  organization: 'Tamil Nadu Agricultural University',
  title: 'Plant Health Specialist Desk',
  photo_url: null,
  districts: [],
  languages: ['ta', 'en'],
  years_experience: null,
  rating: null,
  rating_count: 0,
  verified: true,
  categories: ['crop_disease', 'pest_control'],
  bio: 'Diagnoses crop diseases.',
  source: 'https://tnau.ac.in',
  contact: null,
  specializations: [{ category: 'crop_disease', crop: null }],
  availability: [],
};

const apiConsultation: ApiConsultationDetail = {
  id: 'c1',
  farm_id: 'f1',
  category: 'crop_disease',
  crop: 'Paddy',
  subject: 'Yellow spots',
  priority: 'high',
  status: 'assigned',
  channel: 'in_app',
  assigned_expert_id: 'e1',
  expert: apiExpert,
  attachment_count: 1,
  message_count: 2,
  last_message_at: '2026-07-12T06:00:00Z',
  created_at: '2026-07-12T06:00:00Z',
  updated_at: '2026-07-12T06:00:00Z',
  description: 'Yellow spots spreading.',
  language: 'ta',
  resolution_note: null,
  assigned_at: '2026-07-12T06:00:00Z',
  resolved_at: null,
  messages: [
    {
      id: 'm1',
      sender_type: 'farmer',
      sender_expert_id: null,
      body: 'Yellow spots spreading.',
      language: 'ta',
      is_system: false,
      created_at: '2026-07-12T06:00:00Z',
      attachments: [
        {
          id: 'a1',
          message_id: 'm1',
          kind: 'image',
          file_url: 'https://r2/leaf.jpg',
          thumbnail_url: null,
          mime_type: 'image/jpeg',
          caption: null,
          created_at: '2026-07-12T06:00:00Z',
        },
      ],
    },
  ],
  attachments: [],
  status_history: [
    {
      old_status: null,
      new_status: 'submitted',
      changed_by_type: 'farmer',
      note: 'Consultation created',
      created_at: '2026-07-12T06:00:00Z',
    },
  ],
};

describe('expertMapper', () => {
  it('maps an expert detail to camelCase', () => {
    const e = apiToExpertDetail(apiExpert);
    expect(e.fullName).toBe('TNAU Plant Health Clinic');
    expect(e.expertType).toBe('tnau');
    expect(e.specializations[0].category).toBe('crop_disease');
    expect(e.rating).toBeNull();
  });

  it('maps a consultation detail incl. nested messages/attachments', () => {
    const c = apiToConsultationDetail(apiConsultation);
    expect(c.subject).toBe('Yellow spots');
    expect(c.expert?.fullName).toBe('TNAU Plant Health Clinic');
    expect(c.messages[0].attachments[0].fileUrl).toBe('https://r2/leaf.jpg');
    expect(c.statusHistory[0].newStatus).toBe('submitted');
  });

  it('maps a consultation input to a snake_case body', () => {
    const body = consultationInputToApi({
      category: 'crop_disease',
      subject: 'Spots',
      description: 'Spreading fast',
      priority: 'urgent',
      attachments: [{ fileUrl: 'https://r2/a.jpg' }],
    });
    expect(body.category).toBe('crop_disease');
    expect(body.priority).toBe('urgent');
    expect((body.attachments as unknown[])).toHaveLength(1);
  });

  it('maps a reply input to a snake_case body', () => {
    const body = replyInputToApi({ body: 'Thanks' });
    expect(body.body).toBe('Thanks');
    expect(body.attachments).toEqual([]);
  });
});
