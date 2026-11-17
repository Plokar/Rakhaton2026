'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Radio } from 'lucide-react';
import { toast } from 'sonner';
import { useLiveSession, useMyLive } from './use-live';

/**
 * Pruh v celé aplikaci (T-357): právě probíhá zasedání, kde lékař má být nebo kde je, a kdo je na projektoru.
 * Klepnutí otevře živé zasedání. Nezobrazuje se na živém zasedání ani v jednání komise.
 *
 * T-380: pruh se mění živě (sdílený stream zasedání) a zadávající lékař dostane upozornění, když jeho pacient
 * jde na řadu jako další a když je na projektoru, i na jiné stránce aplikace.
 */
export function LiveBanner() {
  const pathname = usePathname();
  const { data } = useMyLive();
  const item = data?.sessions.find((s) => s.id === data.current);
  // i na dnešní nezahájené: zahájení přijde ze streamu hned, ne až s dalším obnovením přehledu (60 s)
  const { live: streamed } = useLiveSession(item && item.status !== 'closed' ? item.id : null);
  const live = streamed ?? item?.live ?? null;
  useMyPatientAlerts(item ? { id: item.id, mine: item.my_patients } : null, live);

  if (!item || live?.status !== 'in_progress' || pathname.startsWith('/dashboard/live') || pathname.startsWith(`/dashboard/mdt/${item.id}`)) return null;
  const onProjector = live.case?.patient_id;
  const mine = item.my_patients;
  const mineNow = onProjector && mine.includes(onProjector);
  const mineNext = live.next && mine.includes(live.next.patient_id);
  return (
    <Link
      href={`/dashboard/live?zasedani=${item.id}`}
      className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-emerald-300/60 bg-emerald-50 px-4 py-2 text-sm text-emerald-950 hover:bg-emerald-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:px-6 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-100"
    >
      <Radio className="size-4 shrink-0" aria-hidden />
      <span className="font-medium">{item.here ? 'Jste na zasedání' : 'Probíhá zasedání'}: {item.title}</span>
      {onProjector && (
        <span>
          · na projektoru <span translate="no" className="font-semibold">{onProjector}</span>
          {mineNow ? ' (váš pacient)' : ''}
        </span>
      )}
      {!mineNow && mineNext && (
        <span className="font-medium">
          · váš pacient <span translate="no">{live.next!.patient_id}</span> je další
        </span>
      )}
      <span className="ml-auto font-medium underline underline-offset-4">Otevřít</span>
    </Link>
  );
}

/** Upozornění jednou za změnu: „váš pacient je další“ a „váš pacient je na projektoru“ (toast + vibrace mobilu). */
function useMyPatientAlerts(
  session: { id: number; mine: string[] } | null,
  live: { status: string; case: { patient_id: string } | null; next: { patient_id: string } | null } | null,
) {
  const router = useRouter();
  const shown = React.useRef(new Set<string>());
  const now = live?.status === 'in_progress' ? live.case?.patient_id : undefined;
  const next = live?.status === 'in_progress' ? live.next?.patient_id : undefined;
  const id = session?.id;
  const mineKey = session?.mine.join(',') ?? '';
  React.useEffect(() => {
    if (id == null || !mineKey) return;
    const mine = mineKey.split(',');
    const alert = (key: string, title: string) => {
      if (shown.current.has(key)) return;
      shown.current.add(key);
      toast(title, { action: { label: 'Otevřít', onClick: () => router.push(`/dashboard/live?zasedani=${id}`) }, duration: 10_000 });
      navigator.vibrate?.(200);
    };
    if (now && mine.includes(now)) alert(`now:${id}:${now}`, `Váš pacient ${now} je na projektoru`);
    else if (next && mine.includes(next)) alert(`next:${id}:${next}`, `Váš pacient ${next} jde na řadu jako další`);
  }, [id, mineKey, now, next, router]);
}
