/**
 * Evidence neuložené práce (T-373): obrazovka s rozepsaným textem se ohlásí, aby ji odhlášení při nečinnosti
 * nezahodilo. Mimo React (žádné překreslování), čte ho `useIdleLogout`.
 */
const dirty = new Set<string>();

export function setUnsaved(key: string, value: boolean): void {
  if (value) dirty.add(key);
  else dirty.delete(key);
}

export const hasUnsaved = (): boolean => dirty.size > 0;
