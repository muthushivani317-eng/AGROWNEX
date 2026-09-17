import {
  assess,
  buildRecommendations,
  classifyPh,
  worstSeverity,
} from '../services/soilEngine';
import type { SoilValues } from '../types';

describe('soilEngine (client mirror of the backend Soil Engine)', () => {
  it('classifies pH against the Soil Health Card bands', () => {
    expect(classifyPh(null)).toBe('unknown');
    expect(classifyPh(5.0)).toBe('strongly_acidic');
    expect(classifyPh(6.0)).toBe('acidic');
    expect(classifyPh(7.0)).toBe('neutral');
    expect(classifyPh(8.0)).toBe('alkaline');
    expect(classifyPh(9.0)).toBe('strongly_alkaline');
  });

  it('flags whether any measured value is present', () => {
    expect(assess({}).hasAnyValue).toBe(false);
    expect(assess({ ph: 6.5 }).hasAnyValue).toBe(true);
  });

  it('produces generic warnings for low nutrients (no brands)', () => {
    const values: SoilValues = {
      ph: 5.2,
      organicCarbon: 0.3,
      nitrogen: 200,
      phosphorus: 5,
      potassium: 100,
    };
    const codes = buildRecommendations(values).map((r) => r.code);
    expect(codes).toContain('soil.rec.ph.strongly_acidic');
    expect(codes).toContain('soil.rec.organic_carbon.low');
    expect(codes).toContain('soil.rec.nitrogen.low');
    expect(codes).toContain('soil.rec.phosphorus.low');
    expect(codes).toContain('soil.rec.potassium.low');
    // Every code is a generic localization key — never a commercial brand.
    expect(buildRecommendations(values).every((r) => r.code.startsWith('soil.rec.'))).toBe(
      true,
    );
  });

  it('treats optimal soil as informational', () => {
    const recs = buildRecommendations({
      ph: 7.0,
      organicCarbon: 1.0,
      nitrogen: 600,
      phosphorus: 30,
      potassium: 300,
    });
    expect(worstSeverity(recs)).toBe('info');
  });

  it('advises a soil test when there is no data', () => {
    const codes = buildRecommendations({}).map((r) => r.code);
    expect(codes).toContain('soil.rec.general.no_data');
  });

  it('gives soil-type baseline guidance without any measured values', () => {
    expect(buildRecommendations({}, 'Sandy loam').map((r) => r.code)).toContain(
      'soil.rec.water_holding.sandy',
    );
    expect(buildRecommendations({}, 'Black clay').map((r) => r.code)).toContain(
      'soil.rec.drainage.clay',
    );
  });

  it('detects salinity and micronutrient deficiency', () => {
    const recs = buildRecommendations({ ecSalinity: 3.0, micronutrients: { zinc: 0.2 } });
    const codes = recs.map((r) => r.code);
    expect(codes).toContain('soil.rec.general.salinity_high');
    expect(codes).toContain('soil.rec.micronutrient.deficient');
    expect(recs.find((r) => r.code === 'soil.rec.micronutrient.deficient')?.parameter).toBe(
      'zinc',
    );
  });

  it('returns null worst-severity for an empty list', () => {
    expect(worstSeverity([])).toBeNull();
  });
});
