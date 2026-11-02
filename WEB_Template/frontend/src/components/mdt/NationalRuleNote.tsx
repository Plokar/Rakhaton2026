import { BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CompatibilityRuleResult } from '@/types/mdt';
import { Citations } from './citations';

/** Krátký text pro bublinu: o co se práh pravidla opírá v Modré knize ČOS (T-340). */
export function nationalSummary(rule: CompatibilityRuleResult): string | null {
  if (!rule.national_status) return null;
  if (rule.national_status === 'neuvadi') return 'Modrá kniha ČOS práh neuvádí';
  const ref = rule.national?.[0];
  return ref ? `Modrá kniha ČOS ${rule.national_status === 'prah' ? 'uvádí práh' : 'k tématu'}: ${ref.evidence_id}` : null;
}

/**
 * Opora pravidla semaforu v Modré knize ČOS (T-340, D-026): práh (doslovná citace), téma, nebo „neuvádí“.
 * Barvu semaforu to nemění; citace otevře oddíl knihy.
 */
export function NationalRuleNote({ rule, compact = false }: { rule: CompatibilityRuleResult; compact?: boolean }) {
  if (!rule.national_status) return null;
  if (rule.national_status === 'neuvadi') {
    return compact ? null : (
      <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
        <BookOpen className="size-3 shrink-0" aria-hidden /> Modrá kniha ČOS práh neuvádí
      </p>
    );
  }
  const refs = rule.national ?? [];
  const main = refs.find((r) => r.match === 'prah') ?? refs[0];
  if (!main) return null;
  return (
    <p className={cn('mt-0.5 flex items-start gap-1 text-xs', main.match === 'prah' ? 'text-sky-800 dark:text-sky-300' : 'text-muted-foreground')}>
      <BookOpen className="mt-0.5 size-3 shrink-0" aria-hidden />
      <span className="min-w-0">
        Modrá kniha ČOS {main.match === 'prah' ? 'uvádí' : 'k tématu'}
        {!compact && <>: <q className="italic">{main.quote}</q></>}
        <Citations ids={refs.map((r) => r.evidence_id)} />
      </span>
    </p>
  );
}
