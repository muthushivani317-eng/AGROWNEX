import { create } from 'zustand';

/** The active conversation shared between the chat screen and history. */
interface ChatState {
  activeConversationId: string | null;
  setActive: (id: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  setActive: (id) => set({ activeConversationId: id }),
}));
