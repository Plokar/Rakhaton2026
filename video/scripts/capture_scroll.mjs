// Celá stránka detailu pacienta P02 (tmavý režim, všechny sekce rozbalené) pro klip „průlet podkladem“.
// Jen čtení: rozbalení sekcí je jen v prohlížeči; dotaz na případ je bezstavový (/ask, nic se neukládá).
// Výstup: public/textures/scroll/tile_N.png (pruhy 1920 × 3000 CSS px, 2×) + scroll.json (výška, sekce, cíl).
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const BASE = process.env.MDT_BASE ?? 'https://medteam.nervelabs.co.uk';
const OUT = new URL('../public/textures/scroll/', import.meta.url);
const TILE = 3000;
mkdirSync(OUT, { recursive: true });
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
// rozbalit všechny sbalené sekce detailu
for (let round = 0; round < 3; round++) {
  const n = await p.evaluate(() => {
    const bs = [...document.querySelectorAll('main button[aria-expanded="false"][aria-controls$="-obsah"]')];
    bs.forEach((b) => b.click());
    return bs.length;
  });
  console.log('rozbaleno', n);
  if (!n) break;
  await p.waitForTimeout(2500);
}
// bezstavový dotaz na případ (první navržená otázka)
const chip = p.locator('#dotaz button').filter({ hasText: /\?$/ }).first();
if (await chip.count()) {
  const q = await chip.innerText();
  await chip.click();
  await p.waitForFunction(() => /shoda/.test(document.getElementById('dotaz')?.innerText ?? ''), null, { timeout: 120000 }).catch(() => console.log('odpověď nedorazila'));
  console.log('dotaz:', q);
}
await p.evaluate(() => document.fonts.ready);
await p.waitForTimeout(2500);
await p.mouse.move(1919, 1079);
await p.evaluate(() => window.scrollTo(0, 0));

const info = await p.evaluate(() => {
  const r = (el) => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y + scrollY), w: Math.round(b.width), h: Math.round(b.height) }; };
  const sections = [...document.querySelectorAll('main section[id], main [id][aria-labelledby]')]
    .map((s) => ({ id: s.id, title: (s.querySelector('h2, h3, button')?.innerText ?? '').split('\n')[0].trim(), ...r(s) }))
    .filter((s) => s.h > 40 && s.title);
  const ask = document.getElementById('dotaz');
  const answer = ask ? [...ask.querySelectorAll('*')].filter((e) => /^AI návrh$/.test(e.innerText?.trim())).map((e) => e.closest('div[class*="border"], article, section, li') ?? e)[0] : null;
  return { height: document.documentElement.scrollHeight, sections, ask: ask ? r(ask) : null, answer: answer ? r(answer) : null };
});
const tiles = [];
for (let y = 0; y < info.height; y += TILE) {
  const h = Math.min(TILE, info.height - y);
  const name = `tile_${tiles.length}.png`;
  await p.screenshot({ path: fileURLToPath(new URL(name, OUT)), fullPage: true, clip: { x: 0, y, width: 1920, height: h } });
  tiles.push({ file: name, y, h });
}
writeFileSync(new URL('scroll.json', OUT), JSON.stringify({ ...info, tiles }, null, 2));
console.log('výška', info.height, 'pruhů', tiles.length);
console.log('sekce:', info.sections.map((s) => `${s.id}@${s.y} ${s.title}`).join(' | '));
console.log('dotaz', JSON.stringify(info.ask), 'odpověď', JSON.stringify(info.answer));
await browser.close();
