jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localSoilProvider } from '../services/localSoilProvider';
import { SoilError } from '../services/soilProvider';
import { soilStorage } from '../services/soilStorage';
import type { SoilReportInput } from '../types';

const FARM = 'farm-1';

function report(overrides: Partial<SoilReportInput> = {}): SoilReportInput {
  return {
    farmId: FARM,
    source: 'soil_health_card',
    testDate: '2026-07-01',
    values: { ph: 5.2, nitrogen: 200, potassium: 100 },
    ...overrides,
  };
}

describe('localSoilProvider', () => {
  beforeEach(() => soilStorage.clear());

  it('submits a report and sets confidence from the source', async () => {
    const r = await localSoilProvider.submitReport(report());
    expect(r.status).toBe('processed');
    expect(r.confidence).toBe(90); // soil_health_card
    expect(r.result?.ph).toBe(5.2);
  });

  it('builds a dashboard with an assessment and generic advice', async () => {
    await localSoilProvider.submitReport(report());
    const dash = await localSoilProvider.dashboard(FARM);
    expect(dash.hasData).toBe(true);
    expect(dash.assessment?.phClass).toBe('strongly_acidic');
    const codes = dash.recommendations.map((rec) => rec.code);
    expect(codes).toContain('soil.rec.ph.strongly_acidic');
    expect(codes).toContain('soil.rec.nitrogen.low');
  });

  it('reports an honest "no data" dashboard before any report', async () => {
    const dash = await localSoilProvider.dashboard(FARM);
    expect(dash.hasData).toBe(false);
    expect(dash.messageCode).toBe('soil.status.no_data');
    expect(dash.profile).toBeNull();
    expect(dash.recommendations.map((r) => r.code)).toContain('soil.rec.general.no_data');
  });

  it('merges values across reports (latest measured value wins)', async () => {
    await localSoilProvider.submitReport(report({ values: { ph: 6.0, nitrogen: 200 } }));
    await localSoilProvider.submitReport(report({ values: { potassium: 100 } }));
    const dash = await localSoilProvider.dashboard(FARM);
    expect(dash.profile?.nitrogen).toBe(200); // retained
    expect(dash.profile?.potassium).toBe(100); // new
    expect(dash.profile?.ph).toBe(6.0);
  });

  it('lists history newest-first', async () => {
    await localSoilProvider.submitReport(report({ values: { ph: 6.0 } }));
    await localSoilProvider.submitReport(report({ values: { ph: 6.4 } }));
    const page = await localSoilProvider.history(FARM);
    expect(page.total).toBe(2);
    expect(page.items[0].ph).toBe(6.4);
  });

  it('returns recommendations for a farm', async () => {
    await localSoilProvider.submitReport(report({ values: { organicCarbon: 0.3 } }));
    const recs = await localSoilProvider.recommendations(FARM);
    expect(recs.map((r) => r.code)).toContain('soil.rec.organic_carbon.low');
  });

  it('throws when there is no latest report', async () => {
    await expect(localSoilProvider.latest(FARM)).rejects.toBeInstanceOf(SoilError);
  });

  it('never fabricates values — unknowns stay null', async () => {
    await localSoilProvider.submitReport(report({ values: { ph: 6.5 } }));
    const dash = await localSoilProvider.dashboard(FARM);
    expect(dash.profile?.phosphorus).toBeNull();
    expect(dash.profile?.potassium).toBeNull();
  });
});
