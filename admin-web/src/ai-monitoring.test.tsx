import { describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { AiPage, averageRecordedCost, featureActivity, monitoringNumber, type MonitoringData } from './AiMonitoring';

const mock = vi.hoisted(() => ({ error: null as string | null }));
vi.mock('./useResource', () => ({ useResource: () => ({ data: { today_requests: 0, total_messages: 20, disease_detections: 4, nutrient_analyses: null, satellite_analyses: 3, memory_generated: 6, intelligence_reports: 3, average_confidence: 97, api_failures: null, model_latency_ms: null, daily_requests: [], total_cost_inr: 1.769441, total_requests: 25 }, loading: false, error: mock.error, reload: vi.fn() }) }));

describe('AI monitoring', () => {
  it('distinguishes zero from missing and invalid telemetry', () => {
    expect(monitoringNumber(0)).toBe('0');
    for (const value of [null, undefined, NaN, Infinity, -1, '4']) expect(monitoringNumber(value)).toBe('Not reported');
  });
  it('calculates average only from valid cost and positive request counts', () => {
    expect(averageRecordedCost(1.769441, 25)).toBe('₹0.071 per recorded request');
    expect(averageRecordedCost(0, 25)).toBe('₹0.000 per recorded request');
    expect(averageRecordedCost(0, 0)).toBe('Not available');
    expect(averageRecordedCost(null, 25)).toBe('Not available');
    expect(averageRecordedCost(1, Infinity)).toBe('Not available');
  });
  it('filters feature names without changing missing values into zeros', () => {
    const data = { disease_detections: 4, nutrient_analyses: null } as MonitoringData;
    expect(featureActivity(data, ' DISEASE ')).toEqual([{ label: 'Disease detection', value: 4 }]);
    expect(featureActivity(data, 'nutrient')[0].value).toBeNull();
    expect(featureActivity(data, 'unknown')).toEqual([]);
  });
  it('keeps costs behind their permission and explains unavailable instrumentation', () => {
    const html = renderToStaticMarkup(<AiPage canViewCosts={false}/>);
    expect(html).toContain('Cost access restricted');
    expect(html).not.toContain('Cost reporting window');
    expect(html).not.toContain('Export costs');
    expect(html).toContain('Conversations today');
    expect(html).toContain('Confidence is not accuracy');
    expect(html).toContain('Detailed request logs are unavailable');
    expect(html).not.toContain('Healthy');
  });
  it('shows exact estimated costs and a separate cost-only window', () => {
    const html = renderToStaticMarkup(<AiPage canViewCosts/>);
    expect(html).toContain('₹1.769441');
    expect(html).toContain('₹1.77');
    expect(html).toContain('This window applies only to costs');
    expect(html).toContain('Unknown token counts contribute zero');
  });
  it('shows errors without exposing stale usage values', () => {
    mock.error = 'Connection failed';
    try {
      const html = renderToStaticMarkup(<AiPage canViewCosts={false}/>);
      expect(html).toContain('Usage data could not be loaded');
      expect(html).toContain('Connection failed');
      expect(html).not.toContain('>97<');
    } finally { mock.error = null; }
  });
});
