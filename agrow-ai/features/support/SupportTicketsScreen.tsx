import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  CheckCircle2,
  LifeBuoy,
  MessageCircle,
  Send,
} from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { AgScreen, AgText } from "@/components/ui";

import { supportApi, type CreateSupportTicketInput } from "./api";
import type { SupportCategory, SupportTicket } from "./types";

const CATEGORIES: SupportCategory[] = [
  "app_issue",
  "market",
  "disease",
  "farm",
  "account",
  "other",
];
const C = {
  bg: "#F8F5EC",
  card: "#FFFDF8",
  text: "#173B2B",
  muted: "#52645A",
  green: "#17663A",
  pale: "#E9F3E5",
  border: "#D8D2C3",
  gold: "#B87500",
} as const;

export function SupportTicketsScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [category, setCategory] = useState<SupportCategory>("app_issue");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const tickets = useQuery({
    queryKey: ["support", "tickets"],
    queryFn: supportApi.list,
  });
  const create = useMutation({
    mutationFn: (input: CreateSupportTicketInput) => supportApi.create(input),
    onSuccess: () => {
      setSubject("");
      setDescription("");
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
      Alert.alert(t("support.sentTitle"), t("support.sentMessage"));
    },
    onError: () =>
      Alert.alert(t("support.errorTitle"), t("support.errorMessage")),
  });
  const valid = subject.trim().length >= 4 && description.trim().length >= 10;

  return (
    <AgScreen
      scroll
      backgroundColor={C.bg}
      contentContainerStyle={styles.content}
    >
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.iconButton}
          onPress={() => router.back()}
          accessibilityLabel={t("common.back")}
        >
          <ArrowLeft color={C.text} />
        </TouchableOpacity>
        <View style={styles.headerCopy}>
          <AgText variant="caption" weight="bold" style={styles.eyebrow}>
            {t("support.helpCenter")}
          </AgText>
          <AgText variant="headingL" weight="bold" style={styles.title}>
            {t("support.title")}
          </AgText>
        </View>
      </View>
      <View style={styles.intro}>
        <View style={styles.heroIcon}>
          <LifeBuoy size={30} color={C.green} />
        </View>
        <View style={styles.flex}>
          <AgText variant="headingS" weight="bold" style={styles.title}>
            {t("support.reportIssue")}
          </AgText>
          <AgText variant="bodySmall" style={styles.body}>
            {t("support.subtitle")}
          </AgText>
        </View>
      </View>

      {!showForm ? (
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() => setShowForm(true)}
        >
          <MessageCircle size={20} color="#FFFFFF" />
          <AgText weight="bold" style={styles.primaryButtonText}>
            {t("support.newTicket")}
          </AgText>
        </TouchableOpacity>
      ) : (
        <View style={styles.formCard}>
          <AgText variant="headingS" weight="bold" style={styles.title}>
            {t("support.newTicket")}
          </AgText>
          <AgText variant="bodySmall" style={styles.label}>
            {t("support.category")}
          </AgText>
          <View style={styles.chips}>
            {CATEGORIES.map((item) => (
              <TouchableOpacity
                key={item}
                onPress={() => setCategory(item)}
                style={[styles.chip, category === item && styles.chipSelected]}
                accessibilityRole="radio"
                accessibilityState={{ checked: category === item }}
              >
                <AgText
                  variant="caption"
                  weight="semibold"
                  style={
                    category === item
                      ? styles.chipSelectedText
                      : styles.chipText
                  }
                >
                  {t(`support.categories.${item}`)}
                </AgText>
              </TouchableOpacity>
            ))}
          </View>
          <AgText variant="bodySmall" style={styles.label}>
            {t("support.subject")}
          </AgText>
          <TextInput
            value={subject}
            onChangeText={setSubject}
            maxLength={120}
            placeholder={t("support.subjectPlaceholder")}
            placeholderTextColor={C.muted}
            style={styles.input}
          />
          <AgText variant="bodySmall" style={styles.label}>
            {t("support.description")}
          </AgText>
          <TextInput
            value={description}
            onChangeText={setDescription}
            maxLength={4000}
            multiline
            textAlignVertical="top"
            placeholder={t("support.descriptionPlaceholder")}
            placeholderTextColor={C.muted}
            style={[styles.input, styles.textarea]}
          />
          <AgText variant="caption" style={styles.privacy}>
            {t("support.privacyNote")}
          </AgText>
          <View style={styles.actions}>
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={() => setShowForm(false)}
            >
              <AgText weight="semibold" style={styles.secondaryText}>
                {t("common.cancel")}
              </AgText>
            </TouchableOpacity>
            <TouchableOpacity
              disabled={!valid || create.isPending}
              style={[
                styles.submitButton,
                (!valid || create.isPending) && styles.disabled,
              ]}
              onPress={() =>
                create.mutate({
                  category,
                  subject: subject.trim(),
                  description: description.trim(),
                  priority: "normal",
                })
              }
            >
              <Send size={18} color="#FFFFFF" />
              <AgText weight="bold" style={styles.primaryButtonText}>
                {create.isPending ? t("support.sending") : t("support.submit")}
              </AgText>
            </TouchableOpacity>
          </View>
        </View>
      )}

      <AgText variant="headingS" weight="bold" style={styles.sectionTitle}>
        {t("support.myTickets")}
      </AgText>
      {tickets.isLoading ? (
        <AgText style={styles.body}>{t("common.loading")}</AgText>
      ) : tickets.data?.length ? (
        tickets.data.map((ticket) => (
          <TicketCard key={ticket.id} ticket={ticket} t={t} />
        ))
      ) : (
        <View style={styles.empty}>
          <CheckCircle2 color={C.green} size={28} />
          <AgText weight="semibold" style={styles.title}>
            {t("support.noTickets")}
          </AgText>
        </View>
      )}
    </AgScreen>
  );
}

function TicketCard({
  ticket,
  t,
}: {
  ticket: SupportTicket;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const queryClient = useQueryClient();
  const [reply, setReply] = useState("");
  const sendReply = useMutation({
    mutationFn: () => supportApi.reply(ticket.id, reply.trim()),
    onSuccess: () => {
      setReply("");
      void queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
    },
  });
  const latestAdmin = [...ticket.messages]
    .reverse()
    .find((message) => message.author_type === "admin");
  return (
    <View style={styles.ticket}>
      <View style={styles.ticketTop}>
        <AgText weight="bold" style={[styles.title, styles.flex]}>
          {ticket.subject}
        </AgText>
        <View style={styles.status}>
          <AgText variant="caption" weight="bold" style={styles.statusText}>
            {t(`support.status.${ticket.status}`)}
          </AgText>
        </View>
      </View>
      <AgText variant="caption" style={styles.body}>
        {t(`support.categories.${ticket.category}`)} ·{" "}
        {new Date(ticket.created_at).toLocaleDateString()}
      </AgText>
      {latestAdmin ? (
        <View style={styles.reply}>
          <AgText variant="caption" weight="bold" style={styles.replyLabel}>
            {t("support.adminReply")}
          </AgText>
          <AgText variant="bodySmall" style={styles.body}>
            {latestAdmin.message}
          </AgText>
        </View>
      ) : null}
      {ticket.status === "waiting_for_farmer" ? (
        <View style={styles.farmerReply}>
          <TextInput
            value={reply}
            onChangeText={setReply}
            multiline
            maxLength={4000}
            placeholder={t("support.replyPlaceholder")}
            placeholderTextColor={C.muted}
            style={[styles.input, styles.replyInput]}
          />
          <TouchableOpacity
            disabled={!reply.trim() || sendReply.isPending}
            onPress={() => sendReply.mutate()}
            style={[
              styles.replyButton,
              (!reply.trim() || sendReply.isPending) && styles.disabled,
            ]}
          >
            <Send size={17} color="#FFFFFF" />
            <AgText weight="bold" style={styles.primaryButtonText}>
              {t("support.sendReply")}
            </AgText>
          </TouchableOpacity>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 12, paddingBottom: 80, gap: 14 },
  flex: { flex: 1 },
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  headerCopy: { flex: 1 },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.card,
    alignItems: "center",
    justifyContent: "center",
  },
  eyebrow: { color: C.gold, letterSpacing: 0.7, textTransform: "uppercase" },
  title: { color: C.text },
  body: { color: C.muted, lineHeight: 21 },
  intro: {
    flexDirection: "row",
    gap: 14,
    padding: 18,
    borderRadius: 22,
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.border,
  },
  heroIcon: {
    width: 58,
    height: 58,
    borderRadius: 18,
    backgroundColor: C.pale,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryButton: {
    minHeight: 54,
    borderRadius: 16,
    backgroundColor: C.green,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  primaryButtonText: { color: "#FFFFFF" },
  formCard: {
    gap: 10,
    padding: 18,
    borderRadius: 22,
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.border,
  },
  label: { color: C.text, marginTop: 4 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    minHeight: 44,
    paddingHorizontal: 13,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: C.border,
    alignItems: "center",
    justifyContent: "center",
  },
  chipSelected: { borderColor: C.green, backgroundColor: C.pale },
  chipText: { color: C.muted },
  chipSelectedText: { color: C.green },
  input: {
    minHeight: 52,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 14,
    color: C.text,
    fontSize: 16,
  },
  textarea: { minHeight: 132, paddingTop: 13 },
  privacy: { color: C.muted, lineHeight: 18 },
  actions: { flexDirection: "row", gap: 10, marginTop: 4 },
  secondaryButton: {
    minHeight: 50,
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: C.green,
  },
  secondaryText: { color: C.green },
  submitButton: {
    minHeight: 50,
    flex: 2,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    borderRadius: 14,
    backgroundColor: C.green,
  },
  disabled: { opacity: 0.45 },
  sectionTitle: { color: C.text, marginTop: 8 },
  ticket: {
    gap: 7,
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.card,
  },
  ticketTop: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  status: {
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 99,
    backgroundColor: C.pale,
  },
  statusText: { color: C.green },
  reply: {
    gap: 3,
    marginTop: 6,
    padding: 12,
    borderRadius: 12,
    backgroundColor: C.pale,
  },
  replyLabel: { color: C.green },
  farmerReply: { gap: 8, marginTop: 4 },
  replyInput: { minHeight: 88, paddingTop: 12 },
  replyButton: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    borderRadius: 14,
    backgroundColor: C.green,
  },
  empty: {
    minHeight: 110,
    gap: 8,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.card,
  },
});
