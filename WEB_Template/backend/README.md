# Backend - Modulární monolit

Struktura backendu je navržena jako **modulární monolit** pro snadnou škálovatelnost a údržbu.

## Struktura

```
backend/
├── config/              # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                # Doménové moduly (bounded contexts)
│   └── items/          # Příklad modulu
│       ├── models.py   # Doménové modely
│       ├── views.py    # HTTP vrstva (thin controllers)
│       ├── urls.py     # Routing
│       └── admin.py    # Admin interface
├── services/            # Business logika (servisní vrstva)
│   └── items_service.py
├── core/                # Sdílený kód
│   ├── models.py       # Base modely (TimeStampedModel atd.)
│   ├── exceptions.py   # Vlastní výjimky
│   └── utils.py        # Utility funkce
├── manage.py
├── requirements.txt
└── Dockerfile
```

## Principy

### 1. **Oddělení vrstev**
- **Views (Controllers)**: Tenká vrstva, pouze HTTP request/response
- **Services**: Business logika, orchestrace
- **Models**: Doménové modely, databázová vrstva

### 2. **Moduly (Apps)**
Každý modul v `apps/` reprezentuje bounded context:
- Má vlastní models, views, urls
- Komunikuje s ostatními moduly přes services
- Může být v budoucnu extrahován do microservice

### 3. **Core**
Sdílené utility a base třídy použitelné napříč moduly.

### 4. **Services**
Business logika oddělená od HTTP vrstvy:
- Znovupoužitelná
- Testovatelná
- Může být volána z views, CLI, Celery tasků atd.

## Přidání nového modulu

```bash
cd backend/apps
mkdir users
touch users/__init__.py users/models.py users/views.py users/urls.py users/apps.py
```

Pak přidat do `INSTALLED_APPS` v `config/settings.py`.
