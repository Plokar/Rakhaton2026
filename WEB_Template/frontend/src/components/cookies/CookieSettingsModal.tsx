'use client';

import * as React from 'react';
import { useCookieConsent } from '@/contexts/CookieContext';
import { KNOWN_COOKIES } from '@/types/cookies';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ShieldCheck, BarChart3, Sparkles, ChevronDown, ChevronUp, Lock } from 'lucide-react';

export function CookieSettingsModal() {
  const {
    isSettingsOpen,
    closeSettings,
    preferences,
    savePreferences,
    acceptAll,
    acceptNecessaryOnly,
  } = useCookieConsent();

  const [analytics, setAnalytics] = React.useState(preferences.analytics);
  const [marketing, setMarketing] = React.useState(preferences.marketing);
  const [showCookieList, setShowCookieList] = React.useState(false);

  // Synchronizace stavu při otevření
  React.useEffect(() => {
    if (isSettingsOpen) {
      setAnalytics(preferences.analytics);
      setMarketing(preferences.marketing);
    }
  }, [isSettingsOpen, preferences]);

  const handleSave = () => {
    savePreferences({
      necessary: true,
      analytics,
      marketing,
    });
  };

  return (
    <Dialog open={isSettingsOpen} onOpenChange={(open) => !open && closeSettings()}>
      <div className="max-h-[85vh] overflow-y-auto pr-1">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <DialogTitle>Nastavení předvoleb souborů cookie</DialogTitle>
          </div>
          <DialogDescription>
            Tato aplikace využívá soubory cookie a lokální úložiště k zajištění bezpečného přihlášení,
            funkčnosti API a volitelně k analýze návštěvnosti. Zde můžete své preference detailně upravit.
          </DialogDescription>
        </DialogHeader>

        {/* Categories */}
        <div className="space-y-4 my-4">
          {/* Necessary Cookies */}
          <div className="rounded-xl border border-border bg-muted/40 p-4 transition">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-background border border-border text-foreground">
                  <Lock className="h-3.5 w-3.5 text-primary" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground">
                      Technicky nezbytné cookies
                    </span>
                    <Badge variant="default" className="text-[10px] py-0 px-2">
                      Vždy aktivní
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    Nezbytné pro základní chod Hackathon OS, udržení přihlašovací relace (JWT),
                    zabezpečení proti CSRF útokům a správu uživatelských práv. Bez těchto údajů web nemůže bezpečně fungovat.
                  </p>
                </div>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={true}
                  disabled
                  className="h-4 w-4 rounded border-gray-400 text-primary cursor-not-allowed opacity-70"
                />
              </div>
            </div>
          </div>

          {/* Analytics Cookies */}
          <div className="rounded-xl border border-border bg-card p-4 transition hover:border-primary/40">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-muted text-foreground">
                  <BarChart3 className="h-3.5 w-3.5 text-cyan-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground">
                      Analytické &amp; Výkonnostní cookies
                    </span>
                    <Badge variant="outline" className="text-[10px] py-0 px-2">
                      Volitelné
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    Pomáhají nám pochopit, jak uživatelé interagují s jednotlivými funkcemi,
                    měří dobu odezvy WebSocketů a API a umožňují identifikovat chyby v aplikaci.
                    Všechna data jsou sbírána anonymizovaně.
                  </p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer mt-1">
                <input
                  type="checkbox"
                  checked={analytics}
                  onChange={(e) => setAnalytics(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-muted peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>
          </div>

          {/* Marketing & Functional */}
          <div className="rounded-xl border border-border bg-card p-4 transition hover:border-primary/40">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-muted text-foreground">
                  <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground">
                      Funkční &amp; AI Studio preference
                    </span>
                    <Badge variant="outline" className="text-[10px] py-0 px-2">
                      Volitelné
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    Uchovávají vaše osobní přizpůsobení, jako je vybrané barevné schéma,
                    poslední nastavení AI providera (Gemini / OpenAI / Claude) a stav rozbalených panelů.
                  </p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer mt-1">
                <input
                  type="checkbox"
                  checked={marketing}
                  onChange={(e) => setMarketing(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-muted peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>
          </div>
        </div>

        {/* Collapsible cookie list */}
        <div className="my-4 border-t border-border pt-3">
          <button
            type="button"
            onClick={() => setShowCookieList(!showCookieList)}
            className="flex w-full items-center justify-between text-xs font-medium text-muted-foreground hover:text-foreground transition py-1"
          >
            <span>Přehled konkrétních cookies v aplikaci ({KNOWN_COOKIES.length})</span>
            {showCookieList ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>

          {showCookieList && (
            <div className="mt-3 space-y-2 max-h-60 overflow-y-auto pr-1">
              {KNOWN_COOKIES.map((cookie) => (
                <div
                  key={cookie.name}
                  className="rounded-lg border border-border/70 bg-muted/20 p-2.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-mono font-semibold text-primary">{cookie.name}</span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {cookie.duration}
                    </span>
                  </div>
                  <p className="text-muted-foreground text-[11px] leading-relaxed">
                    {cookie.description}
                  </p>
                  <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground/80">
                    <span>Poskytovatel: <strong>{cookie.provider}</strong></span>
                    <span>•</span>
                    <span className="capitalize">Kategorie: {cookie.category}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2 pt-2 border-t border-border">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={acceptNecessaryOnly}
          >
            Pouze nezbytné
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleSave}
          >
            Uložit vybrané
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={acceptAll}
          >
            Přijmout vše
          </Button>
        </DialogFooter>
      </div>
    </Dialog>
  );
}
