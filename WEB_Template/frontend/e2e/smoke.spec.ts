import { expect, test, type Page } from '@playwright/test';

/**
 * Smoke test celého cyklu (T-378): předseda od kalendáře po závěr, člen komise na mobilu.
 * Po celou dobu: žádná výjimka v prohlížeči, žádná odpověď 5xx ani chyba konzole (po T-375 ani 404).
 */
const API = process.env.E2E_API_URL ?? 'http://localhost:8000';
const PASSWORD = process.env.E2E_PASSWORD ?? 'demo123456';

function watchProblems(page: Page) {
  const problems: string[] = [];
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') problems.push(`console: ${m.text().slice(0, 200)}`);
  });
  page.on('response', (r) => {
    if (r.status() >= 500 || (r.status() === 404 && r.url().includes('/api/'))) {
      problems.push(`${r.status()} ${r.request().method()} ${r.url()}`);
    }
  });
  return problems;
}

async function login(page: Page, username: string) {
  await page.goto('/login');
  await page.locator('#login-username').fill(username);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.keyboard.press('Enter');
  await page.waitForURL('**/dashboard**');
}

/** Zasedání a případ pacienta P03 z API (ID se v čisté databázi mohou lišit). */
async function caseOf(page: Page, patient: string) {
  const sessions: { id: number; patients: string[] }[] = await (await page.request.get(`${API}/api/mdt/sessions/`)).json();
  const session = sessions.find((s) => s.patients.includes(patient));
  expect(session, `zasedání s ${patient}`).toBeTruthy();
  const detail: { cases: { id: number; patient_id: string }[] } =
    await (await page.request.get(`${API}/api/mdt/sessions/${session!.id}/`)).json();
  const item = detail.cases.find((c) => c.patient_id === patient);
  expect(item, `případ ${patient}`).toBeTruthy();
  return { sessionId: session!.id, caseId: item!.id };
}

test('předseda: kalendář → jednání → podklad s citací → závěr → úkoly, tým, projektor', async ({ page }) => {
  const problems = watchProblems(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, 'predseda');
  await expect(page.getByRole('heading', { name: 'Kalendář zasedání' })).toBeVisible();

  const { sessionId, caseId } = await caseOf(page, 'P03');
  await page.goto(`/dashboard/mdt/${sessionId}`);
  await expect(page.getByText('P03 · muž · 67 let').first()).toBeVisible();

  await page.goto(`/dashboard/cases/${caseId}`);
  const generate = page.getByRole('button', { name: 'Vytvořit podklad' });
  if (await generate.isVisible().catch(() => false)) {
    await generate.click();
    await expect(page.getByText('Podklad je připravený')).toBeVisible({ timeout: 90_000 });
  }
  const citation = page.getByRole('button', { name: /^Otevřít zdroj / }).first();
  await citation.click();
  await expect(page.locator('[data-slot="sheet-content"]')).toBeVisible();
  await page.keyboard.press('Escape');

  await page.goto(`/dashboard/cases/${caseId}/record`);
  const intent = page.locator('select', { has: page.locator('option', { hasText: 'Kurativní (C)' }) }).first();
  await intent.selectOption({ label: 'Kurativní (C)' });
  await page.getByRole('button', { name: 'Uložit draft' }).click();
  await expect(page.getByText(/Uloženo v/)).toBeVisible();

  await page.goto('/dashboard/tasks');
  await expect(page.getByRole('heading', { name: 'Úkoly po zasedání' })).toBeVisible();
  await page.goto('/dashboard/tym');
  await expect(page.getByRole('heading', { name: 'Tým a účty' })).toBeVisible();
  await page.getByRole('tab', { name: 'Přístupy' }).click();
  await expect(page.getByRole('cell', { name: 'P03' }).first()).toBeVisible();
  await page.goto('/projector');
  await expect(page.locator('body')).not.toBeEmpty();
  await page.waitForTimeout(1500);

  expect(problems, problems.join('\n')).toEqual([]);
});

test('člen komise na mobilu: kalendář, jednání, detail, Živě na MDT bez vodorovného posouvání', async ({ page }) => {
  const problems = watchProblems(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'chirurg');
  const { sessionId, caseId } = await caseOf(page, 'P03');
  for (const path of ['/dashboard', `/dashboard/mdt/${sessionId}`, `/dashboard/cases/${caseId}`, '/dashboard/live']) {
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `vodorovné posouvání na ${path}`).toBeLessThanOrEqual(2);
  }
  expect(problems, problems.join('\n')).toEqual([]);
});
