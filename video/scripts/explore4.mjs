// Průzkum 2 pro film B v2 (jen čtení): rozbalené sekce detailu, porovnání zdrojů, dotaz na případ (bezstavový),
// kontrola druhou AI, stavy editoru okna projektoru (bez uložení), nahrávání diskuse (jen tlačítko).
import { chromium } from 'playwright';
const BASE = 'https://medteam.nervelabs.co.uk';
const out = process.argv[2];
const b = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
const shot = async (n, full = false) => { await p.waitForTimeout(1500); await p.screenshot({ path: `${out}/${n}.png`, fullPage: full }); console.log('saved', n); };
const step = async (name, fn) => { try { await fn(); } catch (e) { console.log('FAIL', name, e.message.split('\n')[0]); } };
const go = async (path) => { await p.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 60000 }); await p.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {}); await p.waitForTimeout(1500); };
const text = (sel) => p.evaluate((sel) => document.querySelector(sel)?.innerText ?? '', sel);

await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });

await step('detail sections', async () => {
  await go('/dashboard/cases/2');
  for (const name of ['Varovné signály', 'Podobné případy', 'Zeptat se na případ']) {
    const btn = p.locator('button[aria-expanded]', { hasText: name }).first();
    if ((await btn.getAttribute('aria-expanded')) === 'false') await btn.click();
    await p.waitForTimeout(800);
  }
  await p.waitForTimeout(3000);
  await shot('e_detail_full', true);
  console.log('VERIFIER:', (await text('[aria-label="Kontrola druhou AI"]')).slice(0, 400));
  const cmp = p.getByRole('button', { name: /Porovnat oba zdroje/ }).first();
  await cmp.scrollIntoViewIfNeeded(); await shot('e_flags_before');
  await cmp.click(); await shot('e_flags_compare');
  await p.evaluate(() => document.getElementById('podobne')?.scrollIntoView({ block: 'start' })); await shot('e_similar');
  console.log('SIMILAR:', (await text('#podobne')).slice(0, 500));
  await p.evaluate(() => document.getElementById('dotaz')?.scrollIntoView({ block: 'start' })); await shot('e_ask_empty');
  const ta = p.locator('#dotaz textarea').first();
  await ta.fill('Kdy byla poslední dávka bevacizumabu a jak to ovlivní termín resekce?');
  await shot('e_ask_typed');
  await p.locator('#dotaz button[type=submit], #dotaz button', { hasText: /Zeptat|Odeslat/ }).first().click().catch(async () => ta.press('Enter'));
  for (let i = 0; i < 20; i++) { await p.waitForTimeout(3000); if (!(await p.locator('#dotaz [aria-busy=true]').count())) break; }
  await p.waitForTimeout(2000);
  await shot('e_ask_answer');
  console.log('ANSWER:', (await text('#dotaz')).slice(0, 900));
});
await step('projector editor states', async () => {
  await go('/dashboard/mdt/2');
  await p.getByRole('button', { name: 'Upravit okno pro projektor' }).click(); await p.waitForTimeout(3500); await shot('f_ed0');
  const dlg = p.locator('[role=dialog]');
  const eyes = dlg.locator('button[aria-label*="Skrýt"], button[aria-label*="skrýt"]');
  console.log('eyes', await eyes.count(), (await eyes.evaluateAll((els) => els.slice(0, 6).map((e) => e.getAttribute('aria-label')))).join(' | '));
  await eyes.nth(0).click(); await shot('f_ed1_hide_anamneza');
  const ups = dlg.locator('button[aria-label*="nahoru"], button[aria-label*="Nahoru"]');
  console.log('ups', await ups.count(), (await ups.evaluateAll((els) => els.slice(0, 8).map((e) => e.getAttribute('aria-label')))).join(' | '));
  await p.keyboard.press('Escape');
});
await step('record button + projector btn', async () => {
  await go('/dashboard/mdt/2');
  await p.getByRole('button', { name: /Nahrávat diskusi/ }).hover(); await shot('g_rec_hover');
});
await b.close();
