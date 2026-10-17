import * as React from 'react';
import { cn } from '@/lib/utils';

/** Obsah stránky v shellu: jednotné okraje a šířka (NAVRH_UI §3.3). Jednání komise má vlastní plochu. */
export function Page({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn('mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8', className)}>{children}</div>;
}

/**
 * Hlavička stránky: titulek 24/32, pod ním jedna řádka kontextu, vpravo akce stránky.
 * Žádný nadtitulek („kicker“) nad nadpisem (craft-floor).
 */
export function PageHeader({
  title,
  meta,
  actions,
  className,
}: {
  title: React.ReactNode;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-wrap items-end justify-between gap-x-6 gap-y-3', className)}>
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-balance">{title}</h1>
        {meta && <div className="mt-1 text-sm text-muted-foreground">{meta}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
