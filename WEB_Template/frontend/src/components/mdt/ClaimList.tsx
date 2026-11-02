'use client';

import * as React from 'react';
import { TriangleAlert } from 'lucide-react';
import { ToggleGroup, ToggleGroupItem } from '@/components/shadcn/toggle-group';
import type { BriefSection, Claim } from '@/types/mdt';
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
        <Confidence value={claim.confidence} />
      </p>
    );
  }
  return (
    <p className="text-sm leading-relaxed">
      {claim.text}
      <Citations ids={claim.citations} />
      <Confidence value={claim.confidence} />
    </p>
  );
}

/**
 * Míra jistoty (BONUS zadání §3.3, T-332): sémantická shoda tvrzení s citovaným textem z grounding validátoru.
 * U strukturovaných dat (laboratoř, TNM) chybí, ta se ověřují čísly a daty přímo ve zdroji.
 */
function Confidence({ value }: { value?: number | null }) {
  if (value === undefined || value === null) return null;
  const percent = Math.round(value * 100);
  return (
    <span
      className="ml-1.5 inline-flex items-center rounded bg-muted px-1 align-baseline text-[11px] tabular-nums text-muted-foreground"
      title="Míra jistoty: sémantická shoda tvrzení s citovaným textem (grounding validátor, ne odhad AI)"
    >
      shoda {percent} %
    </span>
  );
}

/**
 * Tvrzení sekce podkladu. Dlouhá anamnéza má shrnutí AI i doslovné znění (`verbatim`, FR-A5): lékař přepne,
 * obojí s citací odstavce zprávy.
 */
export function SectionClaims({ section, hideUnverified = false }: { section: BriefSection; hideUnverified?: boolean }) {
  const [mode, setMode] = React.useState<'ai' | 'verbatim'>('ai');
  if (!section.verbatim?.length) return <ClaimList claims={section.items} hideUnverified={hideUnverified} />;
  return (
    <div className="flex flex-col gap-3">
      <ToggleGroup
        value={[mode]}
        onValueChange={(v) => v[0] && setMode(v[0] as 'ai' | 'verbatim')}
        variant="outline"
        size="sm"
        spacing={0}
        aria-label="Znění anamnézy"
      >
        <ToggleGroupItem value="ai">Shrnutí AI</ToggleGroupItem>
        <ToggleGroupItem value="verbatim">Doslovně ze zpráv</ToggleGroupItem>
      </ToggleGroup>
      <ClaimList claims={mode === 'verbatim' ? section.verbatim : section.items} hideUnverified={hideUnverified} />
    </div>
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
