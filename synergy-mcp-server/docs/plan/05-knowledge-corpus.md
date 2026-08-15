# 05 — Knowledge Corpus

**Status:** proposed · **Phase:** 2

**Contents:** [Context](#context) · [Decision](#decision) · [Rejected alternatives](#rejected-alternatives) · [Consequences](#consequences)

## Context

Synergy 7.2 shipped around 2012 and is long out of general circulation. A model's parametric knowledge of it is thin, dated and — worse — confidently wrong in places, because it interpolates from Git and from newer tools. Flag spellings on `ccm task`, `ccm folder` and `ccm baseline` are exactly the kind of detail that gets hallucinated.

The authoritative sources are the installed client's own help output and the product manuals. Both are available at the site and neither is in the model's weights.

## Decision

Build a **searchable corpus** from four sources, governed by [corpus-contract.md](../corpus-contract.md):

| Corpus | Source | Why |
|---|---|---|
| `cli` | `ccm help`, `ccm help <verb>` harvested from the live client | Ground truth for *this* installation, including site customisations |
| `manual` | Rational Synergy 7.2 PDF documentation | Concepts, procedures, limits |
| `query` | Manual chapter plus curated recipes | The highest-value, hardest-to-guess surface |
| `release-notes` | IBM release notes and fix lists | Behaviour that changed within 7.x |

Extracted markdown is committed; source PDFs are not. The FTS5 index at `build/synergy-knowledge.sqlite` is a rebuildable artefact and is gitignored.

Exposed in phase 2 as a `knowledge` group: `knowledge_search(query, corpus=None, family=None, limit=10)`, returning chunks with `doc_id`, heading path, source version and trust marking so answers are citable.

The CLI harvest is the first deliverable, because it is cheap, it is the most authoritative, and it directly retires the largest source of error.

## Rejected alternatives

**Relying on the model's own knowledge of Synergy.** This is the status quo and it is why the corpus is needed. Guessed flag spellings on a system of record are not acceptable even in read-only mode — a wrong flag usually errors, but a *plausible wrong* flag can silently answer a different question.

**Embedding the manual text directly in skills.** Blows the context budget and cannot be searched. Skills are operating instructions; bulk reference belongs in a corpus fetched on demand.

**Vector embeddings.** Rejected for now. FTS5 with a porter tokenizer handles the vocabulary well — this is a small, jargon-dense, well-structured corpus where exact terms (`hierarchy_project_members`, `cvtype`) matter more than semantic similarity, and it adds no runtime dependency or model call. Revisit if recall proves inadequate.

**Shipping a pre-built corpus in the repo.** The manuals are licensed material and the CLI harvest is site-specific. Ingestion runs at the site, from the site's own artefacts.

## Consequences

- Phase 2 requires a live 7.2 client for the harvest, so it cannot be done from a laptop with no Synergy access.
- The corpus is site-specific by design, which means it cannot be validated centrally. `scripts/forge_validate.py` enforces the schema; correctness of the content is the site's own harvest.
- Adds a `knowledge` group and therefore tool-schema cost. It stays out of `lean` until it earns its place.
- Once the CLI harvest exists, the `synergy-knowledge-corpus` skill can stay focused on lookup and citation, because the authoritative text is retrievable.
