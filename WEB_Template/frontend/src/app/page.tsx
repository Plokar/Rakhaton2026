'use client';

import * as React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { useCookieConsent } from '@/contexts/CookieContext';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Zap,
  Copy,
  Check,
  ArrowRight,
  ShieldCheck,
  Radio,
  Bot,
  Database,
  Layers,
  Terminal,
  ExternalLink,
  Cpu,
  Mail,
  HardDrive,
} from 'lucide-react';

export default function HomePage() {
  const { user } = useAuth();
  const { openSettings } = useCookieConsent();
  const [copied, setCopied] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState<'dashboard' | 'ai' | 'ws' | 'infra'>('dashboard');

  const copyCommand = () => {
    navigator.clipboard.writeText('git clone https://github.com/your-repo/hackathon-template.git && docker compose -f docker-compose.dev.yml up');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-indigo-500/30">
              <Zap className="h-5 w-5 fill-current" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight">Hackathon OS</span>
              <span className="text-[10px] font-mono text-muted-foreground">v2.0 Starter</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition">Vlastnosti</a>
            <a href="#architecture" className="hover:text-foreground transition">Architektura</a>
            <a href="#quickstart" className="hover:text-foreground transition">Rychlý start</a>
            <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-foreground transition flex items-center gap-1">
              GitHub <ExternalLink className="h-3 w-3 opacity-60" />
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            {user ? (
              <Link href="/dashboard">
                <Button size="sm" className="gap-1.5">
                  Dashboard <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            ) : (
              <>
                <Link href="/login" className="hidden sm:inline-block">
                  <Button variant="ghost" size="sm">
                    Přihlásit se
                  </Button>
                </Link>
                <Link href="/register">
                  <Button size="sm" className="gap-1.5">
                    Začít hackovat <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-16 md:pt-28 md:pb-24 border-b border-border">
        {/* Subtle grid background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-30 pointer-events-none" />

        <div className="relative mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1 text-xs font-semibold text-primary mb-6 animate-in fade-in slide-in-from-top-4 duration-500">
            <span className="h-2 w-2 rounded-full bg-primary animate-ping" />
            Hackathon Boilerplate &amp; Design System
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl lg:text-7xl">
            Od nápadu k produktu <br />
            <span className="bg-gradient-to-r from-primary via-indigo-500 to-cyan-400 bg-clip-text text-transparent">
              za méně než 10 minut
            </span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            Neprogramuj infrastrukturu během hackathonu. Získej připravenou Django + Next.js šablonu
            s JWT v httpOnly cookies, WebSockety, AI Studio abstrakcí, reálnými seed daty a Traefik reverzní proxy.
          </p>

          {/* Quickstart 1-click copy box */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 max-w-2xl mx-auto">
            <div className="flex w-full items-center justify-between rounded-xl border border-border bg-card/80 px-4 py-3 font-mono text-xs text-foreground shadow-sm backdrop-blur">
              <div className="flex items-center gap-2 overflow-hidden truncate">
                <Terminal className="h-4 w-4 text-primary shrink-0" />
                <span className="truncate text-muted-foreground">$ git clone ... &amp;&amp; docker compose up</span>
              </div>
              <button
                type="button"
                onClick={copyCommand}
                className="ml-3 inline-flex items-center gap-1.5 rounded-lg bg-secondary px-2.5 py-1 text-xs font-medium hover:bg-accent transition shrink-0"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? 'Zkopírováno' : 'Kopírovat'}
              </button>
            </div>
            <Link href="/login" className="w-full sm:w-auto">
              <Button size="lg" className="w-full sm:w-auto gap-2">
                Otevřít Demo <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>

          {/* Demo account hint */}
          <p className="mt-3 text-xs text-muted-foreground">
            Předpřipravený účet: <code className="font-mono text-foreground font-semibold">admin / admin123456</code> (1-klik vyplnění na login stránce)
          </p>
        </div>

        {/* Interactive App Preview Showcase */}
        <div className="mt-16 mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-2xl border border-border bg-card shadow-2xl overflow-hidden">
            {/* Mock browser header */}
            <div className="flex items-center justify-between border-b border-border bg-muted/40 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-rose-500/80" />
                <span className="h-3 w-3 rounded-full bg-amber-500/80" />
                <span className="h-3 w-3 rounded-full bg-emerald-500/80" />
                <span className="ml-2 text-xs font-mono text-muted-foreground">http://localhost:3000/dashboard</span>
              </div>
              <div className="flex items-center gap-1">
                {(['dashboard', 'ai', 'ws', 'infra'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`rounded-lg px-2.5 py-1 text-xs font-medium capitalize transition ${
                      activeTab === tab ? 'bg-card text-foreground shadow-sm font-semibold' : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {tab === 'ws' ? 'WebSockets' : tab}
                  </button>
                ))}
              </div>
            </div>

            {/* Mock preview content */}
            <div className="p-6 bg-background/50 min-h-[340px]">
              {activeTab === 'dashboard' && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="rounded-xl border border-border bg-card p-4">
                      <p className="text-xs text-muted-foreground uppercase font-semibold">Aktivní projekty</p>
                      <p className="text-2xl font-bold mt-1">4</p>
                      <span className="text-[10px] text-emerald-500 font-semibold">+2 tento týden</span>
                    </div>
                    <div className="rounded-xl border border-border bg-card p-4">
                      <p className="text-xs text-muted-foreground uppercase font-semibold">Otevřené úkoly</p>
                      <p className="text-2xl font-bold mt-1">11</p>
                      <span className="text-[10px] text-primary font-semibold">4 v řešení</span>
                    </div>
                    <div className="rounded-xl border border-border bg-card p-4">
                      <p className="text-xs text-muted-foreground uppercase font-semibold">Dokončeno</p>
                      <p className="text-2xl font-bold mt-1">68%</p>
                      <span className="text-[10px] text-emerald-500 font-semibold">Nad průměrem</span>
                    </div>
                    <div className="rounded-xl border border-border bg-card p-4">
                      <p className="text-xs text-muted-foreground uppercase font-semibold">AI Latence</p>
                      <p className="text-2xl font-bold mt-1">142 ms</p>
                      <span className="text-[10px] text-cyan-500 font-semibold">Flash 2.0</span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-border bg-card p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold">Živé projekty týmu</h4>
                      <Badge variant="success">Seed Data Active</Badge>
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center justify-between p-2 rounded-lg bg-muted/40">
                        <span className="font-semibold text-foreground">VoiceAgent Copilot</span>
                        <span className="text-muted-foreground">70% dokončeno • Alice Smith</span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-muted/40">
                        <span className="font-semibold text-foreground">FinTech Fraud Sentinel</span>
                        <span className="text-muted-foreground">45% dokončeno • Bob Jenkins</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'ai' && (
                <div className="space-y-4 animate-in fade-in duration-200">
                  <div className="flex items-center gap-3">
                    <Badge variant="info">Provider: Gemini / Mock</Badge>
                    <Badge variant="outline">Model: gemini-1.5-flash</Badge>
                    <Badge variant="outline">Zero-Config Mode</Badge>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-4 font-mono text-xs text-muted-foreground">
                    <p className="text-primary font-semibold">$ ai.generate(&#123; prompt: &quot;Napiš real-time speech WebSocket handler&quot; &#125;)</p>
                    <p className="mt-2 text-foreground">
                      &gt; Připojuji obousměrný stream na Django Channels ASGI consumer... Hotovo (0.18s)
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Funguje ihned i bez zadání API klíčů díky inteligentnímu simulačnímu režimu.
                  </p>
                </div>
              )}

              {activeTab === 'ws' && (
                <div className="space-y-3 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-emerald-500 flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                      WebSocket Echo &amp; Rooms připraveny na ws://localhost:8000/ws/
                    </span>
                    <Badge variant="secondary">Auto-reconnect</Badge>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-4 font-mono text-xs space-y-1.5 h-44 overflow-y-auto">
                    <p className="text-muted-foreground">[10:42:01] <span className="text-emerald-400">CONNECT</span> ws://localhost:8000/ws/room/hackathon/</p>
                    <p className="text-muted-foreground">[10:42:02] <span className="text-sky-400">JOIN</span> Uživatel &apos;alice&apos; se připojil/a</p>
                    <p className="text-muted-foreground">[10:42:05] <span className="text-primary">MSG</span> &apos;bob&apos;: Zvuková pipeline je připravena k testu!</p>
                  </div>
                </div>
              )}

              {activeTab === 'infra' && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 animate-in fade-in duration-200">
                  {[
                    { name: 'Traefik v3', desc: 'Reverzní proxy, automatický routing', port: ':8080' },
                    { name: 'Django 4.2 ASGI', desc: 'Daphne server, REST + WebSockets', port: ':8000' },
                    { name: 'Next.js 16', desc: 'React 19, Turbopack hot-reload', port: ':3000' },
                    { name: 'PostgreSQL 16', desc: 'Auto migrace + connection pool', port: ':5432' },
                    { name: 'Redis 7', desc: 'Cache, WebSocket channel layer', port: ':6379' },
                    { name: 'Mailhog', desc: 'Lokální e-mailová schránka', port: ':8025' },
                    { name: 'Swagger / OpenAPI', desc: 'Interaktivní API dokumentace', port: ':8000/api/docs/' },
                  ].map((s) => (
                    <div key={s.name} className="rounded-xl border border-border bg-card p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-foreground">{s.name}</span>
                        <span className="font-mono text-[10px] text-muted-foreground">{s.port}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-1">{s.desc}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-20 border-b border-border bg-card/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Vše, co potřebuješ na vítězný hackathon
            </h2>
            <p className="mt-4 text-muted-foreground text-base">
              Žádné zbytečné microservices monstrum. Čistý modulární monolit, který nastartuješ jedním příkazem.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                icon: <ShieldCheck className="h-6 w-6 text-primary" />,
                title: 'Stateless JWT v httpOnly Cookies',
                desc: 'Maximální bezpečnost proti XSS. Access token (15 min) + Refresh token (7 dní) s blacklistováním při odhlášení.',
              },
              {
                icon: <Radio className="h-6 w-6 text-emerald-500" />,
                title: 'Real-time WebSockets',
                desc: 'Django Channels s Redis Channel Layer. Podpora pro echo zprávy, skupinové místnosti a auto-reconnect v Reactu.',
              },
              {
                icon: <Bot className="h-6 w-6 text-indigo-500" />,
                title: 'Jednotná AI Provider Abstrakce',
                desc: 'Přepínej mezi Gemini, OpenAI, Claude, Ollamou nebo Zero-Config Mock režimem bez přepisování frontendového kódu.',
              },
              {
                icon: <HardDrive className="h-6 w-6 text-amber-500" />,
                title: 'Správa a Upload Souborů',
                desc: 'Abstrakce pro nahrávání souborů s lokálním diskem i připravenou S3/MinIO kompatibilitou.',
              },
              {
                icon: <Database className="h-6 w-6 text-cyan-500" />,
                title: 'Reálná Seed Data',
                desc: 'Po spuštění nevidíš prázdné tabulky. Databáze obsahuje hotové projekty, úkoly, notifikace a demo uživatele.',
              },
              {
                icon: <Mail className="h-6 w-6 text-rose-500" />,
                title: 'E-mailový Servis s Mailhogem',
                desc: 'Vyzkoušej obnovu zapomenutého hesla a notifikace lokálně na webovém rozhraní portu 8025 bez externího SMTP.',
              },
            ].map((f) => (
              <div
                key={f.title}
                className="rounded-2xl border border-border bg-card p-6 transition-all hover:border-primary/50 hover:shadow-md"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted/60 mb-4">
                  {f.icon}
                </div>
                <h3 className="text-base font-semibold text-foreground mb-2">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Call to action */}
      <section className="py-20 border-b border-border text-center">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Připraven postavit vítězný projekt?
          </h2>
          <p className="mt-4 text-muted-foreground text-base max-w-xl mx-auto">
            Naklonuj repozitář, spusť docker compose a za 2 minuty můžeš prezentovat první funkční mockup.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link href="/register">
              <Button size="lg" className="gap-2">
                Založit účet &amp; Vstoupit <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg">
                Přihlásit se jako Admin
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 text-center text-xs text-muted-foreground border-t border-border">
        <div className="mx-auto max-w-7xl px-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <p>© {new Date().getFullYear()} Hackathon OS v2.0 • MIT Licence • Vytvořeno pro rychlý start hackathon týmů</p>
          <div className="flex items-center gap-4 flex-wrap justify-center">
            <Link href="/privacy" className="hover:text-foreground transition font-medium">
              Zásady soukromí
            </Link>
            <Link href="/terms" className="hover:text-foreground transition font-medium">
              Podmínky užití
            </Link>
            <button
              type="button"
              onClick={openSettings}
              className="hover:text-foreground transition underline-offset-4 hover:underline cursor-pointer"
            >
              Nastavení cookies
            </button>
            <span className="text-border">|</span>
            <a href="http://localhost:8000/api/docs/" target="_blank" rel="noreferrer" className="text-cyan-400 hover:text-cyan-300 transition font-medium">
              Swagger UI (:8000)
            </a>
            <a href="http://localhost:8000/admin/" target="_blank" rel="noreferrer" className="hover:text-foreground transition">
              Django Admin
            </a>
            <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="hover:text-foreground transition">
              Mailhog (:8025)
            </a>
            <a href="http://localhost:8080" target="_blank" rel="noreferrer" className="hover:text-foreground transition">
              Traefik (:8080)
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
