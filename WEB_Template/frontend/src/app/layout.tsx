import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { CookieProvider } from '@/contexts/CookieContext';
import { CookieConsentBanner, CookieSettingsModal } from '@/components/cookies';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-inter',
  display: 'swap',
});

// Značka MedTeam (NAVRH_UI Q5); env NEXT_PUBLIC_APP_NAME je ze šablony („Hackathon Template“), proto se nepoužívá.
const appName = 'MedTeam';

export const metadata: Metadata = {
  title: {
    default: appName,
    template: `%s | ${appName}`,
  },
  description:
    'MedTeam (MDT Copilot): podklady pro multidisciplinární onkologickou komisi s citacemi zdrojů. AI připravuje, rozhoduje lékař.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="cs" className={inter.variable} suppressHydrationWarning>
      <body
        className="min-h-dvh bg-background text-foreground antialiased"
        suppressHydrationWarning
      >
        <ThemeProvider>
          <CookieProvider>
            <AuthProvider>
              <Providers>{children}</Providers>
            </AuthProvider>
            <CookieConsentBanner />
            <CookieSettingsModal />
          </CookieProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

