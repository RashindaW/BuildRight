import { create } from "zustand";

interface UiState {
  cartOpen: boolean;
  chatOpen: boolean;
  sessionId: string;
  /** Product slugs the chat assistant grounded its last answer on (shown on the storefront). */
  shortlistedItemIds: string[];
  setCartOpen: (v: boolean) => void;
  setChatOpen: (v: boolean) => void;
  setShortlistedItemIds: (ids: string[]) => void;
  clearShortlist: () => void;
}

function getSessionId(): string {
  const key = "cutdry_session";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export const useUiStore = create<UiState>((set) => ({
  cartOpen: false,
  chatOpen: false,
  sessionId: getSessionId(),
  shortlistedItemIds: [],
  setCartOpen: (v) => set({ cartOpen: v }),
  setChatOpen: (v) => set({ chatOpen: v }),
  setShortlistedItemIds: (ids) => set({ shortlistedItemIds: ids }),
  clearShortlist: () => set({ shortlistedItemIds: [] }),
}));
