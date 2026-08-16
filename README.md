# synergy-ccm-mcp

Give an AI agent safe, read-only access to a decade of engineering history locked in **IBM Rational Synergy 7.2**.

**Contents:** [What this is](#what-this-is) · [Why](#why) · [Status](#status) · [Install](#install) · [Configure](#configure) · [Use](#use) · [Knowledge corpus](#knowledge-corpus) · [Safety](#safety) · [Documentation](#documentation) · [Compatibility](#compatibility) · [Contributing](#contributing) · [License](#license)

## What this is

An [MCP](https://modelcontextprotocol.io) server and a set of agent skills that expose a Rational Synergy database through its `ccm` command-line client.

It lets an AI assistant answer questions such as:

- Who changed `parser.c`, and what else changed with it?
- What is in release `product/2.0`, and which tasks are still open?
- What is the difference between these two baselines?
- Show me version 7 of this file — without checking anything out.

## Why

Synergy 7.2 shipped around 2012. Sites still running it hold years of engineering history in a system that has no modern query interface, no REST API worth using, and a shrinking pool of people who remember the CLI. The data is valuable and effectively unreachable.

This toolkit makes it reachable, without letting an agent anywhere near a write operation.

## Status

**Phase 1 — read-only.** Actively being built, with local stdio installers for VS Code Copilot and Claude Desktop MCPB.

| Phase | Content | Status |
|---|---|---|
| 1 | Read-only: query, object, task, project tool groups | in progress |
| 2 | Knowledge corpus from harvested `ccm help` + manuals | initial support built |
| 3 | Task-management writes behind a staged-commit flow | designed |
| 4 | Checkout/checkin, work areas | not scheduled |

## Install

Requires Python ≥ 3.10 and a Synergy 7.2 `ccm` client **on the same host**.

Start with [INSTALL.md](INSTALL.md) or [INSTALL.html](INSTALL.html), then choose the client target:

| Target | Guide |
|---|---|
| VS Code Copilot local stdio | [INSTALL-vscode-copilot-stdio.md](INSTALL-vscode-copilot-stdio.md) · [HTML](INSTALL-vscode-copilot-stdio.html) |
| Claude Desktop MCPB | [INSTALL-claude-desktop-mcpb.md](INSTALL-claude-desktop-mcpb.md) · [HTML](INSTALL-claude-desktop-mcpb.html) |

Prepare the local MCP server from the repo root:

```bash
bash ./synergy-mcp-server/scripts/install/mcp_server/install-stdio-mcp-server.sh
```

Windows PowerShell:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\synergy-mcp-server\scripts\install\mcp_server\install-stdio-mcp-server.ps1
```

## Configure

The installer creates `synergy-mcp/inventory.yaml` from `synergy-mcp/inventory.example.yaml` if needed. Describe your databases there — **facts only, never credentials**:

```yaml
databases:
  - name: prod-core
    database: /opt/ccm/db/core
    host: buildhost
    server_url: http://buildhost:8400
    role: developer
    groups: [production]
```

Then either set one MCP-level identity in the environment that launches the MCP server:

```powershell
$env:SYNERGY_MCP_USER = "your-name"
$env:SYNERGY_MCP_PASSWORD = "your-password"
```

Linux bash:

```bash
export SYNERGY_MCP_USER="your-name"
export SYNERGY_MCP_PASSWORD="your-password"
```

Every client using this MCP server will access Synergy through that same account. Use a read-only Synergy account for the phase 1 `query`, `object`, `task` and `project` tool groups. Per-database `SYNERGY_<DB>_USER` and `SYNERGY_<DB>_PASSWORD` variables are still supported when one database needs a different identity.

…or, preferably, use **attach mode** so the server never handles a password:

```bash
ccm start -m -q -nogui -d /opt/ccm/db/core -s http://buildhost:8400 -r developer -n your-name
export SYNERGY_PROD_CORE_CCM_ADDR=buildhost:1234:10.0.0.5
```

Full setup: [INSTALL.md](INSTALL.md) and [docs/connecting-local-mcp.md](synergy-mcp-server/docs/connecting-local-mcp.md).

## Use

```
health_check(database="prod-core")
ccm_query(database="prod-core", expression="cvtype='task' and release='product/2.0'")
task_objects(database="prod-core", task="4711")
object_content(database="prod-core", object_name="parser.c-7:csrc:1")
```

More: [docs/examples.md](synergy-mcp-server/docs/examples.md) · [docs/workflows.md](synergy-mcp-server/docs/workflows.md)

New to Synergy's object model? Start with [docs/CONCEPTS.md](synergy-mcp-server/docs/CONCEPTS.md) — it is not Git, and assuming otherwise produces wrong answers.

## Knowledge corpus

The toolkit can build a local searchable corpus from two kinds of reference material:

- harvested `ccm help` output from the site's own Synergy client
- locally downloaded or extracted IBM/manual documentation that the site is entitled to use

Build and search the corpus from the repo root:

```powershell
$env:PYTHONPATH = "synergy-mcp/src"
py -m synergy_mcp.knowledge_cli harvest-cli --database prod-core --ccm-binary ccm
py -m synergy_mcp.knowledge_cli ingest-manual path\to\extracted\manuals --doc-id rational-synergy-72 --title "IBM Rational Synergy 7.2 manuals"
py -m synergy_mcp.knowledge_cli build
py -m synergy_mcp.knowledge_cli search "ccm query -u"
```

Source PDFs and vendor manual text are local harvest artefacts by default; the repository records source links and ingest procedure, not redistributed IBM documentation text. See [docs/knowledge-sources.md](synergy-mcp-server/docs/knowledge-sources.md) and [manuals/README.md](synergy-mcp-server/manuals/README.md).

## Safety

A Synergy database is often the only copy of a site's engineering history. The design assumes that and is deliberately conservative:

- **Read-only.** Mutating verbs are rejected by the policy layer, not merely unimplemented.
- **Allowlisted verbs**, matched by exact string equality. Fails closed.
- **Permanent denylist** — `delete`, `purge`, `archive`, `migrate`, `db`, `dcm`, `typedef`, `users` are unreachable by any configuration.
- **Mutating sub-flags** (`-create`, `-modify`, `-complete`, …) rejected on otherwise-read verbs.
- **No shell.** All execution is `subprocess.run(argv, shell=False)`.
- **Untrusted-output boundary.** Source code, check-in comments and task synopses are attacker-influenced text. Everything the database returns is wrapped at one seam and treated as data, never instructions.
- **Pooled sessions** so the server does not burn licence seats.
- **Append-only audit log** with secrets redacted.

The contract is [docs/ccm-contract.md](synergy-mcp-server/docs/ccm-contract.md), and it is enforced in code.

## Documentation

Start at [docs/README.md](synergy-mcp-server/docs/README.md).

| | |
|---|---|
| [CONCEPTS.md](synergy-mcp-server/docs/CONCEPTS.md) | Synergy's object model for people who know Git |
| [architecture.md](synergy-mcp-server/docs/architecture.md) | Stack, layout, session model, safety invariants |
| [mcp-capabilities.md](synergy-mcp-server/docs/mcp-capabilities.md) | Every tool, resource and prompt |
| [ccm-contract.md](synergy-mcp-server/docs/ccm-contract.md) | The safety contract |
| [INSTALL.md](INSTALL.md) | Install scripts and client target routing |
| [INSTALL.html](INSTALL.html) | Browser-friendly install guide with copy buttons |
| [knowledge-sources.md](synergy-mcp-server/docs/knowledge-sources.md) | IBM Docs links and local corpus ingest sources |
| [examples.md](synergy-mcp-server/docs/examples.md) | What users can ask from Synergy |
| [skills/](synergy-mcp-server/skills) | Served-only runtime/domain skills exposed as `synergy://skills` resources |
| [plan/](synergy-mcp-server/docs/plan/README.md) | Design decisions and rejected alternatives |

## Compatibility

| Synergy version | Status |
|---|---|
| 7.2, 7.2.1 | Supported — the target |
| 7.1, 7.1a | Expected to work; unverified |
| 7.0 | Unverified |
| 6.5 and earlier (Telelogic / CM Synergy) | Object model matches, CLI flags differ; needs its own driver |

The stable surface is the query language and the four-part object name. The volatile surface is flag spelling on `task`, `folder` and `baseline`.

## Contributing

Safety-critical paths are enumerated in [synergy_core/safety.py](synergy-mcp-server/packages/synergy-core/synergy_core/safety.py) and require two reviewers plus an eval case. Everything else takes one. See [docs/plan/09-contribution-model.md](synergy-mcp-server/docs/plan/09-contribution-model.md).

## License

[Apache-2.0](LICENSE).

Not affiliated with or endorsed by IBM. "Rational Synergy" is a trademark of its respective owner and is used here descriptively.
