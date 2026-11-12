import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthUser } from "./types";

export type SavedTranslation = {
  id: string;
  sourceLanguage: string;
  targetLanguage: string;
  sourceText: string;
  translatedText: string;
  createdAt: string;
  updatedAt?: string;
};

type Preferences = { theme: "light" | "dark"; uiLanguage: "en" | "mm" };
type Store = Preferences & {
  localLibraryOptIn: boolean;
  history: SavedTranslation[];
  favorites: SavedTranslation[];
  toggleTheme: () => void;
  setTheme: (theme: "light" | "dark") => void;
  setUiLanguage: (language: "en" | "mm") => void;
  setLocalLibraryOptIn: (enabled: boolean) => void;
  saveTranslation: (translation: SavedTranslation) => void;
  toggleFavorite: (translation: SavedTranslation) => void;
  clearLocalLibrary: () => void;
  mergeSynced: (items: SavedTranslation[], deletedIds: string[], favoriteIds?: string[]) => void;
};

export const usePreferences = create<Store>()(persist((set) => ({
  theme: "light",
  uiLanguage: "en",
  localLibraryOptIn: false,
  history: [],
  favorites: [],
  toggleTheme: () => set((state) => ({ theme: state.theme === "light" ? "dark" : "light" })),
  setTheme: (theme) => set({ theme }),
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
  clearLocalLibrary: () => set({ history: [], favorites: [] }),
  mergeSynced: (items, deletedIds, favoriteIds = []) => set((state) => {
    const removed = new Set(deletedIds);
    const merged = [...items, ...state.history].filter((item, index, all) => !removed.has(item.id) && all.findIndex((candidate) => candidate.id === item.id) === index);
    const favoriteSet = new Set(favoriteIds);
    const favorites = favoriteIds.length ? merged.filter((item) => favoriteSet.has(item.id)) : state.favorites.filter((item) => !removed.has(item.id));
    return { history: merged.slice(0, 50), favorites: favorites.slice(0, 50) };
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

type AuthStore = {
  user: AuthUser | null;
  checked: boolean;
  setUser: (user: AuthUser) => void;
  clearUser: () => void;
  setChecked: (checked: boolean) => void;
};

// Authentication state is deliberately memory-only. The server owns the
// HttpOnly session cookie; no session secret is persisted in localStorage.
export const useAuth = create<AuthStore>((set) => ({
  user: null,
  checked: false,
  setUser: (user) => set({ user, checked: true }),
  clearUser: () => set({ user: null, checked: true }),
  setChecked: (checked) => set({ checked }),
}));

