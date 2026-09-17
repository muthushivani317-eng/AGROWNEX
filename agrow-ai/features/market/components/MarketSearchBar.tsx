import { Search, X } from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { SEARCH_TYPE_LABEL_KEY } from "../constants";
import { useMarketSearch } from "../hooks/useMarket";
import type { MarketSearchResult } from "../types";

/**
 * Search box with live crop / market / district / state suggestions. Choosing a
 * suggestion applies it as a typed filter (docs: search crop, market, district).
 */
export function MarketSearchBar({
  onSelect,
}: {
  onSelect: (result: MarketSearchResult) => void;
}) {
  const { t } = useTranslation();
  const [term, setTerm] = useState("");
  const { data: results, isFetching, isError, refetch } = useMarketSearch(term);

  const clear = () => setTerm("");

  return (
    <View style={styles.wrapper}>
      <View style={styles.inputShell}>
        <Search size={21} color="#607068" />
        <TextInput
          value={term}
          onChangeText={setTerm}
          placeholder={t("market.searchPlaceholder")}
          placeholderTextColor="#6C7872"
          accessibilityLabel={t("market.searchPlaceholder")}
          autoCapitalize="none"
          style={styles.input}
        />
        {term.length > 0 ? (
          <TouchableOpacity
            onPress={clear}
            accessibilityRole="button"
            accessibilityLabel={t("common.clear")}
            style={styles.clearButton}
          >
            {isFetching ? (
              <ActivityIndicator size="small" color="#176B3A" />
            ) : (
              <X size={20} color="#52635A" />
            )}
          </TouchableOpacity>
        ) : null}
      </View>

      {term.trim().length > 0 && isError ? (
        <View style={styles.results} accessibilityRole="alert">
          <Text style={styles.result}>{t("common.somethingWrong")}</Text>
          <TouchableOpacity style={styles.result} accessibilityRole="button" disabled={isFetching} onPress={() => void refetch({ cancelRefetch: false })}>
            <Text style={styles.resultLabel}>{t("common.retry")}</Text>
          </TouchableOpacity>
        </View>
      ) : term.trim().length > 0 && results && results.length > 0 ? (
        <View style={styles.results}>
          {results.slice(0, 8).map((result, index) => (
            <TouchableOpacity
              key={`${result.type}-${result.value}`}
              onPress={() => {
                onSelect(result);
                clear();
              }}
              accessibilityRole="button"
              accessibilityLabel={`${result.label} — ${t(
                SEARCH_TYPE_LABEL_KEY[result.type],
              )}`}
              style={[styles.result, index > 0 && styles.resultBorder]}
            >
              <Text style={styles.resultLabel} numberOfLines={2}>
                {result.label}
              </Text>
              <Text style={styles.resultType}>
                {t(SEARCH_TYPE_LABEL_KEY[result.type])}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: 8, zIndex: 3 },
  inputShell: {
    minHeight: 56,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderWidth: 1,
    borderColor: "#CCD3CC",
    borderRadius: 18,
    backgroundColor: "#FFFDF8",
    paddingHorizontal: 16,
  },
  input: { flex: 1, color: "#173B2B", fontSize: 16, paddingVertical: 14 },
  clearButton: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  results: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "#D8D7C9",
    borderRadius: 16,
    backgroundColor: "#FFFDF8",
  },
  result: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  resultBorder: { borderTopWidth: 1, borderTopColor: "#E4E4DA" },
  resultLabel: { flex: 1, color: "#173B2B", fontSize: 16 },
  resultType: { color: "#607068", fontSize: 13 },
});
