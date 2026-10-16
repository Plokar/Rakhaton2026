'use client';

import * as React from 'react';
import { PanelRightOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Otevře podklad v samostatném úzkém okně (FR-U2, D-017): lékař ho má vedle PACS.
 * Každý případ má vlastní pojmenované okno; prostřední tlačítko myši otevře běžnou záložku.
 */
export function BriefWindowLink({ caseId, className, children }: { caseId: string | number; className?: string; children?: React.ReactNode }) {
  const href = `/brief/${encodeURIComponent(String(caseId))}`;
  const open = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    const win = window.open(href, `mdt-brief-${caseId}`, 'popup,width=440,height=960');
    if (win) {
      e.preventDefault();
      win.focus();
    }
  };
  return (
    <a href={href} target="_blank" rel="noopener" onClick={open} className={cn('inline-flex items-center gap-1.5', className)}>
      <PanelRightOpen className="h-3.5 w-3.5" aria-hidden />
      {children ?? 'Úzké okno'}
    </a>
  );
}
