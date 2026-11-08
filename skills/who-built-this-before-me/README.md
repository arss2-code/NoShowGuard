# who-built-this-before-me

A skill for Claude Code that checks whether your idea has already been built before you invest time in it. It searches the landscape, clusters what exists, benchmarks your angle against prior art, and delivers a direct verdict: build, fork, contribute, use what's out there, or investigate why someone else gave up.

## Installation

### Claude Code

Clone directly into Claude Code's skills directory:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/iagochavarry/who-built-this-before-me.git ~/.claude/skills/who-built-this-before-me
```

Or copy the skill file manually if you already have this repo cloned:

```bash
mkdir -p ~/.claude/skills/who-built-this-before-me
cp SKILL.md ~/.claude/skills/who-built-this-before-me/
```

### OpenCode

Clone directly into OpenCode's skills directory:

```bash
mkdir -p ~/.config/opencode/skills
git clone https://github.com/iagochavarry/who-built-this-before-me.git ~/.config/opencode/skills/who-built-this-before-me
```

Or copy the skill file manually if you already have this repo cloned:

```bash
mkdir -p ~/.config/opencode/skills/who-built-this-before-me
cp SKILL.md ~/.config/opencode/skills/who-built-this-before-me/
```

Note: OpenCode also scans `~/.claude/skills/` for compatibility, so a single clone into `~/.claude/skills/who-built-this-before-me/` works for both tools.

## Usage

### Claude Code

```
/who-built-this-before-me

I'm thinking of building [your idea here]
```

### OpenCode

```
/who-built-this-before-me

I'm thinking of building [your idea here]
```

Or just describe the idea directly in either tool — the skill triggers on phrases like "I want to build…", "I'm thinking of making…", "should I build X…", or "is there already a…":

```
I want to build a CLI that auto-generates database migrations from OpenAPI schemas. Has anyone done this?
```

## What you get back

A one-screen report with these sections:

- **The idea, restated** — your pitch stripped to one sentence, so you can confirm the search is targeting the right thing.
- **The landscape** — a table of direct matches, adjacent solutions, partial solutions, and abandoned projects (max 3 per bucket).
- **Standard patterns** — what shows up repeatedly across the matches: architecture, libraries, pricing, naming conventions. The default playbook you'd be competing with or building on.
- **Differentiator analysis** — an honest paragraph on whether your angle is actually different, or whether the novelty is manufactured.
- **Verdict** — one of: **Build it**, **Fork X**, **Contribute to Y**, **Use Z**, or **Investigate first**, plus the concrete next step.

## Sharpening the input

The more specific your pitch, the sharper the search. Compare:

Vague — the skill will ask one clarifying question before searching:

```
/who-built-this-before-me

I want to build a dev tool.
```

Specific — the skill goes straight to searching:

```
/who-built-this-before-me

I want to build a CLI that reads an OpenAPI spec and emits reversible Postgres migrations, with rollback safety checks. Target users: backend engineers on API-first teams who don't want to hand-write SQL migrations.
```

If the idea is distinctive because of a constraint (offline-first, on-device, self-hosted, specific regulatory regime, a language nobody supports well), say so in the pitch. That constraint is usually where the real gap — or the real incumbent you didn't know about — lives.
