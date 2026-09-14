import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, type UserInfo } from "../services/api";

export type UserMode = "consumer" | "industry";

interface AuthContextValue {
  user: UserInfo | null;
  mode: UserMode;
  setMode: (m: UserMode) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(() => {
    try {
      const raw = localStorage.getItem("bisbuddy_user");
      return raw ? (JSON.parse(raw) as UserInfo) : null;
    } catch {
      return null;
    }
  });
  const [mode, setModeState] = useState<UserMode>(() => {
    const m = localStorage.getItem("bisbuddy_mode");
    return m === "industry" ? "industry" : "consumer";
  });

  const persist = (u: UserInfo, token: string) => {
    localStorage.setItem("bisbuddy_token", token);
    localStorage.setItem("bisbuddy_user", JSON.stringify(u));
    setUser(u);
  };

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    persist(res.user, res.access_token);
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const res = await api.register(name, email, password);
      persist(res.user, res.access_token);
    },
    []
  );

  const setMode = useCallback((m: UserMode) => {
    localStorage.setItem("bisbuddy_mode", m);
    setModeState(m);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("bisbuddy_token");
    localStorage.removeItem("bisbuddy_user");
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, mode, setMode, login, register, logout }),
    [user, mode, setMode, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
