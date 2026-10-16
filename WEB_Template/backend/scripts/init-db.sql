-- =============================================================================
-- Hackathon Web Template – PostgreSQL Initialization
-- Tento skript se spustí při prvním startu PostgreSQL kontejneru.
-- =============================================================================

-- Rozšíření pro lepší UUID podporu (volitelné)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Rozšíření pro full-text search (volitelné)
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Rozšíření pro šifrování (volitelné)
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Rozšíření pro vektorové embeddingy (pro pgvector – alternativa k Qdrantu)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Poznámka: Tabulky vytváří Django migrace, ne tento skript.
-- Tento soubor slouží pro DB-level konfiguraci a rozšíření.

SELECT 'Database initialized successfully' AS status;
