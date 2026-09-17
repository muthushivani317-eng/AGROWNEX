const React = require('react');
const TestRenderer = require('react-test-renderer');

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock('@/hooks/useAppTheme', () => ({
  useAppTheme: () => ({
    colors: {
      primary: '#4CAF50', primaryLight: '#81C784', success: '#66BB6A', warning: '#FFCA28',
      info: '#42A5F5', card: '#252525', surface: '#1E1E1E', border: '#333333',
      text: '#FFFFFF', textMuted: '#BDBDBD', textDisabled: '#757575',
    },
  }),
}));
jest.mock('@/hooks/useLanguage', () => ({ useLanguage: () => ({ isTamil: false }) }));
jest.mock('lucide-react-native', () => {
  const { View } = require('react-native');
  return new Proxy({}, { get: () => View });
});
jest.mock('@/components/ui', () => {
  const { Text } = require('react-native');
  return { AgText: Text };
});

import fs from 'node:fs';
import path from 'node:path';

import { FARM_STATUSES } from '../constants';
import { FarmCard } from '../components/FarmCard';

const screenSource = fs.readFileSync(
  path.resolve(__dirname, '..', 'screens', 'FarmListScreen.tsx'),
  'utf8',
);
const tabRoute = fs.readFileSync(
  path.resolve(__dirname, '..', '..', '..', 'app', '(tabs)', 'farm.tsx'),
  'utf8',
);
const tabsLayout = fs.readFileSync(
  path.resolve(__dirname, '..', '..', '..', 'app', '(tabs)', '_layout.tsx'),
  'utf8',
);

describe('My Farms redesign', () => {
  const farm = {
    id: 'farm-1', name: 'North Field', crop: 'paddy', status: 'active' as const,
    areaHectares: null, district: null, hasBoundary: false, centroidLat: null,
    centroidLng: null, latitude: null, longitude: null, imageCount: 0,
    updatedAt: null, syncStatus: 'synced' as const,
  };

  it('redesigns the existing tab screen without adding another route', () => {
    expect(tabRoute).toContain('FarmListScreen');
    expect(screenSource).toContain('export function FarmListScreen()');
  });

  it('uses only the canonical farm status values', () => {
    expect(FARM_STATUSES.map((item) => item.value)).toEqual([
      'draft', 'active', 'harvested', 'archived',
    ]);
    expect(screenSource).toContain('...FARM_STATUSES');
  });

  it('renders real farm data and neutral values for missing fields', async () => {
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(FarmCard, {
          farm, onView: jest.fn(), onEdit: jest.fn(), onCalendar: jest.fn(),
        }),
      );
    });
    const output = JSON.stringify(tree.toJSON());
    expect(output).toContain('North Field');
    expect(output).toContain('Paddy (Rice)');
    expect(output).toContain('farm.notSet');
  });

  it('preserves details, edit, calendar, add, and selected-farm behavior', () => {
    expect(screenSource).toMatch(/router\.push\(["']\/farm\/new["']\)/);
    expect(screenSource).toContain('router.push(`/farm/${item.id}`)');
    expect(screenSource).toContain('router.push(`/farm/${item.id}/edit`)');
    expect(screenSource).toMatch(/router\.push\(["']\/calendar["']\)/);
    expect(screenSource).toContain('selectFarm(farmId)');
  });

  it('exposes farm deletion with confirmation and selected-farm cleanup', async () => {
    expect(screenSource).toContain('useDeleteFarm()');
    expect(screenSource).toMatch(/t\(["']farm\.deleteConfirmTitle["']\)/);
    expect(screenSource).toContain('deleteFarm.mutate(farmId');
    expect(screenSource).toContain('appStorage.remove(SELECTED_FARM_KEY)');

    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(FarmCard, {
          farm, onView: jest.fn(), onEdit: jest.fn(), onCalendar: jest.fn(),
          onDelete: jest.fn(),
        }),
      );
    });
    expect(JSON.stringify(tree.toJSON())).toContain('farm.deleteFarm');
  });

  it('keeps search local, includes empty states, and preserves five tabs', () => {
    expect(screenSource).toContain('farm.name, crop, district');
    expect(screenSource).toContain('<AgEmptyState');
    for (const name of ['index', 'ai', 'farm', 'market', 'profile']) {
      expect(tabsLayout).toContain(`name="${name}"`);
    }
  });
});
