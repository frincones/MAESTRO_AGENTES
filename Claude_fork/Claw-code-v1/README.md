<div align="center">

# Claude Code — Source Code

**The full source code of Anthropic's Claude Code CLI, made public on March 31, 2026**

[![TypeScript](https://img.shields.io/badge/TypeScript-512K%2B_lines-3178C6?logo=typescript&logoColor=white)](#tech-stack)
[![Bun](https://img.shields.io/badge/Runtime-Bun-f472b6?logo=bun&logoColor=white)](#tech-stack)
[![React + Ink](https://img.shields.io/badge/UI-React_%2B_Ink-61DAFB?logo=react&logoColor=black)](#tech-stack)
[![Files](https://img.shields.io/badge/~1,900_files-source_only-grey)](#directory-structure)

> The original unmodified source is preserved in the [`backup` branch](https://github.com/nirholas/claude-code/tree/backup).

</div>

---

## Table of Contents

- [Setup & Run](#setup--run)
- [How It Became Public](#how-it-became-public)
- [What Is Claude Code?](#what-is-claude-code)
- [What's Claude Under The Hood?](#whats-claude-under-the-hood)
- [Documentation](#-documentation)
- [Directory Structure](#directory-structure)
- [Architecture](#architecture)
  - [Tool System](#1-tool-system)
  - [Command System](#2-command-system)
  - [Service Layer](#3-service-layer)
  - [Bridge System](#4-bridge-system)
  - [Permission System](#5-permission-system)
  - [Feature Flags](#6-feature-flags)
- [Key Files](#key-files)
- [Tech Stack](#tech-stack)
- [Design Patterns](#design-patterns)
- [GitPretty Setup](#gitpretty-setup)
- [Disclaimer](#disclaimer)

---

## Setup & Run

```bash
# 1. Install dependencies
bun install

# 2. Build the CLI bundle
bun run build

# 3. Run the CLI
bun dist/cli.mjs
```

### Useful commands

```bash
# Help / version
bun dist/cli.mjs --help
bun dist/cli.mjs --version

# Legacy debug alias still supported
bun dist/cli.mjs -d2e --version

# Non-interactive smoke test
bun dist/cli.mjs -p --bare --dangerously-skip-permissions --max-turns 1 "Reply with exactly OK."

# Run the built bundle with Node too
node dist/cli.mjs --help
```

### Notes

- On first interactive run, the CLI shows a workspace trust prompt.
- `bun run build` produces `dist/cli.mjs`.
- This leaked checkout still contains many unrelated repo-wide lint/type errors, so `npm run check` is not currently a reliable setup validation step.

---

## How It Became Public

[Chaofan Shou (@Fried_rice)](https://x.com/Fried_rice) discovered that the published npm package for Claude Code included a `.map` file referencing the full, unobfuscated TypeScript source — accessible as a zip from Anthropic's R2 storage bucket.

An Anthropic employee subsequently made the source available in the public domain on March 31, 2026.

---

## What Is Claude Code?

Claude Code is Anthropic's official CLI tool for interacting with Claude directly from the terminal — editing files, running commands, searching codebases, managing git workflows, and more. This repository contains the `src/` directory.

| | |
|---|---|
| **Published** | 2026-03-31 |
| **Language** | TypeScript (strict) |
| **Runtime** | [Bun](https://bun.sh) |
| **Terminal UI** | [React](https://react.dev) + [Ink](https://github.com/vadimdemedes/ink) |
| **Scale** | ~1,900 files · 512,000+ lines of code |

---

> The following "under the hood" breakdown is adapted from [`Kuberwastaken/claude-code`'s README](https://raw.githubusercontent.com/Kuberwastaken/claude-code/refs/heads/main/README.md) and remapped to this repository's source paths.

## What's Claude Under The Hood?

If you've been living under a rock, Claude Code is Anthropic's official CLI tool for coding with Claude and the most popular AI coding agent.

From the outside, it looks like a polished but relatively simple CLI.

From the inside, It's a **785KB [`src/main.tsx`](src/main.tsx)** entry point, a custom React terminal renderer, 40+ tools, a multi-agent orchestration system, a background memory consolidation engine called "dream," and much more

Enough yapping, here's some parts about the source code that are genuinely cool that I found after an afternoon deep dive:

---

## BUDDY - A Tamagotchi Inside Your Terminal

I am not making this up.

Claude Code has a full **Tamagotchi-style companion pet system** called "Buddy." A **deterministic gacha system** with species rarity, shiny variants, procedurally generated stats, and a soul description written by Claude on first hatch like OpenClaw.

The entire thing lives in [`src/buddy/`](src/buddy/) and is gated behind the `BUDDY` compile-time feature flag.

### The Gacha System

Your buddy's species is determined by a **Mulberry32 PRNG**, a fast 32-bit pseudo-random number generator seeded from your `userId` hash with the salt `'friend-2026-401'`:

```typescript
// Mulberry32 PRNG - deterministic, reproducible per-user
function mulberry32(seed: number): () => number {
  return function() {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
}
```

Same user always gets the same buddy.

### 18 Species (Obfuscated in Code)

The species names are hidden via `String.fromCharCode()` arrays - Anthropic clearly didn't want these showing up in string searches. Decoded, the full species list is:

| Rarity | Species |
|--------|---------|
| **Common** (60%) | Pebblecrab, Dustbunny, Mossfrog, Twigling, Dewdrop, Puddlefish |
| **Uncommon** (25%) | Cloudferret, Gustowl, Bramblebear, Thornfox |
| **Rare** (10%) | Crystaldrake, Deepstag, Lavapup |
| **Epic** (4%) | Stormwyrm, Voidcat, Aetherling |
| **Legendary** (1%) | Cosmoshale, Nebulynx |

On top of that, there's a **1% shiny chance** completely independent of rarity. So a Shiny Legendary Nebulynx has a **0.01%** chance of being rolled. Dang.

### Stats, Eyes, Hats, and Soul

Each buddy gets procedurally generated:
- **5 stats**: `DEBUGGING`, `PATIENCE`, `CHAOS`, `WISDOM`, `SNARK` (0-100 each)
- **6 possible eye styles** and **8 hat options** (some gated by rarity)
- **A "soul"** as mentioned, the personality generated by Claude on first hatch, written in character

The sprites are rendered as **5-line-tall, 12-character-wide ASCII art** with multiple animation frames. There are idle animations, reaction animations, and they sit next to your input prompt.

### The Lore

The code references April 1-7, 2026 as a **teaser window** (so probably for easter?), with a full launch gated for May 2026. The companion has a system prompt that tells Claude:

```
A small {species} named {name} sits beside the user's input box and 
occasionally comments in a speech bubble. You're not {name} - it's a 
separate watcher.
```

So it's not just cosmetic - the buddy has its own personality and can respond when addressed by name. I really do hope they ship it.

---

## KAIROS - "Always-On Claude"

Inside [`src/assistant/`](src/assistant/), there's an entire mode called **KAIROS** i.e. a persistent, always-running Claude assistant that doesn't wait for you to type. It watches, logs, and **proactively** acts on things it notices.

This is gated behind the `PROACTIVE` / `KAIROS` compile-time feature flags and is completely absent from external builds.

### How It Works

KAIROS maintains **append-only daily log files** - it writes observations, decisions, and actions throughout the day. On a regular interval, it receives `<tick>` prompts that let it decide whether to act proactively or stay quiet.

The system has a **15-second blocking budget**, any proactive action that would block the user's workflow for more than 15 seconds gets deferred. This is Claude trying to be helpful without being annoying.

### Brief Mode

When KAIROS is active, there's a special output mode called **Brief**, extremely concise responses designed for a persistent assistant that shouldn't flood your terminal. Think of it as the difference between a chatty friend and a professional assistant who only speaks when they have something valuable to say.

### Exclusive Tools

KAIROS gets tools that regular Claude Code doesn't have:

| Tool | What It Does |
|------|-------------|
| **SendUserFile** | Push files directly to the user (notifications, summaries) |
| **PushNotification** | Send push notifications to the user's device |
| **SubscribePR** | Subscribe to and monitor pull request activity |

 ---

## ULTRAPLAN - 30-Minute Remote Planning Sessions

Here's one that's wild from an infrastructure perspective.

**ULTRAPLAN** is a mode where Claude Code offloads a complex planning task to a **remote Cloud Container Runtime (CCR) session** running **Opus 4.6**, gives it up to **30 minutes** to think, and lets you approve the result from your browser.

The basic flow:

1. Claude Code identifies a task that needs deep planning
2. It spins up a remote CCR session via the `tengu_ultraplan_model` config
3. Your terminal shows a polling state - checking every **3 seconds** for the result
4. Meanwhile, a browser-based UI lets you watch the planning happen and approve/reject it
5. When approved, there's a special sentinel value `__ULTRAPLAN_TELEPORT_LOCAL__` that "teleports" the result back to your local terminal

---

## The "Dream" System - Claude Literally Dreams

Okay this is genuinely one of the coolest things in here.

Claude Code has a system called **autoDream** ([`src/services/autoDream/`](src/services/autoDream/)) - a background memory consolidation engine that runs as a **forked subagent**. The naming is very intentional. It's Claude... dreaming.

This is extremely funny because [I had the same idea for LITMUS last week - OpenClaw subagents creatively having leisure time to find fun new papers](https://github.com/Kuberwastaken/litmus)

### The Three-Gate Trigger

The dream doesn't just run whenever it feels like it. It has a **three-gate trigger system**:

1. **Time gate**: 24 hours since last dream
2. **Session gate**: At least 5 sessions since last dream  
3. **Lock gate**: Acquires a consolidation lock (prevents concurrent dreams)

All three must pass. This prevents both over-dreaming and under-dreaming.

### The Four Phases

When it runs, the dream follows four strict phases from the prompt in [`consolidationPrompt.ts`](src/services/autoDream/consolidationPrompt.ts):

**Phase 1 - Orient**: `ls` the memory directory, read `MEMORY.md`, skim existing topic files to improve.

**Phase 2 - Gather Recent Signal**: Find new information worth persisting. Sources in priority: daily logs → drifted memories → transcript search.

**Phase 3 - Consolidate**: Write or update memory files. Convert relative dates to absolute. Delete contradicted facts.

**Phase 4 - Prune and Index**: Keep `MEMORY.md` under 200 lines AND ~25KB. Remove stale pointers. Resolve contradictions.

The prompt literally says:

> *"You are performing a dream - a reflective pass over your memory files. Synthesize what you've learned recently into durable, well-organized memories so that future sessions can orient quickly."*

The dream subagent gets **read-only bash** - it can look at your project but not modify anything. It's purely a memory consolidation pass.

---

## Undercover Mode - "Do Not Blow Your Cover"


This one is fascinating from a corporate strategy perspective.

Anthropic employees (identified by `USER_TYPE === 'ant'`) use Claude Code on public/open-source repositories. **Undercover Mode** ([`src/utils/undercover.ts`](src/utils/undercover.ts)) prevents the AI from accidentally revealing internal information in commits and PRs.

When active, it injects this into the system prompt:

```
## UNDERCOVER MODE - CRITICAL

You are operating UNDERCOVER in a PUBLIC/OPEN-SOURCE repository. Your commit
messages, PR titles, and PR bodies MUST NOT contain ANY Anthropic-internal
information. Do not blow your cover.

NEVER include in commit messages or PR descriptions:
- Internal model codenames (animal names like Capybara, Tengu, etc.)
- Unreleased model version numbers (e.g., opus-4-7, sonnet-4-8)
- Internal repo or project names
- Internal tooling, Slack channels, or short links (e.g., go/cc, #claude-code-…)
- The phrase "Claude Code" or any mention that you are an AI
- Co-Authored-By lines or any other attribution
```

The activation logic:
- `CLAUDE_CODE_UNDERCOVER=1` forces it ON (even in internal repos)
- Otherwise it's **automatic**: active UNLESS the repo remote matches an internal allowlist
- There is **NO force-OFF** - *"if we're not confident we're in an internal repo, we stay undercover."*

So this confirms:
1. **Anthropic employees actively use Claude Code to contribute to open-source** - and the AI is told to hide that it's an AI
2. **Internal model codenames are animal names** - Capybara, Tengu, etc.
3. **"Tengu"** appears hundreds of times as a prefix for feature flags and analytics events - it's almost certainly **Claude Code's internal project codename**

All of this is dead-code-eliminated from external builds. But source maps don't care about dead code elimination.

Makes me wonder how much are they internally causing havoc to open source repos

---

## Multi-Agent Orchestration - "Coordinator Mode"


Claude Code has a full **multi-agent orchestration system** in [`src/coordinator/`](src/coordinator/), activated via `CLAUDE_CODE_COORDINATOR_MODE=1`.

When enabled, Claude Code transforms from a single agent into a **coordinator** that spawns, directs, and manages multiple worker agents in parallel. The coordinator system prompt in [`coordinatorMode.ts`](src/coordinator/coordinatorMode.ts) is a masterclass in multi-agent design:

| Phase | Who | Purpose |
|-------|-----|---------|
| **Research** | Workers (parallel) | Investigate codebase, find files, understand problem |
| **Synthesis** | **Coordinator** | Read findings, understand the problem, craft specs |
| **Implementation** | Workers | Make targeted changes per spec, commit |
| **Verification** | Workers | Test changes work |

The prompt **explicitly** teaches parallelism:

> *"Parallelism is your superpower. Workers are async. Launch independent workers concurrently whenever possible - don't serialize work that can run simultaneously."*

Workers communicate via `<task-notification>` XML messages. There's a shared **scratchpad directory** (gated behind `tengu_scratch`) for cross-worker durable knowledge sharing. And the prompt has this gem banning lazy delegation:

> *Do NOT say "based on your findings" - read the actual findings and specify exactly what to do.*

The system also includes **Agent Teams/Swarm** capabilities (`tengu_amber_flint` feature gate) with in-process teammates using `AsyncLocalStorage` for context isolation, process-based teammates using tmux/iTerm2 panes, team memory synchronization, and color assignments for visual distinction.

---

## Fast Mode is Internally Called "Penguin Mode"

Yeah, they really called it Penguin Mode. The API endpoint in [`src/utils/fastMode.ts`](src/utils/fastMode.ts) is literally:

```typescript
const endpoint = `${getOauthConfig().BASE_API_URL}/api/claude_code_penguin_mode`
```

The config key is `penguinModeOrgEnabled`. The kill-switch is `tengu_penguins_off`. The analytics event on failure is `tengu_org_penguin_mode_fetch_failed`. Penguins all the way down.

---

## The System Prompt Architecture

The system prompt isn't a single string like most apps have - it's built from **modular, cached sections** composed at runtime in [`src/constants/`](src/constants/).

The architecture uses a `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker that splits the prompt into:
- **Static sections** - cacheable across organizations (things that don't change per user)
- **Dynamic sections** - user/session-specific content that breaks cache when changed

There's a function called `DANGEROUS_uncachedSystemPromptSection()` for volatile sections you explicitly want to break cache. The naming convention alone tells you someone learned this lesson the hard way.

### The Cyber Risk Instruction

One particularly interesting section is the `CYBER_RISK_INSTRUCTION` in [`constants/cyberRiskInstruction.ts`](src/constants/cyberRiskInstruction.ts), which has a massive warning header:

```
IMPORTANT: DO NOT MODIFY THIS INSTRUCTION WITHOUT SAFEGUARDS TEAM REVIEW
This instruction is owned by the Safeguards team (David Forsythe, Kyla Guru)
```

So now we know exactly who at Anthropic owns the security boundary decisions and that it's governed by named individuals on a specific team. The instruction itself draws clear lines: authorized security testing is fine, destructive techniques and supply chain compromise are not.

---

## The Full Tool Registry - 40+ Tools

Claude Code's tool system lives in [`src/tools/`](src/tools/). Here's the complete list:

| Tool | What It Does |
|------|-------------|
| **AgentTool** | Spawn child agents/subagents |
| **BashTool** / **PowerShellTool** | Shell execution (with optional sandboxing) |
| **FileReadTool** / **FileEditTool** / **FileWriteTool** | File operations |
| **GlobTool** / **GrepTool** | File search (uses native `bfs`/`ugrep` when available) |
| **WebFetchTool** / **WebSearchTool** / **WebBrowserTool** | Web access |
| **NotebookEditTool** | Jupyter notebook editing |
| **SkillTool** | Invoke user-defined skills |
| **REPLTool** | Interactive VM shell (bare mode) |
| **LSPTool** | Language Server Protocol communication |
| **AskUserQuestionTool** | Prompt user for input |
| **EnterPlanModeTool** / **ExitPlanModeV2Tool** | Plan mode control |
| **BriefTool** | Upload/summarize files to claude.ai |
| **SendMessageTool** / **TeamCreateTool** / **TeamDeleteTool** | Agent swarm management |
| **TaskCreateTool** / **TaskGetTool** / **TaskListTool** / **TaskUpdateTool** / **TaskOutputTool** / **TaskStopTool** | Background task management |
| **TodoWriteTool** | Write todos (legacy) |
| **ListMcpResourcesTool** / **ReadMcpResourceTool** | MCP resource access |
| **SleepTool** | Async delays |
| **SnipTool** | History snippet extraction |
| **ToolSearchTool** | Tool discovery |
| **ListPeersTool** | List peer agents (UDS inbox) |
| **MonitorTool** | Monitor MCP servers |
| **EnterWorktreeTool** / **ExitWorktreeTool** | Git worktree management |
| **ScheduleCronTool** | Schedule cron jobs |
| **RemoteTriggerTool** | Trigger remote agents |
| **WorkflowTool** | Execute workflow scripts |
| **ConfigTool** | Modify settings (**internal only**) |
| **TungstenTool** | Advanced features (**internal only**) |
| **SendUserFile** / **PushNotification** / **SubscribePR** | KAIROS-exclusive tools |

Tools are registered via `getAllBaseTools()` and filtered by feature gates, user type, environment flags, and permission deny rules. There's a **tool schema cache** ([`toolSchemaCache.ts`](src/utils/toolSchemaCache.ts)) that caches JSON schemas for prompt efficiency.

---

## The Permission and Security System

Claude Code's permission system in [`src/utils/permissions/`](src/utils/permissions/) is far more sophisticated than "allow/deny":

**Permission Modes**: `default` (interactive prompts), `auto` (ML-based auto-approval via transcript classifier), `bypass` (skip checks), `yolo` (deny all - ironically named)

**Risk Classification**: Every tool action is classified as **LOW**, **MEDIUM**, or **HIGH** risk. There's a **YOLO classifier** - a fast ML-based permission decision system that decides automatically.

**Protected Files**: `.gitconfig`, `.bashrc`, `.zshrc`, `.mcp.json`, `.claude.json` and others are guarded from automatic editing.

**Path Traversal Prevention**: URL-encoded traversals, Unicode normalization attacks, backslash injection, case-insensitive path manipulation - all handled.

**Permission Explainer**: A separate LLM call explains tool risks to the user before they approve. When Claude says "this command will modify your git config" - that explanation is itself generated by Claude.

---

## Hidden Beta Headers and Unreleased API Features

The [`src/constants/betas.ts`](src/constants/betas.ts) file reveals every beta feature Claude Code negotiates with the API:

```typescript
'interleaved-thinking-2025-05-14'      // Extended thinking
'context-1m-2025-08-07'                // 1M token context window
'structured-outputs-2025-12-15'        // Structured output format
'web-search-2025-03-05'                // Web search
'advanced-tool-use-2025-11-20'         // Advanced tool use
'effort-2025-11-24'                    // Effort level control
'task-budgets-2026-03-13'              // Task budget management
'prompt-caching-scope-2026-01-05'      // Prompt cache scoping
'fast-mode-2026-02-01'                 // Fast mode (Penguin)
'redact-thinking-2026-02-12'           // Redacted thinking
'token-efficient-tools-2026-03-28'     // Token-efficient tool schemas
'afk-mode-2026-01-31'                  // AFK mode
'cli-internal-2026-02-09'             // Internal-only (ant)
'advisor-tool-2026-03-01'              // Advisor tool
'summarize-connector-text-2026-03-13'  // Connector text summarization
```

`redact-thinking`, `afk-mode`, and `advisor-tool` are also not released.

---

## Feature Gating - Internal vs. External Builds

This is one of the most architecturally interesting parts of the codebase.

Claude Code uses **compile-time feature flags** via Bun's `feature()` function from `bun:bundle`. The bundler **constant-folds** these and **dead-code-eliminates** the gated branches from external builds. The complete list of known flags:

| Flag | What It Gates |
|------|--------------|
| `PROACTIVE` / `KAIROS` | Always-on assistant mode |
| `KAIROS_BRIEF` | Brief command |
| `BRIDGE_MODE` | Remote control via claude.ai |
| `DAEMON` | Background daemon mode |
| `VOICE_MODE` | Voice input |
| `WORKFLOW_SCRIPTS` | Workflow automation |
| `COORDINATOR_MODE` | Multi-agent orchestration |
| `TRANSCRIPT_CLASSIFIER` | AFK mode (ML auto-approval) |
| `BUDDY` | Companion pet system |
| `NATIVE_CLIENT_ATTESTATION` | Client attestation |
| `HISTORY_SNIP` | History snipping |
| `EXPERIMENTAL_SKILL_SEARCH` | Skill discovery |

Additionally, `USER_TYPE === 'ant'` gates Anthropic-internal features: staging API access (`claude-ai.staging.ant.dev`), internal beta headers, Undercover mode, the `/security-review` command, `ConfigTool`, `TungstenTool`, and debug prompt dumping to `~/.config/claude/dump-prompts/`.

**GrowthBook** handles runtime feature gating with aggressively cached values. Feature flags prefixed with `tengu_` control everything from fast mode to memory consolidation. Many checks use `getFeatureValue_CACHED_MAY_BE_STALE()` to avoid blocking the main loop - stale data is considered acceptable for feature gates.

---

## Other Notable Findings

### The Upstream Proxy
The [`src/upstreamproxy/`](src/upstreamproxy/) directory contains a container-aware proxy relay that uses **`prctl(PR_SET_DUMPABLE, 0)`** to prevent same-UID ptrace of heap memory. It reads session tokens from `/run/ccr/session_token` in CCR containers, downloads CA certificates, and starts a local CONNECT→WebSocket relay. Anthropic API, GitHub, npmjs.org, and pypi.org are explicitly excluded from proxying.

### Bridge Mode
A JWT-authenticated bridge system in [`src/bridge/`](src/bridge/) for integrating with claude.ai. Supports work modes: `'single-session'` | `'worktree'` | `'same-dir'`. Includes trusted device tokens for elevated security tiers.

### Model Codenames in Migrations
The [`src/migrations/`](src/migrations/) directory reveals the internal codename history:
- `migrateFennecToOpus` - **"Fennec"** (the fox) was an Opus codename
- `migrateSonnet1mToSonnet45` - Sonnet with 1M context became Sonnet 4.5
- `migrateSonnet45ToSonnet46` - Sonnet 4.5 → Sonnet 4.6
- `resetProToOpusDefault` - Pro users were reset to Opus at some point

### Attribution Header
Every API request includes:
```
x-anthropic-billing-header: cc_version={VERSION}.{FINGERPRINT}; 
  cc_entrypoint={ENTRYPOINT}; cch={ATTESTATION_PLACEHOLDER}; cc_workload={WORKLOAD};
```
The `NATIVE_CLIENT_ATTESTATION` feature lets Bun's HTTP stack overwrite the `cch=00000` placeholder with a computed hash - essentially a client authenticity check so Anthropic can verify the request came from a real Claude Code install.

### Computer Use - "Chicago"
Claude Code includes a full Computer Use implementation, internally codenamed **"Chicago"**, built on `@ant/computer-use-mcp`. It provides screenshot capture, click/keyboard input, and coordinate transformation. Gated to Max/Pro subscriptions (with an ant bypass for internal users).

### Pricing
For anyone wondering - all pricing in [`utils/modelCost.ts`](src/utils/modelCost.ts) matches [Anthropic's public pricing](https://docs.anthropic.com/en/docs/about-claude/models) exactly. Nothing newsworthy there.

---

## Final Thoughts

This is, without exaggeration, one of the most comprehensive looks we've ever gotten at how *the* production AI coding assistant works under the hood. Through the actual source code.

A few things stand out:

**The engineering is genuinely impressive.** This isn't a weekend project wrapped in a CLI. The multi-agent coordination, the dream system, the three-gate trigger architecture, the compile-time feature elimination - these are deeply considered systems.

**There's a LOT more coming.** KAIROS (always-on Claude), ULTRAPLAN (30-minute remote planning), the Buddy companion, coordinator mode, agent swarms, workflow scripts - the codebase is significantly ahead of the public release. Most of these are feature-gated and invisible in external builds.

**The internal culture shows.** Animal codenames (Tengu, Fennec, Capybara), playful feature names (Penguin Mode, Dream System), a Tamagotchi pet system with gacha mechanics. Some people at Anthropic is having fun.

If there's one takeaway this has, it's that security is hard. But `.npmignore` is harder, apparently :P

---

---

## 📚 Documentation

For in-depth guides, see the [`docs/`](docs/) directory:

| Guide | Description |
|-------|-------------|
| **[Architecture](docs/architecture.md)** | Core pipeline, startup sequence, state management, rendering, data flow |
| **[Tools Reference](docs/tools.md)** | Complete catalog of all ~40 agent tools with categories and permission model |
| **[Commands Reference](docs/commands.md)** | All ~85 slash commands organized by category |
| **[Subsystems Guide](docs/subsystems.md)** | Deep dives into Bridge, MCP, Permissions, Plugins, Skills, Tasks, Memory, Voice |
| **[Exploration Guide](docs/exploration-guide.md)** | How to navigate the codebase — study paths, grep patterns, key files |

---

## Directory Structure

```
src/
├── main.tsx                 # Entrypoint — Commander.js CLI parser + React/Ink renderer
├── QueryEngine.ts           # Core LLM API caller (~46K lines)
├── Tool.ts                  # Tool type definitions (~29K lines)
├── commands.ts              # Command registry (~25K lines)
├── tools.ts                 # Tool registry
├── context.ts               # System/user context collection
├── cost-tracker.ts          # Token cost tracking
│
├── tools/                   # Agent tool implementations (~40)
├── commands/                # Slash command implementations (~50)
├── components/              # Ink UI components (~140)
├── services/                # External service integrations
├── hooks/                   # React hooks (incl. permission checks)
├── types/                   # TypeScript type definitions
├── utils/                   # Utility functions
├── screens/                 # Full-screen UIs (Doctor, REPL, Resume)
│
├── bridge/                  # IDE integration (VS Code, JetBrains)
├── coordinator/             # Multi-agent orchestration
├── plugins/                 # Plugin system
├── skills/                  # Skill system
├── server/                  # Server mode
├── remote/                  # Remote sessions
├── memdir/                  # Persistent memory directory
├── tasks/                   # Task management
├── state/                   # State management
│
├── voice/                   # Voice input
├── vim/                     # Vim mode
├── keybindings/             # Keybinding configuration
├── schemas/                 # Config schemas (Zod)
├── migrations/              # Config migrations
├── entrypoints/             # Initialization logic
├── query/                   # Query pipeline
├── ink/                     # Ink renderer wrapper
├── buddy/                   # Companion sprite (Easter egg 🐣)
├── native-ts/               # Native TypeScript utils
├── outputStyles/            # Output styling
└── upstreamproxy/           # Proxy configuration
```

---

## Architecture

### 1. Tool System

> `src/tools/` — Every tool Claude can invoke is a self-contained module with its own input schema, permission model, and execution logic.

| Tool | Description |
|---|---|
| **File I/O** | |
| `FileReadTool` | Read files (images, PDFs, notebooks) |
| `FileWriteTool` | Create / overwrite files |
| `FileEditTool` | Partial modification (string replacement) |
| `NotebookEditTool` | Jupyter notebook editing |
| **Search** | |
| `GlobTool` | File pattern matching |
| `GrepTool` | ripgrep-based content search |
| `WebSearchTool` | Web search |
| `WebFetchTool` | Fetch URL content |
| **Execution** | |
| `BashTool` | Shell command execution |
| `SkillTool` | Skill execution |
| `MCPTool` | MCP server tool invocation |
| `LSPTool` | Language Server Protocol integration |
| **Agents & Teams** | |
| `AgentTool` | Sub-agent spawning |
| `SendMessageTool` | Inter-agent messaging |
| `TeamCreateTool` / `TeamDeleteTool` | Team management |
| `TaskCreateTool` / `TaskUpdateTool` | Task management |
| **Mode & State** | |
| `EnterPlanModeTool` / `ExitPlanModeTool` | Plan mode toggle |
| `EnterWorktreeTool` / `ExitWorktreeTool` | Git worktree isolation |
| `ToolSearchTool` | Deferred tool discovery |
| `SleepTool` | Proactive mode wait |
| `CronCreateTool` | Scheduled triggers |
| `RemoteTriggerTool` | Remote trigger |
| `SyntheticOutputTool` | Structured output generation |

### 2. Command System

> `src/commands/` — User-facing slash commands invoked with `/` in the REPL.

| Command | Description | | Command | Description |
|---|---|---|---|---|
| `/commit` | Git commit | | `/memory` | Persistent memory |
| `/review` | Code review | | `/skills` | Skill management |
| `/compact` | Context compression | | `/tasks` | Task management |
| `/mcp` | MCP server management | | `/vim` | Vim mode toggle |
| `/config` | Settings | | `/diff` | View changes |
| `/doctor` | Environment diagnostics | | `/cost` | Check usage cost |
| `/login` / `/logout` | Auth | | `/theme` | Change theme |
| `/context` | Context visualization | | `/share` | Share session |
| `/pr_comments` | PR comments | | `/resume` | Restore session |
| `/desktop` | Desktop handoff | | `/mobile` | Mobile handoff |

### 3. Service Layer

> `src/services/` — External integrations and core infrastructure.

| Service | Description |
|---|---|
| `api/` | Anthropic API client, file API, bootstrap |
| `mcp/` | Model Context Protocol connection & management |
| `oauth/` | OAuth 2.0 authentication |
| `lsp/` | Language Server Protocol manager |
| `analytics/` | GrowthBook feature flags & analytics |
| `plugins/` | Plugin loader |
| `compact/` | Conversation context compression |
| `extractMemories/` | Automatic memory extraction |
| `teamMemorySync/` | Team memory synchronization |
| `tokenEstimation.ts` | Token count estimation |
| `policyLimits/` | Organization policy limits |
| `remoteManagedSettings/` | Remote managed settings |

### 4. Bridge System

> `src/bridge/` — Bidirectional communication layer connecting IDE extensions (VS Code, JetBrains) with the CLI.

Key files: `bridgeMain.ts` (main loop) · `bridgeMessaging.ts` (protocol) · `bridgePermissionCallbacks.ts` (permission callbacks) · `replBridge.ts` (REPL session) · `jwtUtils.ts` (JWT auth) · `sessionRunner.ts` (session execution)

### 5. Permission System

> `src/hooks/toolPermission/` — Checks permissions on every tool invocation.

Prompts the user for approval/denial or auto-resolves based on the configured permission mode: `default`, `plan`, `bypassPermissions`, `auto`, etc.

### 6. Feature Flags

Dead code elimination at build time via Bun's `bun:bundle`:

```typescript
import { feature } from 'bun:bundle'

const voiceCommand = feature('VOICE_MODE')
  ? require('./commands/voice/index.js').default
  : null
```

Notable flags: `PROACTIVE` · `KAIROS` · `BRIDGE_MODE` · `DAEMON` · `VOICE_MODE` · `AGENT_TRIGGERS` · `MONITOR_TOOL`

---

## Key Files

| File | Lines | Purpose |
|------|------:|---------|
| `QueryEngine.ts` | ~46K | Core LLM API engine — streaming, tool loops, thinking mode, retries, token counting |
| `Tool.ts` | ~29K | Base types/interfaces for all tools — input schemas, permissions, progress state |
| `commands.ts` | ~25K | Command registration & execution with conditional per-environment imports |
| `main.tsx` | — | CLI parser + React/Ink renderer; parallelizes MDM, keychain, and GrowthBook on startup |

---

## Tech Stack

| Category | Technology |
|---|---|
| Runtime | [Bun](https://bun.sh) |
| Language | TypeScript (strict) |
| Terminal UI | [React](https://react.dev) + [Ink](https://github.com/vadimdemedes/ink) |
| CLI Parsing | [Commander.js](https://github.com/tj/commander.js) (extra-typings) |
| Schema Validation | [Zod v4](https://zod.dev) |
| Code Search | [ripgrep](https://github.com/BurntSushi/ripgrep) (via GrepTool) |
| Protocols | [MCP SDK](https://modelcontextprotocol.io) · LSP |
| API | [Anthropic SDK](https://docs.anthropic.com) |
| Telemetry | OpenTelemetry + gRPC |
| Feature Flags | GrowthBook |
| Auth | OAuth 2.0 · JWT · macOS Keychain |

---

## Design Patterns

<details>
<summary><strong>Parallel Prefetch</strong> — Startup optimization</summary>

MDM settings, keychain reads, and API preconnect fire in parallel as side-effects before heavy module evaluation:

```typescript
// main.tsx
startMdmRawRead()
startKeychainPrefetch()
```

</details>

<details>
<summary><strong>Lazy Loading</strong> — Deferred heavy modules</summary>

OpenTelemetry (~400KB) and gRPC (~700KB) are loaded via dynamic `import()` only when needed.

</details>

<details>
<summary><strong>Agent Swarms</strong> — Multi-agent orchestration</summary>

Sub-agents spawn via `AgentTool`, with `coordinator/` handling orchestration. `TeamCreateTool` enables team-level parallel work.

</details>

<details>
<summary><strong>Skill System</strong> — Reusable workflows</summary>

Defined in `skills/` and executed through `SkillTool`. Users can add custom skills.

</details>

<details>
<summary><strong>Plugin Architecture</strong> — Extensibility</summary>

Built-in and third-party plugins loaded through the `plugins/` subsystem.

</details>

---

## GitPretty Setup

<details>
<summary>Show per-file emoji commit messages in GitHub's file UI</summary>

```bash
# Apply emoji commits
bash ./gitpretty-apply.sh .

# Optional: install hooks for future commits
bash ./gitpretty-apply.sh . --hooks

# Push as usual
git push origin main
```

</details>

---

## Disclaimer

This repository contains source code from Anthropic's Claude Code, made publicly available on **2026-03-31**. All original source code is the property of [Anthropic](https://www.anthropic.com). Contact [nichxbt](https://www.x.com/nichxbt) for any questions or comments.
