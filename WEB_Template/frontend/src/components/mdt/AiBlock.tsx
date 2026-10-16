'use client';

import * as React from 'react';
import { CheckCircle2, ChevronDown, Cpu } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Obal obsahu od AI (zlaté pravidlo, FR-R4): zřetelný levý akcent, štítek „AI návrh“,
 * stav draft / potvrzeno. Blok jde sbalit (úzké rozložení, FR-U2).
 */
export function AiBlock({
  id,
  title,
  label,
  status = 'draft',
  defaultOpen = true,
  children,
}: {
  id?: string;
  title: string;
  label?: React.ReactNode;
  status?: 'draft' | 'confirmed';
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const bodyId = React.useId();

  return (
    <section
      id={id}
      className={cn(
        'scroll-mt-28 rounded-xl border border-border bg-card shadow-2xs transition-colors',
        status === 'confirmed'
          ? 'border-l-4 border-l-emerald-700 dark:border-l-emerald-500'
          : 'border-l-4 border-l-teal-700 dark:border-l-teal-400',
      )}
    >
      <h2 className="text-sm font-bold tracking-tight text-foreground">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={bodyId}
          className={cn(
            'flex w-full items-center gap-2.5 px-4 py-3 text-left transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            open && 'border-b border-border/70 bg-muted/30',
          )}
        >
          <span className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
            <span className="text-base font-bold text-foreground">{title}</span>
            {label}
          </span>
          {status === 'confirmed' ? (
            <span className="inline-flex shrink-0 items-center gap-1 rounded-md border border-emerald-600/40 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-200">
              <CheckCircle2 className="h-3 w-3" aria-hidden /> Potvrzeno lékařem
            </span>
          ) : (
            <span
              className="inline-flex shrink-0 items-center gap-1 rounded-md border border-teal-700/30 bg-teal-50/90 px-2 py-0.5 font-mono text-[11px] font-semibold text-teal-900 dark:border-teal-400/30 dark:bg-teal-950/70 dark:text-teal-200"
              title="Syntéza z dokumentace v IRIS připravená AI — podléhá kontrole lékaře"
            >
              <Cpu className="h-3 w-3" aria-hidden /> AI návrh
            </span>
          )}
          <ChevronDown
            className={cn('h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-150', !open && '-rotate-90')}
            aria-hidden
          />
        </button>
      </h2>
      {open && (
        <div id={bodyId} className="p-4">
          {children}
        </div>
      )}
    </section>
  );
}

