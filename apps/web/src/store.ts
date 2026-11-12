import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SavedTranslation = {
  id: string;
  sourceLanguage: string;
  targetLanguage: string;
  sourceText: string;
  translatedText: string;
  createdAt: string;
};

type Preferences = { theme: "light" | "dark"; uiLanguage: "en" | "mm" };
type Store = Preferences & {
  localLibraryOptIn: boolean;
  history: SavedTranslation[];
  favorites: SavedTranslation[];
  toggleTheme: () => void;
  setUiLanguage: (language: "en" | "mm") => void;
  setLocalLibraryOptIn: (enabled: boolean) => void;
  saveTranslation: (translation: SavedTranslation) => void;
  toggleFavorite: (translation: SavedTranslation) => void;
};

export const usePreferences = create<Store>()(persist((set) => ({
  theme: "light",
  uiLanguage: "en",
  localLibraryOptIn: false,
  history: [],
  favorites: [],
  toggleTheme: () => set((state) => ({ theme: state.theme === "light" ? "dark" : "light" })),
  setUiLanguage: (uiLanguage) => set({ uiLanguage }),
  setLocalLibraryOptIn: (enabled) => set((state) => ({
    localLibraryOptIn: enabled,
    history: enabled ? state.history : [],
    favorites: enabled ? state.favorites : [],
  })),
  saveTranslation: (translation) => set((state) => state.localLibraryOptIn
    ? { history: [translation, ...state.history.filter((item) => item.id !== translation.id)].slice(0, 50) }
    : state),
  toggleFavorite: (translation) => set((state) => {
    if (!state.localLibraryOptIn) return state;
    const exists = state.favorites.some((item) => item.id === translation.id);
    return { favorites: exists ? state.favorites.filter((item) => item.id !== translation.id) : [translation, ...state.favorites].slice(0, 50) };
  }),
}), {
  name: "lingua-preferences",
  partialize: (state) => ({
    theme: state.theme,
    uiLanguage: state.uiLanguage,
    localLibraryOptIn: state.localLibraryOptIn,
    history: state.localLibraryOptIn ? state.history : [],
    favorites: state.localLibraryOptIn ? state.favorites : [],
  }),
}));

