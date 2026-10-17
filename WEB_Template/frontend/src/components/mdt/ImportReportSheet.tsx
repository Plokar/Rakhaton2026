'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { CircleX } from 'lucide-react';
import { toast } from 'sonner';
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/shadcn/sheet';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import type { ImportProposal, ImportValue } from '@/types/mdt';
import { AiTag } from './AiBlock';
import { formatDate } from './format';

const KIND_LABEL: Record<ImportValue['kind'], string> = {
  lab: 'laboratoř',
  biomarker: 'biomarker',
  ecog: 'ECOG',
  tnm: 'TNM',
  vital: 'vitální funkce',
};

/** Odstavec zprávy podle čísla z citace „P03-imp01#2“ (stejné dělení jako backend: prázdné řádky). */
const paragraphs = (text: string) => text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);

/**
 * Strukturovaná extrakce (BON-7): vložená zpráva nebo PDF → AI navrhne hodnoty (laboratoř, biomarkery,
 * ECOG, TNM) s citací odstavce, ověřené proti textu. Lékař vybere, co zapsat; server návrh ověří znovu
 * a zapíše do IRIS jako `DocumentReference` + `Observation` + `Provenance`.
 */
export function ImportReportSheet({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const client = useQueryClient();
  const [text, setText] = React.useState('');
  const [pdf, setPdf] = React.useState<File | null>(null);
  const [proposal, setProposal] = React.useState<ImportProposal | null>(null);
  const [selected, setSelected] = React.useState<Set<number>>(new Set());
  const [busy, setBusy] = React.useState(false);

  const reset = () => {
    setProposal(null);
    setSelected(new Set());
  };

  const propose = async () => {
    setBusy(true);
    try {
      const result = await mdtApi.importReport(patientId, pdf ? { pdf } : { text });
      setProposal(result);
      setSelected(new Set(result.values.map((_, i) => i)));
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Zprávu se nepodařilo zpracovat.'));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!proposal) return;
    setBusy(true);
    try {
      const values = proposal.values.filter((_, i) => selected.has(i));
      const { fhir_written } = await mdtApi.confirmImport(patientId, { ...proposal, values });
      toast.success(`Zapsáno do IRIS: ${values.length} hodnot`, { description: `${proposal.document_id} · ${fhir_written.length} záznamů s Provenance` });
      void client.invalidateQueries({ queryKey: ['patient', patientId] });
      setText('');
      setPdf(null);
      reset();
      onClose();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Hodnoty se nepodařilo zapsat.'));
    } finally {
      setBusy(false);
    }
  };

  const paras = proposal ? paragraphs(proposal.text) : [];

  return (
    <Sheet open={open} onOpenChange={(next) => !next && !busy && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 data-[side=right]:sm:max-w-xl">
        <SheetHeader className="border-b border-border px-5 py-4 pr-12">
          <SheetTitle className="flex items-center gap-2 text-base font-semibold">
            Vložit zprávu <AiTag />
          </SheetTitle>
          <SheetDescription>
            <span translate="no">{patientId}</span>: AI vytěží hodnoty s odkazem na odstavec. Do IRIS se zapíše jen to, co potvrdíte.
          </SheetDescription>
        </SheetHeader>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {!proposal ? (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="import-text" className="text-[13px] font-medium">Text zprávy</label>
                <Textarea
                  id="import-text"
                  rows={12}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  disabled={Boolean(pdf)}
                  placeholder="Vložte laboratoř, patologii nebo zprávu z vyšetření. Odstavce oddělte prázdným řádkem."
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="import-pdf" className="text-[13px] font-medium">nebo PDF (do 20 MB)</label>
                <input
                  id="import-pdf"
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
                  className="text-sm file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-2.5 file:py-1 file:text-sm file:font-medium hover:file:bg-muted"
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              <div>
                <p className="text-sm font-semibold">{proposal.title}</p>
                <p className="text-xs text-muted-foreground">
                  <span translate="no">{proposal.document_id}</span>
                  {proposal.date && <> · {formatDate(proposal.date)}</>}
                </p>
              </div>
              <section aria-labelledby="import-values">
                <h3 id="import-values" className="mb-1.5 text-sm font-semibold">
                  Návrh hodnot <span className="font-normal text-muted-foreground">({selected.size} z {proposal.values.length} vybráno)</span>
                </h3>
                {proposal.values.length === 0 ? (
                  <p className="text-sm text-muted-foreground">AI ve zprávě nenašla žádnou ověřitelnou hodnotu.</p>
                ) : (
                  <ul className="divide-y divide-border rounded-lg border border-border bg-card">
                    {proposal.values.map((v, i) => (
                      <li key={`${v.citation}-${v.label}-${i}`}>
                        <label className="flex cursor-pointer items-start gap-3 px-3 py-2.5 hover:bg-muted/50">
                          <input
                            type="checkbox"
                            className="mt-1 size-4 accent-primary"
                            checked={selected.has(i)}
                            onChange={(e) =>
                              setSelected((prev) => {
                                const next = new Set(prev);
                                if (e.target.checked) next.add(i);
                                else next.delete(i);
                                return next;
                              })
                            }
                          />
                          <span className="min-w-0 flex-1">
                            <span className="flex flex-wrap items-baseline gap-x-2 text-sm">
                              <span className="font-medium">{v.label}</span>
                              <span className="tabular-nums">{v.value_text}</span>
                              <span className="text-xs text-muted-foreground">{KIND_LABEL[v.kind]}{v.date ? `, ${formatDate(v.date)}` : ''}</span>
                            </span>
                            <span className="mt-0.5 block text-xs text-muted-foreground">
                              <span translate="no">odst. {v.paragraph}</span>: {paras[v.paragraph - 1] ?? ''}
                            </span>
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              {proposal.rejected.length > 0 && (
                <section aria-labelledby="import-rejected">
                  <h3 id="import-rejected" className="mb-1.5 text-sm font-semibold">
                    Neověřené <span className="font-normal text-muted-foreground">({proposal.rejected.length}, nezapíšou se)</span>
                  </h3>
                  <ul className="flex flex-col gap-1.5 text-[13px]">
                    {proposal.rejected.map((v, i) => (
                      <li key={`${v.label}-${i}`} className="flex items-start gap-2">
                        <CircleX className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                        <span>
                          <span className="font-medium">{v.label}</span> {v.value_text}
                          <span className="text-muted-foreground"> · {(v.reasons ?? []).join(', ') || 'hodnota není v citovaném odstavci'}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}
        </div>

        <SheetFooter className="flex-row justify-end gap-2 border-t border-border px-5 py-3">
          {proposal ? (
            <>
              <Button variant="outline" onClick={reset} disabled={busy}>Zpět k textu</Button>
              <Button onClick={confirm} isLoading={busy} disabled={selected.size === 0}>
                Zapsat vybrané do IRIS
              </Button>
            </>
          ) : (
            <Button onClick={propose} isLoading={busy} disabled={!pdf && text.trim().length < 20}>
              Vytěžit hodnoty
            </Button>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
