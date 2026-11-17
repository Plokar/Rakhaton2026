// Snímky pro klip „Chatbot“: jednání P04 (tmavý režim) s otevřeným panelem chatbotu.
// Na produkci se rozhovor nenačte, proto se dotaz a odpověď vkládají JEN do DOM prohlížeče se stejnými třídami
// jako ChatbotPanel / ClaimItem / AiTag (nic se neodesílá; pole se jen vyplní, neodešle).
// Hodnota z datasetu: P04-spiro01 · FEV1 1,9 l (58 % NH) · 25. 8. 2026 · zdroj P04-doc03 (spirometrie, pneumologická ambulance).
// Výstup: public/textures/bot/{empty,loading,answer,drawer}.png + type_N.png (pole při psaní) + bot.json.
import { chromium } from 'playwright';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const BASE = process.env.MDT_BASE ?? 'https://medteam.nervelabs.co.uk';
const OUT = new URL('../public/textures/bot/', import.meta.url);
const Q = 'Jaká je hodnota FEV1?';
rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });
const file = (n) => fileURLToPath(new URL(n, OUT));
const browser = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 })).newPage();
const HIDE = '::-webkit-scrollbar{display:none!important} *{scrollbar-width:none!important} nextjs-portal{display:none!important} textarea{caret-color:transparent!important}';

await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });
await p.goto(BASE + '/dashboard/mdt/3', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
await p.waitForTimeout(4000);
await p.getByRole('button', { name: /^Chatbot/ }).first().click();
await p.waitForTimeout(3000);
await p.addStyleTag({ content: HIDE });
await p.evaluate(() => document.fonts.ready);
await p.mouse.move(1919, 600);

const PANEL = 'section[aria-labelledby="chatbot-title"]';
const rect = (sel) => p.evaluate((sel) => { const e = document.querySelector(sel); if (!e) return null; const b = e.getBoundingClientRect(); return { x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }; }, sel);

// vzor citačního čipu z klíčových údajů (skutečné třídy aplikace)
const chipHtml = await p.evaluate(() => document.querySelector('main button[aria-label^="Otevřít zdroj P04-"]')?.outerHTML ?? '');
if (!chipHtml) throw new Error('nenalezen citační čip');

const setList = (html) => p.evaluate(({ sel, html }) => { document.querySelector(`${sel} ol[role=log]`).innerHTML = html; }, { sel: PANEL, html });
const chip = (text, label) => chipHtml.replace(/aria-label="[^"]*"/, `aria-label="Otevřít zdroj ${label}"`).replace(/>[^<>]*<\/button>$/, `>${text}</button>`);
const EMPTY = `<li class="space-y-2 text-sm text-muted-foreground"><p>Zeptejte se AI na pacienta na řadě, třeba „Jak se vyvíjí CEA?“ nebo „Splňuje kritéria studie RKT-03?“.</p><p>AI odpovídá jen z dokumentace v IRIS. Každé tvrzení má zdroj, kliknutím na číslo ho otevřete. Rozhovor vidíte jen vy.</p></li>`;
const QUESTION = `<li class="flex flex-col items-end gap-1 pl-8"><p class="flex flex-wrap items-baseline gap-x-1.5 text-xs text-muted-foreground"><span class="font-medium text-foreground">Vy</span><time class="tabular-nums">14:06</time><span class="rounded-md bg-muted px-1.5 py-px font-medium text-foreground">P04</span></p><p class="max-w-full rounded-lg bg-primary/10 px-3 py-2 text-sm whitespace-pre-wrap break-words text-foreground">${Q}</p></li>`;
const SPIN = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="size-4"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>';
const LOADING = `<li class="flex items-center gap-2 text-sm text-muted-foreground" data-v="loader">${SPIN}AI odpovídá…</li>`;
const CAL = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="size-3.5 shrink-0"><path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/></svg>';
const DOC = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="size-3.5 shrink-0"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>';
const ANSWER = `<li class="flex flex-col items-start gap-1 pr-4" data-v="answer">
  <p class="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground"><span class="inline-flex shrink-0 items-center rounded-md bg-ai-soft px-1.5 py-0.5 text-xs font-medium text-ai">AI návrh</span><span class="font-medium text-foreground">P04</span><time class="tabular-nums">14:06</time></p>
  <div class="w-full space-y-2 border-l-2 border-ai/50 pl-3">
    <ul class="flex flex-col gap-2">
      <li><p class="text-sm leading-relaxed" data-v="value">FEV1 je <strong class="font-semibold text-foreground">1,9 l (58 % náležité hodnoty)</strong>. ${chip('1', 'P04-spiro01')}<span class="ml-1.5 inline-flex items-center rounded bg-muted px-1 align-baseline text-[11px] tabular-nums text-muted-foreground">shoda 96 %</span></p></li>
    </ul>
    <div class="space-y-1 rounded-md bg-muted/60 px-2.5 py-2 text-xs text-muted-foreground" data-v="meta">
      <p class="flex items-center gap-1.5" data-v="date">${CAL}<span>Naměřeno <span class="font-medium text-foreground">25. 8. 2026</span> · pneumologie</span></p>
      <p class="flex items-center gap-1.5" data-v="source">${DOC}<span>Zdroj: <span class="font-medium text-primary underline underline-offset-2" data-v="link">P04-doc03 · spirometrie</span></span></p>
    </div>
  </div>
</li>`;

const L = { panel: await rect(PANEL), list: await rect(`${PANEL} ol[role=log]`), form: await rect(`${PANEL} form`), input: await rect('#chatbot-input'), send: await rect(`${PANEL} button[type=submit]`) };

// 1) prázdný rozhovor
await setList(EMPTY);
await p.waitForTimeout(300);
await p.screenshot({ path: file('empty.png') });
// 2) psaní dotazu: jen vyplnění pole (neodesílá se)
const F = L.form;
for (let i = 1; i <= Q.length; i++) {
  await p.fill('#chatbot-input', Q.slice(0, i));
  await p.waitForTimeout(60);
  await p.screenshot({ path: file(`type_${i}.png`), clip: { x: F.x, y: F.y, width: F.w, height: F.h } });
}
await p.fill('#chatbot-input', '');
await p.waitForTimeout(200);
// 3) dotaz odeslán, AI odpovídá
await setList(QUESTION + LOADING);
await p.waitForTimeout(300);
await p.screenshot({ path: file('loading.png') });
L.loader = await rect(`${PANEL} [data-v=loader]`);
// 4) odpověď
await setList(QUESTION + ANSWER);
await p.waitForTimeout(400);
await p.screenshot({ path: file('answer.png') });
for (const k of ['answer', 'value', 'meta', 'date', 'source', 'link']) L[k] = await rect(`${PANEL} [data-v=${k}]`);
L.question = await rect(`${PANEL} ol[role=log] > li:first-child`);
// 5) skutečný panel zdroje: citace u FEV1 v klíčových údajích (P04-spiro01 → dokument P04-doc03)
const src = p.locator('main button[aria-label="Otevřít zdroj P04-spiro01"]').first();
if (!(await src.count())) throw new Error('citace P04-spiro01 nenalezena');
await src.click();
await p.waitForTimeout(2500);
await p.mouse.move(1000, 600);
L.drawer = await rect('[role=dialog]');
L.drawerText = (await p.evaluate(() => document.querySelector('[role=dialog]')?.innerText ?? '')).slice(0, 600);
L.sentence = await p.evaluate(() => {
  const d = document.querySelector('[role=dialog]');
  const w = document.createTreeWalker(d, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const i = n.textContent.indexOf('FEV1 1,9 l');
    if (i < 0) continue;
    const r = document.createRange();
    r.setStart(n, i); r.setEnd(n, Math.min(n.textContent.length, i + 'FEV1 1,9 l (58 % náležité hodnoty)'.length));
    return [...r.getClientRects()].map((b) => ({ x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }));
  }
  return null;
});
await p.screenshot({ path: file('drawer.png') });
writeFileSync(new URL('bot.json', OUT), JSON.stringify({ q: Q, ...L }, null, 2));
console.log(JSON.stringify({ ...L, drawerText: L.drawerText.replace(/\n+/g, ' | ') }, null, 1));
await browser.close();
