import { CircleCheck, CircleDashed, CircleDot, CircleMinus, Clock, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KbItem, KbItemStatus } from '@/types/mdt';
import { Citations } from './citations';

/** Stav údaje z katalogu báze (T-318/T-319): tvar ikony + text, barva jen doplňuje. */
export const KB_STATUS: Record<KbItemStatus, { label: string; icon: LucideIcon; tone: string }> = {
  present: { label: 'v podkladech', icon: CircleCheck, tone: 'text-emerald-700 dark:text-emerald-400' },
  mention: { label: 'jen zmínka', icon: CircleDot, tone: 'text-amber-700 dark:text-amber-400' },
  stale: { label: 'starší než limit', icon: Clock, tone: 'text-amber-700 dark:text-amber-400' },
  missing: { label: 'chybí', icon: CircleDashed, tone: 'text-red-700 dark:text-red-400' },
  not_applicable: { label: 'nepoužije se', icon: CircleMinus, tone: 'text-muted-foreground' },
};

export function KbItemRow({ item }: { item: KbItem }) {
  const meta = KB_STATUS[item.status];
  const Icon = meta.icon;
  return (
    <li className="flex items-start gap-2 py-1.5 text-[13px] leading-5">
      <Icon className={cn('mt-0.5 size-4 shrink-0', meta.tone)} strokeWidth={2.25} aria-hidden />
      <div className="min-w-0">
        <p>
          {item.label}
          <span className="text-muted-foreground">
            {' · '}
            {item.status === 'stale' && item.age_days ? `${item.age_days} dní` : meta.label}
          </span>
          <Citations ids={item.citations} />
        </p>
        {item.warning && <p className="text-xs text-muted-foreground">{item.warning.title}</p>}
      </div>
    </li>
  );
}
