'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { authApi, refreshSession, type RegisterData, type User } from '@/lib/api';

/** Access cookie platí 15 min: obnovit dřív, ať nevyprší, dokud je aplikace otevřená (T-336). */
const RENEW_EVERY_MS = 10 * 60_000;

/** Na chráněnou stránku pustí proxy.ts jen s access nebo refresh cookie, jinde (přihlášení) obnova nemá smysl. */
const PROTECTED_PATHS = ['/dashboard', '/brief', '/projector'];
const onProtectedPage = () =>
  typeof window !== 'undefined' && PROTECTED_PATHS.some((path) => window.location.pathname.startsWith(path));

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  /** Načte aktuálního uživatele ze serveru (stav se nastaví až v callbacku promise). */
  const refreshUser = useCallback(
    () =>
      authApi
        .checkStatus()
        // access cookie mohla vypršet, refresh cookie ale platí 7 dní (T-336)
        .then(async (status) =>
          status.authenticated || !onProtectedPage() || !(await refreshSession()) ? status : authApi.checkStatus(),
        )
        .then((status) =>
          setState({ user: status.user, isAuthenticated: status.authenticated, isLoading: false }),
        )
        .catch(() => setState({ user: null, isAuthenticated: false, isLoading: false })),
    [],
  );

  // Při mountu zkontrolovat auth status (JWT cookie)
  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  // Průběžná obnova přihlášení: přechod mezi stránkami (proxy.ts) ani živý chat (SSE) po 15 min neodpadne (T-336).
  // Uspaná záložka časovač brzdí, proto obnova i po návratu do okna.
  useEffect(() => {
    if (!state.isAuthenticated) return;
    let last = Date.now();
    const renew = () => {
      last = Date.now();
      void refreshSession();
    };
    const timer = setInterval(renew, RENEW_EVERY_MS);
    const onVisible = () => {
      if (document.visibilityState === 'visible' && Date.now() - last >= RENEW_EVERY_MS) renew();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [state.isAuthenticated]);

  const login = useCallback(
    async (username: string, password: string) => {
      const response = await authApi.login({ username, password });
      setState({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
    },
    [],
  );

  const register = useCallback(
    async (data: RegisterData) => {
      const response = await authApi.register(data);
      setState({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setState({ user: null, isAuthenticated: false, isLoading: false });
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login, register, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
