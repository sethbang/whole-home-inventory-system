import React, { createContext, useContext, useEffect, useState } from 'react';

interface DevModeContextType {
  isDevMode: boolean;
  toggleDevMode: () => void;
}

const DevModeContext = createContext<DevModeContextType | undefined>(undefined);

// Dev mode is only ever available in development builds. In production builds
// (`import.meta.env.DEV === false`) the provider is a hard-off no-op so that
// a compromised localStorage entry can never bypass auth in a shipped app.
const DEV_BUILD = import.meta.env.DEV;

export function DevModeProvider({ children }: { children: React.ReactNode }) {
  const [isDevMode, setIsDevMode] = useState<boolean>(() => {
    if (!DEV_BUILD) return false;
    const saved = localStorage.getItem('whis_dev_mode');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    if (!DEV_BUILD) return;
    localStorage.setItem('whis_dev_mode', JSON.stringify(isDevMode));
  }, [isDevMode]);

  const toggleDevMode = () => {
    if (!DEV_BUILD) return;
    setIsDevMode((prev) => !prev);
  };

  return (
    <DevModeContext.Provider value={{ isDevMode: DEV_BUILD && isDevMode, toggleDevMode }}>
      {children}
    </DevModeContext.Provider>
  );
}

export function useDevMode() {
  const context = useContext(DevModeContext);
  if (context === undefined) {
    throw new Error('useDevMode must be used within a DevModeProvider');
  }
  return context;
}
