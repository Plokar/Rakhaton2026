import { CircleCheck, ShieldAlert, ShieldOff } from 'lucide-react';
import type { BriefVerifier } from '@/types/mdt';

const VERDICT: Record<BriefVerifier['issues'][number]['verdict'], string> = {
  unsupported: 'Nepodloženo zdrojem',
  uncertain: 'Nejisté',
  unchecked: 'Nezkontrolováno',
};

/**
 * Výsledek druhé AI (Microsoft Azure OpenAI), která nezávisle kontroluje, zda tvrzení podkladu
 * opravdu stojí na citovaném zdroji (ARCH §5.3). „Ověřeno“ neznamená bezchybně, rozhoduje lékař.
 */
export function VerifierPanel({ verifier }: { verifier?: BriefVerifier | null }) {
  if (!verifier || verifier.status === 'off') {
    return (
      <p className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
        <ShieldOff className="size-4 shrink-0" aria-hidden />
        Druhá AI podklad neověřovala (kontrola je vypnutá).
      </p>
    );
  }
  const ok = verifier.status === 'ok' && verifier.rejected === 0 && verifier.unchecked === 0;
  const Icon = ok ? CircleCheck : ShieldAlert;
  return (
    <section
      aria-label="Kontrola druhou AI"
      className="rounded-lg border border-border bg-card px-3 py-2.5 text-sm"
    >
      <p className="flex items-start gap-2 font-medium">
        <Icon
          className={ok ? 'mt-0.5 size-4 shrink-0 text-emerald-700 dark:text-emerald-400' : 'mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400'}
          aria-hidden
        />
        <span>
          {ok
            ? 'Druhá AI nenašla žádné nepodložené tvrzení.'
            : verifier.status === 'ok'
              ? `Druhá AI má výhrady k ${verifier.rejected + verifier.unchecked} tvrzením.`
              : 'Kontrola druhou AI proběhla jen částečně nebo selhala.'}
          <span className="block text-xs font-normal text-muted-foreground">
            Microsoft Azure OpenAI ({verifier.model}) · zkontrolováno {verifier.checked}, zamítnuto {verifier.rejected}, bez verdiktu{' '}
            {verifier.unchecked}. Rozhoduje lékař.
          </span>
        </span>
      </p>
      {verifier.issues.length > 0 && (
        <ul className="mt-2 flex flex-col gap-1 border-t border-border pt-2 text-[13px]">
          {verifier.issues.map((i) => (
            <li key={`${i.claim_id}-${i.verdict}`}>
              <span className="mr-1.5 text-xs font-medium text-muted-foreground">{VERDICT[i.verdict]}</span>
              {i.issue} <span className="text-xs text-muted-foreground">({i.claim_id})</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
