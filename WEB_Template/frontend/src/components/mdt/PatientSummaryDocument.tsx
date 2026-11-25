import { formatDate } from './format';

/**
 * Shrnutí pro pacienta k přečtení a tisku (T-384): jen věty laického shrnutí z potvrzeného závěru a datum
 * zasedání. Bez jména, RČ, ID pacienta a citací (ty jsou pro lékaře v aplikaci).
 */
export function PatientSummaryDocument({ title, mdtDate, items }: { title: string; mdtDate: string | null; items: { text: string }[] }) {
  return (
    <article className="mx-auto w-full max-w-2xl px-4 py-8 text-foreground print:max-w-none print:px-0 print:py-0">
      <h1 className="text-2xl font-semibold leading-tight">{title}</h1>
      {mdtDate && <p className="mt-1 text-sm text-muted-foreground">Zasedání komise {formatDate(mdtDate)}</p>}
      <ul className="mt-6 space-y-3 text-base leading-relaxed">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span aria-hidden className="mt-2.5 size-1.5 shrink-0 rounded-full bg-primary" />
            <span>{item.text}</span>
          </li>
        ))}
      </ul>
      <p className="mt-8 border-t border-border pt-4 text-sm text-muted-foreground">
        Shrnutí připravila multidisciplinární onkologická komise. S otázkami se obraťte na svého ošetřujícího lékaře,
        který vám vše vysvětlí a domluví další postup.
      </p>
    </article>
  );
}
