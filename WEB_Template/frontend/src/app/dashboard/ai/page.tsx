'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { aiApi, type AiProviderInfo, type AiGenerateResponse } from '@/lib/api';
import {
  Bot,
  Send,
  Copy,
  Check,
  Sparkles,
  Sliders,
  History,
  Terminal,
  Zap,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';

interface HistoryItem {
  prompt: string;
  response: string;
  provider: string;
  tokens: number;
  timestamp: string;
}

export default function AiStudioPage() {
  const [providers, setProviders] = React.useState<AiProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = React.useState('mock');
  const [selectedModel, setSelectedModel] = React.useState('mock-gpt-v1');
  const [temperature, setTemperature] = React.useState(0.7);
  const [systemPrompt, setSystemPrompt] = React.useState(
    'Jsi technický AI architekt pro hackathony. Poskytuj stručné, přesné a produkční odpovědi včetně TypeScript/Python ukázek.'
  );
  const [prompt, setPrompt] = React.useState('');
  const [response, setResponse] = React.useState<AiGenerateResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [error, setError] = React.useState('');
  const [history, setHistory] = React.useState<HistoryItem[]>([]);

  React.useEffect(() => {
    aiApi.getProviders()
      .then((res) => {
        setProviders(res.providers);
        const first = res.providers[0];
        if (first) {
          setSelectedProvider(first.id);
          setSelectedModel(first.default_model);
        }
      })
      .catch(() => {
        // Fallback
        setProviders([
          {
            id: 'mock',
            name: 'Hackathon Mock (Zero-Config)',
            is_configured: true,
            default_model: 'mock-gpt-v1',
            models: ['mock-gpt-v1', 'mock-fast-v1'],
            description: 'Simulátor bez nutnosti zadávat klíče.',
          },
        ]);
      });
  }, []);

  const handleProviderChange = (provId: string) => {
    setSelectedProvider(provId);
    const prov = providers.find((p) => p.id === provId);
    if (prov) {
      setSelectedModel(prov.default_model);
    }
  };

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!prompt.trim()) return;

    setError('');
    setLoading(true);

    try {
      const res = await aiApi.generate({
        prompt: prompt.trim(),
        system_prompt: systemPrompt.trim(),
        provider: selectedProvider,
        model: selectedModel,
        temperature,
      });

      setResponse(res);
      setHistory((prev) => [
        {
          prompt: prompt.trim(),
          response: res.response,
          provider: res.provider,
          tokens: res.tokens_used,
          timestamp: new Date().toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' }),
        },
        ...prev.slice(0, 9),
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Chyba při volání AI providera.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!response?.response) return;
    navigator.clipboard.writeText(response.response);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const samplePrompts = [
    { label: '⚡ TS Stream funkce', text: 'Napiš TypeScript async generátor pro čtení chunků z audio streamu.' },
    { label: '📊 Hackathon Pitch', text: 'Vytvoř 1-minutový přesvědčivý pitch pro porotu pro náš projekt.' },
    { label: '🔒 JWT Validace', text: 'Jak ověřit JWT token v Django Channels WebSocket scope middleware?' },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                AI Studio Playground
              </h1>
              <Badge variant={selectedProvider === 'mock' ? 'info' : 'success'}>
                {selectedProvider === 'mock' ? 'Mock Simulator' : 'Live API'}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Jednotné rozhraní pro Google Gemini, OpenAI, Claude, Ollama a offline simulační mód.
            </p>
          </div>
        </div>

        {/* Studio Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column (2 cols): Prompt & Output */}
          <div className="lg:col-span-2 space-y-6">
            {/* Prompt Card */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" /> Prompt &amp; Vstup
                  </CardTitle>

                  {/* Sample prompt pills */}
                  <div className="hidden sm:flex items-center gap-1.5">
                    {samplePrompts.map((s) => (
                      <button
                        key={s.label}
                        type="button"
                        onClick={() => setPrompt(s.text)}
                        className="rounded-lg border border-border/80 bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground hover:text-foreground transition"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  rows={4}
                  placeholder="Zadej prompt nebo zadání pro AI model... (např. Napiš React komponentu pro vizualizaci audia)"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="font-sans text-sm"
                />

                {error && (
                  <div className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-muted-foreground font-mono">
                    Provider: <strong className="text-foreground uppercase">{selectedProvider}</strong> ({selectedModel})
                  </span>
                  <Button
                    type="button"
                    onClick={() => handleGenerate()}
                    isLoading={loading}
                    disabled={!prompt.trim()}
                    className="gap-2"
                  >
                    <Send className="h-4 w-4" /> Spustit generování
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Output Card */}
            <Card className="border-border shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/60">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-emerald-500" /> Výstup modelu
                  </CardTitle>
                  {response && (
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {response.tokens_used} tokenů
                    </Badge>
                  )}
                </div>

                {response && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={copyToClipboard}
                    className="h-8 gap-1 text-xs"
                  >
                    {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                    {copied ? 'Zkopírováno' : 'Kopírovat'}
                  </Button>
                )}
              </CardHeader>

              <CardContent className="p-4 sm:p-6 min-h-[220px]">
                {loading ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent mb-3" />
                    <span className="text-xs font-mono">Volám model {selectedModel}...</span>
                  </div>
                ) : response ? (
                  <div className="prose dark:prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap font-mono bg-muted/20 p-4 rounded-xl border border-border/60">
                    {response.response}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
                    <Bot className="h-10 w-10 text-muted-foreground/40 mb-2" />
                    <p className="text-xs">Zadejte prompt a klikněte na &quot;Spustit generování&quot;.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column (1 col): Configuration & Settings */}
          <div className="space-y-6">
            {/* Configuration Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-primary" /> Nastavení modelu
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                {/* Provider Selector */}
                <div>
                  <label className="block font-semibold text-foreground mb-1.5">AI Provider</label>
                  <div className="space-y-1.5">
                    {providers.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleProviderChange(p.id)}
                        className={`flex w-full items-center justify-between rounded-xl border p-2.5 text-left transition ${
                          selectedProvider === p.id
                            ? 'border-primary bg-primary/10 text-primary font-semibold'
                            : 'border-border bg-card text-foreground hover:bg-muted/40'
                        }`}
                      >
                        <span className="truncate">{p.name}</span>
                        {p.is_configured ? (
                          <span className="text-[10px] text-emerald-500 font-mono">Připraveno</span>
                        ) : (
                          <span className="text-[10px] text-muted-foreground font-mono">Vyžaduje klíč</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Model Selector */}
                <div>
                  <label className="block font-semibold text-foreground mb-1.5">Model</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full rounded-lg border border-border bg-card p-2 text-xs font-mono text-foreground focus:outline-none"
                  >
                    {providers
                      .find((p) => p.id === selectedProvider)
                      ?.models.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                  </select>
                </div>

                {/* Temperature slider */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="font-semibold text-foreground">Temperature (kreativita)</label>
                    <span className="font-mono text-muted-foreground">{temperature}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    className="w-full accent-primary"
                  />
                  <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
                    <span>Přesný (0.0)</span>
                    <span>Kreativní (1.0)</span>
                  </div>
                </div>

                {/* System prompt */}
                <div>
                  <label className="block font-semibold text-foreground mb-1">Systémový kontext</label>
                  <Textarea
                    rows={3}
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    className="text-xs"
                    placeholder="Instrukce pro chování modelu..."
                  />
                </div>
              </CardContent>
            </Card>

            {/* Prompt History */}
            {history.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <History className="h-4 w-4 text-muted-foreground" /> Historie dotazů
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {history.map((h, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        setPrompt(h.prompt);
                        setResponse({
                          response: h.response,
                          provider: h.provider,
                          model: selectedModel,
                          tokens_used: h.tokens,
                          status: 'success',
                        });
                      }}
                      className="flex w-full flex-col rounded-lg border border-border/60 bg-muted/20 p-2 text-left hover:bg-muted/40 transition"
                    >
                      <span className="text-xs font-medium text-foreground truncate">{h.prompt}</span>
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground mt-1">
                        <span className="uppercase">{h.provider}</span>
                        <span>{h.timestamp}</span>
                      </div>
                    </button>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
