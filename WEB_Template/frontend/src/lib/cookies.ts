import {
  CookiePreferences,
  CURRENT_COOKIE_VERSION,
  DEFAULT_COOKIE_PREFERENCES,
} from '@/types/cookies';

export const COOKIE_NAME = 'cookie_consent';
export const COOKIE_STORAGE_KEY = 'hackathon_cookie_consent';
export const COOKIE_CONSENT_EVENT = 'cookie_consent_updated';

/**
 * Přečte uloženou volbu cookies z document.cookie nebo z localStorage
 */
export function getStoredConsent(): CookiePreferences | null {
  if (typeof window === 'undefined') return null;

  try {
    // 1. Zkusit přečíst cookie
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const trimmed = c.trim();
      if (trimmed.startsWith(`${COOKIE_NAME}=`)) {
        const value = trimmed.substring(COOKIE_NAME.length + 1);
        const parsed = JSON.parse(decodeURIComponent(value));
        if (parsed && typeof parsed.necessary === 'boolean') {
          return {
            necessary: true,
            analytics: Boolean(parsed.analytics),
            marketing: Boolean(parsed.marketing),
            updatedAt: parsed.updatedAt || new Date().toISOString(),
            version: parsed.version || CURRENT_COOKIE_VERSION,
          };
        }
      }
    }

    // 2. Fallback na localStorage
    const local = localStorage.getItem(COOKIE_STORAGE_KEY);
    if (local) {
      const parsed = JSON.parse(local);
      if (parsed && typeof parsed.necessary === 'boolean') {
        return {
          necessary: true,
          analytics: Boolean(parsed.analytics),
          marketing: Boolean(parsed.marketing),
          updatedAt: parsed.updatedAt || new Date().toISOString(),
          version: parsed.version || CURRENT_COOKIE_VERSION,
        };
      }
    }
  } catch (err) {
    console.warn('[Cookies] Chyba při čtení uloženého souhlasu:', err);
  }

  return null;
}

/**
 * Uloží vybrané preference do cookie i do localStorage a vyšle event
 */
export function saveStoredConsent(preferences: Partial<CookiePreferences>): CookiePreferences {
  if (typeof window === 'undefined') {
    return {
      ...DEFAULT_COOKIE_PREFERENCES,
      ...preferences,
      necessary: true,
      updatedAt: new Date().toISOString(),
      version: CURRENT_COOKIE_VERSION,
    };
  }

  const completePreferences: CookiePreferences = {
    necessary: true,
    analytics: Boolean(preferences.analytics),
    marketing: Boolean(preferences.marketing),
    updatedAt: new Date().toISOString(),
    version: CURRENT_COOKIE_VERSION,
  };

  try {
    const jsonVal = JSON.stringify(completePreferences);

    // 1. Uložit do localStorage
    localStorage.setItem(COOKIE_STORAGE_KEY, jsonVal);

    // 2. Uložit do document.cookie (platnost 1 rok, SameSite=Lax, cesta /)
    const isSecure = window.location.protocol === 'https:' ? '; Secure' : '';
    const maxAge = 60 * 60 * 24 * 365; // 365 dní
    document.cookie = `${COOKIE_NAME}=${encodeURIComponent(jsonVal)}; path=/; max-age=${maxAge}; SameSite=Lax${isSecure}`;

    // 3. Dispatch události pro libovolné analytické knihovny
    window.dispatchEvent(
      new CustomEvent(COOKIE_CONSENT_EVENT, {
        detail: completePreferences,
      })
    );
  } catch (err) {
    console.error('[Cookies] Chyba při ukládání souhlasu:', err);
  }

  return completePreferences;
}

/**
 * Vymaže uložený souhlas (vhodné pro testování nebo reset)
 */
export function removeStoredConsent(): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(COOKIE_STORAGE_KEY);
    document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
    window.dispatchEvent(
      new CustomEvent(COOKIE_CONSENT_EVENT, {
        detail: null,
      })
    );
  } catch (err) {
    console.error('[Cookies] Chyba při mazání souhlasu:', err);
  }
}
