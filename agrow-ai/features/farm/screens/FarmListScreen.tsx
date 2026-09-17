import { useRouter } from "expo-router";
import {
  Archive,
  FileText,
  Grid2X2,
  Plus,
  Search,
  Sprout,
  Wheat,
  X,
  type LucideIcon,
} from "lucide-react-native";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";

import { AgEmptyState, AgErrorState, AgScreen, AgText } from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { SELECTED_FARM_KEY } from "@/features/weather/constants";
import { useLanguage } from "@/hooks/useLanguage";
import { appStorage } from "@/lib/storage";

import { FarmCard } from "../components/FarmCard";
import { FARM_STATUSES } from "../constants";
import { useFarms } from "../hooks/useFarms";
import { useDeleteFarm } from "../hooks/useFarmMutations";
import { useFarmSync } from "../hooks/useFarmSync";
import type { FarmStatus } from "../types";
import { cropLabel, districtLabel } from "../utils/labels";

const STATUS_ICON: Record<FarmStatus, LucideIcon> = {
  draft: FileText,
  active: Sprout,
  harvested: Wheat,
  archived: Archive,
};

export function FarmListScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { isTamil } = useLanguage();
  const { selected: selectedFarm, select: selectFarm } = useSelectedFarm();
  const deleteFarm = useDeleteFarm();
  const [status, setStatus] = useState<FarmStatus | undefined>(undefined);
  const [searchVisible, setSearchVisible] = useState(false);
  const [search, setSearch] = useState("");

  useFarmSync();
  const { data, isLoading, isError, refetch, isRefetching } = useFarms({
    status,
  });
  const loadedFarms = useMemo(() => data?.items ?? [], [data]);
  const farms = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    if (!term) return loadedFarms;
    return loadedFarms.filter((farm) => {
      const crop = cropLabel(farm.crop, isTamil) ?? "";
      const district = districtLabel(farm.district, isTamil) ?? "";
      return [farm.name, crop, district].some((value) =>
        value.toLocaleLowerCase().includes(term),
      );
    });
  }, [isTamil, loadedFarms, search]);

  const goToAdd = () => router.push("/farm/new");
  const goToCalendar = (farmId: string) => {
    selectFarm(farmId);
    router.push("/calendar");
  };
  const confirmDelete = (farmId: string, farmName: string) => {
    Alert.alert(
      t("farm.deleteConfirmTitle"),
      `${farmName}\n\n${t("farm.deleteConfirmMsg")}`,
      [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("common.delete"),
          style: "destructive",
          onPress: () =>
            deleteFarm.mutate(farmId, {
              onSuccess: () => {
                if (selectedFarm?.id === farmId)
                  appStorage.remove(SELECTED_FARM_KEY);
                Alert.alert(t("farm.deleted"));
              },
              onError: () => Alert.alert(t("errors.generic")),
            }),
        },
      ],
    );
  };

  const header = (
    <View style={styles.header}>
      <View style={styles.headerRow}>
        <View style={styles.headerCopy}>
          <AgText variant="headingL" weight="bold" style={styles.title}>
            {t("farm.myFarms")}
          </AgText>
          <AgText variant="bodySmall" style={styles.subtitle}>
            {t("farm.listSubtitle")}
          </AgText>
        </View>
        <View style={styles.headerActions}>
          <HeaderButton
            icon={searchVisible ? X : Search}
            label={
              searchVisible ? t("farm.closeSearch") : t("farm.searchFarms")
            }
            onPress={() => {
              setSearchVisible((visible) => !visible);
              if (searchVisible) setSearch("");
            }}
          />
          <HeaderButton
            icon={Plus}
            label={t("farm.addFarm")}
            onPress={goToAdd}
            primary
          />
        </View>
      </View>

      {searchVisible ? (
        <View style={styles.searchBox}>
          <Search size={20} color="#607068" />
          <TextInput
            testID="farm-search-input"
            value={search}
            onChangeText={setSearch}
            placeholder={t("farm.searchPlaceholder")}
            placeholderTextColor="#718078"
            style={styles.searchInput}
            accessibilityLabel={t("farm.searchFarms")}
            autoCorrect={false}
            returnKeyType="search"
          />
          {search ? (
            <Pressable
              onPress={() => setSearch("")}
              accessibilityRole="button"
              accessibilityLabel={t("farm.clearSearch")}
              hitSlop={10}
            >
              <X size={18} color="#607068" />
            </Pressable>
          ) : null}
        </View>
      ) : null}

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filters}
      >
        {[
          { value: undefined, labelKey: "farm.filterAll" },
          ...FARM_STATUSES,
        ].map((item) => {
          const selected = status === item.value;
          const Icon = item.value ? STATUS_ICON[item.value] : Grid2X2;
          return (
            <Pressable
              key={item.value ?? "all"}
              testID={`farm-filter-${item.value ?? "all"}`}
              onPress={() => setStatus(item.value as FarmStatus | undefined)}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              style={({ pressed }) => [
                styles.filter,
                {
                  backgroundColor: selected ? "#176B3A" : "#FFFDF8",
                  borderColor: selected ? "#176B3A" : "#CBD5CB",
                  opacity: pressed ? 0.72 : 1,
                },
              ]}
            >
              <Icon size={17} color={selected ? "#FFFFFF" : "#52635A"} />
              <AgText
                variant="bodySmall"
                weight={selected ? "semibold" : "medium"}
                style={{ color: selected ? "#FFFFFF" : "#27483A" }}
              >
                {t(item.labelKey)}
              </AgText>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );

  if (isLoading) {
    return (
      <AgScreen padded={false} backgroundColor="#FBF7EA">
        <View style={styles.stateContent}>
          {header}
          <FarmSkeleton />
          <FarmSkeleton />
        </View>
      </AgScreen>
    );
  }

  if (isError) {
    return (
      <AgScreen padded={false} backgroundColor="#FBF7EA">
        <View style={styles.stateContent}>
          {header}
          <AgErrorState onRetry={() => void refetch()} />
        </View>
      </AgScreen>
    );
  }

  const hasNoFarmsAtAll = !search && !status && loadedFarms.length === 0;

  return (
    <AgScreen padded={false} backgroundColor="#FBF7EA">
      <FlatList
        data={farms}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={header}
        contentContainerStyle={styles.listContent}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        renderItem={({ item }) => (
          <FarmCard
            farm={item}
            onView={() => router.push(`/farm/${item.id}`)}
            onEdit={() => router.push(`/farm/${item.id}/edit`)}
            onCalendar={() => goToCalendar(item.id)}
            onDelete={() => confirmDelete(item.id, item.name)}
          />
        )}
        onRefresh={() => void refetch()}
        refreshing={isRefetching}
        ListEmptyComponent={
          <View style={styles.emptyWrap}>
            <AgEmptyState
              icon={Sprout}
              title={
                hasNoFarmsAtAll
                  ? t("farm.emptyTitle")
                  : t("farm.noMatchingFarms")
              }
              message={
                hasNoFarmsAtAll
                  ? t("farm.emptyListMessage")
                  : t("farm.adjustFilters")
              }
              actionLabel={hasNoFarmsAtAll ? t("farm.addFarm") : undefined}
              onAction={hasNoFarmsAtAll ? goToAdd : undefined}
            />
          </View>
        }
        ListFooterComponent={
          loadedFarms.length > 0 ? <AddFarmCard onPress={goToAdd} /> : null
        }
      />
    </AgScreen>
  );
}

function HeaderButton({
  icon: Icon,
  label,
  onPress,
  primary = false,
}: {
  icon: LucideIcon;
  label: string;
  onPress: () => void;
  primary?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.headerButton,
        primary ? styles.headerButtonPrimary : styles.headerButtonNeutral,
        { opacity: pressed ? 0.72 : 1 },
      ]}
    >
      <Icon size={24} color={primary ? "#FFFFFF" : "#176B3A"} />
    </Pressable>
  );
}

function AddFarmCard({ onPress }: { onPress: () => void }) {
  const { t } = useTranslation();
  return (
    <Pressable
      testID="add-new-farm-card"
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={t("farm.addFarm")}
      style={({ pressed }) => [styles.addCard, { opacity: pressed ? 0.72 : 1 }]}
    >
      <View style={styles.addIcon}>
        <Plus size={27} color="#176B3A" />
      </View>
      <AgText variant="bodyLarge" weight="semibold" style={styles.addTitle}>
        {t("farm.addNewFarm")}
      </AgText>
      <AgText variant="bodySmall" center style={styles.addSubtitle}>
        {t("farm.addNewFarmSubtitle")}
      </AgText>
    </Pressable>
  );
}

function FarmSkeleton() {
  return <View style={styles.skeleton} />;
}

const styles = StyleSheet.create({
  stateContent: { flex: 1, paddingHorizontal: 20, backgroundColor: "#FBF7EA" },
  listContent: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingBottom: 110,
    backgroundColor: "#FBF7EA",
  },
  header: { gap: 16, paddingTop: 14, paddingBottom: 18 },
  title: { color: "#173B2B" },
  subtitle: { color: "#58685F", lineHeight: 21 },
  headerRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  headerCopy: { flex: 1, gap: 3 },
  headerActions: { flexDirection: "row", gap: 9 },
  headerButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  headerButtonPrimary: { backgroundColor: "#176B3A", borderColor: "#176B3A" },
  headerButtonNeutral: { backgroundColor: "#FFFDF8", borderColor: "#CBD5CB" },
  searchBox: {
    minHeight: 54,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderWidth: 1,
    borderColor: "#CBD5CB",
    backgroundColor: "#FFFDF8",
    borderRadius: 18,
    paddingHorizontal: 15,
  },
  searchInput: {
    flex: 1,
    minWidth: 0,
    color: "#173B2B",
    fontSize: 16,
    paddingVertical: 11,
  },
  filters: { gap: 9, paddingRight: 20 },
  filter: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    borderWidth: 1,
    borderRadius: 22,
    paddingHorizontal: 15,
  },
  separator: { height: 14 },
  emptyWrap: { minHeight: 320, flex: 1 },
  addCard: {
    minHeight: 190,
    borderWidth: 1,
    borderColor: "#8EBB94",
    borderStyle: "dashed",
    backgroundColor: "#F4F9F1",
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    padding: 22,
    marginTop: 18,
  },
  addIcon: {
    width: 58,
    height: 58,
    borderRadius: 29,
    borderWidth: 1,
    borderColor: "#BBD5BE",
    backgroundColor: "#E8F3E6",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 2,
  },
  addTitle: { color: "#173B2B" },
  addSubtitle: { color: "#58685F" },
  skeleton: {
    height: 220,
    borderRadius: 24,
    marginBottom: 14,
    opacity: 0.72,
    backgroundColor: "#D8D7C9",
  },
});
