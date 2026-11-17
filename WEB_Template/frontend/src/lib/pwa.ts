'use client';

import * as React from 'react';
import { apiFetch } from '@/lib/api';

/**
 * PWA (T-383): service worker `/sw.js` jen v produkčním buildu (v `next dev` by mezipaměť statických souborů
 * vracela staré chunky). Uložení pro čtení bez signálu je výslovná akce lékaře a odhlášení ho smaže.
 */
export const pwaEnabled = () =>
  typeof window !== 'undefined' && 'serviceWorker' in navigator
  && (process.env.NODE_ENV === 'production' || process.env.NEXT_PUBLIC_PWA === 'true');

export function registerServiceWorker() {
  if (!pwaEnabled()) return;
  navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => undefined);
}

/** Registrace SW po načtení aplikace (komponenta bez vzhledu v `providers.tsx`). */
export function PwaRegister() {
  React.useEffect(() => {
    registerServiceWorker();
  }, []);
  return null;
}

/** Adresy API pro čtení dnešního zasedání bez signálu: agenda, projektor a přehled každého pacienta. */
export function offlineUrls(sessionId: number, cases: { id: number; patient_id: string }[]): string[] {
  const urls = [`/api/mdt/sessions/${sessionId}/`, `/api/mdt/sessions/${sessionId}/live/`, '/api/mdt/live/'];
  for (const c of cases) {
    const pid = encodeURIComponent(c.patient_id);
    urls.push(
      `/api/mdt/cases/${c.id}/brief/`,
      `/api/mdt/cases/${c.id}/compatibility/`,
      `/api/mdt/cases/${c.id}/template/`,
      `/api/mdt/cases/${c.id}/decision/`,
      `/api/mdt/patients/${pid}/intake/`,
      `/api/patients/${pid}/observations/`,
    );
  }
  return urls;
}

async function controller(): Promise<ServiceWorker | null> {
  if (!pwaEnabled()) return null;
  const registration = await navigator.serviceWorker.ready;
  return registration.active;
}

/** Uloží odpovědi do mezipaměti SW (12 h); vrátí počet uložených adres. */
export async function saveForOffline(urls: string[]): Promise<{ saved: number; total: number } | null> {
  const worker = await controller();
  if (!worker) return null;
  return new Promise((resolve) => {
    const onMessage = (event: MessageEvent<{ type?: string; saved?: number; total?: number }>) => {
      if (event.data?.type !== 'saved') return;
      navigator.serviceWorker.removeEventListener('message', onMessage);
      resolve({ saved: event.data.saved ?? 0, total: event.data.total ?? urls.length });
    };
    navigator.serviceWorker.addEventListener('message', onMessage);
    worker.postMessage({ type: 'save', urls });
  });
}

/** Odhlášení: smazat uložená data pacientů a odhlásit push oznámení na tomto zařízení. */
export async function clearDeviceData() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
  const registration = await navigator.serviceWorker.getRegistration();
  registration?.active?.postMessage({ type: 'clear' });
  const subscription = await registration?.pushManager?.getSubscription();
  if (subscription) {
    await apiFetch('/api/mdt/push/subscriptions/', {
      method: 'DELETE',
      body: JSON.stringify({ endpoint: subscription.endpoint }),
    }).catch(() => undefined);
    await subscription.unsubscribe().catch(() => undefined);
  }
}

function base64ToBytes(base64: string): Uint8Array<ArrayBuffer> {
  const padded = (base64 + '='.repeat((4 - (base64.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(padded);
  const bytes = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

export type PushState = 'unsupported' | 'disabled' | 'denied' | 'off' | 'on';

/** Stav push oznámení na tomto zařízení (server bez klíčů VAPID = `disabled`). */
export async function pushState(): Promise<PushState> {
  if (!pwaEnabled() || !('PushManager' in window) || !('Notification' in window)) return 'unsupported';
  const config = await apiFetch<{ enabled: boolean }>('/api/mdt/push/key/').catch(() => ({ enabled: false }));
  if (!config.enabled) return 'disabled';
  if (Notification.permission === 'denied') return 'denied';
  const registration = await navigator.serviceWorker.ready;
  return (await registration.pushManager.getSubscription()) ? 'on' : 'off';
}

/** Zapne push oznámení: povolení prohlížeče, odběr u push služby a uložení na serveru. */
export async function enablePush(): Promise<PushState> {
  const config = await apiFetch<{ enabled: boolean; public_key?: string }>('/api/mdt/push/key/');
  if (!config.enabled || !config.public_key) return 'disabled';
  if ((await Notification.requestPermission()) !== 'granted') return 'denied';
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: base64ToBytes(config.public_key),
  });
  await apiFetch('/api/mdt/push/subscriptions/', { method: 'POST', body: JSON.stringify(subscription.toJSON()) });
  return 'on';
}
