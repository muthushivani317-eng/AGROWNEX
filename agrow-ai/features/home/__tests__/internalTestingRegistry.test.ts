import fs from 'node:fs';
import path from 'node:path';

const repo = path.resolve(__dirname, '..', '..', '..', '..');
const artifacts = path.join(repo, 'artifacts', 'internal_testing');
const features = JSON.parse(fs.readFileSync(path.join(artifacts, 'FEATURE_REGISTRY.json'), 'utf8'));
const routes = JSON.parse(fs.readFileSync(path.join(artifacts, 'ROUTE_REGISTRY.json'), 'utf8'));

const normalize = (route: string) => route.replace('/(tabs)', '') || '/';

describe('internal-testing registry', () => {
  it('represents all 20 required features as visible and reachable', () => {
    expect(features.feature_count).toBe(20);
    for (const feature of features.features) {
      expect(feature.visible_in_internal_testing).toBe(true);
      expect(feature.reachable_in_internal_testing).toBe(true);
      expect(feature.navigation_source).toBeTruthy();
    }
  });

  it('maps every registered feature route to an Expo Router file', () => {
    const registered = new Set(routes.mobile_routes.map((entry: { route: string }) => normalize(entry.route)));
    for (const feature of features.features) expect(registered).toContain(normalize(feature.route));
  });

  it('preserves safety gates while removing stale artificial gates', () => {
    for (const feature of features.features) expect(feature.safety_gate_preserved).toBe(true);
    expect(features.features.find((item: { feature_id: string }) => item.feature_id === 'disease_detection').feature_gate).toContain('crop confirmation');
  });
});
