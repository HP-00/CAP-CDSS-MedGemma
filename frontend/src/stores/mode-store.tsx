import { createContext, useCallback, useContext, useMemo, useState } from "react";

interface ModeContextValue {
  demoMode: boolean;
  setDemoMode: (v: boolean) => void;
}

const ModeContext = createContext<ModeContextValue | null>(null);

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const [demoMode, setDemoModeRaw] = useState(false);

  const setDemoMode = useCallback((v: boolean) => setDemoModeRaw(v), []);

  const value = useMemo(() => ({ demoMode, setDemoMode }), [demoMode, setDemoMode]);

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

export function useModeContext(): ModeContextValue {
  const ctx = useContext(ModeContext);
  if (!ctx) throw new Error("useModeContext must be used within ModeProvider");
  return ctx;
}
