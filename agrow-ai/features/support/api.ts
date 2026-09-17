import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";

import type { SupportCategory, SupportTicket } from "./types";

export interface CreateSupportTicketInput {
  category: SupportCategory;
  subject: string;
  description: string;
  priority: "normal" | "high" | "urgent";
}

export const supportApi = {
  list: () => api.get<SupportTicket[]>(endpoints.support.tickets),
  create: (input: CreateSupportTicketInput) =>
    api.post<SupportTicket>(endpoints.support.tickets, input),
  reply: (id: string, message: string) =>
    api.post<SupportTicket>(endpoints.support.messages(id), { message }),
};
