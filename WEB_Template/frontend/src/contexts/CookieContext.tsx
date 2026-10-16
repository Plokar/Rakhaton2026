'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  CookiePreferences,
  DEFAULT_COOKIE_PREFERENCES,
} from '@/types/cookies';
import {
  getStoredConsent,
  saveStoredConsent,
  removeStoredConsent,
} from '@/lib/cookies';

interface CookieContextType {
  preferences: CookiePreferences;
  hasAnswered: boolean;
  showBanner: boolean;
  isSettingsOpen: boolean;
  isLoaded: boolean;
  acceptAll: () => void;
  acceptNecessaryOnly: () => void;
  savePreferences: (prefs: Partial<CookiePreferences>) => void;
  openSettings: () => void;
  closeSettings: () => void;
  resetConsent: () => void;
}

const CookieContext = createContext<CookieContextType | undefined>(undefined);

export function CookieProvider({ children }: { children: React.ReactNode }) {
  const [preferences, setPreferences] = useState<CookiePreferences>(DEFAULT_COOKIE_PREFERENCES);
  const [hasAnswered, setHasAnswered] = useState<boolean>(false);
  const [showBanner, setShowBanner] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);

  // Načíst existující consent po připojení na klienta
  useEffect(() => {
    const existing = getStoredConsent();
    if (existing) {
      setPreferences(existing);
      setHasAnswered(true);
      setShowBanner(false);
    } else {
      setHasAnswered(false);
      // Malá prodleva (např. 300ms) pro plynulý nástup a aby to nepřebíjelo první render
      const timer = setTimeout(() => {
        setShowBanner(true);
      }, 300);
      return () => clearTimeout(timer);
    }
    setIsLoaded(true);
  }, []);

  const acceptAll = useCallback(() => {
    const updated = saveStoredConsent({
      necessary: true,
      analytics: true,
      marketing: true,
    });
    setPreferences(updated);
    setHasAnswered(true);
    setShowBanner(false);
    setIsSettingsOpen(false);
  }, []);

  const acceptNecessaryOnly = useCallback(() => {
    const updated = saveStoredConsent({
      necessary: true,
      analytics: false,
      marketing: false,
    });
    setPreferences(updated);
    setHasAnswered(true);
    setShowBanner(false);
    setIsSettingsOpen(false);
  }, []);

  const savePreferences = useCallback((prefs: Partial<CookiePreferences>) => {
    const updated = saveStoredConsent({
      necessary: true,
      analytics: Boolean(prefs.analytics),
      marketing: Boolean(prefs.marketing),
    });
    setPreferences(updated);
    setHasAnswered(true);
    setShowBanner(false);
    setIsSettingsOpen(false);
  }, []);

  const openSettings = useCallback(() => {
    setIsSettingsOpen(true);
  }, []);

  const closeSettings = useCallback(() => {
    setIsSettingsOpen(false);
  }, []);

  const resetConsent = useCallback(() => {
    removeStoredConsent();
    setPreferences(DEFAULT_COOKIE_PREFERENCES);
    setHasAnswered(false);
    setShowBanner(true);
    setIsSettingsOpen(false);
  }, []);

  return (
    <CookieContext.Provider
      value={{
        preferences,
        hasAnswered,
        showBanner,
        isSettingsOpen,
        isLoaded,
        acceptAll,
        acceptNecessaryOnly,
        savePreferences,
        openSettings,
        closeSettings,
        resetConsent,
      }}
    >
      {children}
    </CookieContext.Provider>
  );
}

export function useCookieConsent() {
  const context = useContext(CookieContext);
  if (!context) {
    throw new Error('useCookieConsent must be used within a CookieProvider');
  }
  return context;
}
