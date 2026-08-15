# 06 — MCP Prompts and Slash Commands

**Status:** accepted · **Phase:** 1

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

The valuable workflows in Synergy are multi-step and non-obvious. "Who changed this file" is five calls and requires knowing that the answer is a *task* question, not a file question. Left to itself the model will do a plausible three-call version and produce a half-answer.

These workflows need to be available in two places: as MCP **prompts** (portable, any client) and as **slash commands** (native to Claude Code). Two copies of the same procedure will drift.

## Decision

**One definition, two surfaces.** Workflow bodies live in `synergy_core/prompts.py`. The MCP prompt registration imports them; `commands/*.md` reference the same workflow and carry only the invocation frontmatter.

| Prompt | Command | Workflow |
|---|---|---|
| `synergy_health` | `/synergy-health` | Session, version, delimiter |
| `synergy_who_changed` | `/synergy-who-changed` | File → history → task → author → sibling objects |
| `synergy_task_audit` | `/synergy-task-audit` | Tasks for a release, with completeness check |
| `synergy_baseline_diff` | `/synergy-baseline-diff` | Compare two baselines by task set |

Command frontmatter is minimal — description and argument hint only:

```yaml
---
description: Trace who changed a file and what else changed with it
argument-hint: <database> <file-name>
---
```

`scripts/check_skill_sync.py` fails CI if a command references a workflow that no longer exists, or if the prompt and command descriptions diverge.

## Rejected alternatives

**Prompts only.** Slash commands are how the primary users actually work; dropping them would mean the workflows go unused.

**Commands only.** Non-Claude clients get nothing, and the workflows are the main mechanism for encoding domain judgement.

**Encoding workflows in skills instead.** Skills say *how to think*; prompts are *invocable procedures* with arguments. `synergy-core` does carry the short version of `who_changed` because it is needed so often, but a five-step parameterised procedure belongs in a prompt.

**Server-side orchestration** — one `who_changed(file)` tool that internally makes five `ccm` calls. Rejected: it hides the reasoning, returns an opaque blob, and cannot adapt when step 2 returns something unexpected. The model should see each result and decide. Prompts guide; they do not automate.

## Consequences

- `synergy_core/prompts.py` is a shared dependency of the server and the command files, so it stays in the core package rather than in a capability package.
- Adding a workflow means touching three places (prompt body, prompt registration, command file). The sync check makes drift a build failure rather than a discovery six months later.
- Prompt bodies are prose instructions to the model, so they are subject to the same review standard as skills: imperative, specific, and honest about what the tools cannot do.
