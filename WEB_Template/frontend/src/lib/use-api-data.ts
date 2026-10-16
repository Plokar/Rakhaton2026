'use client';

import * as React from 'react';

type Loaded<T> = { arg: string; data?: T; error?: string };

/**
 * Načte data z API pro daný argument. `fetcher` má být stabilní funkce (např. `mdtApi.getSession`).
 * Stav se nastavuje jen v callbacku promise, ne synchronně v efektu (react-hooks/set-state-in-effect).
 */
export function useApiData<T>(fetcher: (arg: string) => Promise<T>, arg: string) {
  const [loaded, setLoaded] = React.useState<Loaded<T> | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    fetcher(arg)
      .then((data) => !cancelled && setLoaded({ arg, data }))
      .catch((err: unknown) => {
        if (!cancelled) setLoaded({ arg, error: err instanceof Error ? err.message : 'Data se nepodařilo načíst.' });
      });
    return () => {
      cancelled = true;
    };
  }, [fetcher, arg]);

  const current = loaded?.arg === arg ? loaded : null;
  return { data: current?.data, error: current?.error, loading: current === null };
}
