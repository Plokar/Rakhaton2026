// Snímky pro film B v2 (souvislý průchod s kamerou za myší): stavy interakcí ve 2× rozlišení + layout2.json.
// Jen čte: nic se neukládá ani neodesílá. Chat: testovací zprávy kolegů se před snímkem nahradí věcnými
// zprávami jen v DOM prohlížeče (klony skutečných prvků, na server nic nejde). Editor projektoru se zavře bez uložení.
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const BASE = process.env.MDT_BASE ?? 'https://medteam.nervelabs.co.uk';
const OUT = new URL('../public/textures/v2/', import.meta.url);
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 })).newPage();
const L = {};
const HIDE = '::-webkit-scrollbar{display:none!important} nextjs-portal{display:none!important} *{caret-color:transparent!important}';

const settle = async (ms = 1500) => { await p.addStyleTag({ content: HIDE }).catch(() => {}); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(ms); };
const go = async (path) => { await p.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 60000 }); await p.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {}); await settle(2500); };
const shot = async (name, full = false) => {
  await p.waitForTimeout(500);
  await p.screenshot({ path: fileURLToPath(new URL(`${name}.png`, OUT)), fullPage: full });
  L[name] = { ...(L[name] ?? {}), pageH: full ? await p.evaluate(() => document.documentElement.scrollHeight) : 1080 };
  console.log('✓', name, L[name].pageH);
};
const rect = async (loc) => {
  const b = await loc.first().boundingBox().catch(() => null);
  const sy = await p.evaluate(() => scrollY);
  return b && { x: Math.round(b.x), y: Math.round(b.y + sy), w: Math.round(b.width), h: Math.round(b.height) };
};
const put = (name, key, v) => { L[name] = { ...(L[name] ?? {}), [key]: v }; };

await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });

// ── B1 kalendář → menu → rychlý přehled ──
await go('/dashboard');
await p.mouse.move(1700, 980);
const chip = p.locator('main li', { hasText: 'P03' }).first();
put('cal_base', 'chip', await rect(chip));
put('cal_base', 'tile', await rect(p.locator('main li', { hasText: 'P03' }).first().locator('xpath=ancestor::*[contains(@class,"rounded")][2]')));
await shot('cal_base');
await chip.hover(); await p.waitForTimeout(400);
put('cal_hover', 'dots', await rect(p.getByRole('button', { name: 'Akce pro P03' })));
await shot('cal_hover');
await p.getByRole('button', { name: 'Akce pro P03' }).click(); await p.waitForTimeout(700);
put('cal_menu', 'menu', await rect(p.getByRole('menu')));
put('cal_menu', 'quick', await rect(p.getByRole('menuitem', { name: /Rychlý přehled/ })));
put('cal_menu', 'detail', await rect(p.getByRole('menuitem', { name: /Otevřít detail/ })));
await shot('cal_menu');
await p.getByRole('menuitem', { name: /Rychlý přehled/ }).hover(); await p.waitForTimeout(300);
await shot('cal_menu_hover');
await p.getByRole('menuitem', { name: /Rychlý přehled/ }).click(); await p.waitForTimeout(2500);
put('cal_sheet', 'sheet', await rect(p.getByRole('dialog')));
put('cal_sheet', 'open', await rect(p.getByRole('dialog').getByRole('button', { name: /Otevřít detail/ }).or(p.getByRole('dialog').getByRole('link', { name: /Otevřít detail/ }))));
put('cal_sheet', 'head', await rect(p.getByRole('dialog').getByText('P03 · muž · 67 let')));
put('cal_sheet', 'facts', await rect(p.getByRole('dialog').getByText('Klíčové údaje', { exact: true })));
await shot('cal_sheet');

// ── B2 detail → Pro mě ──
await p.getByRole('dialog').getByRole('button', { name: /Otevřít detail/ }).or(p.getByRole('dialog').getByRole('link', { name: /Otevřít detail/ })).first().click();
await p.waitForURL(/cases\/2/, { timeout: 60000 }); await settle(3500);
await p.mouse.move(1700, 980);
put('det_top', 'toggleMe', await rect(p.getByText(/Pro mě ·/)));
put('det_top', 'back', await rect(p.getByText('Jednání', { exact: true })));
await shot('det_top');
await p.getByText(/Pro mě ·/).first().click(); await settle(1500);
await p.mouse.move(1700, 980);
await shot('det_me_top');
const askSec = p.locator('button[aria-expanded]', { hasText: 'Zeptat se na případ' }).first();
if ((await askSec.getAttribute('aria-expanded')) === 'false') await askSec.click();
await p.addStyleTag({ content: '.sticky{position:static!important}' });
await p.evaluate(() => window.scrollTo(0, 0)); await settle(1200);
for (const [k, t] of [['decide', 'Údaje pro vaše rozhodnutí'], ['postupy', 'Postupy, ke kterým se vyjadřujete'], ['ask', 'Otázka k případu'], ['proVas', 'Pro vás · klinický onkolog']]) put('det_me_full', k, await rect(p.getByText(t, { exact: true })));
put('det_me_full', 'mmr', await rect(p.locator('li, div', { hasText: /^MMR \/ MSI · jen zmínka/ }).last()));
put('det_me_full', 'dpd', await rect(p.locator('li, div', { hasText: /^Deficit DPD \(DPYD\) · chybí/ }).last()));
put('det_me_full', 'chipQ', await rect(p.getByRole('button', { name: 'Kdy byla poslední dávka oxaliplatiny a s jakou toxicitou?' })));
put('det_me_full', 'input', await rect(p.getByPlaceholder(/Např. Kdy byla poslední dávka/)));
put('det_me_full', 'submit', await rect(p.getByRole('button', { name: 'Zeptat se', exact: true })));
await shot('det_me_full', true);
await p.getByRole('button', { name: 'Kdy byla poslední dávka oxaliplatiny a s jakou toxicitou?' }).click();
await p.waitForTimeout(500);
await shot('det_ask_loading', true);
await p.waitForFunction(() => /shoda/.test(document.getElementById('dotaz')?.innerText ?? ''), null, { timeout: 120000 }).catch(() => console.log('odpověď nedorazila'));
await settle(1500);
put('det_ask_answer', 'answer', await rect(p.locator('#dotaz').getByText('AI návrh').locator('xpath=ancestor::*[self::section or self::article or self::div][2]')));
await shot('det_ask_answer', true);
console.log((await p.evaluate(() => document.getElementById('dotaz')?.innerText ?? '')).slice(0, 900));

// ── B4–B8 jednání ──
await go('/dashboard/mdt/2');
await p.mouse.move(1700, 1040);
for (const [k, n] of [['edit', 'Upravit okno pro projektor'], ['projector', 'Projektor'], ['chat', 'Chat'], ['record', /Nahrávat diskusi/], ['decision', /Závěr komise/]]) put('meet', k, await rect(p.getByRole('button', { name: n })));
put('meet', 'chip12', await rect(p.locator('main button', { hasText: /^12$/ })));
put('meet', 'ps', await rect(p.getByText('PS', { exact: true })));
await shot('meet');
// editor okna projektoru (bez uložení)
await p.getByRole('button', { name: 'Upravit okno pro projektor' }).click(); await settle(3000);
const dlg = p.getByRole('dialog');
const row = (t) => dlg.locator('li', { hasText: t }).first();
put('ed0', 'dialog', await rect(dlg));
put('ed0', 'save', await rect(dlg.getByRole('button', { name: /Uložit okno pro projektor/ })));
put('ed0', 'preview', await rect(dlg.getByText('Klíčové údaje', { exact: true }).last().locator('xpath=ancestor::*[contains(@class,"rounded")][2]')));
put('ed0', 'eyeWeight', await rect(row('Hmotnost').getByRole('button', { name: /Skrýt/ })));
put('ed0', 'eyeHbv', await rect(row('Doporučeno').getByRole('button', { name: /Skrýt/ })));
const mmrButtons = await row('MMR/MSI').getByRole('button').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')));
console.log('MMR row buttons:', mmrButtons.join(' | '));
await shot('ed0');
await row('Hmotnost').getByRole('button', { name: /Skrýt/ }).click(); await p.waitForTimeout(600); await shot('ed1');
await row('Doporučeno').getByRole('button', { name: /Skrýt/ }).click(); await p.waitForTimeout(600); await shot('ed2');
const upBtn = row('MMR/MSI').getByRole('button').nth(1);
put('ed2', 'upMmr', await rect(upBtn));
for (let i = 0; i < 9; i++) { await row('MMR/MSI').getByRole('button').nth(1).click(); await p.waitForTimeout(150); }
await p.waitForTimeout(600);
put('ed3', 'mmrRow', await rect(row('MMR/MSI')));
await shot('ed3');
await dlg.getByRole('button', { name: 'Zrušit' }).click(); await p.waitForTimeout(800);
// citace → panel zdroje
await p.locator('main button', { hasText: /^12$/ }).first().click(); await settle(1500);
put('drawer', 'panel', await rect(p.getByRole('dialog')));
await shot('drawer');
await p.keyboard.press('Escape'); await p.waitForTimeout(600);
// chat: čisté zprávy jen v DOM
await p.getByRole('button', { name: 'Chat' }).click(); await settle(2500);
const MSGS = [
  { own: false, name: 'Chirurg', time: '14:02', text: 'FLR 38 % – jednodobá resekce je hraniční, zvažuji dvoudobý postup.' },
  { own: false, name: 'Radiolog', time: '14:03', text: 'Restaging je bez CT hrudníku. Bez něj resekabilitu neuzavřu.' },
  { own: true, name: 'Vy', spec: 'Klinický onkolog', time: '14:04', text: 'Souhlas. Doplníme i MMR/MSI z bioptického bloku.' },
  { own: false, name: 'Radiolog', time: '14:05', text: 'CT hrudníku jsem objednal na pátek 23. 10.' },
];
const fillChat = (n) => p.evaluate(({ msgs, n }) => {
  const log = document.querySelector('ol[role=log]');
  const items = [...log.querySelectorAll(':scope > li')];
  const ownT = items.find((li) => li.className.includes('items-end'));
  const otherT = items.find((li) => li.className.includes('items-start'));
  log.innerHTML = '';
  for (const m of msgs.slice(0, n)) {
    const li = (m.own ? ownT : otherT).cloneNode(true);
    const meta = li.querySelector('p');
    const spans = meta.querySelectorAll('span');
    spans[0].textContent = m.name;
    if (spans.length > 1 && !spans[1].getAttribute('translate')) { if (m.spec) spans[1].textContent = m.spec; else spans[1].remove(); }
    meta.querySelector('time').textContent = m.time;
    const tag = meta.querySelector('button, span[translate]'); if (tag) tag.textContent = 'P03';
    li.querySelectorAll('p')[1].textContent = m.text;
    log.appendChild(li);
  }
  log.scrollTop = log.scrollHeight;
}, { msgs: MSGS, n });
await fillChat(3); await p.waitForTimeout(400);
put('chat3', 'panel', await rect(p.locator('section[aria-labelledby="session-chat-title"]')));
put('chat3', 'log', await rect(p.locator('ol[role=log]')));
await shot('chat3');
await fillChat(4); await p.waitForTimeout(400);
put('chat4', 'last', await rect(p.locator('ol[role=log] > li').last()));
put('chat4', 'tag', await rect(p.locator('ol[role=log] > li').last().locator('button, span[translate]')));
await shot('chat4');

// ── B8–B9 závěr komise ──
await go('/dashboard/cases/2/record');
for (const [k, t] of [['confirmed', 'Potvrzeno:'], ['iris', 'Zapsáno do IRIS'], ['assess', 'Klinické zhodnocení']]) put('record', k, await rect(p.getByText(new RegExp('^' + t))));
put('record', 'pdf', await rect(p.getByText('Export PDF', { exact: true })));
put('record', 'fhir', await rect(p.getByText('FHIR document Bundle', { exact: true })));
await shot('record', true);

// ── projektor (fallback obsah plátna) ──
await go('/projector?board=2&case=2&patient=P03');
await shot('projector');

writeFileSync(new URL('layout2.json', OUT), JSON.stringify(L, null, 2));
console.log('layout2.json hotovo');
await browser.close();
