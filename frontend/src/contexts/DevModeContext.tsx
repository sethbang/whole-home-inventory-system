import React, { createContext, useContext, useState, useEffect } from 'react';

interface DevModeContextType {
  isDevMode: boolean;
  toggleDevMode: () => void;
}

const DevModeContext = createContext<DevModeContextType | undefined>(undefined);

export function DevModeProvider({ children }: { children: React.ReactNode }) {
  const [isDevMode, setIsDevMode] = useState(() => {
    const saved = localStorage.getItem('whis_dev_mode');
    // Default to false in production, only true in development if explicitly enabled
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    localStorage.setItem('whis_dev_mode', JSON.stringify(isDevMode));
  }, [isDevMode]);

  const toggleDevMode = () => {
    setIsDevMode((prev: boolean) => !prev);
  };

  return (
    <DevModeContext.Provider value={{ isDevMode, toggleDevMode }}>
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