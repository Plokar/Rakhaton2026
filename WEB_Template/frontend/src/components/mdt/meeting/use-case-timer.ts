'use client';

import * as React from 'react';

type Elapsed = Record<string, number>;

const read = (key: string): Elapsed => {
  try {
    return JSON.parse(sessionStorage.getItem(key) ?? '{}') as Elapsed;
  } catch {
    return {};
  }
};

const write = (key: string, value: Elapsed) => {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // bez úložiště čas platí jen do přenačtení
  }
};

/**
 * Čas strávený u pacienta během jednání (NAVRH_UI §7.4): běží u pacienta na řadě, jen v paměti
 * prohlížeče (sessionStorage), do IRIS se neukládá. Slouží předsedovi k řízení, ne k hodnocení.
 */
export function useCaseTimer(sessionId: number | string, activeCaseId: number | null) {
  const key = `mdt-cas-${sessionId}`;
  const [elapsed, setElapsed] = React.useState<Elapsed>({});
  const loaded = React.useRef(false);

  React.useEffect(() => {
    if (activeCaseId === null) return;
    const timer = window.setInterval(() => {
      setElapsed((prev) => {
        const base = loaded.current ? prev : { ...read(key), ...prev };
        loaded.current = true;
        const next = { ...base, [activeCaseId]: (base[activeCaseId] ?? 0) + 1 };
        write(key, next);
        return next;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [key, activeCaseId]);

  const total = Object.values(elapsed).reduce((sum, s) => sum + s, 0);
  return { elapsed, total };
}

/** „4:05“, od hodiny „1:04:05“. */
export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const mm = h ? String(m).padStart(2, '0') : String(m);
  return `${h ? `${h}:` : ''}${mm}:${String(s).padStart(2, '0')}`;
}
