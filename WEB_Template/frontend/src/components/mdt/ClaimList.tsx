import { TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Claim } from '@/types/mdt';
import { Citations } from './citations';
import { MissingData } from './MissingData';

/** Tvrzení AI s klikacími citacemi; neověřené tvrzení je výrazně označené (ARCH §5.3). */
export function ClaimItem({ claim }: { claim: Claim }) {
  if (claim.kind === 'missing') {
    return <MissingData text={claim.text} expectedSource={claim.expected_source} citations={claim.citations} />;
  }
  const unverified = claim.verification === 'unverified';
  return (
    <p
      className={cn(
        'text-sm leading-relaxed',
        unverified && 'rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1',
      )}
    >
      {unverified && (
        <span
          className="mr-1.5 inline-flex items-center gap-1 rounded bg-amber-500/20 px-1.5 py-0.5 align-baseline text-[11px] font-semibold text-amber-700 dark:text-amber-300"
          title="Grounding validátor tvrzení neověřil proti citovanému zdroji"
        >
          <TriangleAlert className="h-3 w-3" aria-hidden /> Neověřeno
        </span>
      )}
      {claim.text}
      <Citations ids={claim.citations} />
    </p>
  );
}

export function ClaimList({ claims, hideUnverified = false }: { claims: Claim[]; hideUnverified?: boolean }) {
  const visible = hideUnverified
    ? claims.filter((c) => !(c.kind === 'claim' && c.verification === 'unverified'))
    : claims;
  const hidden = claims.length - visible.length;
  return (
    <div className="space-y-2">
      <ul className="space-y-2">
        {visible.map((claim) => (
          <li key={claim.id}>
            <ClaimItem claim={claim} />
          </li>
        ))}
      </ul>
      {hidden > 0 && (
        <p className="text-xs text-muted-foreground">Skryto neověřených tvrzení: {hidden}</p>
      )}
    </div>
  );
}
