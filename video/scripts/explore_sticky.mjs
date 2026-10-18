// Které prvky detailu pacienta jsou sticky/fixed (zůstávají při posouvání) a jejich bboxy.
import { chromium } from 'playwright';
const BASE = 'https://medteam.nervelabs.co.uk';
const b = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const p = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
await p.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
await p.getByRole('button', { name: 'Povolit vše' }).click({ timeout: 8000 }).catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 60000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });
await p.goto(BASE + '/dashboard/cases/1', { waitUntil: 'domcontentloaded' }); await p.waitForTimeout(5000);
for (const sy of [0, 3000]) {
  await p.evaluate((y) => window.scrollTo(0, y), sy); await p.waitForTimeout(800);
  const res = await p.evaluate(() => [...document.querySelectorAll('body *')].filter((e) => ['sticky', 'fixed'].includes(getComputedStyle(e).position))
    .map((e) => { const r = e.getBoundingClientRect(); return `${getComputedStyle(e).position} ${e.tagName.toLowerCase()} ${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.width)}x${Math.round(r.height)} ${(e.getAttribute('aria-label') || e.className || '').toString().slice(0, 60)} | ${(e.innerText || '').replace(/\n/g, ' ').slice(0, 50)}`; }));
  console.log('scrollY', sy, await p.evaluate(() => scrollY), 'scroller:', await p.evaluate(() => document.scrollingElement.scrollHeight));
  console.log(res.join('\n'));
  const nav = await p.evaluate(() => [...document.querySelectorAll('nav a, nav button')].filter((a) => a.getBoundingClientRect().x > 300 && a.getBoundingClientRect().x < 700).map((a) => `${a.innerText.replace(/\n/g, ' ')}${a.getAttribute('aria-current') ? '*' : ''}`).join(' | '));
  console.log('nav:', nav);
}
await b.close();
