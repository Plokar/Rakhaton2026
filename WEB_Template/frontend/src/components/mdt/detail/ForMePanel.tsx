import type { SpecialtyView } from '@/types/mdt';
import { Citations } from '../citations';
import { KbItemRow } from '../KbItem';

/**
 * „Pro vás“ (T-319): údaje, postupy a důvody podle odbornosti přihlášeného z báze `data/onko`
 * (deterministicky, bez AI). Doplňuje podklad, pořadí předsedy (`BriefConfig`) nemění.
 */
export function ForMePanel({ view }: { view: SpecialtyView }) {
  return (
    <div className="grid gap-x-10 gap-y-6 @container lg:grid-cols-2">
      <section aria-labelledby="pro-me-udaje">
        <h3 id="pro-me-udaje" className="mb-1 text-sm font-semibold">Údaje pro vaše rozhodnutí</h3>
        {view.items.length ? (
          <ul className="divide-y divide-border/60">{view.items.map((item) => <KbItemRow key={item.id} item={item} />)}</ul>
        ) : (
          <p className="text-sm text-muted-foreground">Pro vaši odbornost báze u této diagnózy nic zvláštního neuvádí.</p>
        )}
      </section>
      <div className="flex flex-col gap-6">
        {view.procedures.length > 0 && (
          <section aria-labelledby="pro-me-postupy">
            <h3 id="pro-me-postupy" className="mb-1.5 text-sm font-semibold">Postupy, ke kterým se vyjadřujete</h3>
            <ul className="flex flex-col gap-1 text-[13px]">
              {view.procedures.map((p) => (
                <li key={p.id}>
                  {p.title}
                  <Citations ids={p.sources} />
                </li>
              ))}
            </ul>
          </section>
        )}
        {view.interests.length > 0 && (
          <section aria-labelledby="pro-me-proc">
            <h3 id="pro-me-proc" className="mb-1.5 text-sm font-semibold">Co sledujete a proč</h3>
            <ul className="flex flex-col gap-2 text-[13px] leading-snug">
              {view.interests.map((i) => (
                <li key={`${i.specialty}-${i.what}`}>
                  <span className="font-medium">{i.what}</span>
                  <span className="text-muted-foreground"> → {i.why}</span>
                  <Citations ids={i.sources} />
                </li>
              ))}
            </ul>
          </section>
        )}
        <p className="text-xs text-muted-foreground">Podle znalostní báze onkologie a diagnózy pacienta, bez AI. Pořadí předsedy se nemění.</p>
      </div>
    </div>
  );
}
