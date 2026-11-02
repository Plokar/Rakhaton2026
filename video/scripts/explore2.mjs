// Průzkum interakcí (bez ukládání): formulář zařazení, panel zdroje citace, porovnání zdrojů.
import { chromium } from 'playwright';
const BASE = 'https://medteam.nervelabs.co.uk';
const out = process.argv[2];
const b = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
await p.goto(BASE + '/login', { waitUntil: 'networkidle' });
await p.getByRole('button', { name: 'Povolit vše' }).click().catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 30000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });
const snap = async (n) => { await p.waitForTimeout(2500); await p.screenshot({ path: `${out}/${n}.png` }); console.log('saved', n, p.url()); };
// 1) zařazení: klik na P01 (jen otevře formulář, nic neukládá)
await p.goto(BASE + '/dashboard/mdt/2/add', { waitUntil: 'networkidle' });
await p.getByRole('button', { name: /^P01/ }).click();
await snap('add_p01');
console.log((await p.evaluate(() => document.querySelector('main')?.innerText || '')).slice(0, 1500));
// 2) jednání: klik na první citační čip
await p.goto(BASE + '/dashboard/mdt/2', { waitUntil: 'networkidle' });
await p.waitForTimeout(2000);
await p.locator('main button', { hasText: /^12$/ }).first().click();
await snap('drawer_12');
console.log((await p.evaluate(() => [...document.querySelectorAll('[role=dialog]')].map(d => d.innerText).join('\n---\n'))).slice(0, 1500));
await b.close();
