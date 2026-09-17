jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn((options) => options),
  useMutation: jest.fn((options) => options),
}));

jest.mock('@/lib/queryClient', () => ({
  queryClient: { invalidateQueries: jest.fn() },
}));

jest.mock('../services/marketProvider', () => ({
  getMarketProvider: jest.fn(() => ({
    prices: jest.fn(),
    history: jest.fn(),
    search: jest.fn(),
    favourites: jest.fn(),
    addFavourite: jest.fn(),
    removeFavourite: jest.fn(),
  })),
}));

import { useQuery } from '@tanstack/react-query';

import { useMarketPrices } from '../hooks/useMarket';

describe('useMarketPrices', () => {
  it('disables React Query retries because apiClient already retries transient 503s', () => {
    useMarketPrices({ crop: 'Paddy' });

    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({ retry: false }),
    );
  });
});
