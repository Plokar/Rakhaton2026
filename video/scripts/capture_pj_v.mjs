// Úzký (vertikální) náhled okna projektoru P04 pro krátký klip (jen čtení, nic se neukládá).
// node scripts/capture_pj_v.mjs [dark|light] → public/textures/pjv-<theme>/ :
//   full_base / mine_base  = okno 528 × 940 (jako vyskakovací okno projektoru), stav bez úpravy / s úpravou pneumologa,
//   full_tall / mine_tall  = stejná šířka, vysoké okno bez posouvání (zdroj textur řádků, které jsou v base pod okrajem),
//   pjv.json               = bboxy buněk podle zkratky údaje, nadpisů skupin a posuvné oblasti.
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const THEME = process.argv[2] === 'light' ? 'light' : 'dark';
const BASE = process.env.MDT_BASE ?? 'https://medteam.nervelabs.co.uk';
const URL_PJ = '/projector?board=3&case=3&patient=P04';
const W = 528, H = 940, TALL = 2600;
const OUT = new URL(`../public/textures/pjv-${THEME}/`, import.meta.url);
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 2 })).newPage();
const HIDE = '::-webkit-scrollbar{display:none!important} *{scrollbar-width:none!important;caret-color:transparent!important;transition:none!important} nextjs-portal{display:none!important}';

await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate((t) => { localStorage.setItem('theme', t); window.dispatchEvent(new Event('mdt-theme-change')); }, THEME);

const strip = (v) => {
  if (Array.isArray(v)) return v.map(strip);
  if (v && typeof v === 'object') {
    const o = {};
    for (const [k, x] of Object.entries(v)) if (k !== 'projector_layout' && k !== 'requester_layout') o[k] = strip(x);
    return o;
  }
  return v;
};
const measure = () => p.evaluate(() => {
  const r = (el) => { const b = el.getBoundingClientRect(); return { x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }; };
  const sec = document.querySelector('section[aria-labelledby="pj-facts"]');
  const cells = [...sec.querySelectorAll('ul > li')].map((li) => ({ key: (li.querySelector('button')?.getAttribute('aria-label') ?? li.innerText).split(':')[0].trim(), ...r(li) }));
  const groups = [...sec.querySelectorAll('h3')].map((h) => ({ label: h.querySelector('span')?.innerText ?? '', ...r(h) }));
  // posuvná oblast: nejbližší předek seznamu, který se posouvá (jinak celá karta)
  let sc = sec.querySelector('ul');
  while (sc && sc !== document.body && !(sc.scrollHeight > sc.clientHeight + 2 && /(auto|scroll)/.test(getComputedStyle(sc).overflowY))) sc = sc.parentElement;
  const clip = sc && sc !== document.body ? r(sc) : r(sec);
  return { cells, groups, clip, section: r(sec), title: r(document.getElementById('pj-facts')), scrolls: !!(sc && sc !== document.body) };
});

const L = {};
for (const [state, stripLayout] of [['full', true], ['mine', false]]) {
  await p.unroute('**/api/**').catch(() => {});
  if (stripLayout) {
    await p.route('**/api/**', async (route) => {
      const res = await route.fetch();
      if (!(res.headers()['content-type'] ?? '').includes('json')) return route.fulfill({ response: res });
      return route.fulfill({ response: res, body: JSON.stringify(strip(await res.json())) });
    });
  }
  for (const [kind, h] of [['base', H], ['tall', TALL]]) {
    await p.setViewportSize({ width: W, height: h });
    await p.goto(BASE + URL_PJ, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    await p.addStyleTag({ content: HIDE });
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(4000);
    await p.mouse.move(W - 1, h - 1);
    L[`${state}_${kind}`] = await measure();
    await p.screenshot({ path: fileURLToPath(new URL(`${state}_${kind}.png`, OUT)) });
    console.log('✓', state, kind, 'buněk', L[`${state}_${kind}`].cells.length, 'posouvá se', L[`${state}_${kind}`].scrolls, JSON.stringify(L[`${state}_${kind}`].clip));
  }
}
writeFileSync(new URL('pjv.json', OUT), JSON.stringify({ W, H, ...L }, null, 2));
await browser.close();
