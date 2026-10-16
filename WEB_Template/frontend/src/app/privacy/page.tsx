'use client';

import * as React from 'react';
import Link from 'next/link';
import { useCookieConsent } from '@/contexts/CookieContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import {
  ShieldCheck,
  ArrowLeft,
  Cookie,
  Lock,
  Database,
  Bot,
  UserCheck,
  FileText,
  Mail,
  SlidersHorizontal,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

export default function PrivacyPolicyPage() {
  const { preferences, openSettings, hasAnswered } = useCookieConsent();

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Top Navigation */}
      <header className="sticky top-0 z-40 w-full border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Zpět na hlavní stránku</span>
          </Link>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link href="/terms">
              <Button variant="ghost" size="sm" className="text-xs">
                Podmínky užití
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="text-xs">
                Začít hackovat
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 py-12 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          {/* Header */}
          <div className="mb-10 text-center sm:text-left border-b border-border pb-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary mb-4">
              <ShieldCheck className="h-3.5 w-3.5" /> Ochrana soukromí &amp; GDPR
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-foreground">
              Zásady ochrany osobních údajů
            </h1>
            <p className="mt-3 text-base text-muted-foreground leading-relaxed">
              V Hackathon OS klademe maximální důraz na bezpečnost vašich dat, transparentnost
              jejich zpracování a respekt k soukromí vývojářů i uživatelů.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
              <span>Poslední aktualizace: <strong>11. září 2026</strong></span>
              <span>•</span>
              <span>Verze: <strong>2.0</strong></span>
              <span>•</span>
              <span>Právní rámec: <strong>Nařízení EU 2016/679 (GDPR)</strong></span>
            </div>
          </div>

          {/* Interactive Cookie Preference Box */}
          <div className="mb-10 rounded-2xl border border-primary/30 bg-primary/5 p-6 relative overflow-hidden">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Cookie className="h-4 w-4 text-primary" />
                  <span className="font-semibold text-sm text-foreground">
                    Vaše aktuální preference cookies
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {hasAnswered ? (
                    <span>
                      Nezbytné: <strong>Aktivní</strong> • Analytické:{' '}
                      <strong>{preferences.analytics ? 'Povoleno' : 'Zakázáno'}</strong> • Funkční:{' '}
                      <strong>{preferences.marketing ? 'Povoleno' : 'Zakázáno'}</strong>
                    </span>
                  ) : (
                    <span>Zatím jste nenastavili své předvolby pro cookies.</span>
                  )}
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={openSettings}
                className="gap-2 shrink-0 bg-background"
              >
                <SlidersHorizontal className="h-3.5 w-3.5 text-primary" />
                Upravit nastavení cookies
              </Button>
            </div>
          </div>

          {/* Policy Content */}
          <div className="space-y-10 text-sm leading-relaxed text-muted-foreground">
            {/* 1. Správce */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <UserCheck className="h-5 w-5 text-primary" />
                1. Správce osobních údajů
              </h2>
              <p>
                Správcem osobních údajů zpracovávaných v rámci projektu <strong>Hackathon OS</strong> je
                provozovatel a organizátorský tým této instalace webové aplikace (dále jen „Správce“).
              </p>
              <p>
                V případě jakýchkoli dotazů týkajících se zpracování osobních údajů nebo uplatnění vašich
                práv nás můžete kontaktovat na e-mailové adrese:{' '}
                <a
                  href="mailto:privacy@hackathon-os.local"
                  className="font-medium text-primary hover:underline"
                >
                  privacy@hackathon-os.local
                </a>.
              </p>
            </section>

            {/* 2. Zpracovávané údaje */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                2. Rozsah zpracovávaných osobních údajů
              </h2>
              <p>
                Zpracováváme pouze ty údaje, které jsou nezbytné pro fungování hackathon platformy,
                autorizaci uživatele a stabilitu infrastruktury:
              </p>
              <ul className="list-disc pl-5 space-y-2">
                <li>
                  <strong>Registrační a profilové údaje:</strong> Uživatelské jméno, e-mailová adresa,
                  jméno, příjmení a bezpečně zahashované heslo (PBKDF2 / Argon2).
                </li>
                <li>
                  <strong>Autentizační a technická data:</strong> JWT přístupové a obnovovací tokeny
                  (uložené v zabezpečených httpOnly cookies), IP adresa, otisk uživatelského agenta (User-Agent)
                  a časová razítka přihlášení.
                </li>
                <li>
                  <strong>Projektová data a komunikace:</strong> Název projektu, popisy úkolů v Kanban
                  nástěnce, nahrané soubory a zprávy odeslané prostřednictvím reálného WebSocket chatu.
                </li>
                <li>
                  <strong>AI Studio vstupy a výstupy:</strong> Prompty a parametry zadané do AI asistenta
                  pro generování odpovědí či kódu.
                </li>
              </ul>
            </section>

            {/* 3. Účely a právní základ */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                3. Účely a právní základ zpracování
              </h2>
              <p>Osobní údaje zpracováváme na základě následujících právních titulů podle čl. 6 GDPR:</p>
              <div className="grid gap-3 sm:grid-cols-2 mt-2">
                <div className="rounded-xl border border-border bg-card p-4">
                  <span className="font-semibold text-foreground text-xs block mb-1">
                    Plnění smlouvy (čl. 6 odst. 1 písm. b GDPR)
                  </span>
                  <p className="text-xs">
                    Vytvoření uživatelského účtu, správa hackathon týmu, ukládání rozpracovaných projektů
                    a umožnění spolupráce v reálném čase.
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card p-4">
                  <span className="font-semibold text-foreground text-xs block mb-1">
                    Oprávněný zájem (čl. 6 odst. 1 písm. f GDPR)
                  </span>
                  <p className="text-xs">
                    Zajištění bezpečnosti sítě, ochrana před zneužitím API, detekce DoS útoků a prevence
                    neoprávněného přístupu k datům.
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card p-4">
                  <span className="font-semibold text-foreground text-xs block mb-1">
                    Udělený souhlas (čl. 6 odst. 1 písm. a GDPR)
                  </span>
                  <p className="text-xs">
                    Využití nepovinných analytických cookies k měření rychlosti odezvy a optimalizaci
                    uživatelského rozhraní.
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card p-4">
                  <span className="font-semibold text-foreground text-xs block mb-1">
                    Plnění právních povinností (čl. 6 odst. 1 písm. c GDPR)
                  </span>
                  <p className="text-xs">
                    Vedení bezpečnostních systémových auditních záznamů podle platné legislativy.
                  </p>
                </div>
              </div>
            </section>

            {/* 4. AI a třetí strany */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary" />
                4. Zapojení AI modelů a subdodavatelů
              </h2>
              <p>
                V rámci modulu <strong>AI Studio</strong> může aplikace komunikovat s externími poskytovateli
                velkých jazykových modelů (např. Google Gemini, OpenAI nebo Anthropic), popřípadě lokálně
                běžící instancí Ollama.
              </p>
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-semibold mb-1">
                  <AlertCircle className="h-4 w-4" /> Upozornění pro vkládání citlivých údajů do AI
                </div>
                Do zadání pro AI asistenta nikdy nevkládejte hesla, reálné platební údaje, rodná čísla ani
                jiná citlivá osobní data. Poskytovatelé AI modelů mohou data zpracovávat v souladu se svými
                vlastními licenčními podmínkami.
              </div>
            </section>

            {/* 5. Cookies */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Cookie className="h-5 w-5 text-primary" />
                5. Soubory Cookie a lokální úložiště
              </h2>
              <p>
                Při návštěvě našich webových stránek ukládáme do vašeho zařízení malé datové soubory (cookies)
                a hodnoty do lokálního úložiště prohlížeče:
              </p>
              <ul className="list-disc pl-5 space-y-1.5">
                <li>
                  <strong>Technicky nezbytné:</strong> Udržují vaši identitu po přihlášení (JWT cookie),
                  zajišťují ochranu proti CSRF a pamatují si stav vašeho souhlasu s cookies. Tyto cookies nelze
                  vypnout, protože jsou kritické pro bezpečný běh systému.
                </li>
                <li>
                  <strong>Analytické:</strong> Slouží k vyhodnocování výkonnosti a zatížení backendu. Jsou
                  aktivovány pouze na základě vašeho dobrovolného souhlasu.
                </li>
                <li>
                  <strong>Funkční:</strong> Ukládají volbu světlého/tmavého režimu a vaše vývojářské předvolby.
                </li>
              </ul>
              <p className="pt-2">
                Svůj souhlas můžete kdykoliv změnit nebo odvolat kliknutím na odkaz v patičce stránky nebo
                pomocí tlačítka pro otevření předvoleb na této stránce.
              </p>
            </section>

            {/* 6. Doba uchování */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Lock className="h-5 w-5 text-primary" />
                6. Doba uchovávání údajů
              </h2>
              <p>
                Osobní údaje uchováváme pouze po dobu nezbytnou k naplnění účelů uvedených v těchto zásadách:
              </p>
              <ul className="list-disc pl-5 space-y-1.5">
                <li>Účet a projektová data: Po dobu trvání vašeho účtu a hackathonu, nebo do jeho smazání uživatelem.</li>
                <li>Systémové logy a bezpečnostní záznamy: Maximálně 90 dní od jejich vytvoření.</li>
                <li>Soubory cookies: Maximálně 12 měsíců od udělení souhlasu, případně do jejich vymazání z prohlížeče.</li>
              </ul>
            </section>

            {/* 7. Práva uživatele */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-primary" />
                7. Vaše práva podle GDPR
              </h2>
              <p>Jako subjekt údajů máte podle platné evropské legislativy následující práva:</p>
              <div className="grid gap-2 sm:grid-cols-2 mt-2">
                <div className="rounded-lg border border-border bg-card/60 p-3 text-xs">
                  <strong>Právo na přístup:</strong> Můžete požadovat informaci, jaké údaje o vás zpracováváme.
                </div>
                <div className="rounded-lg border border-border bg-card/60 p-3 text-xs">
                  <strong>Právo na opravu:</strong> Můžete kdykoliv aktualizovat nesprávné či neaktuální údaje.
                </div>
                <div className="rounded-lg border border-border bg-card/60 p-3 text-xs">
                  <strong>Právo na výmaz:</strong> Máte právo požádat o trvalé smazání vašeho účtu („být zapomenut“).
                </div>
                <div className="rounded-lg border border-border bg-card/60 p-3 text-xs">
                  <strong>Právo na přenositelnost:</strong> Získat svá data ve strojově čitelném formátu (JSON).
                </div>
              </div>
              <p className="text-xs pt-1">
                Pokud se domníváte, že zpracování vašich údajů porušuje GDPR, máte právo podat stížnost u
                dozorového úřadu (v České republice Úřad pro ochranu osobních údajů –{' '}
                <a
                  href="https://www.uoou.cz"
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-primary hover:underline"
                >
                  www.uoou.cz
                </a>).
              </p>
            </section>
          </div>

          {/* Footer Back action */}
          <div className="mt-12 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link href="/">
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowLeft className="h-4 w-4" /> Zpět na úvodní stránku
              </Button>
            </Link>

            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={openSettings}
                className="gap-2 text-xs"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
                Spravovat cookies
              </Button>
              <Link href="/terms">
                <Button size="sm" className="text-xs">
                  Přejít na Podmínky užití
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-xs text-muted-foreground border-t border-border">
        <div className="mx-auto max-w-7xl px-4">
          <p>© {new Date().getFullYear()} Hackathon OS • Veškerá práva vyhrazena</p>
        </div>
      </footer>
    </div>
  );
}
