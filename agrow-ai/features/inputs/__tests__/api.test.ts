jest.mock("@/services/apiClient", () => ({
  api: { get: jest.fn(), post: jest.fn() },
}));

import { api } from "@/services/apiClient";
import { placeInputOrder } from "../api";

test("checkout sends displayed price and stock version and disables retries", async () => {
  (api.post as jest.Mock).mockResolvedValue({ id: "order-1" });
  await placeInputOrder({
    cart: [
      {
        item: {
          id: "item-1",
          name: "Seed",
          name_ta: null,
          category: "seed",
          unit: "bag",
          unit_price: "450.00",
          stock_quantity: 2,
          stock_version: 7,
          crop_tags: [],
          description: null,
        },
        quantity: 1,
      },
    ],
    deliveryAddress: "12 Sample Village Road",
    idempotencyKey: "order-key-0000001",
  });
  expect(api.post).toHaveBeenCalledWith(
    "/inputs/orders",
    expect.objectContaining({
      items: [
        expect.objectContaining({
          expected_unit_price: "450.00",
          expected_stock_version: 7,
        }),
      ],
    }),
    expect.objectContaining({ _skipRetry: true }),
  );
});
