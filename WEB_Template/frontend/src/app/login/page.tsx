import type { Metadata } from 'next';
import { Suspense } from 'react';
import LoginForm from './LoginForm';

export const metadata: Metadata = {
  title: 'Přihlásit se',
  description: 'Přihlášení do MedTeam: podklady pro multidisciplinární onkologickou komisi.',
};

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-dvh items-center justify-center bg-background" aria-busy="true">
          <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent motion-reduce:animate-none" />
          <span className="sr-only">Načítám přihlášení…</span>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
