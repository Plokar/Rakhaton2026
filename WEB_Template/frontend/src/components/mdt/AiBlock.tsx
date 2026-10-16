'use client';

import * as React from 'react';
import { ChevronDown, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Obal obsahu od AI (zlaté pravidlo, FR-R4): fialový levý okraj, štítek „AI návrh“,
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
      className="scroll-mt-24 rounded-xl border border-border border-l-4 border-l-purple-500 bg-purple-500/[0.03] dark:bg-purple-500/[0.06]"
    >
      <h2 className="text-sm font-semibold text-foreground">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={bodyId}
          className="flex w-full items-center gap-2 px-4 py-3 text-left"
        >
          <span className="min-w-0 flex-1">
            <span className="mr-2">{title}</span>
            {label}
          </span>
          {status === 'confirmed' ? (
            <span className="shrink-0 rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
              Potvrzeno lékařem
            </span>
          ) : (
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-purple-500/15 px-2 py-0.5 text-[10px] font-semibold text-purple-700 dark:text-purple-300">
              <Sparkles className="h-3 w-3" aria-hidden /> AI návrh
            </span>
          )}
          <ChevronDown
            className={cn('h-4 w-4 shrink-0 text-muted-foreground transition-transform', !open && '-rotate-90')}
            aria-hidden
          />
        </button>
      </h2>
      {open && (
        <div id={bodyId} className="px-4 pb-4">
          {children}
        </div>
      )}
    </section>
  );
}
