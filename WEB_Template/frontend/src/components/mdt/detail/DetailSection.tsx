'use client';

import * as React from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SectionDef {
  id: string;
  label: string;
  count?: number;
}

interface SectionsContextValue {
  open: Set<string>;
  toggle: (id: string, next?: boolean) => void;
}

const SectionsContext = React.createContext<SectionsContextValue | null>(null);

/**
 * Otevřené sekce detailu (NAVRH_UI §8): rychlý přehled a varování otevřené, ostatní sbalené.
 * Odkaz s hashem (`#varovani` z jednání) sekci otevře a doroluje k ní. Nic se neskrývá natrvalo (D-019).
 */
export function SectionsProvider({ initialOpen, children }: { initialOpen: string[]; children: React.ReactNode }) {
  const [open, setOpen] = React.useState(() => new Set(initialOpen));
  const toggle = React.useCallback((id: string, next?: boolean) => {
    setOpen((prev) => {
      const result = new Set(prev);
      if (next ?? !prev.has(id)) result.add(id);
      else result.delete(id);
      return result;
    });
  }, []);

  React.useEffect(() => {
    const fromHash = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!id || !document.getElementById(id)) return;
      toggle(id, true);
      requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ block: 'start' }));
    };
    // Až po vykreslení sekcí (a mimo tělo efektu): odkaz z jednání míří na sbalenou sekci.
    const frame = requestAnimationFrame(fromHash);
    window.addEventListener('hashchange', fromHash);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('hashchange', fromHash);
    };
  }, [toggle]);

  const value = React.useMemo(() => ({ open, toggle }), [open, toggle]);
  return <SectionsContext.Provider value={value}>{children}</SectionsContext.Provider>;
}

function useSections() {
  const ctx = React.useContext(SectionsContext);
  if (!ctx) throw new Error('DetailSection musí být uvnitř <SectionsProvider>.');
  return ctx;
}

/** Sbalitelná sekce detailu s nadpisem a počtem. */
export function DetailSection({
  id,
  title,
  count,
  aside,
  children,
}: {
  id: string;
  title: string;
  count?: number;
  /** Ovládání vpravo v nadpisu (přepínač, filtr); vidět jen u otevřené sekce. */
  aside?: React.ReactNode;
  children: React.ReactNode;
}) {
  const { open, toggle } = useSections();
  const isOpen = open.has(id);
  const bodyId = `${id}-obsah`;
  return (
    <section id={id} aria-labelledby={`${id}-nadpis`} className="scroll-mt-40 border-t border-border pt-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id={`${id}-nadpis`} className="text-base font-semibold">
          <button
            type="button"
            onClick={() => toggle(id)}
            aria-expanded={isOpen}
            aria-controls={bodyId}
            className="-ml-1.5 inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ChevronRight className={cn('size-4 text-muted-foreground transition-transform motion-reduce:transition-none', isOpen && 'rotate-90')} aria-hidden />
            {title}
            {count !== undefined && <span className="font-normal text-muted-foreground">({count})</span>}
          </button>
        </h2>
        {isOpen && aside}
      </div>
      {isOpen && (
        <div id={bodyId} className="pb-2 pt-4">
          {children}
        </div>
      )}
    </section>
  );
}

/** Kde právě jsem: sekce nejblíž pod přilepenou hlavičkou. */
function useActiveSection(ids: string[]) {
  const [active, setActive] = React.useState(ids[0]);
  React.useEffect(() => {
    const visible = new Map<string, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.set(entry.target.id, entry.boundingClientRect.top);
          else visible.delete(entry.target.id);
        }
        const first = ids.find((id) => visible.has(id));
        if (first) setActive(first);
      },
      { rootMargin: '-160px 0px -55% 0px' },
    );
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [ids]);
  return active;
}

/**
 * Navigace po sekcích (NAVRH_UI §8): od 1280 px svislý seznam vlevo, užší obrazovky vodorovné
 * záložky pod hlavičkou. Klik sekci otevře a doroluje k ní.
 */
export function SectionNav({ sections, variant }: { sections: SectionDef[]; variant: 'rail' | 'tabs' }) {
  const { toggle } = useSections();
  const ids = React.useMemo(() => sections.map((s) => s.id), [sections]);
  const active = useActiveSection(ids);
  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    toggle(id, true);
    window.history.replaceState(null, '', `#${id}`);
    requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: 'smooth' }));
  };
  if (variant === 'tabs') {
    return (
      <nav aria-label="Sekce detailu" className="-mx-4 overflow-x-auto px-4 sm:-mx-6 sm:px-6">
        <ul className="flex gap-1 whitespace-nowrap">
          {sections.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                onClick={go(s.id)}
                aria-current={active === s.id ? 'location' : undefined}
                className={cn(
                  'inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                  active === s.id && 'bg-muted text-foreground',
                )}
              >
                {s.label}
                {s.count !== undefined && <span className="tabular-nums text-muted-foreground">{s.count}</span>}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    );
  }
  return (
    <nav aria-label="Sekce detailu">
      <ul className="flex flex-col gap-0.5">
        {sections.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              onClick={go(s.id)}
              aria-current={active === s.id ? 'location' : undefined}
              className={cn(
                'flex items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                active === s.id && 'bg-muted font-medium text-foreground',
              )}
            >
              {s.label}
              {s.count !== undefined && <span className="text-xs tabular-nums">{s.count}</span>}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
