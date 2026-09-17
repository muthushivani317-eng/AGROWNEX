import { buildProfile } from './env';

const internal =
  (buildProfile === 'internal_testing' || buildProfile === 'kvk_field_test') &&
  process.env.EXPO_PUBLIC_AGROWAI_INTERNAL_FEATURE_TESTING === 'true';

export const internalTestFlags = Object.freeze({
  releaseChannel: buildProfile,
  internalFeatureTesting: internal,
  founderFullAccess:
    buildProfile === 'internal_testing' &&
    internal &&
    process.env.EXPO_PUBLIC_AGROWAI_FOUNDER_FULL_ACCESS === 'true',
  enableAllTestRoutes:
    internal && process.env.EXPO_PUBLIC_AGROWAI_ENABLE_ALL_TEST_ROUTES === 'true',
  enableAllTestableFeatures: internal,
  developerMocksEnabled: false,
  productionAuthEnabled: internal,
  productionApiEnabled: internal,
  testChilliDisease: internal,
  testRedgramDisease: internal,
  testAllRecommendations: internal,
  testExternalServices: internal,
  testErrorStates: internal,
});
