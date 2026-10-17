import { TriangleAlert } from 'lucide-react';
import type { Claim } from '@/types/mdt';
import { Citations } from './citations';
import { MissingData } from './MissingData';

/** Tvrzení AI s klikacími citacemi; neověřené tvrzení je výrazně označené (ARCH §5.3). */
export function ClaimItem({ claim }: { claim: Claim }) {
  if (claim.kind === 'missing') {
    return <MissingData text={claim.text} expectedSource={claim.expected_source} citations={claim.citations} />;
  }
  if (claim.verification === 'unverified') {
    return (
      <p className="rounded-md bg-amber-50 px-2.5 py-1.5 text-sm leading-relaxed dark:bg-amber-400/10">
        <span
          className="mr-1.5 inline-flex items-center gap-1 align-baseline text-xs font-medium text-amber-800 dark:text-amber-300"
          title="Grounding validátor tvrzení neověřil proti citovanému zdroji"
        >
          <TriangleAlert className="size-3.5 self-center" aria-hidden /> Neověřeno
        </span>
        {claim.text}
        <Citations ids={claim.citations} />
      </p>
    );
  }
  return (
    <p className="text-sm leading-relaxed">
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
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col gap-2">
        {visible.map((claim) => (
          <li key={claim.id}>
            <ClaimItem claim={claim} />
          </li>
        ))}
      </ul>
      {hidden > 0 && <p className="text-xs text-muted-foreground">Skryto neověřených tvrzení: {hidden} (nastavení podkladu).</p>}
    </div>
  );
}
