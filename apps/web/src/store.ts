import { create } from "zustand";
import { persist } from "zustand/middleware";

type Preferences = { theme: "light" | "dark"; uiLanguage: "en" | "mm" };
type Store = Preferences & { toggleTheme: () => void; setUiLanguage: (language: "en" | "mm") => void };

export const usePreferences = create<Store>()(persist((set) => ({
  theme: "light",
  uiLanguage: "en",
  toggleTheme: () => set((state) => ({ theme: state.theme === "light" ? "dark" : "light" })),
  setUiLanguage: (uiLanguage) => set({ uiLanguage }),
}), { name: "lingua-preferences", partialize: (state) => ({ theme: state.theme, uiLanguage: state.uiLanguage }) }));

