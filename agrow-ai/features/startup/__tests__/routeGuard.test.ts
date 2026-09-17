import { shouldReplaceStartupRoute } from '../startupStateMachine';

describe('authenticated route guard', () => {
  it.each(['disease', 'weather', 'calendar', 'growth', 'schemes', 'produce', 'notifications', 'plant-identifier', 'soil']) (
    'keeps authenticated feature route %s instead of replacing it with Home',
    (screen) => {
      expect(
        shouldReplaceStartupRoute({
          atIndex: false,
          inAuth: false,
          status: 'authenticated',
          screen,
        }),
      ).toBe(false);
    },
  );

  it('moves an authenticated user out of the auth group', () => {
    expect(
      shouldReplaceStartupRoute({
        atIndex: false,
        inAuth: true,
        status: 'authenticated',
        screen: 'login',
      }),
    ).toBe(true);
  });

  it('keeps protected feature routes protected for signed-out users', () => {
    expect(
      shouldReplaceStartupRoute({
        atIndex: false,
        inAuth: false,
        status: 'unauthenticated',
        screen: 'disease',
      }),
    ).toBe(true);
  });
});
