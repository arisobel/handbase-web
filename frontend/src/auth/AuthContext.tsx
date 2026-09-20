import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setSessionListener } from "../api/client";
import type {
  Capability,
  Identity,
  Membership,
  Session,
  SupportedLocale,
} from "../api/types";
import i18n, { applyDocumentDirection } from "../i18n";

interface AuthState {
  /** `undefined` while the initial session restore is still in flight. */
  session: Identity | null | undefined;
  login: (email: string, password: string) => Promise<Session>;
  logout: () => Promise<void>;
  setLocale: (locale: SupportedLocale) => Promise<void>;
  applyWorkspaceLocale: (locale: SupportedLocale) => void;
  refreshIdentity: () => Promise<void>;
  /** Capability check for one workspace; the server enforces the same rules. */
  can: (workspaceId: string | undefined, capability: Capability) => boolean;
  membershipFor: (workspaceId: string | undefined) => Membership | undefined;
}

const AuthContext = createContext<AuthState | null>(null);

function applyLocale(locale: SupportedLocale) {
  void i18n.changeLanguage(locale);
  localStorage.setItem("locale", locale);
  applyDocumentDirection(locale);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Identity | null | undefined>(undefined);

  // A silent refresh (triggered by any expired request) must reach React state
  // too, otherwise the token in memory and the one in context drift apart.
  useEffect(() => {
    setSessionListener((next) => setSession((current) => (next ? { ...current, ...next } : null)));
    return () => setSessionListener(null);
  }, []);

  // On load there is no access token in memory, but the browser may still hold
  // a refresh cookie from a previous visit.
  useEffect(() => {
    let cancelled = false;
    void api.restoreSession().then((restored) => {
      if (cancelled) return;
      setSession(restored);
      if (restored) applyLocale(restored.user.preferred_locale ?? restored.effective_locale);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const next = await api.login(email, password);
    setSession(next);
    // The account's stored preference wins over whatever this browser last used.
    applyLocale(next.user.preferred_locale ?? next.effective_locale);
    return next;
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setSession(null);
  }, []);

  const setLocale = useCallback(
    async (locale: SupportedLocale) => {
      applyLocale(locale);
      if (!session) return;
      // Persist it so the choice follows the account to any other device.
      const updated = await api.updateProfile({ preferred_locale: locale });
      setSession((current) => (current ? { ...current, user: updated.user } : current));
    },
    [session],
  );

  const applyWorkspaceLocale = useCallback(
    (locale: SupportedLocale) => {
      if (session && !session.user.preferred_locale) applyLocale(locale);
    },
    [session],
  );

  const refreshIdentity = useCallback(async () => {
    const updated = await api.me();
    setSession(updated);
    applyLocale(updated.user.preferred_locale ?? updated.effective_locale);
  }, []);

  const membershipFor = useCallback(
    (workspaceId: string | undefined) =>
      workspaceId
        ? session?.memberships.find((membership) => membership.workspace_id === workspaceId)
        : undefined,
    [session],
  );

  const can = useCallback(
    (workspaceId: string | undefined, capability: Capability) =>
      membershipFor(workspaceId)?.capabilities.includes(capability) ?? false,
    [membershipFor],
  );

  const value = useMemo<AuthState>(
    () => ({ session, login, logout, setLocale, applyWorkspaceLocale, refreshIdentity, can, membershipFor }),
    [session, login, logout, setLocale, applyWorkspaceLocale, refreshIdentity, can, membershipFor],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>.");
  return context;
}
