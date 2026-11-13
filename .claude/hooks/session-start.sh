#!/bin/bash
# SessionStart (T-356): graphify na každém zařízení a v každé session (AGENTS.md „Graphify“).
#  1. nástroj `graphify` (uv tool install graphifyy, pozor dvě „y“), jen když chybí
#  2. skill pro Claude Code (`graphify install --platform claude`), jen když chybí
#  3. graf kódu `graphify-out/` obnoví na pozadí (`graphify update .`, jen AST, bez LLM, ~25 s), start neblokuje
# Idempotentní; při chybě session nezastaví, jen vypíše, co doinstalovat ručně.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
export PATH="$HOME/.local/bin:$PATH"

warn() { echo "graphify: $*" >&2; }

if ! command -v graphify >/dev/null 2>&1; then
  if ! command -v uv >/dev/null 2>&1; then
    python3 -m pip install --user --quiet uv >/dev/null 2>&1 || python -m pip install --user --quiet uv >/dev/null 2>&1 \
      || { warn "chybí uv; nainstalujte ho (https://docs.astral.sh/uv/) a pak: uv tool install graphifyy"; exit 0; }
  fi
  uv tool install --quiet graphifyy >/dev/null 2>&1 || { warn "uv tool install graphifyy selhal, spusťte ho ručně"; exit 0; }
  # nové spustitelné soubory uv do PATH session
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"; fi
fi

if [ ! -f "$HOME/.claude/skills/graphify/SKILL.md" ]; then
  graphify install --platform claude >/dev/null 2>&1 || warn "graphify install selhal, spusťte ho ručně"
fi

# graf kódu na pozadí; souběžné session se nepřetahují (zámek), výstup jen do logu
mkdir -p graphify-out
if command -v flock >/dev/null 2>&1; then
  nohup flock -n graphify-out/.update.lock graphify update . > graphify-out/.update.log 2>&1 &
else
  nohup graphify update . > graphify-out/.update.log 2>&1 &
fi
exit 0
