import { useRouter } from "expo-router";
import type { ReactNode } from "react";
import {
  Award,
  Building2,
  ChevronRight,
  LayoutDashboard,
  Leaf,
  LifeBuoy,
  LockKeyhole,
  Map,
  MapPin,
  Pencil,
  Phone,
  Settings,
  ShieldCheck,
  Sprout,
  TriangleAlert,
  UserPlus,
  type LucideIcon,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import {
  RefreshControl,
  StyleSheet,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from "react-native";

import {
  AgAvatar,
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { COMMON_CROPS } from "@/constants/crops";
import { TAMIL_NADU_DISTRICTS } from "@/constants/locations";
import { useAdminMe } from "@/features/admin";
import { useAuth } from "@/features/auth";
import { useLanguage } from "@/hooks/useLanguage";
import { ApiError } from "@/types";
import { formatIndianPhone } from "@/utils/format";

import { useProfile } from "../hooks/useProfile";

const PAGE_BG = "#FBF7EA";
const CARD_BG = "#FFFDF8";
const PRIMARY_TEXT = "#173B2B";
const SECONDARY_TEXT = "#58685F";
const GREEN = "#176B3A";
const PALE_GREEN = "#EEF6EC";
const BORDER = "#D8D7C9";

function ProfileSkeleton() {
  return (
    <View className="pt-2">
      <View className="flex-row items-start justify-between gap-4">
        <View className="flex-1">
          <AgSkeleton className="h-8 w-32 rounded-md" />
          <AgSkeleton className="mt-2 h-4 w-64 rounded-md" />
        </View>
        <AgSkeleton className="h-11 w-28 rounded-xl" />
      </View>
      <AgSkeleton className="mt-6 h-44 w-full rounded-card" />
      <AgSkeleton className="mt-5 h-72 w-full rounded-card" />
      <AgSkeleton className="mt-5 h-52 w-full rounded-card" />
    </View>
  );
}

interface SectionCardProps {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  children: ReactNode;
}

function SectionCard({
  icon: Icon,
  title,
  subtitle,
  children,
}: SectionCardProps) {
  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeader}>
        <View style={styles.headerIcon}>
          <Icon size={25} color={GREEN} strokeWidth={2.2} />
        </View>
        <View style={styles.flexOne}>
          <AgText variant="headingS" weight="bold" style={styles.primaryText}>
            {title}
          </AgText>
          <AgText
            variant="caption"
            className="mt-1"
            style={styles.secondaryText}
          >
            {subtitle}
          </AgText>
        </View>
      </View>
      <View style={styles.rows}>{children}</View>
    </View>
  );
}

interface ProfileRowProps {
  icon: LucideIcon;
  label: string;
  value: string;
  onPress: () => void;
  last?: boolean;
  accentValue?: boolean;
}

function ProfileRow({
  icon: Icon,
  label,
  value,
  onPress,
  last,
  accentValue,
}: ProfileRowProps) {
  return (
    <TouchableOpacity
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${label}: ${value}`}
      activeOpacity={0.72}
      style={[styles.profileRow, !last && styles.profileRowDivider]}
    >
      <View style={styles.rowIcon}>
        <Icon size={22} color={GREEN} strokeWidth={2.1} />
      </View>
      <View style={styles.rowCopy}>
        <AgText
          variant="caption"
          style={styles.secondaryText}
          maxFontSizeMultiplier={1.2}
        >
          {label}
        </AgText>
        <AgText
          variant="body"
          weight="semibold"
          className="mt-0.5"
          numberOfLines={2}
          maxFontSizeMultiplier={1.2}
          style={accentValue ? styles.accentText : styles.primaryText}
        >
          {value}
        </AgText>
      </View>
      <View style={styles.chevronCircle}>
        <ChevronRight size={20} color={GREEN} />
      </View>
    </TouchableOpacity>
  );
}

export function ProfileScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { language } = useLanguage();
  const { width } = useWindowDimensions();
  const { user } = useAuth();
  const {
    data: profile,
    error,
    isLoading,
    isRefetchError,
    isRefetching,
    refetch,
  } = useProfile();
  const { data: admin } = useAdminMe();
  const compact = width < 360;

  if (isLoading) {
    return (
      <AgScreen scroll backgroundColor={PAGE_BG}>
        <ProfileSkeleton />
      </AgScreen>
    );
  }

  if (!profile) {
    return (
      <AgScreen backgroundColor={PAGE_BG}>
        <AgErrorState
          light
          offline={error instanceof ApiError && error.isNetwork}
          onRetry={() => void refetch()}
        />
      </AgScreen>
    );
  }

  if (!user?.profileCompleted || !profile.fullName.trim()) {
    return (
      <AgScreen backgroundColor={PAGE_BG}>
        <AgEmptyState
          icon={UserPlus}
          title={t("profile.emptyTitle")}
          message={t("profile.emptyMessage")}
          actionLabel={t("profile.completeCta")}
          onAction={() => router.push("/profile/edit")}
        />
      </AgScreen>
    );
  }

  const notSet = t("profile.notSet");
  const district = TAMIL_NADU_DISTRICTS.find(
    (item) => item.id === profile.district,
  );
  const districtLabel = district
    ? language === "ta"
      ? district.ta
      : district.en
    : notSet;
  const cropLabels = profile.preferredCrops.map((id) => {
    const crop = COMMON_CROPS.find((item) => item.id === id);
    return crop ? (language === "ta" ? crop.ta : crop.en) : id;
  });
  const experience =
    profile.experienceYears == null ? notSet : String(profile.experienceYears);
  const crops = cropLabels.length
    ? cropLabels.join(", ")
    : t("profile.preferredCropsEmpty");
  const editProfile = () => router.push("/profile/edit");

  return (
    <AgScreen
      scroll
      backgroundColor={PAGE_BG}
      contentContainerStyle={styles.screenContent}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={() => void refetch()}
          colors={[GREEN]}
          tintColor={GREEN}
        />
      }
    >
      <View style={styles.pageHeader}>
        <View style={styles.headerCopy}>
          <AgText variant="headingL" weight="bold" style={styles.primaryText}>
            {t("tabs.profile")}
          </AgText>
          <AgText variant="body" className="mt-1" style={styles.secondaryText}>
            {t("profile.profileSubtitle")}
          </AgText>
        </View>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityLabel={t("profile.editProfileButton")}
          activeOpacity={0.72}
          onPress={editProfile}
          style={styles.editButton}
        >
          <Pencil size={18} color={GREEN} />
          <AgText
            variant="body"
            weight="semibold"
            numberOfLines={1}
            style={[styles.greenText, styles.editButtonText]}
          >
            {t("profile.editProfileButton")}
          </AgText>
        </TouchableOpacity>
      </View>

      {isRefetchError ? (
        <View style={styles.refreshWarning} accessibilityRole="alert">
          <TriangleAlert size={21} color="#9A5B12" />
          <AgText variant="caption" style={styles.refreshWarningText}>
            {t("profile.refreshFailedCached")}
          </AgText>
        </View>
      ) : null}

      <View style={styles.identityCard}>
        <Leaf
          size={116}
          color={GREEN}
          opacity={0.08}
          style={styles.identityLeaf}
          pointerEvents="none"
        />
        <View
          style={[
            styles.identityContent,
            compact && styles.identityContentCompact,
          ]}
        >
          <View style={styles.avatarHalo}>
            <AgAvatar
              uri={profile.photoUrl}
              name={profile.fullName}
              size={92}
              light
            />
          </View>
          <View
            style={[styles.identityCopy, compact && styles.identityCopyCompact]}
          >
            <AgText
              variant="headingM"
              weight="bold"
              numberOfLines={2}
              style={styles.primaryText}
            >
              {profile.fullName}
            </AgText>
            <View style={styles.phoneRow}>
              <Phone size={17} color={SECONDARY_TEXT} />
              <AgText
                variant="body"
                numberOfLines={1}
                style={styles.primaryText}
              >
                {profile.phone ? formatIndianPhone(profile.phone) : notSet}
              </AgText>
            </View>
          </View>
        </View>
      </View>

      <SectionCard
        icon={MapPin}
        title={t("profile.location")}
        subtitle={t("profile.locationSubtitle")}
      >
        <ProfileRow
          icon={Map}
          label={t("profile.district")}
          value={districtLabel}
          onPress={editProfile}
        />
        <ProfileRow
          icon={Building2}
          label={t("profile.block")}
          value={profile.block || notSet}
          onPress={editProfile}
        />
        <ProfileRow
          icon={MapPin}
          label={t("profile.village")}
          value={profile.village || notSet}
          onPress={editProfile}
          last
        />
      </SectionCard>

      <SectionCard
        icon={Sprout}
        title={t("profile.farming")}
        subtitle={t("profile.farmingSubtitle")}
      >
        <ProfileRow
          icon={Award}
          label={t("profile.experience")}
          value={experience}
          onPress={editProfile}
        />
        <ProfileRow
          icon={Sprout}
          label={t("profile.crops")}
          value={crops}
          onPress={editProfile}
          accentValue={!cropLabels.length}
          last
        />
      </SectionCard>

      <SectionCard
        icon={Settings}
        title={t("profile.account")}
        subtitle={t("profile.accountSubtitle")}
      >
        <ProfileRow
          icon={LockKeyhole}
          label={t("profile.accountSettings")}
          value={t("profile.accountSettingsRedesignDesc")}
          onPress={() => router.push("/profile/account")}
        />
        <ProfileRow
          icon={LifeBuoy}
          label={t("support.reportIssue")}
          value={t("support.profileDescription")}
          onPress={() => router.push("/support" as never)}
          last
        />
      </SectionCard>

      {admin ? (
        <TouchableOpacity
          onPress={() => router.push("/admin")}
          accessibilityRole="button"
          accessibilityLabel={t("admin.entry")}
          activeOpacity={0.72}
          style={styles.adminCard}
        >
          <View style={styles.rowIcon}>
            <LayoutDashboard size={22} color={GREEN} />
          </View>
          <View style={styles.flexOne}>
            <AgText variant="body" weight="semibold" style={styles.primaryText}>
              {t("admin.entry")}
            </AgText>
            <AgText variant="caption" style={styles.secondaryText}>
              {t("admin.entryDesc")}
            </AgText>
          </View>
          <View style={styles.chevronCircle}>
            <ChevronRight size={20} color={GREEN} />
          </View>
        </TouchableOpacity>
      ) : null}

      <View style={styles.privacyCard}>
        <ShieldCheck size={28} color={GREEN} />
        <View style={styles.flexOne}>
          <AgText variant="body" weight="bold" style={styles.greenText}>
            {t("profile.privacyMatters")}
          </AgText>
          <AgText variant="caption" className="mt-1" style={styles.primaryText}>
            {t("profile.privacyManage")}
          </AgText>
        </View>
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screenContent: { paddingTop: 12, paddingBottom: 128 },
  flexOne: { flex: 1 },
  primaryText: { color: PRIMARY_TEXT },
  secondaryText: { color: SECONDARY_TEXT },
  greenText: { color: GREEN },
  accentText: { color: GREEN },
  // Stacked: Tamil title + edit label are too long to share one row.
  pageHeader: { flexDirection: "column", gap: 14 },
  headerCopy: { alignSelf: "stretch" },
  editButton: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 17,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: GREEN,
    backgroundColor: CARD_BG,
    alignSelf: "stretch",
  },
  editButtonText: { flexShrink: 1 },
  refreshWarning: {
    marginTop: 16,
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 11,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#E8C98A",
    backgroundColor: "#FFF7E7",
  },
  refreshWarningText: { flex: 1, color: "#70430F" },
  identityCard: {
    marginTop: 22,
    padding: 20,
    overflow: "hidden",
    borderRadius: 22,
    borderWidth: 1,
    borderColor: "#BCD4BE",
    backgroundColor: CARD_BG,
    elevation: 2,
    shadowColor: "#173B2B",
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
  },
  identityLeaf: {
    position: "absolute",
    right: -18,
    bottom: -24,
    transform: [{ rotate: "-20deg" }],
  },
  identityContent: { flexDirection: "row", alignItems: "center", gap: 22 },
  identityContentCompact: {
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 14,
  },
  avatarHalo: {
    width: 116,
    height: 116,
    borderRadius: 58,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: PALE_GREEN,
  },
  identityCopy: { flex: 1, minWidth: 0 },
  identityCopyCompact: { width: "100%" },
  phoneRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    marginTop: 15,
  },
  sectionCard: {
    marginTop: 16,
    padding: 16,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: CARD_BG,
    elevation: 1,
    shadowColor: "#173B2B",
    shadowOpacity: 0.055,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    marginBottom: 15,
  },
  headerIcon: {
    width: 54,
    height: 54,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: PALE_GREEN,
  },
  rows: {
    overflow: "hidden",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E1DFD3",
    backgroundColor: "#FFFFFF",
  },
  profileRow: {
    minHeight: 82,
    width: "100%",
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: "#FFFFFF",
  },
  profileRowDivider: { borderBottomWidth: 1, borderBottomColor: "#E7E4D9" },
  rowIcon: {
    width: 48,
    height: 48,
    borderRadius: 13,
    flexShrink: 0,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: PALE_GREEN,
  },
  rowCopy: { flex: 1, minWidth: 0, paddingVertical: 1 },
  chevronCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    flexShrink: 0,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: "auto",
    backgroundColor: PALE_GREEN,
  },
  adminCard: {
    minHeight: 82,
    marginTop: 16,
    paddingHorizontal: 16,
    paddingVertical: 13,
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: CARD_BG,
  },
  privacyCard: {
    marginTop: 18,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 14,
    padding: 18,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#BBD9BE",
    backgroundColor: "#EEF7EA",
  },
});
