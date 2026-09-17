import { useRouter } from "expo-router";
import { type ReactNode, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { SafeAreaView } from "react-native-safe-area-context";

import { AgErrorState, AgSkeleton } from "@/components/ui";
import { DailyFarmTaskCard } from "@/features/dailyFarmTask";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";

import { DashboardHeader } from "../components/DashboardHeader";
import { PriorityHeroCard } from "../components/PriorityHeroCard";
import { QuickActions } from "../components/QuickActions";
import { TodaysFarmCard } from "../components/TodaysFarmCard";
import { TodaysTasks } from "../components/TodaysTasks";
import { useDashboard } from "../hooks/useDashboard";

/** A subtly-animated dashboard section (60 FPS, UI-thread entering). */
function Section({ index, children }: { index: number; children: ReactNode }) {
  return (
    <Animated.View
      entering={FadeInDown.duration(350).delay(index * 60)}
      style={styles.sectionShell}
    >
      <View className="mt-5" style={styles.section}>
        {children}
      </View>
    </Animated.View>
  );
}

export function HomeScreen() {
  const router = useRouter();
  const { colors } = useAppTheme();
  const {
    user,
    farms,
    selected,
    select,
    tasks,
    farmsLoading,
    farmsError,
    refresh,
  } = useDashboard();

  const [refreshing, setRefreshing] = useState(false);
  const onRefresh = () => {
    setRefreshing(true);
    refresh();
    setTimeout(() => setRefreshing(false), 600);
  };

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerClassName="px-5 pb-10"
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary}
          />
        }
      >
        <DashboardHeader user={user} />

        {farms.length ? (
          <View className="mt-3">
            <FarmSelector
              farms={farms}
              selectedId={selected?.id ?? null}
              onSelect={select}
              light
              compact
            />
          </View>
        ) : null}

        <Section index={0}>
          <PriorityHeroCard />
        </Section>

        <Section index={1}>
          {farmsError ? (
            <AgErrorState onRetry={refresh} />
          ) : farmsLoading && !farms.length ? (
            <AgSkeleton style={styles.farmSkeleton} />
          ) : (
            <TodaysFarmCard
              farm={selected}
              onPress={() => {
                if (selected) router.push(`/farm/${selected.id}`);
              }}
              onRegister={() => router.push("/farm/new")}
            />
          )}
        </Section>

        <Section index={2}>
          <DailyFarmTaskCard />
        </Section>

        <Section index={3}>
          <TodaysTasks tasks={tasks} />
        </Section>

        <Section index={4}>
          <QuickActions />
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F7F4E8" },
  content: { paddingHorizontal: 18, paddingTop: 4, paddingBottom: 128 },
  sectionShell: { width: "100%", alignSelf: "stretch" },
  section: { width: "100%", alignSelf: "stretch", marginTop: 14 },
  farmSkeleton: { width: "100%", height: 190, borderRadius: 20 },
});
