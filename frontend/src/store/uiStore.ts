import { create } from "zustand";

interface UiState {
  cartOpen: boolean;
  chatOpen: boolean;
  sessionId: string;
  /** Product slugs the chat assistant grounded its last answer on (shown on the storefront). */
  shortlistedItemIds: string[];
  /** When true, the storefront shows ONLY the shortlisted items (set from the chat). */
  showOnlyShortlist: boolean;
  setCartOpen: (v: boolean) => void;
  setChatOpen: (v: boolean) => void;
  setShortlistedItemIds: (ids: string[]) => void;
  clearShortlist: () => void;
  setShowOnlyShortlist: (v: boolean) => void;
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
  showOnlyShortlist: false,
  setCartOpen: (v) => set({ cartOpen: v }),
  setChatOpen: (v) => set({ chatOpen: v }),
  setShortlistedItemIds: (ids) => set({ shortlistedItemIds: ids }),
  clearShortlist: () => set({ shortlistedItemIds: [], showOnlyShortlist: false }),
  setShowOnlyShortlist: (v) => set({ showOnlyShortlist: v }),
}));
