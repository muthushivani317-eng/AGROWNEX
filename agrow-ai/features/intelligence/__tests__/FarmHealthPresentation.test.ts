import fs from 'fs';
import path from 'path';

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, '..', relative), 'utf8');

describe('Farm Health presentation contract', () => {
  it('uses honest insufficient-evidence copy and actionable module routes', () => {
    const dashboard = read('screens/IntelligenceDashboardScreen.tsx');
    const card = read('components/HealthScoreCard.tsx');
    const recs = read('components/RecommendationTimeline.tsx');

    expect(card).toContain('intelligence.insufficientEvidence');
    expect(card).toContain('onModulePress');
    expect(dashboard).toContain('disease: "/disease"');
    expect(dashboard).toContain('nutrient: "/nutrient"');
    expect(dashboard).toContain('soil: "/soil"');
    expect(dashboard).toContain('satellite: "/satellite"');
    expect(dashboard).toContain('weather: "/weather"');
    expect(dashboard).toContain('growth: "/growth"');
    expect(recs).toContain('onRecommendationPress');
  });

  it('uses light badges and narrow-screen-safe layouts', () => {
    const history = read('screens/IntelligenceHistoryScreen.tsx');
    const recs = read('components/RecommendationTimeline.tsx');
    const card = read('components/HealthScoreCard.tsx');

    expect(history).toContain('light');
    expect(recs).toContain('light');
    expect(card).toContain('useWindowDimensions');
    expect(card).toContain('flexDirection: narrow ? "column" : "row"');
  });
});
