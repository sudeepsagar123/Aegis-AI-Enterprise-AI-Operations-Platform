/**
 * Aegis AI — Auth Store (Zustand).
 *
 * Global authentication state management with:
 * - Login/logout flows
 * - Token persistence via sessionStorage
 * - User profile caching
 * - Role-based access helpers
 */

import { create } from "zustand";
import { api, setTokens, clearTokens, getAccessToken, type UserProfile, type TokenPair } from "./api-client";

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; org_name: string }) => Promise<void>;
  logout: () => void;
  loadProfile: () => Promise<void>;
  clearError: () => void;

  // RBAC helpers
  hasRole: (role: string) => boolean;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: !!getAccessToken(),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const tokens = await api.auth.login(email, password);
      setTokens(tokens);
      const user = await api.auth.me();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (err: any) {
      set({
        error: err?.detail || err?.message || "Login failed",
        isLoading: false,
        isAuthenticated: false,
      });
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.auth.register(data);
      setTokens(res.tokens);
      set({
        user: res.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        error: err?.detail || err?.message || "Registration failed",
        isLoading: false,
      });
    }
  },

  logout: () => {
    clearTokens();
    set({ user: null, isAuthenticated: false, error: null });
  },

  loadProfile: async () => {
    if (!getAccessToken()) return;
    set({ isLoading: true });
    try {
      const user = await api.auth.me();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      clearTokens();
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),

  hasRole: (role: string) => get().user?.role === role,

  isAdmin: () => {
    const role = get().user?.role;
    return role === "super_admin" || role === "org_admin";
  },
}));
