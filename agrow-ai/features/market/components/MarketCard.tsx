import { Clock, MapPin, Star } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { CATEGORY_LABEL_KEY, UNIT_LABEL_KEY } from "../constants";
import type { MarketPrice } from "../types";
import { formatRupees, updatedAgo } from "../utils/format";

/**
 * A single market price card (docs: crop, market, district, min/max/modal price,
 * unit, updated time, favourite button). Fully accessible and Tamil-first.
 */
export function MarketCard({
  price,
  isFavourite,
  onToggleFavourite,
  busy,
}: {
  price: MarketPrice;
  isFavourite: boolean;
  onToggleFavourite: (price: MarketPrice) => void;
  busy?: boolean;
}) {
  const { t } = useTranslation();

  const unit = t(UNIT_LABEL_KEY[price.unit], { defaultValue: price.unit });
  const category = t(CATEGORY_LABEL_KEY[price.category], {
    defaultValue: price.category,
  });
  const ago = updatedAgo(price.priceDate);
  const updatedLabel =
    ago.key === "daysAgo"
      ? t("market.updatedDaysAgo", { count: ago.days })
      : t(`market.updated_${ago.key}`);

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.grow}>
          <View style={styles.titleRow}>
            <Text style={styles.commodity} numberOfLines={2}>
              {price.commodity}
            </Text>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{category}</Text>
            </View>
          </View>
          {price.variety ? (
            <Text style={styles.variety}>{price.variety}</Text>
          ) : null}
          <View style={styles.locationRow}>
            <MapPin size={16} color="#607068" />
            <Text style={styles.location} numberOfLines={2}>
              {price.market}
              {price.district ? `, ${price.district}` : ""}
            </Text>
          </View>
        </View>

        <TouchableOpacity
          onPress={() => onToggleFavourite(price)}
          disabled={busy}
          accessibilityRole="button"
          accessibilityState={{ selected: isFavourite, busy }}
          accessibilityLabel={
            isFavourite ? t("market.removeFavourite") : t("market.addFavourite")
          }
          style={styles.starButton}
        >
          <Star
            size={22}
            color={isFavourite ? "#B87900" : "#607068"}
            fill={isFavourite ? "#F4B72C" : "transparent"}
          />
        </TouchableOpacity>
      </View>

      {/* Modal price is the headline; min/max are the day's range. */}
      <View style={styles.priceRow}>
        <View>
          <Text style={styles.priceLabel}>{t("market.modalPrice")}</Text>
          <Text style={styles.modalPrice}>
            {formatRupees(price.modalPrice)}
          </Text>
          <Text style={styles.unit}>{t("market.perUnit", { unit })}</Text>
        </View>
        <View style={styles.rangeBox}>
          <View style={styles.rangeRow}>
            <Text style={styles.rangeLabel}>{t("market.minPrice")}</Text>
            <Text style={styles.rangeValue}>
              {formatRupees(price.minimumPrice)}
            </Text>
          </View>
          <View style={styles.rangeRow}>
            <Text style={styles.rangeLabel}>{t("market.maxPrice")}</Text>
            <Text style={styles.rangeValue}>
              {formatRupees(price.maximumPrice)}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.updatedRow}>
        <Clock size={14} color="#607068" />
        <Text style={styles.updatedText}>
          {price.isStale
            ? t("market.lastVerifiedPrice", {
                date: price.priceDate,
                count: price.ageDays,
              })
            : updatedLabel}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFDF8",
    borderWidth: 1,
    borderColor: "#D8D7C9",
    borderRadius: 22,
    padding: 18,
    gap: 4,
    shadowColor: "#173B2B",
    shadowOpacity: 0.08,
    shadowRadius: 9,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  topRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  grow: { flex: 1 },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 8,
  },
  commodity: {
    color: "#173B2B",
    fontSize: 21,
    lineHeight: 27,
    fontWeight: "700",
  },
  badge: {
    borderRadius: 12,
    backgroundColor: "#EEF6EC",
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  badgeText: { color: "#176B3A", fontSize: 12, fontWeight: "600" },
  variety: { color: "#607068", fontSize: 14, marginTop: 2 },
  locationRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 8,
  },
  location: { flex: 1, color: "#52635A", fontSize: 15, lineHeight: 20 },
  starButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "#D8D7C9",
    alignItems: "center",
    justifyContent: "center",
  },
  priceRow: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: 12,
  },
  priceLabel: { color: "#607068", fontSize: 13 },
  modalPrice: {
    color: "#176B3A",
    fontSize: 28,
    lineHeight: 34,
    fontWeight: "800",
  },
  unit: { color: "#607068", fontSize: 12 },
  rangeBox: { gap: 7, alignItems: "flex-end" },
  rangeRow: { flexDirection: "row", gap: 7 },
  rangeLabel: { color: "#607068", fontSize: 13 },
  rangeValue: { color: "#173B2B", fontSize: 14, fontWeight: "700" },
  updatedRow: {
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: "#E4E4DA",
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
  },
  updatedText: { flex: 1, color: "#607068", fontSize: 12, lineHeight: 17 },
});
