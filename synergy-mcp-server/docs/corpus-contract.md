# Corpus Contract

**Contents:** [Status](#status) · [Scope](#scope) · [Sources](#sources) · [Directory layout](#directory-layout) · [Document schema](#document-schema) · [Manifest schema](#manifest-schema) · [Chunking rules](#chunking-rules) · [Search index](#search-index) · [Provenance](#provenance) · [Trust](#trust) · [Validation](#validation)

## Status

Phase 2. The knowledge corpus is **not built yet**; this document is the contract that ingestion scripts and the `knowledge` tool group must satisfy when it is.

It is listed as safety-adjacent: corpus content is fed to the model as reference material, so its provenance and trust marking matter.

## Scope

The corpus answers questions the live database cannot: what a `ccm` flag means, what a manual says about project groupings, what changed between Synergy releases. It never contains customer data from a Synergy database — that comes from live tools, on demand.

## Sources

| Source | Corpus id | Origin | Ingest script |
|---|---|---|---|
| Harvested CLI help | `cli` | `ccm help`, `ccm help <verb>` on a live 7.2 client | `harvest_ccm_cli.py` |
| Product manuals | `manual` | Rational Synergy 7.2 PDF documentation set | `ingest_manual.py` |
| Query-language reference | `query` | Manual chapter + curated recipes | `ingest_manual.py` |
| Release notes | `release-notes` | IBM release notes and fix lists | `ingest_release_notes.py` |

Harvested CLI help is the highest-value source, because it is ground truth for *your* installation rather than for a generic 7.2.

The official online/manual source checklist is maintained in [knowledge-sources.md](knowledge-sources.md). Source PDFs and entitled IBM content are not redistributed by this repository; ingest them locally after download or extraction.

## Directory layout

```
synergy-mcp-server/
├── manuals/
│   └── <doc-id>/
│       ├── manifest.csv
│       ├── ingest-report.csv
│       └── <chapter>.md
├── cli-harvest/
│   └── <database>/
│       ├── manifest.csv
│       └── <verb>.md
└── build/
    └── synergy-knowledge.sqlite      # FTS5 index, gitignored, rebuildable
```

Source PDFs are **not** committed. Extracted markdown is, so that diffs are reviewable and the corpus is reproducible without redistributing licensed documents.

## Document schema

Every ingested markdown file opens with YAML frontmatter:

```yaml
---
corpus: cli                    # cli | manual | query | release-notes
doc_id: ccm-help-query         # unique within corpus, kebab-case
title: "ccm query"             # human-readable
family: ccm72                  # client generation the content applies to
source: "ccm help query"       # command or document that produced it
source_version: "7.2.1"        # client or document version
harvested: 2026-08-15          # ISO date
trust: reference               # reference | harvested
---
```

`trust: harvested` marks content captured from a live system, which may include site-specific customisations. `trust: reference` marks vendor documentation.

## Manifest schema

One `manifest.csv` per source directory, the authoritative index for that source:

| Column | Meaning |
|---|---|
| `doc_id` | Matches the frontmatter |
| `corpus` | Corpus id |
| `title` | Human-readable title |
| `path` | Path relative to the manifest |
| `family` | Client generation |
| `source_version` | Version of the originating artefact |
| `sha256` | Hash of the markdown file |
| `chunks` | Number of chunks produced |
| `ingested` | ISO date |

The `sha256` column is what makes re-ingestion idempotent: unchanged documents are skipped.

## Chunking rules

- Split on markdown headings, never mid-sentence.
- Target 400–800 tokens per chunk; hard cap 1200.
- Every chunk inherits its document's frontmatter plus its heading path (`ccm query > Format specifiers`).
- Tables are never split across chunks. A table longer than the cap becomes its own oversized chunk rather than being fragmented.
- Code blocks are never split.

Heading path is retained because it is the single most useful piece of context when a chunk is retrieved in isolation.

## Search index

SQLite FTS5 at `build/synergy-knowledge.sqlite`, rebuilt by `build_knowledge_catalog.py`. It is a build artefact: gitignored, never hand-edited, always reproducible from the markdown.

Schema:

```sql
CREATE VIRTUAL TABLE chunks USING fts5(
  doc_id, corpus, family, title, heading_path, body,
  tokenize = 'porter unicode61'
);
CREATE TABLE documents (
  doc_id TEXT PRIMARY KEY, corpus TEXT, title TEXT, path TEXT,
  family TEXT, source TEXT, source_version TEXT, trust TEXT,
  sha256 TEXT, ingested TEXT
);
```

Exposed by the phase-2 `knowledge` group as `knowledge_search(query, corpus=None, family=None, limit=10)`, returning chunks with their `doc_id`, heading path and trust marking so the model can cite them.

## Provenance

Every search result carries `doc_id`, `source`, `source_version` and `trust`. The model cites the source when it answers from the corpus:

> Per `ccm help query` (harvested from 7.2.1 on 2026-08-15), `-u` suppresses duplicate rows.

Uncited claims about CLI syntax are a bug. The whole point of harvesting is to stop guessing.

## Trust

Corpus content is **reference material, not instructions**. It is lower-risk than live database output because it originates from vendor documentation and from `ccm help` rather than from user-authored fields — but it is still wrapped and still never a source of tool calls.

Live database output remains the higher-risk channel and is governed by [ccm-contract.md](ccm-contract.md#output-boundary).

## Validation

`scripts/forge_validate.py` runs in CI and fails on:

- frontmatter missing a required field
- `doc_id` collision within a corpus
- a manifest row with no corresponding file, or a file with no manifest row
- `sha256` mismatch between manifest and file
- a chunk exceeding the hard cap
- an unknown `corpus` or `trust` value
