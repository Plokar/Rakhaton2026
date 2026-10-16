export type CookieCategory = 'necessary' | 'analytics' | 'marketing';

export interface CookiePreferences {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  updatedAt?: string;
  version?: number;
}

export interface CookieItem {
  name: string;
  provider: string;
  category: CookieCategory;
  duration: string;
  description: string;
}

export const CURRENT_COOKIE_VERSION = 1;

export const DEFAULT_COOKIE_PREFERENCES: CookiePreferences = {
  necessary: true,
  analytics: false,
  marketing: false,
};

export const KNOWN_COOKIES: CookieItem[] = [
  {
    name: 'access_token',
    provider: 'Hackathon OS Auth API',
    category: 'necessary',
    duration: '1 den / relace',
    description: 'Bezpečný JWT token v httpOnly cookie zajišťující ověření přihlášeného uživatele a ochranu API endpointů.',
  },
  {
    name: 'csrftoken',
    provider: 'Django Backend',
    category: 'necessary',
    duration: '1 rok',
    description: 'Chrání webové formuláře a API požadavky před útoky typu Cross-Site Request Forgery (CSRF).',
  },
  {
    name: 'cookie_consent',
    provider: 'Tato aplikace',
    category: 'necessary',
    duration: '1 rok',
    description: 'Uchovává vaše preference a vyjádřený souhlas s jednotlivými kategoriemi cookies.',
  },
  {
    name: 'theme',
    provider: 'Hackathon OS UI',
    category: 'marketing',
    duration: 'Trvalé (localStorage)',
    description: 'Ukládá zvolený grafický režim (tmavý / světlý / systémový) pro optimální vizuální zážitek.',
  },
  {
    name: '_hackathon_analytics',
    provider: 'Interní telemetrie',
    category: 'analytics',
    duration: '30 dní',
    description: 'Měří anonymizovanou návštěvnost stránek, rychlost odezvy API a výskyt klientských chyb za účelem ladění stability.',
  },
  {
    name: 'ai_studio_prefs',
    provider: 'AI Studio',
    category: 'marketing',
    duration: 'Relace / trvalé',
    description: 'Ukládá naposledy zvoleného AI providera (OpenAI, Gemini, Claude, Ollama) a parametry generování.',
  },
];
