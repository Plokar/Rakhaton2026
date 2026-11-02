// Snímky živé aplikace pro filmy (V-06): tmavý režim, 1920×1080 viewport, deviceScaleFactor 2.
// Výstup: public/textures/*.png + public/textures/layout.json (bboxy klíčových prvků v CSS px stránky).
// Jen čte: nic neukládá (formulář zařazení se otevře, ale neodešle).
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const BASE = process.env.MDT_BASE ?? 'https://medteam.nervelabs.co.uk';
const OUT = new URL('../public/textures/', import.meta.url);
const CHROME = process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
const p = await ctx.newPage();
const layout = {};
const HIDE = '::-webkit-scrollbar{display:none!important} nextjs-portal{display:none!important} *{caret-color:transparent!important}';

const settle = async (ms = 2500) => {
  await p.addStyleTag({ content: HIDE }).catch(() => {});
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(ms);
};
const go = async (path) => {
  await p.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await settle();
};
// bbox nejmenšího prvku, jehož text začíná `text` (souřadnice stránky = viewport + scroll)
const box = (text, opts = {}) => p.evaluate(({ text, opts }) => {
  const root = opts.within ? document.querySelector(opts.within) : document.body;
  const els = [...root.querySelectorAll(opts.sel ?? '*')].filter((e) => {
    const t = (e.innerText ?? '').trim();
    return opts.exact ? t === text : t.startsWith(text);
  });
  els.sort((a, b) => a.getBoundingClientRect().width * a.getBoundingClientRect().height - b.getBoundingClientRect().width * b.getBoundingClientRect().height);
  const e = els[opts.nth ?? 0];
  if (!e) return null;
  const r = e.getBoundingClientRect();
  return { x: Math.round(r.x + scrollX), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height) };
}, { text, opts });
const shot = async (name, full = false) => {
  await p.screenshot({ path: fileURLToPath(new URL(name + '.png', OUT)), fullPage: full });
  const pageH = full ? await p.evaluate(() => document.documentElement.scrollHeight) : 1080;
  layout[name] = { ...(layout[name] ?? {}), pageH };
  console.log('✓', name, pageH);
};
const crop = async (name, clip) => {
  await p.screenshot({ path: fileURLToPath(new URL(name + '.png', OUT)), clip });
  layout[name] = { ...clip };
  console.log('✓ crop', name, JSON.stringify(clip));
};

// — přihlášení předsedy (1-click demo účet), tmavý režim —
await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });

// B1 · kalendář zasedání
await go('/dashboard');
layout.dashboard = { git: await box('GIT – kolorektální karcinom /', { sel: 'main *' }), p03: await box('P03 · M · 67', { sel: 'main *' }) };
await shot('dashboard');

// B3 · nastavení podkladu (celá stránka)
await go('/dashboard/mdt/2/setup');
layout.setup = {
  template: await box('mKRC s jaterními metastázami'),
  sections: await box('Sekce a pořadí'),
  roles: await box('Přítomní (pohledy a posouzení rolí)'),
};
await shot('setup', true);

// B4 · jednání komise (hlavní obrazovka) + výřezy pro hook
await go('/dashboard/mdt/2');
await p.waitForTimeout(1500);
layout.session = {
  name: await box('P03 · muž · 67 let'),
  ps: await box('PS', { exact: true }),
  warnings: await box('13 varování'),
  facts: await box('Klíčové údaje', { exact: true }),
  options: await box('Léčebné postupy'),
  question: await box('Jsou jaterní metastázy po 8 cyklech'),
  record: await box('Nahrávat diskusi', { sel: 'button' }),
  optResekce: await box('Resekce jaterních metastáz'),
  optEgfr: await box('Anti-EGFR protilátka'),
  optImuno: await box('Imunoterapie inhibitorem'),
  aiUncertain: await box('Nejistota AI', { exact: true }),
  pnp: await box('PNP', { exact: true }),
};
await shot('session');
// výřezy řádků léčby (celý řádek seznamu = rodič s okrajem)
for (const [key, text] of [['opt-resekce', 'Resekce jaterních metastáz'], ['opt-egfr', 'Anti-EGFR protilátka'], ['opt-imuno', 'Imunoterapie inhibitorem']]) {
  const r = await p.evaluate((text) => {
    const t = [...document.querySelectorAll('main *')].filter((e) => (e.innerText ?? '').trim().startsWith(text))
      .sort((a, b) => a.getBoundingClientRect().height - b.getBoundingClientRect().height)[0];
    let e = t;
    while (e && e.parentElement && e.getBoundingClientRect().width < 560) e = e.parentElement;
    const r = e.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(Math.min(r.height, 150)) };
  }, text);
  await crop(key, r);
}
const rec = layout.session.record;
if (rec) await crop('btn-record', { x: rec.x - 4, y: rec.y - 4, width: rec.w + 8, height: rec.h + 8 });

// B5 · panel zdroje po kliknutí na citační čip u PNP
const chip = p.locator('main button', { hasText: /^12$/ }).first();
layout.session.chip12 = await chip.boundingBox().then((b) => b && { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) });
await chip.click();
await settle(2000);
layout.drawer = { panel: await p.evaluate(() => {
  const d = document.querySelector('[role=dialog]');
  if (!d) return null;
  const r = d.getBoundingClientRect();
  return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), text: d.innerText.slice(0, 400) };
}) };
await shot('drawer');
await p.keyboard.press('Escape');

// B6 + A4 · okno projektoru (úzký panel)
await go('/projector?board=2&case=2&patient=P03');
await p.waitForTimeout(1500);
await shot('projector');
await crop('panel', { x: 750, y: 0, width: 420, height: 1080 });
layout.projector = {
  header: await box('P03 · muž · 67 let'),
  ps: await box('PS', { exact: true }),
  facts: await box('Klíčové údaje', { exact: true }),
  question: await box('OTÁZKA PRO MDT'),
};

// B2 · zařazení P03 na jiný board (jen otevřít formulář), záloha P01 na boardu GIT
let intakeOk = false;
for (const board of [6, 5, 4, 3]) {
  await go(`/dashboard/mdt/${board}/add`);
  const btn = p.getByRole('button', { name: /^P03/ });
  if (await btn.count() && await btn.isEnabled()) {
    await btn.click();
    await settle(3000);
    intakeOk = true;
    layout.intake = { board, patient: 'P03' };
    break;
  }
}
if (!intakeOk) {
  await go('/dashboard/mdt/2/add');
  await p.getByRole('button', { name: /^P01/ }).click();
  await settle(3000);
  layout.intake = { board: 2, patient: 'P01' };
}
layout.intake.iris = await box('Údaje z IRIS', { exact: true });
layout.intake.warn = await p.evaluate(() => [...document.querySelectorAll('main button')].filter((b) => b.innerText.trim() === 'Doplnit').map((b) => {
  let e = b; while (e && e.parentElement && e.getBoundingClientRect().width < 640) e = e.parentElement;
  const r = e.getBoundingClientRect(); return { x: Math.round(r.x + scrollX), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height) };
}));
await shot('intake', true);

// B7 + B8 · závěr komise (potvrzený, AI návrhy fialově)
await go('/dashboard/cases/2/record');
layout.record = {
  confirmed: await box('Potvrzeno:'),
  iris: await box('Zapsáno do IRIS'),
  pdf: await box('Export PDF', { exact: true }),
  fhir: await box('FHIR document Bundle', { exact: true }),
  ai: await box('AI návrh', { exact: true }),
  assessment: await box('Klinické zhodnocení', { exact: true }),
};
await shot('record', true);
const c = layout.record.confirmed;
if (c) {
  const r = await p.evaluate(() => {
    const t = [...document.querySelectorAll('main *')].filter((e) => (e.innerText ?? '').trim().startsWith('Potvrzeno:'))
      .sort((a, b) => a.getBoundingClientRect().height - b.getBoundingClientRect().height)[0];
    let e = t; while (e && e.parentElement && e.getBoundingClientRect().width < 700) e = e.parentElement;
    const r = e.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
  });
  await crop('confirmed', r);
}

// detail případu (celá stránka) pro hook: zdroje a varování
await go('/dashboard/cases/2');
await shot('case', true);

writeFileSync(new URL('layout.json', OUT), JSON.stringify(layout, null, 2));
console.log('layout.json hotovo');
await browser.close();
