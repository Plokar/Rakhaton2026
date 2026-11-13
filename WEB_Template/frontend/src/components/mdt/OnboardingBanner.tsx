'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Sparkles } from 'lucide-react';
import { buttonVariants } from '@/components/shadcn/button';
import { useMe } from './me';

/** Lékař po pozvánce ještě nedokončil průvodce nastavením (T-363): odkaz na něj nad obsahem. */
export function OnboardingBanner() {
  const me = useMe();
  const pathname = usePathname();
  if (!me || me.onboarding_done !== false || pathname.startsWith('/dashboard/vitejte')) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border bg-primary/5 px-4 py-2 text-sm sm:px-6">
      <Sparkles className="size-4 shrink-0 text-primary" aria-hidden />
      <span className="min-w-0 flex-1">
        Dokončete nastavení: jak má vypadat váš PVW (okno pro projektor), co od kolegů vyžadujete a vaše normy.
      </span>
      <Link href="/dashboard/vitejte" className={buttonVariants({ size: 'sm' })}>Pokračovat v nastavení</Link>
    </div>
  );
}
