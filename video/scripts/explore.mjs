// Průzkum živé aplikace: přihlášení předsedy, tmavý režim, snímky hlavních obrazovek.
import { chromium } from 'playwright';
const BASE = 'https://medteam.nervelabs.co.uk';
const [out, ...routes] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: process.env.LOCALAPPDATA + '/ms-playwright/chromium-1228/chrome-win64/chrome.exe' });
const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 } });
const p = await ctx.newPage();
await p.goto(BASE + '/login', { waitUntil: 'networkidle' });
await p.getByRole('button', { name: 'Povolit vše' }).click().catch(() => {});
await p.getByRole('button', { name: /Předseda komise/ }).click();
await p.waitForURL(/dashboard/, { timeout: 30000 });
await p.evaluate(() => { localStorage.setItem('theme', 'dark'); window.dispatchEvent(new Event('mdt-theme-change')); });
for (const r of routes) {
  await p.goto(BASE + r, { waitUntil: 'networkidle' }).catch(() => {});
  await p.waitForTimeout(3000);
  const name = r.replace(/[^\w]+/g, '_');
  await p.screenshot({ path: `${out}/${name}.png` });
  const h = await p.evaluate(() => document.documentElement.scrollHeight);
  const links = await p.evaluate(() => [...new Set([...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')))].filter(h => !/^\/dashboard(\/mdt\/\d)?$/.test(h)));
  const btns = await p.evaluate(() => [...document.querySelectorAll('main button')].map(e => e.textContent.trim()).filter(Boolean).slice(0, 40));
  console.log(`\n== ${r} -> ${p.url()} h=${h}\nlinks: ${links.join(' ')}\nbuttons: ${btns.join(' | ')}`);
}
await b.close();
