'use client';

import * as React from 'react';
import QRCode from 'qrcode';
import { cn } from '@/lib/utils';

/** Adresa živého zasedání pro mobil (T-380): po přihlášení se lékař sám ohlásí jako přítomný. */
export const liveJoinUrl = (sessionId: number) =>
  `${typeof window === 'undefined' ? '' : window.location.origin}/dashboard/live?zasedani=${sessionId}`;

/**
 * QR kód pro příchod na zasedání (T-380): lékař ho načte mobilem z projektoru nebo z obrazovky předsedy a otevře
 * se mu „Živě na MDT“ pro toto zasedání. Kód obsahuje jen adresu aplikace a číslo zasedání, žádné údaje pacienta.
 */
export function JoinQr({ sessionId, size = 160, className, caption = true }: {
  sessionId: number;
  size?: number;
  className?: string;
  caption?: boolean;
}) {
  const [svg, setSvg] = React.useState<string | null>(null);
  const url = React.useMemo(() => liveJoinUrl(sessionId), [sessionId]);
  React.useEffect(() => {
    let cancelled = false;
    QRCode.toString(url, { type: 'svg', margin: 1, errorCorrectionLevel: 'M', color: { dark: '#0f172a', light: '#ffffff' } })
      .then((text) => !cancelled && setSvg(text))
      .catch(() => !cancelled && setSvg(null));
    return () => {
      cancelled = true;
    };
  }, [url]);
  return (
    <figure className={cn('flex flex-col items-center gap-2', className)}>
      <div
        role="img"
        aria-label="QR kód pro připojení k zasedání z mobilu"
        className="rounded-lg bg-white p-1 shadow-sm ring-1 ring-border [&_svg]:h-full [&_svg]:w-full"
        style={{ width: size, height: size }}
        // SVG generuje knihovna qrcode z adresy aplikace (bez vstupu od uživatele)
        dangerouslySetInnerHTML={svg ? { __html: svg } : undefined}
      />
      {caption && (
        <figcaption className="max-w-[16rem] text-center text-[13px] text-muted-foreground">
          Načtěte mobilem: uvidíte pacienta na projektoru a jeho detail.
        </figcaption>
      )}
    </figure>
  );
}
