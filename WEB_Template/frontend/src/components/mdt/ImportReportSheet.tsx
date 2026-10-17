'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { FileText, TriangleAlert } from 'lucide-react';
import { toast } from 'sonner';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/shadcn/sheet';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { mdtApi, type ImportProposal, type ImportValue } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { AiTag } from './AiBlock';
import { formatDate } from './format';

/**
 * Vstup zprávy (BON-7): vložený text nebo PDF → AI navrhne hodnoty s odstavcem zdroje → lékař vybere,
 * co zapsat → server návrh znovu ověří a zapíše do IRIS (`DocumentReference` + `Observation` + `Provenance`).
 * Neověřené hodnoty (číslo není v odstavci) se nezapíšou nikdy.
 */
export function ImportReportSheet({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 data-[side=right]:sm:max-w-xl">
        <SheetHeader className="border-b border-border px-5 py-4 pr-12">
          <SheetTitle className="text-base font-semibold">Vložit zprávu</SheetTitle>
          <SheetDescription>
            <span translate="no">{patientId}</span> · AI navrhne hodnoty se zdrojem, do IRIS se zapíše až po vašem potvrzení.
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {open && <ImportForm patientId={patientId} onDone={onClose} />}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function ImportForm({ patientId, onDone }: { patientId: string; onDone: () => void }) {
  const client = useQueryClient();
  const [text, setText] = React.useState('');
  const [busy, setBusy] = React.useState<'text' | 'pdf' | 'confirm' | null>(null);
  const [proposal, setProposal] = React.useState<ImportProposal | null>(null);
  const [selected, setSelected] = React.useState<Set<number>>(new Set());
  const [error, setError] = React.useState<string | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const propose = async (kind: 'text' | 'pdf', input: { text: string } | { pdf: File }) => {
    setBusy(kind);
    setError(null);
    try {
      const next = await mdtApi.proposeImport(patientId, input);
      setProposal(next);
      setSelected(new Set(next.values.map((_, i) => i)));
    } catch (err) {
      setError(apiErrorMessage(err, 'Zprávu se nepodařilo zpracovat.'));
    } finally {
      setBusy(null);
    }
  };

  const confirm = async () => {
    if (!proposal) return;
    setBusy('confirm');
    setError(null);
    try {
      const { fhir_written } = await mdtApi.confirmImport({ ...proposal, values: proposal.values.filter((_, i) => selected.has(i)) });
      void client.invalidateQueries({ queryKey: ['patient', patientId] });   // detail, časová osa, řady, intake
      toast.success(`Zapsáno do IRIS: ${fhir_written.length} záznamů`, { description: `${proposal.document_id} s Provenance` });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'Zápis se nepodařil.'));
    } finally {
      setBusy(null);
    }
  };

  if (proposal) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold">
            {proposal.title} <AiTag />
          </p>
          <p className="text-[13px] text-muted-foreground">
            <span translate="no">{proposal.document_id}</span>
            {proposal.date && <> · {formatDate(proposal.date)}</>} · vyberte hodnoty, které se zapíší
          </p>
        </div>
        {proposal.values.length === 0 ? (
          <p className="text-sm text-muted-foreground">AI ve zprávě nenašla žádnou ověřitelnou hodnotu.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {proposal.values.map((v, i) => (
              <li key={`${v.citation}-${v.label}-${i}`}>
                <label className="flex gap-3 rounded-lg border border-border p-3 text-sm has-checked:border-ai">
                  <input
                    type="checkbox"
                    className="mt-1 size-4 accent-ai"
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
                  <ValueRow value={v} />
                </label>
              </li>
            ))}
          </ul>
        )}
        {proposal.rejected.length > 0 && (
          <div>
            <h3 className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold">
              <TriangleAlert className="size-4 text-amber-700 dark:text-amber-400" aria-hidden /> Neověřeno, nezapíše se ({proposal.rejected.length})
            </h3>
            <ul className="flex flex-col gap-2">
              {proposal.rejected.map((v, i) => (
                <li key={`${v.citation}-${v.label}-${i}`} className="rounded-lg bg-amber-50 p-3 text-sm dark:bg-amber-400/10">
                  <ValueRow value={v} />
                  <p className="mt-1 text-xs text-amber-900 dark:text-amber-200">{v.reasons?.join('; ')}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-wrap gap-2">
          <Button onClick={confirm} disabled={selected.size === 0} isLoading={busy === 'confirm'}>
            Zapsat {selected.size} do IRIS
          </Button>
          <Button variant="outline" onClick={() => setProposal(null)} disabled={busy !== null}>
            Zpět ke zprávě
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium">Text zprávy</span>
        <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} placeholder={'Laboratoř 12. 10. 2026\n\nCEA 15,2 µg/l, CA 19-9 40 kU/l.\n\nHemoglobin 118 g/l.'} />
      </label>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => void propose('text', { text })} disabled={!text.trim() || busy !== null} isLoading={busy === 'text'}>
          Navrhnout hodnoty
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(e) => {
            const pdf = e.target.files?.[0];
            e.target.value = '';
            if (pdf) void propose('pdf', { pdf });
          }}
        />
        <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={busy !== null} isLoading={busy === 'pdf'}>
          <FileText aria-hidden /> Nahrát PDF
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Každá hodnota musí být doslova ve svém odstavci zprávy, jinak ji server odmítne. Nic se nezapíše bez potvrzení.
      </p>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

function ValueRow({ value }: { value: ImportValue }) {
  return (
    <span className="flex min-w-0 flex-col gap-0.5">
      <span>
        <span className="font-medium">{value.label}</span> {value.value_text}
        {value.date && <span className="text-muted-foreground"> · {formatDate(value.date)}</span>}
      </span>
      {value.source && (
        <span className="text-xs text-muted-foreground">
          Odstavec {value.paragraph}: „{value.source}“
        </span>
      )}
    </span>
  );
}
