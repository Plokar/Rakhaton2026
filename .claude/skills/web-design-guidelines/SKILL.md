---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

> **V MDT Copilot (čti první, má přednost před textem skillu níže):**
>
> - UI je česky ve `WEB_Template/frontend/src` (`app/`, `components/mdt/`, `components/ui/`). Nálezy piš česky, ve formátu `soubor:řádek` podle stažených pravidel.
> - Kontroluj navíc požadavky projektu: použitelnost od 360 px bez vodorovného posouvání (FR-U2, D-017), čitelnost na projektoru (kontrast, velikost písma, T-310), tmavý režim (třída `.dark`), odlišený AI text a citace u tvrzení (`AGENTS.md`). Tři barevné systémy semafor / odbornost / AI jsou záměr (D-017), nehlas je jako nekonzistenci.
> - Pravidla se při každém auditu stahují z GitHubu (viz níže). Když stažení selže, řekni to a pravidla nedomýšlej.
>
> Převzato z [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines) (commit `063bee9`, MIT, viz `../LICENSE-vercel-agent-skills`). Text skillu níže je beze změny.

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.
