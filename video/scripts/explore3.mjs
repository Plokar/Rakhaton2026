// Průzkum interakcí pro film B v2 (jen čtení; nic neukládá ani neodesílá): menu pacienta v kalendáři,
// rychlý přehled, chat, editor okna projektoru, ukončení boardu (zrušit), detail (druhá AI, podobné, dotaz).
import { chromium } from 'playwright';
const BASE = 'https://medteam.nervelabs.co.uk';
const out = process.argv[2];
const b = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
const shot = async (n) => { await p.waitForTimeout(1800); await p.screenshot({ path: `${out}/${n}.png` }); console.log('saved', n); };
const step = async (name, fn) => { try { await fn(); } catch (e) { console.log('FAIL', name, e.message.split('\n')[0]); } };
const go = async (path) => { await p.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 60000 }); await p.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {}); await p.waitForTimeout(1500); };

await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });

await step('calendar menu', async () => {
  await go('/dashboard');
  const chip = p.locator('li', { hasText: 'P03' }).first();
  await chip.hover(); await shot('c1_hover');
  await p.getByRole('button', { name: 'Akce pro P03' }).click(); await shot('c2_menu');
  await p.getByRole('menuitem', { name: /Rychlý přehled/ }).hover(); await shot('c3_menu_hover');
  await p.getByRole('menuitem', { name: /Rychlý přehled/ }).click(); await p.waitForTimeout(2500); await shot('c4_sheet');
  console.log((await p.evaluate(() => [...document.querySelectorAll('[role=dialog] button, [role=dialog] a')].map((e) => e.innerText.trim()).filter(Boolean).join(' | '))).slice(0, 600));
});
await step('session chat', async () => {
  await go('/dashboard/mdt/2');
  await p.getByRole('button', { name: 'Chat' }).click(); await p.waitForTimeout(2500); await shot('s1_chat');
  await p.keyboard.press('Escape');
});
await step('projector editor', async () => {
  await go('/dashboard/mdt/2');
  await p.getByRole('button', { name: 'Upravit okno pro projektor' }).click(); await p.waitForTimeout(3000); await shot('s2_pjeditor');
  console.log((await p.evaluate(() => document.querySelector('[role=dialog]')?.innerText ?? '')).slice(0, 900));
  await p.keyboard.press('Escape');
});
await step('close board dialog', async () => {
  await go('/dashboard/mdt/2');
  await p.getByRole('button', { name: 'Ukončit board' }).click(); await p.waitForTimeout(1500); await shot('s3_close');
  console.log((await p.evaluate(() => document.querySelector('[role=dialog]')?.innerText ?? '')).slice(0, 500));
  await p.keyboard.press('Escape');
});
await step('detail sections', async () => {
  await go('/dashboard/cases/2');
  for (const id of ['pro-me', 'souhrn', 'varovani', 'podobne', 'dotaz']) {
    await p.evaluate((id) => document.getElementById(id)?.scrollIntoView({ block: 'start' }), id);
    await shot(`d_${id}`);
  }
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await shot('d_bottom');
});
await step('detail ask', async () => {
  await go('/dashboard/cases/2');
  await p.evaluate(() => document.getElementById('dotaz')?.scrollIntoView({ block: 'start' }));
  const ta = p.locator('#dotaz textarea, #dotaz input').first();
  await ta.fill('Kdy byla poslední dávka bevacizumabu a jaké je riziko pro resekci?');
  await shot('d_ask_typed');
  await ta.press('Enter');
  await p.waitForTimeout(45000); await shot('d_ask_answer');
});
await step('record p02', async () => { await go('/dashboard/cases/1/record'); await shot('r_p02'); });
await step('new patient form', async () => {
  await go('/dashboard/mdt/6/add');
  await p.getByRole('button', { name: /Nový pacient/ }).click(); await p.waitForTimeout(2000); await shot('n1_newpatient');
});
await step('zaznamy', async () => { await go('/dashboard/zaznamy'); await shot('z_zaznamy'); });
await step('tasks', async () => { await go('/dashboard/tasks'); await shot('t_tasks'); });
await b.close();
