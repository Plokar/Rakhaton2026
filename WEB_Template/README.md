# 🚀 Hackathon OS (Web Template v2.0)

Produkčně připravený **Hackathon Starter / Operační systém** pro rychlé prototypování a vítězné prezentace. Cíl: do 2 minut od `git clone` mít funkční aplikaci s autentizací, UI design systémem, reálnými daty, AI studiem, uploadem souborů a WebSockety.

**Stack:** Django 4.2 (ASGI/Daphne) + Next.js 16 (React 19, TypeScript, Tailwind v4) + JWT Auth (httpOnly cookies) + WebSockets + PostgreSQL 16 + Redis 7 + Traefik v3 + Mailhog

---

## ⚡ Rychlý start

### Windows (PowerShell)
```powershell
# 1. Spustit dev stack (automaticky vytvoří .env, spustí Docker, migrace i seed data)
.\dev.ps1 up

# Nebo přes Make:
make dev
```

### Linux / macOS (Bash)
```bash
# 1. Spustit dev stack
./dev.sh up

# Nebo přes Make:
make dev
```

### 🌐 Přístupové adresy:
- **Frontend App:** [http://localhost:3000](http://localhost:3000)
- **Swagger / OpenAPI UI:** [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **ReDoc Dokumentace:** [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
- **Backend REST API:** [http://localhost:8000/api/](http://localhost:8000/api/)
- **Django Admin:** [http://localhost:8000/admin/](http://localhost:8000/admin/)
- **Mailhog (E-maily lokálně):** [http://localhost:8025](http://localhost:8025)
- **Traefik Dashboard:** [http://localhost:8080](http://localhost:8080)

---

## 👤 Předpřipravené demo účty (Seed Data)

Po spuštění je databáze automaticky naplněna realistickými demo daty (projekty, úkoly, notifikace):

| Uživatel | Heslo | Role | Použití |
|----------|-------|------|---------|
| `admin` | `admin123456` | Administrátor / Team Lead | Plný přístup do appky i Django Adminu |
| `alice` | `demo123456` | AI Lead | Demo člen týmu |
| `bob` | `demo123456` | Fullstack Dev | Demo člen týmu |
| `charlie` | `demo123456` | UI Designer | Demo člen týmu |

*Na přihlašovací stránce `/login` jsou k dispozici tlačítka pro 1-klikové vyplnění těchto účtů.*

---

## 🏗️ Architektura a vrstvy

```
┌─────────────────────────────────────────────────────────────┐
│                       HACKATHON OS                          │
├──────────────────────────────┬──────────────────────────────┤
│ FRONTEND (Next.js 16 + TW4)  │ BACKEND (Django 4.2 + DRF)   │
│ ├─ Design Tokens (Dark/Light)│ ├─ AI Layer Abstraction      │
│ ├─ shadcn UI komponenty      │ ├─ File Storage Abstraction  │
│ ├─ Collapsible Sidebar & Nav │ ├─ Projects, Tasks, Notifs   │
│ ├─ Command Palette (Ctrl+K)  │ ├─ Email Service (Mailhog)   │
│ ├─ Dashboard Přehled         │ ├─ Realistic Seed Data       │
│ ├─ AI Studio Playground      │ ├─ Password Reset Flow       │
│ ├─ Správce souborů           │ └─ Observability / Health    │
│ ├─ WebSocket Live Monitor    │                              │
│ └─ Split-screen Auth         │                              │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 🤖 AI Layer Abstraction

Jednotné rozhraní pro práci s umělou inteligencí. Podporuje:
- **Mock (Simulator - Zero Config):** Funguje ihned i bez zadání API klíče. Ideální pro rychlé prezentace a pitch na hackathonu.
- **Google Gemini:** `gemini-1.5-flash`, `gemini-1.5-pro` (nastav `GEMINI_API_KEY` v `.env`).
- **OpenAI:** `gpt-4o-mini`, `gpt-4o` (nastav `OPENAI_API_KEY` v `.env`).
- **Ollama:** Lokální modely offline na `http://localhost:11434`.

### Endpointy
- `POST /api/ai/generate/` – Generování odpovědi (`{ prompt, system_prompt, provider, model, temperature }`)
- `GET /api/ai/providers/` – Seznam dostupných providerů a stav jejich konfigurace

---

## 📁 Souborové úložiště (Storage Abstraction)

- Lokální diskové úložiště v dev prostředí (`media/uploads/`).
- Připraveno pro MinIO / AWS S3 v produkci.
- Endpointy:
  - `POST /api/upload/` – Nahrání souboru (až 25 MB)
  - `GET /api/upload/` – Seznam souborů
  - `DELETE /api/upload/<id>/` – Smazání souboru i fyzicky z disku

---

## ⚡ WebSockets (Django Channels)

- WebSocket URL: `ws://localhost:8000/ws/echo/` (Echo test)
- WebSocket URL: `ws://localhost:8000/ws/room/<room_name>/` (Skupinový broadcast, chat, stav)
- Autentizace: Automaticky přes JWT httpOnly cookie nebo `?token=<jwt>` query parametr.

---

## 🛠️ Užitečné příkazy (Dev Automation)

| Příkaz (Make) | Příkaz (PowerShell) | Popis |
|---------------|---------------------|-------|
| `make dev` | `.\dev.ps1 up` | Spustí celý stack s hot-reloadem |
| `make down` | `.\dev.ps1 down` | Zastaví kontejnery |
| `make seed` | `.\dev.ps1 seed` | Znovu naplní databázi ukázkovými daty |
| `make reset` | `.\dev.ps1 reset` | Reset DB volume + nové migrace + seed |
| `make logs` | `.\dev.ps1 logs` | Živý výpis logů |
| `make test` | `.\dev.ps1 test` | Spustí testy v backendu |
