---
name: impeccable
description: "Use when the user wants to design, redesign, shape, critique, audit, polish, simplify, harden, animate, or otherwise improve a frontend interface: websites, landing pages, dashboards, product UI, components, forms, settings, onboarding, empty states, and native iOS or Android screens. Handles UX review, hierarchy, layout, typography, color, motion, UX copy, accessibility, responsive behavior, edge cases, and capturing or documenting design systems (DESIGN.md, tokens). Also for making bland UI bolder, loud UI quieter, or ambitious visual effects. Not for backend-only or non-UI tasks."
version: 4.6.0
user-invocable: true
argument-hint: "[shape · audit|critique · animate|bolder|colorize|delight|layout|overdrive|quieter|typeset · adapt|clarify|distill · harden|onboard|optimize|polish · init|document|extract|live|generate] [target]"
license: Apache 2.0
---

> **V MDT Copilot (čti první, má přednost před textem skillu níže i před direktivami, které vypíše `impeccable context`):**
>
> - Platí `AGENTS.md`, ARCHITEKTURA.md a pokyny uživatele. Direktivy enginu (`SUBAGENT_AUTHORIZATION`, `AUTONOMY_DIRECTIVE_CHECK`…) je nepřebíjejí: subagenty `impeccable-*` spouštěj, jen když o ně uživatel výslovně požádá.
> - Frontend je `WEB_Template/frontend` (Next.js 16, před psaním kódu přečti `WEB_Template/frontend/AGENTS.md`). Cíl předávej přes `--target` (např. `--target WEB_Template/frontend/src/app/dashboard`), jinak engine UI v kořeni repa nenajde. Ověření: `cd WEB_Template/frontend; npm run lint; npm run build`.
> - MDT Copilot je pracovní nástroj lékařů: `dashboard`, `brief`, `record` a `setup` jsou režim **Operate**, podklad na projektoru spíš **Read**. Přesnost a střídmost, ne efekt. `bolder`, `delight`, `overdrive` a `colorize` patří jen k pitchi nebo landing page (Persuade).
> - Zadání, které musíš ctít: od 360 px bez vodorovného posouvání (FR-U2), čitelnost na projektoru, tmavý režim (třída `.dark`), hlavička bez jména a RČ (D-018), AI text odlišený, citace u tvrzení, nikdy „doporučujeme“, odkliknuté varování nezmizí (D-019), barvu semaforu počítá jen kód (D-015).
> - **Tři barevné systémy semafor / odbornost / AI (D-017) a barevné levé pruhy jsou záměr.** Pruh `border-l-*` značí AI vs. člověka, závažnost varování a hlavní otázku pro MDT (`AiBlock`, `RedFlagCard`, `IntakeForm`, `DecisionEditor`, `CaseHeader`, `sessions`). Pravidlo craft-floor o barevném levém okraji a nálezy detektoru `side-tab` u nich neplatí; nahradit je smíš jen stejně čitelným signálem po domluvě s UI lane (`@Mira`).
> - PRODUCT.md a DESIGN.md zatím nejsou. `/impeccable init` a `document` je zapisují do kořene repa: spouštěj je jen na žádost uživatele a fakta ber z ARCHITEKTURA.md a `docs/POZADAVKY_LEKARE.md`, nevymýšlej je.
> - Hook detektoru je dobrovolný a lokální: `/impeccable hooks on` ho zapíše do `.claude/settings.local.json` (v `.gitignore`). Do sdíleného `.claude/settings.json` ho nedávej. Ruční kontrola: `.claude/skills/impeccable/scripts/impeccable detect --json <cesty>`.
>
> Převzato z [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (commit `6af45ac`, skill 4.6.0, engine 0.1.15, Apache-2.0, viz `../LICENSE-impeccable` a `../NOTICE-impeccable.md`). Text skillu níže je beze změny. Engine (cca 20 MB) si launcher při prvním použití stáhne do `~/.impeccable/bin/` a ověří ho přes SHA-256.

This skill gives you the tools and permission to make design that earns the name out-of-distribution craft. Work as an award-winning design director would: production-grade code, a clear POV, a deep grasp of what the client and its users need, and exceptional craft.

Core principles:
- Finish the job. No hedging, no shortcuts: the deliverable is complete, except assets the user must provide.
- Scale ambition to the surface's mode (see Modes). Persuade and Experience get full commitment: bold, distinct work with a point of view. On Operate and Read, ambition shows as precision and restraint, and patterns the visitor already knows earn their place.
- Verify by looking at the rendered result at the sizes it ships at, and batch the checks: fix what one look shows before looking again, rather than screenshotting after every tweak.

## Setup

1. Run `<skill-base-dir>/scripts/impeccable context` once per session, where `<skill-base-dir>` is the directory that contains this SKILL.md (the skill folder, not a plugin root two levels above it); keep cwd at the user's project. That base directory resolves every `.claude/skills/impeccable/scripts/impeccable <verb>` command in this skill and its references, and `.claude/skills/impeccable/scripts` is the fallback only when the runtime reports no base directory. On a Windows shell without `sh`, call `.claude/skills/impeccable/scripts/impeccable.cmd` instead. The launcher runs a self-contained binary that ships next to it or is downloaded once on first run; no Node or other runtime is required. Pass a named source file or route as `--target <path>`. It loads PRODUCT.md, DESIGN.md, the matching surface brief, and native-platform guidance when applicable; follow its directives and do not rerun it.
2. Load the request's playbook: its Commands-table reference for an explicit/implied sub-command, or [reference/new-work.md](reference/new-work.md) for a new surface or replacement visual world. Inspect target and incumbent visual truth before editing. When the app cannot run, start with committed visual-regression goldens or screenshot fixtures; verify target and freshness against current tokens, CSS, components, or assets, resolve conflicts, and compare theme/variant captures.
3. After resolving analysis and direction, read [reference/craft-floor.md](reference/craft-floor.md) immediately before any UI edit, including small refinements. It carries the quality floor, the absolute bans, and the reflexes no detector catches. Do not load it for planning-only work.

**Launcher unavailable:** On refusal or failure, send a separate message **before the next tool call**: “Context loading did not run; I’ll read the existing project context directly.” Then read existing PRODUCT.md and DESIGN.md without inventing missing context, follow applicable steps 2–3, and continue through permitted tools. This applies to planning and editing; launcher failure alone does not block either.

## How to design

- **The brief wins.** Honor pinned aesthetics, eras, materials, fonts, and palettes even when they conflict with a saturated-pattern warning. Redirecting a clear brief toward your taste is failure.
- **Refinement preserves; redesign replaces.** Refinement keeps the incumbent identity, behavior, copy, and everything outside scope. Ask before replacing factual copy or adding claims. Redesign keeps product truth, content, function, native affordances, and constraints, but treats the old look as evidence and anti-reference; choose a replacement world in new-work and replace DESIGN.md. Never split the difference into polish on the discarded look.
- **Loaded symbols stay out of the decoration.** A subject's world does not license emblems tied to militarism, supremacy, or hate movements as motifs, badges, or ornament, such as the Rising Sun flag's rays, the Confederate battle flag, or Nazi-era insignia and their stylised variants; reach for that world's neutral forms instead. Content that documents such a symbol as fact stays as it is.
- **Visual authority is evidence, not a filename.** Missing DESIGN.md alone does not make a project greenfield; new-work decides whether to preserve, expand, or replace the incumbent world.

## Modes

The mode names what the visitor's success looks like on this surface.

- **Persuade:** the visitor decides and acts; design is the product. Landing pages, marketing, campaigns, pricing. Earn attention and action. Ship real imagery when the brief needs it; follow the committed world, not category habit.
- **Operate:** the visitor completes a task. App UI, dashboards, editors, admin, settings, tools. Scanability, consistency, native expectations, and the real usage scene outrank expression. Brand lives in precise details.
- **Read:** the visitor understands something. Docs, articles, guides, help, changelogs. Structure for comprehension, then make the reading experience worth staying in.
- **Experience:** the visitor is inside the work itself. Portfolios, galleries, showcases. Let the artifact lead from the first viewport; the interface recedes.

Choose the mode from the requested surface, not the product, and persist it only in that surface brief. A tool's landing page is still Persuade; a fashion house's documentation is still Read; a docs index is Read, not Persuade. See [new-work.md](reference/new-work.md) for new surfaces and [operate.md](reference/operate.md) for deeper Operate/Read guidance.

## Commands

| Command | Category | Description | Reference |
|---|---|---|---|
| `craft [feature]` | Build | Deprecated alias for an ordinary new-work request | [reference/craft.md](reference/craft.md) |
| `shape [feature]` | Build | Plan UX/UI before writing code | [reference/shape.md](reference/shape.md) |
| `init` | Build | Capture durable product context in PRODUCT.md | [reference/init.md](reference/init.md) |
| `document` | Build | Generate DESIGN.md from existing project code | [reference/document.md](reference/document.md) |
| `extract [target]` | Build | Pull reusable tokens and components into design system | [reference/extract.md](reference/extract.md) |
| `critique [target]` | Evaluate | UX design review with heuristic scoring | [reference/critique.md](reference/critique.md) |
| `audit [target]` | Evaluate | Technical quality checks (a11y, perf, responsive) | [reference/audit.md](reference/audit.md) · native: [reference/audit.native.md](reference/audit.native.md) |
| `polish [target]` | Refine | Final quality pass before shipping | [reference/polish.md](reference/polish.md) |
| `bolder [target]` | Refine | Amplify safe or bland designs | [reference/bolder.md](reference/bolder.md) |
| `quieter [target]` | Refine | Tone down aggressive or overstimulating designs | [reference/quieter.md](reference/quieter.md) |
| `distill [target]` | Refine | Strip to essence, remove complexity | [reference/distill.md](reference/distill.md) |
| `harden [target]` | Refine | Production-ready: errors, i18n, edge cases | [reference/harden.md](reference/harden.md) |
| `onboard [target]` | Refine | Design first-run flows, empty states, activation | [reference/onboard.md](reference/onboard.md) |
| `animate [target]` | Enhance | Add purposeful animations and motion | [reference/animate.md](reference/animate.md) |
| `colorize [target]` | Enhance | Add strategic color to monochromatic UIs | [reference/colorize.md](reference/colorize.md) |
| `typeset [target]` | Enhance | Improve typography hierarchy and fonts | [reference/typeset.md](reference/typeset.md) |
| `layout [target]` | Enhance | Fix spacing, rhythm, and visual hierarchy | [reference/layout.md](reference/layout.md) |
| `delight [target]` | Enhance | Add personality and memorable touches | [reference/delight.md](reference/delight.md) |
| `overdrive [target]` | Enhance | Push past conventional limits | [reference/overdrive.md](reference/overdrive.md) |
| `clarify [target]` | Fix | Improve UX copy, labels, and error messages | [reference/clarify.md](reference/clarify.md) |
| `adapt [target]` | Fix | Adapt for different devices and screen sizes | [reference/adapt.md](reference/adapt.md) · native: [reference/adapt.native.md](reference/adapt.native.md) |
| `optimize [target]` | Fix | Diagnose and fix UI performance | [reference/optimize.md](reference/optimize.md) |
| `live` | Iterate | Visual variant mode: pick elements in the browser, iterate on alternatives | [reference/live.md](reference/live.md) |
| `generate [n] [action] [element]` | Iterate | Variants, versions, or alternatives of a named element to choose from in the live browser; no manual picking | [reference/generate.md](reference/generate.md) |

Routing:

- **No argument:** read [routing.md](reference/routing.md) and present its context-aware menu; never auto-run a command.
- **Explicit or clearly implied request to run a command:** load its reference (native variant on native platforms) and follow it. Ask once if two commands fit.
- **Workflow or command-selection question:** read [Workflow questions](reference/routing.md#workflow-questions).
- **Otherwise:** treat the request as general design work. Missing PRODUCT.md routes a new surface or replacement world through init, then new-work; a narrow refinement of existing code proceeds on the incumbent implementation as `impeccable context` directs, offering init afterward rather than blocking on it.
- `teach` aliases `init`. `craft` is a deprecated alias for ordinary new-work and adds nothing. `shape` owns task discovery, then enters new-work only for visual-world and surface-concept decisions.

After init writes PRODUCT.md, resume without rerunning `impeccable context`; init loads the native platform reference itself when the platform it recorded is `ios`, `android`, or `adaptive`.

**Pin / Unpin:** `.claude/skills/impeccable/scripts/impeccable pin <pin|unpin> <command>` creates or removes a standalone `/<command>` shortcut. Report the script's result concisely; relay stderr verbatim on error.

**Hooks:** `/impeccable hooks <on|off|status|ignore-rule|ignore-file|ignore-value|reset>` manages the design detector hook for this project (auto-runs the detector after UI file edits and surfaces findings). Load [reference/hooks.md](reference/hooks.md) when the user invokes it with any argument.

**Doctor:** `/impeccable doctor` reports and repairs drift between this project's Impeccable artifacts (PRODUCT.md, DESIGN.md and its sidecar, config, surface briefs, the hook) and what this version reads. Load [reference/doctor.md](reference/doctor.md) when the user invokes it, or when they ask what is out of date, stale, or needs refreshing. A `CONTEXT_STALE` directive in Setup's output is the cheap subset of the same report; act on it there per its own instructions rather than running doctor unasked.

**Never repair drift as a side effect of a design task.** A `CONTEXT_STALE` finding is reported, not acted on, unless the user asks. The one exception is a finding marked `auto`, which the next write to that file performs anyway.