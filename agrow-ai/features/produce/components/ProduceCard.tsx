import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  CalendarClock,
  ChevronRight,
  CloudOff,
  IndianRupee,
  Scale,
  Sprout,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";

import { UNIT_LABEL_KEY } from "../constants";
import { PRODUCE_COLORS as C } from "../produceTheme";
import type { ProduceOffer } from "../types";
import {
  formatQuantity,
  formatRupees,
  harvestCountdown,
} from "../utils/format";
import { ProduceStatusBadge } from "./ProduceStatusBadge";

export function ProduceCard({ offer }: { offer: ProduceOffer }) {
  const { t } = useTranslation();
  const router = useRouter();
  const unit = t(UNIT_LABEL_KEY[offer.unit], { defaultValue: offer.unit });
  const countdown = offer.insight
    ? harvestCountdown(offer.insight.daysToHarvest)
    : null;
  const countdownLabel = offer.availabilityType === 'available_now'
    ? t('produce.availableNow')
    : countdown
    ? countdown.key === "inDays"
      ? t("produce.harvestInDays", { count: countdown.days })
      : countdown.key === "overdue"
        ? t("produce.harvestOverdue", { count: countdown.days })
        : t(`produce.harvest_${countdown.key}`)
    : offer.expectedHarvestDate ?? t('produce.upcomingHarvest');

  return (
    <Pressable
      onPress={() => router.push(`/produce/${offer.id}`)}
      accessibilityRole="button"
      accessibilityLabel={`${offer.cropName}, ${formatQuantity(offer.quantity, unit)}`}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View style={styles.topRow}>
        {offer.thumbnailUrl ? (
          <Image
            source={{ uri: offer.thumbnailUrl }}
            style={styles.image}
            contentFit="cover"
          />
        ) : (
          <View style={styles.imagePlaceholder}>
            <Sprout size={30} color={C.green} />
          </View>
        )}
        <View style={styles.copy}>
          <View style={styles.titleRow}>
            <AgText
              variant="headingS"
              weight="bold"
              numberOfLines={2}
              style={styles.ink}
            >
              {offer.productName || offer.cropName}
            </AgText>
            <ChevronRight size={22} color={C.green} />
          </View>
          {offer.variety ? (
            <AgText variant="bodySmall" numberOfLines={1} style={styles.muted}>
              {offer.variety}
            </AgText>
          ) : null}
          <View style={styles.badgeRow}>
            <ProduceStatusBadge status={offer.status} />
            {offer.organicCertificationVerified ? (
              <AgBadge label={t("produce.organicVerified")} tone="success" />
            ) : null}
            {offer.syncStatus === "pending" ? (
              <View style={styles.syncBadge}>
                <CloudOff size={14} color={C.gold} />
                <AgText variant="caption" style={styles.gold}>
                  {t("produce.pendingSync")}
                </AgText>
              </View>
            ) : null}
          </View>
        </View>
      </View>

      <View style={styles.facts}>
        <View style={styles.fact}>
          <Scale size={19} color={C.green} />
          <View>
            <AgText variant="caption" style={styles.muted}>
              {t("produce.quantity")}
            </AgText>
            <AgText weight="semibold" style={styles.ink}>
              {formatQuantity(offer.quantity, unit)}
            </AgText>
          </View>
        </View>
        <View style={styles.divider} />
        <View style={styles.fact}>
          <CalendarClock size={19} color={C.gold} />
          <View style={styles.copy}>
            <AgText variant="caption" style={styles.muted}>
              {offer.availabilityType === 'available_now' ? t('produce.listingType') : t("produce.expectedHarvest")}
            </AgText>
            <AgText weight="semibold" style={styles.ink} numberOfLines={2}>
              {countdownLabel}
            </AgText>
          </View>
        </View>
      </View>

      {offer.insight?.estimatedMarketValue != null ? (
        <View style={styles.valueRow}>
          <IndianRupee size={17} color={C.green} />
          <AgText variant="bodySmall" style={styles.muted}>
            {t("produce.estimatedValue")}
          </AgText>
          <AgText weight="bold" style={styles.value}>
            {formatRupees(offer.insight.estimatedMarketValue)}
          </AgText>
        </View>
      ) : null}
      {offer.askingPrice != null ? (
        <View style={styles.valueRow}>
          <IndianRupee size={17} color={C.green} />
          <AgText variant="bodySmall" style={styles.muted}>{t('produce.askingPrice')}</AgText>
          <AgText weight="bold" style={styles.value}>
            {formatRupees(offer.askingPrice)} / {t(UNIT_LABEL_KEY[offer.priceUnit ?? offer.unit])}
            {offer.negotiable ? ` · ${t('produce.negotiable')}` : ''}
          </AgText>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 18,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    shadowColor: C.ink,
    shadowOpacity: 0.07,
    shadowRadius: 9,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  topRow: { flexDirection: "row", alignItems: "flex-start", gap: 14 },
  image: { width: 72, height: 72, borderRadius: 20 },
  imagePlaceholder: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: C.greenSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  copy: { flex: 1, minWidth: 0 },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  badgeRow: {
    marginTop: 8,
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 8,
  },
  syncBadge: { flexDirection: "row", alignItems: "center", gap: 5 },
  facts: {
    marginTop: 16,
    padding: 14,
    borderRadius: 18,
    backgroundColor: C.greenSoft,
    flexDirection: "row",
    alignItems: "stretch",
  },
  fact: { flex: 1, flexDirection: "row", alignItems: "center", gap: 9 },
  divider: { width: 1, marginHorizontal: 12, backgroundColor: "#C9D8C4" },
  valueRow: {
    marginTop: 14,
    paddingTop: 13,
    borderTopWidth: 1,
    borderTopColor: C.border,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  ink: { color: C.ink },
  muted: { color: C.muted },
  gold: { color: C.gold },
  value: { marginLeft: "auto", color: C.green },
  pressed: { opacity: 0.8 },
});
