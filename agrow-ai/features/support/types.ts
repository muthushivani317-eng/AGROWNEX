export type SupportCategory =
  "app_issue" | "market" | "disease" | "farm" | "account" | "other";

export interface SupportMessage {
  id: string;
  author_type: "farmer" | "admin";
  message: string;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  category: SupportCategory;
  subject: string;
  description: string;
  priority: "normal" | "high" | "urgent";
  status: "open" | "in_progress" | "waiting_for_farmer" | "resolved" | "closed";
  created_at: string;
  updated_at: string;
  messages: SupportMessage[];
}
