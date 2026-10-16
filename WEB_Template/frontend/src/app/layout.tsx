import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { CookieProvider } from '@/contexts/CookieContext';
import { CookieConsentBanner, CookieSettingsModal } from '@/components/cookies';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const appName = process.env.NEXT_PUBLIC_APP_NAME || 'MDT Copilot';
const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

export const metadata: Metadata = {
  title: {
    default: appName,
    template: `%s | ${appName}`,
  },
  description:
    'Podklady pro multidisciplinární onkologickou komisi (MDT) s citacemi zdrojů. AI připravuje, rozhoduje lékař.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="cs" className={inter.variable} suppressHydrationWarning>
      <body
        className="min-h-screen bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary"
        suppressHydrationWarning
      >
        <ThemeProvider>
          <CookieProvider>
            <AuthProvider>{children}</AuthProvider>
            <CookieConsentBanner />
            <CookieSettingsModal />
          </CookieProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

