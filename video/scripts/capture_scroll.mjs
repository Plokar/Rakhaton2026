// Detail pacienta P02 (tmavý režim, sekce rozbalené) pro klip „průjezd podkladem“ (podle whatsapp_inspirace.mp4).
// Dvě vrstvy: posuvný obsah celé stránky (pevné prvky skryté) + pevné prvky (panel, lišta, hlavička, navigace sekcí)
// a navigace v každém stavu aktivní sekce. Jen čtení: rozbalení sekcí je jen v prohlížeči, nic se neodesílá.
// Výstup: public/textures/scroll/{tile_N,chrome,nav_N}.png (2×) + scroll.json.
import { chromium } from 'playwright';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const BASE = process.env.MDT_BASE ?? 'https://medteam.nervelabs.co.uk';
const OUT = new URL('../public/textures/scroll/', import.meta.url);
const TILE = 3000;
rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });
const file = (n) => fileURLToPath(new URL(n, OUT));
const browser = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 })).newPage();
const HIDE = '::-webkit-scrollbar{display:none!important} *{scrollbar-width:none!important;caret-color:transparent!important} nextjs-portal{display:none!important}';

await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });
await p.goto(BASE + '/dashboard/cases/1', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
await p.waitForTimeout(5000);
await p.addStyleTag({ content: HIDE });
for (let round = 0; round < 3; round++) {
  const n = await p.evaluate(() => {
    const bs = [...document.querySelectorAll('main button[aria-expanded="false"][aria-controls$="-obsah"]')];
    bs.forEach((b) => b.click());
    return bs.length;
  });
  if (!n) break;
  await p.waitForTimeout(2500);
}
await p.evaluate(() => document.fonts.ready);
await p.waitForTimeout(2000);
await p.mouse.move(1919, 1079);
await p.evaluate(() => window.scrollTo(0, 0));
await p.waitForTimeout(800);

const info = await p.evaluate(() => {
  const r = (el) => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y + scrollY), w: Math.round(b.width), h: Math.round(b.height) }; };
  const pinned = [...document.querySelectorAll('body *')].filter((e) => ['sticky', 'fixed'].includes(getComputedStyle(e).position));
  pinned.forEach((e, i) => e.setAttribute('data-pin', String(i)));
  const sections = [...document.querySelectorAll('main section[id]')].map((s) => ({ id: s.id, y: r(s).y })).filter((s) => s.y > 0);
  const ask = document.getElementById('dotaz');
  const nav = pinned.find((e) => /Rychlý přehled/.test(e.innerText ?? '') && e.getBoundingClientRect().x > 300);
  return {
    height: document.documentElement.scrollHeight,
    pinned: pinned.map((e) => ({ pos: getComputedStyle(e).position, ...r(e) })),
    nav: nav ? r(nav) : null, sections, ask: ask ? r(ask) : null,
  };
});

// pevné prvky ve výchozím stavu (posun 0)
await p.screenshot({ path: file('chrome.png') });

// navigace sekcí: aktivní položka podle posunu (scroll-spy aplikace), obrázek pro každý stav
const nav = info.nav;
const navStates = [];
let last = null;
for (let y = 0; y <= info.height - 1080; y += 150) {
  await p.evaluate((v) => window.scrollTo(0, v), y);
  await p.waitForTimeout(260);
  const active = await p.evaluate(() => {
    const a = [...document.querySelectorAll('[aria-current]')].find((e) => e.getBoundingClientRect().x > 300 && e.getBoundingClientRect().x < 700);
    return a ? a.innerText.split('\n')[0].trim() : '';
  });
  if (active !== last) {
    const name = `nav_${navStates.length}.png`;
    await p.screenshot({ path: file(name), clip: { x: nav.x, y: nav.y - y + 0, width: nav.w, height: nav.h } }).catch(async () => {
      await p.screenshot({ path: file(name), clip: { x: nav.x, y: 160, width: nav.w, height: nav.h } });
    });
    navStates.push({ from: y, active, file: name });
    last = active;
  }
}
await p.evaluate(() => window.scrollTo(0, 0));
await p.waitForTimeout(600);

// posuvný obsah: pevné prvky skryté (jejich místo v toku zůstává), pruhy po 3000 px
await p.evaluate(() => document.querySelectorAll('[data-pin]').forEach((e) => { e.style.visibility = 'hidden'; }));
const tiles = [];
for (let y = 0; y < info.height; y += TILE) {
  const h = Math.min(TILE, info.height - y);
  const name = `tile_${tiles.length}.png`;
  await p.screenshot({ path: file(name), fullPage: true, clip: { x: 0, y, width: 1920, height: h } });
  tiles.push({ file: name, y, h });
}
writeFileSync(new URL('scroll.json', OUT), JSON.stringify({ ...info, navStates, tiles }, null, 2));
console.log('výška', info.height, 'pruhů', tiles.length, 'stavů navigace', navStates.length);
console.log('navigace:', navStates.map((s) => `${s.from}:${s.active}`).join(' | '));
console.log('pevné:', info.pinned.map((x) => `${x.pos} ${x.x},${x.y} ${x.w}x${x.h}`).join(' | '));
console.log('dotaz', JSON.stringify(info.ask));
await browser.close();
