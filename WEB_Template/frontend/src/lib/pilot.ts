/**
 * Pilotní provoz (T-355, docs/PILOT.md): lékaři zkoušejí MDTcore na fiktivních pacientech.
 * `NEXT_PUBLIC_PILOT_MODE=true` (Vercel) skryje 1-click demo účty na přihlášení (heslo by bylo v JS)
 * a v aplikaci ukáže pruh „Pilotní provoz · jen fiktivní data“ s odkazem na zpětnou vazbu.
 */
export const PILOT_MODE = process.env.NEXT_PUBLIC_PILOT_MODE === 'true';

/** Kam hlásit problém: formulář nebo `mailto:` (bez něj se odkaz neukáže). */
export const PILOT_FEEDBACK_URL = process.env.NEXT_PUBLIC_PILOT_FEEDBACK_URL || '';
