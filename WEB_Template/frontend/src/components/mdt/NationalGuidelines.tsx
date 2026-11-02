import { BookOpen, ExternalLink } from 'lucide-react';
import type { NationalGuideline } from '@/types/mdt';
import { Citations } from './citations';

/**
 * Modrá kniha ČOS k diagnóze pacienta: pasáže národních doporučených postupů, které měl podklad k dispozici
 * (vybrané vyhledáváním podle otázky pro MDT a diagnózy, ne AI). Citace otevře celé znění oddílu.
 */
export function NationalGuidelines({ items }: { items?: NationalGuideline[] | null }) {
  if (!items?.length) return null;
  return (
    <section aria-labelledby="modra-kniha" className="rounded-lg border border-border bg-card px-3 py-2.5">
      <h3 id="modra-kniha" className="flex flex-wrap items-center gap-x-2 text-sm font-semibold">
        <BookOpen className="size-4 text-primary" aria-hidden /> Modrá kniha ČOS
        <span className="font-normal text-muted-foreground">národní doporučené postupy, 32. aktualizace (2026)</span>
      </h3>
      <ul className="mt-2 flex flex-col divide-y divide-border">
        {items.map((g) => {
          const page = g.url?.match(/#page=(\d+)/)?.[1];
          return (
            <li key={g.evidence_id} className="py-2 text-[13px]">
              <p className="font-medium">
                {g.title.replace(/^\d+\.\s*/, '')}
                <Citations ids={[g.evidence_id]} />
              </p>
              <p className="mt-0.5 line-clamp-2 text-muted-foreground">{g.excerpt}</p>
              {g.url && (
                <a href={g.url} target="_blank" rel="noreferrer" className="mt-0.5 inline-flex items-center gap-1 text-xs text-primary hover:underline">
                  PDF Modré knihy{page && `, strana ${page}`} <ExternalLink className="size-3" aria-hidden />
                </a>
              )}
            </li>
          );
        })}
      </ul>
      <p className="mt-1 text-xs text-muted-foreground">Vybráno k diagnóze a otázce pro MDT vyhledáváním v textu knihy. Rozhoduje lékař.</p>
    </section>
  );
}
