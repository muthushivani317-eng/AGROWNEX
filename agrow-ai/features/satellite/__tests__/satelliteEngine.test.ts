import {
  assess,
  buildAlerts,
  classifyHealth,
  classifyMoisture,
  classifyStress,
  classifyTrend,
  computeConfidence,
  computeIndices,
  worstSeverity,
  type Bands,
} from '../services/satelliteEngine';

describe('satelliteEngine (client mirror of the backend Satellite + Alert engines)', () => {
  it('computes NDVI/NDRE/EVI/NDMI from bands and never fabricates a missing band', () => {
    const bands: Bands = { red: 0.1, nir: 0.5, redEdge: 0.3, swir: 0.2, blue: 0.06 };
    const idx = computeIndices(bands);
    // NDVI = (0.5-0.1)/(0.5+0.1) = 0.6667
    expect(idx.ndvi).toBeCloseTo(0.6667, 3);
    expect(idx.ndre).toBeCloseTo(0.25, 3); // (0.5-0.3)/(0.5+0.3)
    expect(idx.ndmi).toBeCloseTo(0.4286, 3); // (0.5-0.2)/(0.5+0.2)
    expect(idx.evi).not.toBeNull();
  });

  it('returns null for an index whose bands are absent (honest "Not Available")', () => {
    const idx = computeIndices({ nir: 0.5, red: 0.1 });
    expect(idx.ndvi).not.toBeNull();
    expect(idx.ndre).toBeNull(); // no red-edge band
    expect(idx.ndmi).toBeNull(); // no swir band
    expect(idx.evi).toBeNull(); // no blue band
  });

  it('classifies vegetation health against standard NDVI bands', () => {
    expect(classifyHealth(null)).toBe('unknown');
    expect(classifyHealth(0.05)).toBe('bare');
    expect(classifyHealth(0.15)).toBe('very_low');
    expect(classifyHealth(0.3)).toBe('low');
    expect(classifyHealth(0.5)).toBe('moderate');
    expect(classifyHealth(0.7)).toBe('good');
    expect(classifyHealth(0.9)).toBe('very_good');
  });

  it('classifies moisture status against standard NDMI bands', () => {
    expect(classifyMoisture(null)).toBe('unknown');
    expect(classifyMoisture(-0.3)).toBe('very_dry');
    expect(classifyMoisture(-0.1)).toBe('dry');
    expect(classifyMoisture(0.1)).toBe('adequate');
    expect(classifyMoisture(0.3)).toBe('moist');
    expect(classifyMoisture(0.5)).toBe('wet');
  });

  it('derives the NDVI trend and delta between consecutive scenes', () => {
    expect(classifyTrend(null, 0.5)).toEqual({ trend: 'unknown', delta: null });
    expect(classifyTrend(0.6, null)).toEqual({ trend: 'unknown', delta: null });
    expect(classifyTrend(0.6, 0.5).trend).toBe('improving');
    expect(classifyTrend(0.4, 0.5).trend).toBe('declining');
    expect(classifyTrend(0.51, 0.5).trend).toBe('stable');
  });

  it('escalates stress on a rapid drop and stays unknown without NDVI', () => {
    expect(classifyStress(null, 'unknown', null)).toBe('unknown');
    expect(classifyStress(0.7, 'stable', 0)).toBe('none');
    expect(classifyStress(0.5, 'stable', 0)).toBe('mild'); // < moderate band
    expect(classifyStress(0.15, 'stable', 0)).toBe('severe'); // < very_low band
    // healthy NDVI but a rapid drop still lifts stress off "none"
    expect(classifyStress(0.7, 'declining', -0.16)).toBe('mild');
  });

  it('assess() combines the classifications and flags whether any value is present', () => {
    const a = assess({ ndvi: 0.7, ndre: 0.25, evi: 0.4, ndmi: 0.1 }, 0.6);
    expect(a.vegetationHealth).toBe('good');
    expect(a.moistureStatus).toBe('adequate');
    expect(a.trend).toBe('improving');
    expect(a.hasValues).toBe(true);
    expect(assess({ ndvi: null, ndre: null, evi: null, ndmi: null }).hasValues).toBe(false);
  });

  it('computes confidence from cloud cover and caps sample data', () => {
    expect(computeConfidence(null)).toBe(50);
    expect(computeConfidence(0)).toBe(99); // clamped to 99
    expect(computeConfidence(20)).toBe(70); // 100 - 30
    expect(computeConfidence(0, true)).toBe(55); // sample cap
  });

  describe('buildAlerts', () => {
    it('reports imagery alerts for unavailable scenes (and none for no_polygon)', () => {
      expect(
        buildAlerts({ status: 'unavailable', unavailableReason: 'cloud_cover', cloudCover: 60 })[0]
          .code,
      ).toBe('satellite.alert.cloud_obstruction');
      expect(
        buildAlerts({ status: 'unavailable', unavailableReason: 'no_imagery' })[0].code,
      ).toBe('satellite.alert.missing_imagery');
      expect(buildAlerts({ status: 'unavailable', unavailableReason: 'no_polygon' })).toHaveLength(0);
    });

    it('flags an abnormal seasonal change as critical', () => {
      const alerts = buildAlerts({ status: 'available', ndvi: 0.5, ndviDelta: -0.25 });
      const seasonal = alerts.find((a) => a.code === 'satellite.alert.abnormal_seasonal_change');
      expect(seasonal?.severity).toBe('critical');
    });

    it('flags moisture stress and low vigor as warnings', () => {
      const alerts = buildAlerts({ status: 'available', ndvi: 0.2, ndmi: -0.1 });
      const codes = alerts.map((a) => a.code);
      expect(codes).toContain('satellite.alert.low_vigor');
      expect(codes).toContain('satellite.alert.moisture_stress');
    });

    it('flags large field variation as advice', () => {
      const alerts = buildAlerts({ status: 'available', ndvi: 0.7, ndviStd: 0.2 });
      const variation = alerts.find((a) => a.code === 'satellite.alert.large_field_variation');
      expect(variation?.severity).toBe('advice');
    });

    it('produces no alerts for a healthy, stable field', () => {
      expect(
        buildAlerts({ status: 'available', ndvi: 0.75, ndmi: 0.3, ndviDelta: 0.01, ndviStd: 0.05 }),
      ).toHaveLength(0);
    });

    it('uses generic localization codes only (never a brand or fabricated value)', () => {
      const alerts = buildAlerts({ status: 'available', ndvi: 0.2, ndmi: -0.1, ndviDelta: -0.16 });
      expect(alerts.every((a) => a.code.startsWith('satellite.alert.'))).toBe(true);
    });
  });

  it('worstSeverity returns the highest severity, or null for an empty list', () => {
    expect(worstSeverity([])).toBeNull();
    const alerts = buildAlerts({ status: 'available', ndvi: 0.2, ndmi: -0.1, ndviDelta: -0.25 });
    expect(worstSeverity(alerts)).toBe('critical');
  });
});
