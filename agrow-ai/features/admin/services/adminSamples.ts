import type {
  AdminMe,
  AiMonitoring,
  AuditRow,
  Broadcast,
  FarmerDetail,
  FarmerRow,
  OverviewCard,
} from '../types';
import type { ProcurementFact } from './procurementAnalytics';

/**
 * Deterministic sample dataset for the local (no-backend / dev) admin provider. Clearly
 * flagged as sample everywhere it surfaces so it is never mistaken for real operational
 * data. Figures are internally consistent so the dashboard, analytics and procurement
 * views agree.
 */

export const SAMPLE_ADMIN: AdminMe = {
  id: 'sample-admin',
  userId: 'sample-user',
  role: 'super_admin',
  fullName: 'Sample Admin',
  permissions: [
    'view_dashboard',
    'view_analytics',
    'manage_farmers',
    'manage_procurement',
    'view_ai',
    'manage_content',
    'send_broadcast',
    'view_audit',
    'manage_admins',
  ],
  status: 'active',
  isSample: true,
};

export const SAMPLE_OVERVIEW: OverviewCard[] = [
  { key: 'total_farmers', value: 1284 },
  { key: 'total_farms', value: 1710 },
  { key: 'active_users', value: 372 },
  { key: 'today_ai_chats', value: 96 },
  { key: 'disease_reports', value: 431 },
  { key: 'soil_reports', value: 158 },
  { key: 'satellite_reports', value: 203 },
  { key: 'intelligence_reports', value: 117 },
  { key: 'scheme_saves', value: 542 },
  { key: 'produce_listings', value: 88 },
  { key: 'expert_consultations', value: 64 },
  { key: 'notifications_sent', value: 4820 },
];

export interface SampleOffer extends ProcurementFact {
  offerId: string;
  variety: string | null;
  expectedGrade: string | null;
  district: string | null;
  farmerName: string | null;
  offerStatus: string;
}

export const SAMPLE_OFFERS: SampleOffer[] = [
  {
    offerId: 'offer-1',
    crop: 'paddy',
    variety: 'ADT-43',
    quantity: 2,
    unit: 'tonne',
    expectedGrade: 'A',
    village: 'Kabisthalam',
    district: 'Thanjavur',
    harvestDate: '2026-08-01',
    farmerName: 'Raja Selvam',
    offerStatus: 'submitted',
  },
  {
    offerId: 'offer-2',
    crop: 'paddy',
    variety: 'CO-51',
    quantity: 500,
    unit: 'kg',
    expectedGrade: 'B',
    village: 'Kabisthalam',
    district: 'Thanjavur',
    harvestDate: '2026-08-20',
    farmerName: 'Meena Kumari',
    offerStatus: 'submitted',
  },
  {
    offerId: 'offer-3',
    crop: 'banana',
    variety: 'Grand Naine',
    quantity: 5,
    unit: 'quintal',
    expectedGrade: 'A',
    village: 'Papanasam',
    district: 'Thanjavur',
    harvestDate: '2026-09-05',
    farmerName: 'Anbu Rasu',
    offerStatus: 'planned',
  },
  {
    offerId: 'offer-4',
    crop: 'sugarcane',
    variety: null,
    quantity: 3,
    unit: 'tonne',
    expectedGrade: null,
    village: 'Ammapettai',
    district: 'Thanjavur',
    harvestDate: '2026-12-10',
    farmerName: 'Karthik V',
    offerStatus: 'submitted',
  },
];

export const SAMPLE_FARMERS: FarmerRow[] = [
  {
    userId: 'farmer-1',
    fullName: 'Raja Selvam',
    phoneNumber: '+919000000001',
    district: 'Thanjavur',
    village: 'Kabisthalam',
    primaryCrop: 'paddy',
    language: 'ta',
    farmCount: 2,
    createdAt: '2026-01-12T06:00:00.000Z',
  },
  {
    userId: 'farmer-2',
    fullName: 'Meena Kumari',
    phoneNumber: '+919000000002',
    district: 'Thanjavur',
    village: 'Kabisthalam',
    primaryCrop: 'paddy',
    language: 'ta',
    farmCount: 1,
    createdAt: '2026-02-03T06:00:00.000Z',
  },
  {
    userId: 'farmer-3',
    fullName: 'Anbu Rasu',
    phoneNumber: '+919000000003',
    district: 'Thanjavur',
    village: 'Papanasam',
    primaryCrop: 'banana',
    language: 'ta',
    farmCount: 3,
    createdAt: '2026-03-19T06:00:00.000Z',
  },
];

export const SAMPLE_FARMER_DETAILS: Record<string, FarmerDetail> = {
  'farmer-1': {
    userId: 'farmer-1',
    fullName: 'Raja Selvam',
    phoneNumber: '+919000000001',
    district: 'Thanjavur',
    block: 'Papanasam',
    village: 'Kabisthalam',
    primaryCrop: 'paddy',
    language: 'ta',
    farms: [
      {
        id: 'farm-1a',
        name: 'North field',
        crop: 'paddy',
        areaHectares: 1.2,
        status: 'active',
        createdAt: '2026-01-12T06:00:00.000Z',
      },
      {
        id: 'farm-1b',
        name: 'River plot',
        crop: 'banana',
        areaHectares: 0.8,
        status: 'active',
        createdAt: '2026-04-02T06:00:00.000Z',
      },
    ],
    counts: { disease: 4, soil: 2, ai_chats: 11, memory: 6, notifications: 23 },
  },
  'farmer-2': {
    userId: 'farmer-2',
    fullName: 'Meena Kumari',
    phoneNumber: '+919000000002',
    district: 'Thanjavur',
    block: 'Papanasam',
    village: 'Kabisthalam',
    primaryCrop: 'paddy',
    language: 'ta',
    farms: [
      {
        id: 'farm-2a',
        name: 'Home field',
        crop: 'paddy',
        areaHectares: 0.6,
        status: 'active',
        createdAt: '2026-02-03T06:00:00.000Z',
      },
    ],
    counts: { disease: 1, soil: 1, ai_chats: 3, memory: 2, notifications: 9 },
  },
  'farmer-3': {
    userId: 'farmer-3',
    fullName: 'Anbu Rasu',
    phoneNumber: '+919000000003',
    district: 'Thanjavur',
    block: 'Papanasam',
    village: 'Papanasam',
    primaryCrop: 'banana',
    language: 'ta',
    farms: [
      {
        id: 'farm-3a',
        name: 'Plantation A',
        crop: 'banana',
        areaHectares: 2.4,
        status: 'active',
        createdAt: '2026-03-19T06:00:00.000Z',
      },
    ],
    counts: { disease: 6, soil: 3, ai_chats: 8, memory: 5, notifications: 17 },
  },
};

export const SAMPLE_AI: AiMonitoring = {
  todayRequests: 96,
  totalMessages: 5421,
  diseaseDetections: 431,
  nutrientAnalyses: 122,
  satelliteAnalyses: 203,
  memoryGenerated: 640,
  intelligenceReports: 117,
  averageConfidence: 84,
  dailyRequests: [
    { label: '2026-07-07', count: 71 },
    { label: '2026-07-08', count: 88 },
    { label: '2026-07-09', count: 79 },
    { label: '2026-07-10', count: 102 },
    { label: '2026-07-11', count: 94 },
    { label: '2026-07-12', count: 110 },
    { label: '2026-07-13', count: 96 },
  ],
  // Not instrumented in V1 — honest null, never fabricated.
  modelLatencyMs: null,
  apiFailures: null,
  isSample: true,
};

export const SAMPLE_BROADCASTS: Broadcast[] = [
  {
    id: 'bc-1',
    title: 'Heavy rain expected',
    body: 'Heavy rain is forecast across Thanjavur over the next 2 days.',
    language: 'ta',
    targetType: 'district',
    targetValue: 'Thanjavur',
    scheduleType: 'immediate',
    status: 'sent',
    recipientCount: 412,
    deliveredCount: 412,
    scheduledFor: null,
    sentAt: '2026-07-12T04:00:00.000Z',
    createdAt: '2026-07-12T04:00:00.000Z',
    isSample: true,
  },
];

export const SAMPLE_AUDIT: AuditRow[] = [
  {
    id: 'audit-1',
    adminId: 'sample-admin',
    role: 'super_admin',
    action: 'view_dashboard',
    target: null,
    targetId: null,
    ipAddress: '10.0.0.9',
    meta: null,
    createdAt: '2026-07-13T08:00:00.000Z',
  },
  {
    id: 'audit-2',
    adminId: 'sample-admin',
    role: 'super_admin',
    action: 'procurement_status_changed',
    target: 'procurement',
    targetId: 'offer-1',
    ipAddress: '10.0.0.9',
    meta: { status: 'contacted', previous: 'new' },
    createdAt: '2026-07-13T08:05:00.000Z',
  },
];
