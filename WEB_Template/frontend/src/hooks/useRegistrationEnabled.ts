'use client';

import * as React from 'react';
import { authApi } from '@/lib/api';
import { PILOT_MODE } from '@/lib/pilot';

/**
 * Smí se nabízet registrace (T-372)? Rozhoduje backend (`registration_enabled` z `/api/auth/status/`,
 * tj. `MDT_ALLOW_REGISTRATION`), v pilotu nikdy. `null` = ještě nevíme (nic neukazovat, ať odkaz neproblikne).
 */
export function useRegistrationEnabled(): boolean | null {
  const [enabled, setEnabled] = React.useState<boolean | null>(PILOT_MODE ? false : null);
  React.useEffect(() => {
    if (PILOT_MODE) return;
    let cancelled = false;
    authApi
      .checkStatus()
      .then((status) => !cancelled && setEnabled(Boolean(status.registration_enabled)))
      .catch(() => !cancelled && setEnabled(false));
    return () => {
      cancelled = true;
    };
  }, []);
  return enabled;
}
