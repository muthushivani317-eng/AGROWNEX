import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { ArrowLeft, Minus, Plus, ShoppingBasket } from "lucide-react-native";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert, Pressable, StyleSheet, TextInput, View } from "react-native";
import { AgButton, AgCard, AgScreen, AgText } from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { useAppTheme } from "@/hooks/useAppTheme";
import { uuid } from "@/utils/id";
import { getInputCatalog, getInputOrders, placeInputOrder } from "./api";
import type { CatalogItem, InputCategory } from "./types";

const categories: Array<InputCategory | "all"> = [
  "all",
  "seed",
  "fertilizer",
  "pesticide",
];

export function InputsMarketplaceScreen() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const client = useQueryClient();
  const { selected } = useSelectedFarm();
  const [category, setCategory] = useState<InputCategory | "all">("all");
  const [cart, setCart] = useState<Record<string, number>>({});
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState(false);
  const catalog = useQuery({
    queryKey: ["inputs", "catalog", category, selected?.crop],
    queryFn: () =>
      getInputCatalog(
        category === "all" ? undefined : category,
        selected?.crop,
      ),
  });
  const orders = useQuery({
    queryKey: ["inputs", "orders"],
    queryFn: getInputOrders,
  });
  const lines = useMemo(
    () =>
      (catalog.data ?? [])
        .filter((item) => cart[item.id])
        .map((item) => ({ item, quantity: cart[item.id] })),
    [catalog.data, cart],
  );
  const total = lines.reduce(
    (sum, line) => sum + Number(line.item.unit_price) * line.quantity,
    0,
  );
  const adjust = (item: CatalogItem, delta: number) =>
    setCart((current) => ({
      ...current,
      [item.id]: Math.max(
        0,
        Math.min(item.stock_quantity, (current[item.id] ?? 0) + delta),
      ),
    }));
  const checkout = async () => {
    if (!lines.length || address.trim().length < 10) {
      Alert.alert(t("inputs.cannotOrder"), t("inputs.addressRequired"));
      return;
    }
    setBusy(true);
    try {
      const order = await placeInputOrder({
        cart: lines,
        deliveryAddress: address.trim(),
        idempotencyKey: uuid(),
      });
      setCart({});
      setAddress("");
      await Promise.all([
        client.invalidateQueries({ queryKey: ["inputs", "catalog"] }),
        client.invalidateQueries({ queryKey: ["inputs", "orders"] }),
      ]);
      Alert.alert(
        t("inputs.orderPlaced"),
        t("inputs.orderReference", { reference: order.order_ref }),
      );
    } catch {
      Alert.alert(t("inputs.cannotOrder"), t("inputs.refreshRequired"));
      await catalog.refetch();
    } finally {
      setBusy(false);
    }
  };
  return (
    <AgScreen scroll contentContainerStyle={styles.screen}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()}>
          <ArrowLeft size={24} color={colors.text} />
        </Pressable>
        <ShoppingBasket size={28} color={colors.primary} />
        <View style={styles.flex}>
          <AgText variant="headingM" weight="bold">
            {t("inputs.title")}
          </AgText>
          <AgText variant="bodySmall" color="muted">
            {t("inputs.cashOnly")}
          </AgText>
        </View>
      </View>
      <View style={styles.filters}>
        {categories.map((value) => (
          <Pressable
            key={value}
            onPress={() => setCategory(value)}
            style={[
              styles.chip,
              {
                borderColor: colors.border,
                backgroundColor:
                  category === value ? colors.primary : colors.card,
              },
            ]}
          >
            <AgText
              style={{
                color: category === value ? colors.onPrimary : colors.text,
              }}
            >
              {t(`inputs.category.${value}`)}
            </AgText>
          </Pressable>
        ))}
      </View>
      {catalog.isLoading ? <AgText>{t("common.loading")}</AgText> : null}
      {catalog.isError ? (
        <AgButton title={t("common.retry")} onPress={() => catalog.refetch()} />
      ) : null}
      {(catalog.data ?? []).map((item) => (
        <AgCard key={item.id} style={styles.card}>
          <AgText variant="headingS" weight="bold">
            {i18n.language.startsWith("ta") && item.name_ta
              ? item.name_ta
              : item.name}
          </AgText>
          <AgText color="muted">
            {t(`inputs.category.${item.category}`)} · {item.unit}
          </AgText>
          <AgText weight="bold">₹{item.unit_price}</AgText>
          <AgText variant="bodySmall" color="muted">
            {t("inputs.stock", { count: item.stock_quantity })}
          </AgText>
          <View style={styles.quantity}>
            <Pressable onPress={() => adjust(item, -1)}>
              <Minus color={colors.primary} />
            </Pressable>
            <AgText weight="bold">{cart[item.id] ?? 0}</AgText>
            <Pressable
              onPress={() => adjust(item, 1)}
              disabled={(cart[item.id] ?? 0) >= item.stock_quantity}
            >
              <Plus color={colors.primary} />
            </Pressable>
          </View>
        </AgCard>
      ))}
      {lines.length ? (
        <AgCard style={styles.card}>
          <AgText variant="headingS" weight="bold">
            {t("inputs.cart")}
          </AgText>
          <AgText>{t("inputs.total", { total: total.toFixed(2) })}</AgText>
          <TextInput
            value={address}
            onChangeText={setAddress}
            multiline
            placeholder={t("inputs.deliveryAddress")}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.input,
              { borderColor: colors.border, color: colors.text },
            ]}
          />
          <AgButton
            title={t("inputs.placeOrder")}
            onPress={checkout}
            loading={busy}
          />
          <AgText variant="bodySmall" color="muted">
            {t("inputs.noOnlinePayment")}
          </AgText>
        </AgCard>
      ) : null}
      <AgText variant="headingS" weight="bold">
        {t("inputs.orderHistory")}
      </AgText>
      {(orders.data ?? []).map((order) => (
        <AgCard key={order.id} style={styles.card}>
          <AgText weight="bold">{order.order_ref}</AgText>
          <AgText>{t(`inputs.status.${order.status}`)}</AgText>
          <AgText>₹{order.total_amount}</AgText>
          {order.delivery_eta ? (
            <AgText>
              {t("inputs.eta", {
                date: new Date(order.delivery_eta).toLocaleString(),
              })}
            </AgText>
          ) : null}
        </AgCard>
      ))}
    </AgScreen>
  );
}
const styles = StyleSheet.create({
  screen: { padding: 16, gap: 14 },
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  flex: { flex: 1 },
  filters: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  card: { gap: 8 },
  quantity: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    width: 130,
  },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    minHeight: 80,
    padding: 12,
    textAlignVertical: "top",
  },
});
