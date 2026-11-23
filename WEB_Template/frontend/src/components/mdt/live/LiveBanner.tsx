'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Radio } from 'lucide-react';
import { useMyLive } from './use-live';

/**
 * Pruh v celé aplikaci (T-357): právě probíhá zasedání, kde lékař má být nebo kde je, a kdo je na projektoru.
 * Klepnutí otevře živé zasedání. Nezobrazuje se na živém zasedání ani v jednání komise.
 */
export function LiveBanner() {
  const pathname = usePathname();
  const { data } = useMyLive();
  const item = data?.sessions.find((s) => s.id === data.current);
  if (!item || item.status !== 'in_progress' || pathname.startsWith('/dashboard/live') || pathname.startsWith(`/dashboard/mdt/${item.id}`)) return null;
  const onProjector = item.live.case?.patient_id;
  return (
    <Link
      href={`/dashboard/live?zasedani=${item.id}`}
      className="flex items-center gap-2 border-b border-emerald-300/60 bg-emerald-50 px-4 py-2 text-sm text-emerald-950 hover:bg-emerald-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:px-6 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-100"
    >
      <Radio className="size-4 shrink-0" aria-hidden />
      {/* jeden řádek i na telefonu (T-379): název zasedání se zkrátí */}
      <span className="min-w-0 truncate font-medium">
        <span className="hidden sm:inline">{item.here ? 'Jste na zasedání' : 'Probíhá zasedání'}: </span>
        {item.title}
      </span>
      {onProjector && (
        <span className="shrink-0 whitespace-nowrap">
          · <span className="hidden sm:inline">na projektoru</span> <span translate="no" className="font-semibold">{onProjector}</span>
        </span>
      )}
      <span className="ml-auto shrink-0 font-medium underline underline-offset-4">Otevřít</span>
    </Link>
  );
}
