'use client';

import * as React from 'react';
import { CircleCheck, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Štítek původu obsahu (zlaté pravidlo, FR-R4): AI návrh fialově (NAVRH_UI Q1, nesplete se s akcí
 * ani se semaforem), po potvrzení lékařem zeleně. Vždy text, ne jen barva.
 */
export function AiTag({ status = 'draft', className }: { status?: 'draft' | 'confirmed'; className?: string }) {
  if (status === 'confirmed') {
    return (
      <span className={cn('inline-flex shrink-0 items-center gap-1 rounded-md bg-emerald-50 px-1.5 py-0.5 text-xs font-medium text-emerald-900 dark:bg-emerald-400/10 dark:text-emerald-200', className)}>
        <CircleCheck className="size-3.5" aria-hidden /> Potvrzeno lékařem
      </span>
    );
  }
  return (
    <span
      className={cn('inline-flex shrink-0 items-center rounded-md bg-ai-soft px-1.5 py-0.5 text-xs font-medium text-ai', className)}
      title="Syntéza z dokumentace v IRIS připravená AI, podléhá kontrole lékaře"
    >
      AI návrh
    </span>
  );
}

/**
 * Obsah od AI (FR-R4): fialový pruh vlevo (D-017: pruh značí AI vs. člověka), nadpis se štítkem
 * a stav draft / potvrzeno. Není to karta, aby uvnitř sekcí nevznikala karta v kartě. Jde sbalit.
 */
export function AiBlock({
  id,
  title,
  label,
  status = 'draft',
  defaultOpen = true,
  headingLevel = 'h2',
  className,
  children,
}: {
  id?: string;
  title: string;
  label?: React.ReactNode;
  status?: 'draft' | 'confirmed';
  defaultOpen?: boolean;
  headingLevel?: 'h2' | 'h3';
  className?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const bodyId = React.useId();
  const Heading = headingLevel;

  return (
    <section
      id={id}
      className={cn(
        'scroll-mt-32 border-l-2 pl-4',
        status === 'confirmed' ? 'border-emerald-600 dark:border-emerald-500' : 'border-ai',
        className,
      )}
    >
      <Heading className="text-sm font-semibold">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={bodyId}
          className="-ml-1 flex w-full items-center gap-2 rounded-md px-1 py-1 text-left transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRight
            className={cn('size-4 shrink-0 text-muted-foreground transition-transform duration-150 motion-reduce:transition-none', open && 'rotate-90')}
            aria-hidden
          />
          <span className="min-w-0 flex-1 text-[15px] font-semibold text-foreground">{title}</span>
          {label}
          <AiTag status={status} />
        </button>
      </Heading>
      {open && (
        <div id={bodyId} className="pb-1 pt-2">
          {children}
        </div>
      )}
    </section>
  );
}
