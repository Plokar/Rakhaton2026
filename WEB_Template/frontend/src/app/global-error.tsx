'use client';

/**
 * Chyba v kořenovém layoutu (T-374): nahrazuje celý dokument, proto vlastní <html> a styly přímo tady
 * (globální CSS ani motiv sem nedosáhnou). Barvy podle systému.
 */
export default function GlobalError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <html lang="cs">
      <body style={{ margin: 0, fontFamily: 'system-ui, sans-serif', colorScheme: 'light dark' }}>
        <title>Něco se pokazilo | MDTcore</title>
        <main role="alert" style={{ minHeight: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
          <div style={{ maxWidth: 420, textAlign: 'center' }}>
            <h1 style={{ fontSize: 20, fontWeight: 600 }}>Něco se pokazilo</h1>
            <p style={{ fontSize: 14, opacity: 0.75, lineHeight: 1.5 }}>
              Aplikaci se nepodařilo zobrazit. Uložená data se nezměnila. Zkuste to znovu.
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 20 }}>
              <button type="button" onClick={() => retry()}
                style={{ padding: '8px 16px', borderRadius: 8, border: 0, background: '#0f766e', color: '#fff', fontSize: 14, cursor: 'pointer' }}>
                Zkusit znovu
              </button>
              <a href="/dashboard" style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid currentColor', fontSize: 14, color: 'inherit', textDecoration: 'none' }}>
                Zpět na přehled
              </a>
            </div>
            {error.digest && <p style={{ marginTop: 16, fontSize: 12, opacity: 0.6 }}>Kód chyby pro hlášení: {error.digest}</p>}
          </div>
        </main>
      </body>
    </html>
  );
}
