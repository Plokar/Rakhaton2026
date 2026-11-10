import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { PILOT_FEEDBACK_URL } from '@/lib/pilot';

/** Kostra právních stránek (Zásady soukromí, Podmínky užití; T-371): čitelný text, bez marketingu. */
export function LegalPage({
  title,
  updated,
  intro,
  children,
}: {
  title: string;
  updated: string;
  intro: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <Link href="/login" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-4" aria-hidden /> Zpět do MDTcore
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/privacy" className="text-muted-foreground hover:text-foreground">Zásady soukromí</Link>
            <Link href="/terms" className="text-muted-foreground hover:text-foreground">Podmínky užití</Link>
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Platí od {updated} · pilotní provoz MDTcore</p>
        <div className="mt-6 text-base leading-relaxed text-muted-foreground">{intro}</div>
        <div className="mt-8 flex flex-col gap-8 text-[15px] leading-relaxed [&_h2]:mb-2 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-foreground [&_li]:ml-5 [&_li]:list-disc [&_ul]:flex [&_ul]:flex-col [&_ul]:gap-1">
          {children}
        </div>
      </main>
    </div>
  );
}

/** Kontakt na koordinátora pilotu (`NEXT_PUBLIC_PILOT_FEEDBACK_URL`); bez něj zástupný text pro provozovatele. */
export function PilotContact() {
  if (!PILOT_FEEDBACK_URL) return <Placeholder>kontakt na koordinátora pilotu</Placeholder>;
  const external = !PILOT_FEEDBACK_URL.startsWith('mailto:');
  return (
    <a href={PILOT_FEEDBACK_URL} className="font-medium text-foreground underline underline-offset-4"
      {...(external ? { target: '_blank', rel: 'noreferrer' } : {})}>
      koordinátor pilotu
    </a>
  );
}

/** Údaj, který doplní provozovatel pilotu (název, adresa, kontakt); nevymýšlíme ho. */
export function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <mark className="rounded bg-amber-100 px-1 text-amber-900 dark:bg-amber-950 dark:text-amber-200">
      [doplní provozovatel pilotu: {children}]
    </mark>
  );
}
