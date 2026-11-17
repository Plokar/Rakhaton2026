'use client';

import * as React from 'react';
import { BellRing, CloudDownload, WifiOff } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { enablePush, offlineUrls, pushState, pwaEnabled, saveForOffline, type PushState } from '@/lib/pwa';
import { cn } from '@/lib/utils';

const subscribeOnline = (notify: () => void) => {
  window.addEventListener('online', notify);
  window.addEventListener('offline', notify);
  return () => {
    window.removeEventListener('online', notify);
    window.removeEventListener('offline', notify);
  };
};

/** Je zařízení bez signálu (`navigator.onLine`)? Na serveru vždy online. */
export function useOffline(): boolean {
  return !React.useSyncExternalStore(subscribeOnline, () => navigator.onLine, () => true);
}

/**
 * Tento telefon (T-383): uložit dnešní zasedání pro čtení bez signálu (výslovně, na 12 h, odhlášení smaže)
 * a zapnout upozornění „váš pacient je další“. Bez service workeru (vývoj, starý prohlížeč) se nic neukáže.
 */
export function DeviceBar({ sessionId, cases, className }: {
  sessionId: number;
  cases: { id: number; patient_id: string }[];
  className?: string;
}) {
  const offline = useOffline();
  const [push, setPush] = React.useState<PushState>('unsupported');
  const [saving, setSaving] = React.useState(false);
  const [savedAt, setSavedAt] = React.useState<string | null>(null);
  const supported = React.useSyncExternalStore(subscribeOnline, pwaEnabled, () => false);

  React.useEffect(() => {
    if (!supported) return;
    let cancelled = false;
    void pushState().then((state) => !cancelled && setPush(state));
    return () => {
      cancelled = true;
    };
  }, [supported]);

  if (!supported && !offline) return null;
  return (
    <div className={cn('flex flex-wrap items-center gap-2 text-[13px]', className)}>
      {offline && (
        <span role="status" className="inline-flex items-center gap-1 rounded-md bg-amber-100 px-2 py-0.5 font-medium text-amber-900 dark:bg-amber-400/15 dark:text-amber-200">
          <WifiOff className="size-3.5" aria-hidden /> Bez signálu: zobrazuji uložená data
        </span>
      )}
      {supported && !offline && (
        <Button
          size="sm"
          variant="outline"
          disabled={saving || !cases.length}
          title="Uloží agendu a přehled pacientů dnešního zasedání do telefonu na 12 hodin; odhlášení je smaže."
          onClick={async () => {
            setSaving(true);
            const result = await saveForOffline(offlineUrls(sessionId, cases));
            setSaving(false);
            if (!result) return;
            setSavedAt(new Date().toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' }));
            toast(`Uloženo pro čtení bez signálu (${result.saved} z ${result.total}). Platí 12 h, odhlášení je smaže.`);
          }}
        >
          <CloudDownload aria-hidden /> {saving ? 'Ukládám…' : savedAt ? `Uloženo ${savedAt}` : 'Uložit pro čtení bez signálu'}
        </Button>
      )}
      {supported && !offline && (push === 'off' || push === 'on' || push === 'denied') && (
        <Button
          size="sm"
          variant={push === 'on' ? 'secondary' : 'outline'}
          disabled={push !== 'off'}
          onClick={async () => {
            const next = await enablePush().catch(() => 'denied' as const);
            setPush(next);
            if (next === 'on') toast('Upozornění zapnutá: dáme vědět, když váš pacient půjde na řadu.');
            if (next === 'denied') toast.error('Prohlížeč upozornění nepovolil. Povolte je v nastavení stránky.');
          }}
        >
          <BellRing aria-hidden />
          {push === 'on' ? 'Upozornění zapnutá' : push === 'denied' ? 'Upozornění zakázaná v prohlížeči' : 'Upozornit na mobil'}
        </Button>
      )}
    </div>
  );
}
