'use client';

import * as React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import {
  FileCheck2,
  ArrowLeft,
  Shield,
  Code2,
  AlertTriangle,
  Scale,
  Ban,
  Terminal,
  CheckCircle2,
} from 'lucide-react';

export default function TermsOfUsePage() {
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
            <Link href="/privacy">
              <Button variant="ghost" size="sm" className="text-xs">
                Zásady soukromí
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

      {/* Main Content */}
      <main className="flex-1 py-12 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          {/* Header */}
          <div className="mb-10 text-center sm:text-left border-b border-border pb-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary mb-4">
              <FileCheck2 className="h-3.5 w-3.5" /> Podmínky služby &amp; Pravidla
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-foreground">
              Podmínky užití služby
            </h1>
            <p className="mt-3 text-base text-muted-foreground leading-relaxed">
              Tento dokument upravuje pravidla a podmínky používání webové platformy, API rozhraní
              a doplňkových nástrojů Hackathon OS.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
              <span>Poslední aktualizace: <strong>11. září 2026</strong></span>
              <span>•</span>
              <span>Verze: <strong>2.0</strong></span>
              <span>•</span>
              <span>Licence kódu: <strong>MIT Licence</strong></span>
            </div>
          </div>

          {/* Terms Content */}
          <div className="space-y-10 text-sm leading-relaxed text-muted-foreground">
            {/* 1. Úvod */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Scale className="h-5 w-5 text-primary" />
                1. Úvodní ustanovení a přijetí podmínek
              </h2>
              <p>
                Používáním platformy Hackathon OS (webové aplikace, REST API, WebSocket rozhraní nebo
                AI integračních nástrojů) vyjadřujete svůj úplný a bezvýhradný souhlas s těmito Podmínkami užití.
              </p>
              <p>
                Pokud s těmito podmínkami nesouhlasíte, jste povinni se zdržet registrace a používání jakýchkoli
                součástí této platformy.
              </p>
            </section>

            {/* 2. Uživatelské účty */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                2. Uživatelský účet a bezpečnost
              </h2>
              <p>
                Při registraci jste povinni uvádět pravdivé a úplné informace. Každý uživatel nese plnou
                odpovědnost za:
              </p>
              <ul className="list-disc pl-5 space-y-1.5">
                <li>Uchování svých přihlašovacích údajů a hesel v tajnosti.</li>
                <li>Veškeré operace a síťové požadavky provedené pod svým uživatelským účtem či API tokenem.</li>
                <li>Okamžité nahlášení jakéhokoli podezření na zneužití přístupu administrátorům platformy.</li>
              </ul>
            </section>

            {/* 3. Pravidla přijatelného užití */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Ban className="h-5 w-5 text-rose-500" />
                3. Pravidla přijatelného užití (AUP)
              </h2>
              <p>
                Při používání aplikace, API a napojených AI služeb je přísně zakázáno:
              </p>
              <div className="rounded-xl border border-border bg-card p-4 space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-rose-500 font-bold">•</span>
                  <span>
                    Využívat AI Studio nebo API ke generování škodlivého kódu, malwaru, phishingu,
                    nenávistného obsahu či materiálů porušujících zákony České republiky nebo EU.
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-rose-500 font-bold">•</span>
                  <span>
                    Provádět záměrné zatěžovací útoky (DoS/DDoS), přetěžovat společné API limity či provádět
                    neoprávněné penetrační testování bez předchozího písemného souhlasu organizátorů.
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-rose-500 font-bold">•</span>
                  <span>
                    Pokoušet se o obcházení autentizačních mechanismů, manipulaci s cizími JWT tokeny
                    nebo přístup k projektům jiných soutěžních týmů bez oprávnění.
                  </span>
                </div>
              </div>
            </section>

            {/* 4. Duševní vlastnictví */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Code2 className="h-5 w-5 text-primary" />
                4. Duševní vlastnictví a autorská práva k projektům
              </h2>
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 text-muted-foreground">
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold mb-2">
                  <CheckCircle2 className="h-5 w-5" /> Vlastnictví vašeho hackathon kódu
                </div>
                <p className="text-xs leading-relaxed">
                  <strong>Veškerý kód, nápady, design a datové modely, které v rámci Hackathon OS vytvoříte,
                  zůstávají 100% vaším výhradním duševním vlastnictvím.</strong> Provozovatel platformy si
                  nenárokuje žádná majetková ani autorská práva k vašim hackathon projektům.
                </p>
              </div>
              <p className="pt-2 text-xs">
                Samotný základní boilerplate kód Hackathon OS je distribuován pod svobodnou licencí <strong>MIT License</strong>,
                což vám dává plnou svobodu jej upravovat, rozšiřovat a využívat i pro komerční účely.
              </p>
            </section>

            {/* 5. Vyloučení záruk */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                5. Vyloučení záruk a dostupnost („AS IS“)
              </h2>
              <p>
                Platforma Hackathon OS je poskytována <strong>„tak jak je“ (AS IS)</strong> a <strong>„jak je dostupná“ (AS AVAILABLE)</strong>,
                bez jakýchkoli výslovných nebo předpokládaných záruk.
              </p>
              <p>
                Vzhledem k charakteru prototypování a hackathonového vývoje provozovatel negarantuje:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li>Nepřetržitou dostupnost serverů, databáze či WebSocket konektorů bez výpadků.</li>
                <li>Bezchybnost odpovědí generovaných externími AI modely (Gemini, OpenAI, Claude).</li>
                <li>Dostupnost externích API kvót poskytovaných třetími stranami.</li>
              </ul>
            </section>

            {/* 6. Omezení odpovědnosti */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Terminal className="h-5 w-5 text-primary" />
                6. Omezení odpovědnosti
              </h2>
              <p>
                V maximálním rozsahu povoleném platnými právními předpisy nenese provozovatel žádnou odpovědnost
                za nepřímé, náhodné nebo následné škody, ztrátu dat, zisků ani za újmu vzniklou v souvislosti
                s používáním nebo nemožností používat tuto platformu.
              </p>
            </section>

            {/* 7. Ukončení a rozhodné právo */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                <Scale className="h-5 w-5 text-primary" />
                7. Rozhodné právo a řešení sporů
              </h2>
              <p>
                Tyto Podmínky užití a veškeré právní vztahy z nich vyplývající se řídí právním řádem
                <strong> České republiky</strong>. Případné spory budou přednostně řešeny smírnou cestou
                či věcně a místně příslušnými soudy v ČR.
              </p>
            </section>
          </div>

          {/* Bottom links */}
          <div className="mt-12 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link href="/">
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowLeft className="h-4 w-4" /> Zpět na úvodní stránku
              </Button>
            </Link>

            <div className="flex items-center gap-3">
              <Link href="/privacy">
                <Button variant="ghost" size="sm" className="text-xs">
                  Zásady ochrany soukromí
                </Button>
              </Link>
              <Link href="/register">
                <Button size="sm" className="text-xs">
                  Vytvořit účet &amp; Začít
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-xs text-muted-foreground border-t border-border">
        <div className="mx-auto max-w-7xl px-4">
          <p>© {new Date().getFullYear()} Hackathon OS • MIT Licence</p>
        </div>
      </footer>
    </div>
  );
}
