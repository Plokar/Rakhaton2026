// Fotky dialogu „Přidat lékaře“ (Tým komise) v tmavém režimu: krok 1 vyplněný profil, krok 2 šablona údajů
// pro okno projektoru (preset pneumologa). NIC se neukládá: tlačítko „Založit lékaře“ se nestiskne.
// Produkce zatím nemá endpoint katalogu (404), proto se jeho odpověď v tomto prohlížeči nahradí výstupem
// `services/rules/fact_templates.catalog()` z aktuálního master (catalog.json, viz FILM_SCENAR §12).
// node scripts/capture_sablona.mjs <catalog.json> → out/fotky/sablona_*.png
import { chromium } from 'playwright';
import { mkdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const BASE = process.env.MDT_BASE ?? 'https://medteam.nervelabs.co.uk';
const CATALOG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const OUT = new URL('../out/fotky/', import.meta.url);
mkdirSync(OUT, { recursive: true });
const file = (n) => fileURLToPath(new URL(n, OUT));
const browser = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });

for (const [suffix, H] of [['', 1080], ['_vysoka', 1500], ['_cela', 5600]  /* seznam má výšku 60 % okna: ve vysokém okně se vejde celý */]) {
  const p = await (await browser.newContext({ viewport: { width: 1920, height: H }, deviceScaleFactor: 2 })).newPage();
  p.on('request', (r) => { if (r.url().includes('/api/') && r.method() !== 'GET' && !r.url().includes('/auth/')) console.log('!! ', r.method(), r.url()); });
  await p.route('**/api/mdt/templates/catalog/**', (route) => {
    const area = new URL(route.request().url()).searchParams.get('area') ?? 'OBC';
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CATALOG[area]) });
  });
  await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
  await p.getByRole('button', { name: /Předseda komise/ }).click();
  await p.waitForURL(/dashboard/, { timeout: 60000 });
  await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });
  await p.goto(BASE + '/dashboard/tym', { waitUntil: 'domcontentloaded' });
  await p.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await p.waitForTimeout(2500);
  await p.addStyleTag({ content: '::-webkit-scrollbar{display:none!important} *{scrollbar-width:none!important} nextjs-portal{display:none!important} input{caret-color:transparent!important}' });
  await p.getByRole('button', { name: /Přidat lékaře/ }).first().click();
  await p.waitForTimeout(1200);
  const d = p.getByRole('dialog');
  const fill = (label, v) => d.getByLabel(label, { exact: true }).fill(v);
  await fill('Titul před jménem', 'MUDr.');
  await fill('Titul za jménem', 'Ph.D.');
  await fill('Jméno', 'Jana');
  await fill('Příjmení', 'Nováková');
  await d.getByText('Pneumolog', { exact: true }).click();
  await d.getByText('Zadávající lékař', { exact: true }).click().catch(() => {});
  await fill('Uživatelské jméno', 'novakova');
  await fill('E-mail', 'jana.novakova@nemocnice.cz');
  await fill('Dočasné heslo (aspoň 8 znaků)', 'Komise2026');
  await p.mouse.move(1900, H - 20);
  await p.waitForTimeout(600);
  if (!suffix) await p.screenshot({ path: file('sablona_krok1_profil.png') });
  await d.getByRole('button', { name: 'Pokračovat na šablonu' }).click();
  await p.waitForTimeout(3500);
  await p.mouse.move(1900, H - 20);
  await p.waitForTimeout(400);
  if (suffix !== '_cela') await p.screenshot({ path: file(`sablona_krok2_projektor${suffix}.png`) });
  const box = await d.boundingBox();
  await p.screenshot({ path: file(`sablona_krok2_dialog${suffix}.png`), clip: { x: box.x - 24, y: box.y - 24, width: box.width + 48, height: box.height + 48 } });
  console.log(suffix || 'normal', 'dialog', JSON.stringify(box), (await d.innerText()).replace(/\n+/g, ' | ').slice(0, 700));
  await p.context().close();
}
await browser.close();
