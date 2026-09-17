import {
  apiToAiMonitoring,
  apiToAuditRow,
  apiToDashboard,
  apiToFarmerDetail,
  apiToMe,
  apiToProcurementView,
} from '../services/adminMapper';
import type {
  ApiAdminDashboard,
  ApiAdminMe,
  ApiAiMonitoring,
  ApiAuditRow,
  ApiFarmerDetail,
  ApiProcurementView,
} from '../types';

describe('adminMapper', () => {
  it('maps the admin identity (never invents permissions)', () => {
    const dto: ApiAdminMe = {
      id: 'a1',
      user_id: 'u1',
      role: 'super_admin',
      full_name: 'Ops',
      permissions: ['view_dashboard', 'manage_farmers'],
      status: 'active',
    };
    const me = apiToMe(dto);
    expect(me.userId).toBe('u1');
    expect(me.permissions).toEqual(['view_dashboard', 'manage_farmers']);
    expect(me.isSample).toBe(false);
  });

  it('maps the dashboard, preserving null metric values honestly', () => {
    const dto: ApiAdminDashboard = {
      cards: [
        { key: 'total_farmers', value: 10 },
        { key: 'satellite_reports', value: null },
      ],
      procurement_status_counts: { new: 3, contacted: 1 },
      generated_at: '2026-07-13T08:00:00.000Z',
    };
    const dash = apiToDashboard(dto);
    expect(dash.cards[1].value).toBeNull();
    expect(dash.procurementStatusCounts.new).toBe(3);
  });

  it('maps the procurement view (snake → camel, quantity_kg → quantityKg)', () => {
    const dto: ApiProcurementView = {
      page: {
        items: [
          {
            offer_id: 'o1',
            crop: 'paddy',
            variety: 'ADT-43',
            quantity: 2,
            unit: 'tonne',
            expected_grade: 'A',
            harvest_date: '2026-08-01',
            village: 'Kabisthalam',
            district: 'Thanjavur',
            farmer_name: 'Raja',
            offer_status: 'submitted',
            admin_status: 'farmer_contacted',
            assigned_admin_id: null,
            follow_up_at: null,
            buyer_name: null,
            buyer_contact: null,
            buyer_contact_masked: false,
            cultivated_area_hectares: 1,
            expected_total_quantity: 2,
            available_quantity: 2,
            quantity_provenance: 'farmer_reported',
            quality_notes: 'Good quality',
            buyer_offer_quantity: null,
            buyer_offer_price: null,
            transport_cost: null,
            commission_rate: null,
            negotiation_notes: null,
          },
        ],
        page: 1,
        page_size: 20,
        total: 1,
        total_pages: 1,
      },
      analytics: {
        by_village: [{ label: 'Kabisthalam', count: 1, quantity_kg: 2000 }],
        by_crop: [{ label: 'paddy', count: 1, quantity_kg: 2000 }],
        by_season: [{ label: 'kharif', count: 1, quantity_kg: 2000 }],
        quantity_trend: [{ label: '2026-08', quantity_kg: 2000, count: 1 }],
        total_offers: 1,
        total_quantity_kg: 2000,
      },
    };
    const view = apiToProcurementView(dto);
    expect(view.page.items[0].adminStatus).toBe('farmer_contacted');
    expect(view.page.items[0].offerId).toBe('o1');
    expect(view.analytics.byVillage[0].quantityKg).toBe(2000);
    expect(view.analytics.quantityTrend[0].quantityKg).toBe(2000);
  });

  it('maps AI monitoring, keeping untracked metrics null', () => {
    const dto: ApiAiMonitoring = {
      today_requests: 5,
      total_messages: 100,
      disease_detections: 12,
      nutrient_analyses: 4,
      satellite_analyses: 8,
      memory_generated: 20,
      intelligence_reports: 3,
      average_confidence: 82,
      daily_requests: [{ label: '2026-07-13', count: 5 }],
      model_latency_ms: null,
      api_failures: null,
    };
    const ai = apiToAiMonitoring(dto);
    expect(ai.modelLatencyMs).toBeNull();
    expect(ai.apiFailures).toBeNull();
    expect(ai.averageConfidence).toBe(82);
  });

  it('maps a farmer detail and an audit row', () => {
    const fd: ApiFarmerDetail = {
      user_id: 'u1',
      full_name: 'Raja',
      phone_number: '+919000000001',
      district: 'Thanjavur',
      block: 'Papanasam',
      village: 'Kabisthalam',
      primary_crop: 'paddy',
      language: 'ta',
      farms: [
        {
          id: 'f1',
          name: 'North',
          crop: 'paddy',
          area_hectares: 1.2,
          status: 'active',
          created_at: '2026-01-01T00:00:00.000Z',
        },
      ],
      counts: { disease: 2 },
    };
    const detail = apiToFarmerDetail(fd);
    expect(detail.farms[0].areaHectares).toBe(1.2);
    expect(detail.counts.disease).toBe(2);

    const audit: ApiAuditRow = {
      id: 'x1',
      admin_id: 'a1',
      role: 'super_admin',
      action: 'procurement_status_changed',
      target: 'procurement',
      target_id: 'o1',
      ip_address: '10.0.0.9',
      meta: { status: 'contacted' },
      created_at: '2026-07-13T08:00:00.000Z',
    };
    const row = apiToAuditRow(audit);
    expect(row.targetId).toBe('o1');
    expect(row.meta?.status).toBe('contacted');
  });
});
