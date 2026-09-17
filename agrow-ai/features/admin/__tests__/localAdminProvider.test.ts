import { appStorage } from '@/lib/storage';

import { AdminError } from '../services/adminProvider';
import { localAdminProvider } from '../services/localAdminProvider';

const KEYS = [
  'agrowai.admin.procurementStatus',
  'agrowai.admin.broadcasts',
  'agrowai.admin.audit',
];

describe('localAdminProvider (sample dataset, no backend)', () => {
  beforeEach(() => {
    for (const k of KEYS) appStorage.setJSON(k, Array.isArray(k) ? [] : {});
    appStorage.setJSON('agrowai.admin.procurementStatus', {});
    appStorage.setJSON('agrowai.admin.broadcasts', []);
    appStorage.setJSON('agrowai.admin.audit', []);
  });

  it('exposes a clearly-flagged sample admin with full permissions', async () => {
    const me = await localAdminProvider.me();
    expect(me.isSample).toBe(true);
    expect(me.role).toBe('super_admin');
    expect(me.permissions).toContain('manage_procurement');
  });

  it('serves the dashboard with sample cards and default procurement counts', async () => {
    const dash = await localAdminProvider.dashboard();
    expect(dash.isSample).toBe(true);
    expect(dash.cards.length).toBeGreaterThan(0);
    // With no overrides every sample offer is "new".
    expect(dash.procurementStatusCounts.new).toBe(4);
  });

  it('filters the farmer directory by search term', async () => {
    const all = await localAdminProvider.farmers();
    expect(all.total).toBe(3);
    const found = await localAdminProvider.farmers({ search: 'raja' });
    expect(found.total).toBe(1);
    expect(found.items[0].fullName).toBe('Raja Selvam');
  });

  it('rejects an unknown farmer detail (never fabricates one)', async () => {
    await expect(localAdminProvider.farmerDetail('nope')).rejects.toBeInstanceOf(AdminError);
  });

  it('computes procurement analytics from the sample offers', async () => {
    const view = await localAdminProvider.procurement();
    expect(view.isSample).toBe(true);
    expect(view.analytics.totalOffers).toBe(4);
    expect(view.page.items[0].adminStatus).toBe('new');
  });

  it('persists a procurement status change and audits it (immutable trail)', async () => {
    await localAdminProvider.updateProcurementStatus('offer-1', 'farmer_contacted');
    const view = await localAdminProvider.procurement();
    const offer1 = view.page.items.find((r) => r.offerId === 'offer-1');
    expect(offer1?.adminStatus).toBe('farmer_contacted');

    const dash = await localAdminProvider.dashboard();
    expect(dash.procurementStatusCounts.farmer_contacted).toBe(1);
    expect(dash.procurementStatusCounts.new).toBe(3);

    const audit = await localAdminProvider.audit({ action: 'procurement_status_changed' });
    expect(audit.items.some((a) => a.targetId === 'offer-1')).toBe(true);
  });

  it('rejects a status change for an unknown offer', async () => {
    await expect(
      localAdminProvider.updateProcurementStatus('ghost', 'cancelled'),
    ).rejects.toBeInstanceOf(AdminError);
  });

  it('delivers an immediate village broadcast to the matching farmers only', async () => {
    const broadcast = await localAdminProvider.sendBroadcast({
      title: 'Rain',
      body: 'Heavy rain expected',
      language: 'ta',
      targetType: 'village',
      targetValue: 'Kabisthalam',
      scheduleType: 'immediate',
    });
    expect(broadcast.recipientCount).toBe(2);
    expect(broadcast.deliveredCount).toBe(2);
    expect(broadcast.status).toBe('sent');

    const overview = await localAdminProvider.notifications();
    expect(overview.broadcasts.items.some((b) => b.id === broadcast.id)).toBe(true);
  });

  it('queues a scheduled broadcast without delivering it', async () => {
    const broadcast = await localAdminProvider.sendBroadcast({
      title: 'Reminder',
      body: 'Sow soon',
      language: 'ta',
      targetType: 'all',
      scheduleType: 'scheduled',
    });
    expect(broadcast.status).toBe('queued');
    expect(broadcast.deliveredCount).toBe(0);
    expect(broadcast.recipientCount).toBe(3); // all sample farmers
  });
});
