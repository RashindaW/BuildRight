import { create } from "zustand";

interface UiState {
  cartOpen: boolean;
  chatOpen: boolean;
  sessionId: string;
  setCartOpen: (v: boolean) => void;
  setChatOpen: (v: boolean) => void;
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
  setCartOpen: (v) => set({ cartOpen: v }),
  setChatOpen: (v) => set({ chatOpen: v }),
}));
