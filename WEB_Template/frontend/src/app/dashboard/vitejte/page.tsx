'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { Page, PageHeader } from '@/components/layout/Page';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useRouter } from 'next/navigation';
import { MDT_ROLE_LABEL, useMe, useRefreshMe } from '@/components/mdt/me';
import { NormsEditor, RequirementsEditor } from '@/components/mdt/MyRulesEditor';
import { MyTemplateCard } from '@/components/mdt/MyTemplateCard';
import { ROLE_META } from '@/components/mdt/roles';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { cn } from '@/lib/utils';

const STEPS = [
  { title: 'Profil', hint: 'Zkontrolujte jméno, tituly a profesi z pozvánky.' },
  {
    title: 'Můj PVW',
    hint: 'Nejdřív si nastavte, jak má vypadat PVW (okno pro projektor): co je pro vás „must have“ a v jakém pořadí. Platí u pacientů, které zařazujete; u konkrétního pacienta jde upravit.',
  },
  {
    title: 'Moje požadavky',
    hint: 'Co vyžadujete, když jste na MDT pozvaný. Lékař, který pacienta připravuje, uvidí upozornění, co chybí, a rozhodne, zda vás u pacienta potřebuje.',
  },
  {
    title: 'Moje normy',
    hint: 'Prahy a kritéria pro řešení, za která odpovídáte. Na PVW se ukážou s vaším jménem a hodnotou pacienta. Semafor postupů nemění.',
  },
] as const;

/**
 * Průvodce nastavením lékaře po prvním přihlášení (T-358, D-028, docs/UCTY_A_PVW.md §3): profil → must-have PVW
 * s živým náhledem → požadavky → normy. Každý krok jde přeskočit a později změnit v Nastavení.
 */
export default function OnboardingPage() {
  const me = useMe();
  const refreshMe = useRefreshMe();
  const router = useRouter();
  const [step, setStep] = React.useState(0);
  const [finishing, setFinishing] = React.useState(false);
  const saveTemplate = React.useRef<(() => Promise<void>) | null>(null);
  // Můj PVW se při odchodu z kroku uloží sám (lékař na tlačítko Uložit nemusí myslet)
  const go = async (next: number) => {
    if (step === 1 && saveTemplate.current) await saveTemplate.current();
    setStep(next);
  };

  const finish = async () => {
    setFinishing(true);
    try {
      await mdtApi.finishOnboarding();
      toast.success('Nastavení hotové', { description: 'Kdykoli ho změníte v Nastavení.' });
      refreshMe();                                    // profil znovu: průvodce už se nenabízí
      router.push('/dashboard');
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Nastavení se nepodařilo uložit.'));
      setFinishing(false);
    }
  };

  return (
    <Page className="max-w-6xl">
      <PageHeader title="Nastavení lékaře" meta={`Krok ${step + 1} ze ${STEPS.length} · ${STEPS[step].title}`} />
      <ol className="mb-5 flex flex-wrap gap-2" aria-label="Kroky průvodce">
        {STEPS.map((s, i) => (
          <li key={s.title}>
            <button type="button" onClick={() => void go(i)} aria-current={i === step ? 'step' : undefined}
              className={cn('rounded-full border px-3 py-1 text-[13px] font-medium',
                i === step ? 'border-primary bg-primary text-primary-foreground'
                  : i < step ? 'border-border bg-card text-foreground' : 'border-border bg-card text-muted-foreground')}>
              {i + 1}. {s.title}
            </button>
          </li>
        ))}
      </ol>
      <p className="mb-5 max-w-3xl text-sm text-muted-foreground">{STEPS[step].hint}</p>

      {!me ? (
        <Skeleton className="h-64" />
      ) : step === 0 ? (
        <ProfileStep />
      ) : step === 1 ? (
        <MyTemplateCard showTitles={false} bare onboarding saveRef={saveTemplate} />
      ) : step === 2 ? (
        <RequirementsEditor />
      ) : (
        <NormsEditor />
      )}

      <div className="mt-6 flex flex-wrap gap-2 border-t border-border pt-4">
        {step > 0 && <Button variant="outline" onClick={() => void go(step - 1)}>Zpět</Button>}
        {step < STEPS.length - 1 ? (
          <>
            <Button onClick={() => void go(step + 1)}>Pokračovat</Button>
            <Button variant="ghost" onClick={() => setStep(step + 1)}>Přeskočit krok</Button>
          </>
        ) : (
          <Button onClick={() => void finish()} isLoading={finishing}>Dokončit nastavení</Button>
        )}
      </div>
    </Page>
  );
}

function ProfileStep() {
  const me = useMe()!;
  const [titles, setTitles] = React.useState({ title_before: me.title_before ?? '', title_after: me.title_after ?? '' });
  const [saving, setSaving] = React.useState(false);
  const changed = titles.title_before !== (me.title_before ?? '') || titles.title_after !== (me.title_after ?? '');
  const save = async () => {
    setSaving(true);
    try {
      const updated = await mdtApi.updateMyTitles(titles);
      toast.success(`Uloženo: ${updated.name}`);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Tituly se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="flex max-w-xl flex-col gap-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 rounded-xl border border-border bg-card p-4 text-sm">
        <dt className="text-muted-foreground">Jméno</dt><dd className="font-medium">{me.name}</dd>
        <dt className="text-muted-foreground">Profese</dt><dd>{me.specialty ? ROLE_META[me.specialty].label : 'nevyplněno'}</dd>
        <dt className="text-muted-foreground">Role</dt><dd>{MDT_ROLE_LABEL[me.role]}{me.is_manager ? ' · správce MDT' : ''}</dd>
        <dt className="text-muted-foreground">Nemocnice</dt><dd>{me.is_external ? me.organization : 'naše'}</dd>
        <dt className="text-muted-foreground">Komise</dt><dd>{me.committees?.length ? me.committees.map((c) => c.name).join(', ') : 'zatím žádná'}</dd>
      </dl>
      <p className="text-xs text-muted-foreground">Profesi, roli, nemocnici a komise mění správce MDT.</p>
      <div className="grid grid-cols-[1fr_1fr_auto] items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold">
          Titul před jménem
          <Input value={titles.title_before} onChange={(e) => setTitles({ ...titles, title_before: e.target.value })} placeholder="MUDr." maxLength={40} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold">
          Titul za jménem
          <Input value={titles.title_after} onChange={(e) => setTitles({ ...titles, title_after: e.target.value })} placeholder="Ph.D." maxLength={40} />
        </label>
        <Button variant="outline" onClick={() => void save()} disabled={!changed} isLoading={saving}>Uložit tituly</Button>
      </div>
    </div>
  );
}
