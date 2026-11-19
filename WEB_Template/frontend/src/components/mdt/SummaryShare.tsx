'use client';

import * as React from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link2, Printer } from 'lucide-react';
import { toast } from 'sonner';
import { Button, buttonVariants } from '@/components/shadcn/button';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { formatDate } from './format';

/**
 * Shrnutí pro pacienta ven (T-384): tisk a bezpečný odkaz (14 dní, jde zrušit). Odkaz ukáže jen věty shrnutí
 * a datum zasedání: žádné jméno, RČ, ID pacienta ani citace. Odkaz se zobrazí jen teď, server drží jen jeho hash.
 */
export function SummaryShare({ caseId, canShare }: { caseId: string; canShare: boolean }) {
  const client = useQueryClient();
  const key = ['case', caseId, 'summary-links'];
  const links = useQuery({ queryKey: key, queryFn: () => mdtApi.getSummaryLinks(caseId), enabled: canShare });
  const [created, setCreated] = React.useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => mdtApi.createSummaryLink(caseId),
    onSuccess: async (link) => {
      setCreated(link.url);
      void client.invalidateQueries({ queryKey: key });
      try {
        await navigator.clipboard.writeText(link.url);
        toast.success('Odkaz pro pacienta zkopírován', { description: `Platí do ${formatDate(link.expires_at.slice(0, 10))}.` });
      } catch {
        toast('Odkaz vytvořen, zkopírujte ho níže.');
      }
    },
    onError: (err) => toast.error(apiErrorMessage(err, 'Odkaz se nepodařilo vytvořit.')),
  });
  const revoke = useMutation({
    mutationFn: () => mdtApi.revokeSummaryLinks(caseId),
    onSuccess: () => {
      setCreated(null);
      void client.invalidateQueries({ queryKey: key });
      toast('Všechny odkazy pro pacienta jsou zrušené.');
    },
  });
  const active = links.data?.length ?? 0;
  return (
    <div className="mt-3 flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <Link href={`/dashboard/cases/${caseId}/tisk-shrnuti`} target="_blank" className={buttonVariants({ variant: 'outline', size: 'sm' })}>
          <Printer aria-hidden /> Vytisknout pro pacienta
        </Link>
        {canShare && (
          <Button variant="outline" size="sm" onClick={() => create.mutate()} disabled={create.isPending}>
            <Link2 aria-hidden /> Odkaz pro pacienta
          </Button>
        )}
        {canShare && active > 0 && (
          <Button variant="ghost" size="sm" onClick={() => revoke.mutate()} disabled={revoke.isPending}>
            Zrušit odkazy ({active})
          </Button>
        )}
      </div>
      {created && (
        <p className="break-all rounded-md bg-muted px-2 py-1 font-mono text-xs" aria-label="Odkaz pro pacienta">{created}</p>
      )}
      {canShare && (
        <p className="text-xs text-muted-foreground">
          Odkaz platí 14 dní a ukáže jen text shrnutí, bez jména a rodného čísla. Předávejte ho jen pacientovi.
        </p>
      )}
    </div>
  );
}
