# Knowledge Sources

**Contents:** [Official IBM documentation](#official-ibm-documentation) · [Local CLI help](#local-cli-help) · [Licensed manuals](#licensed-manuals) · [Ingest commands](#ingest-commands)

This is the source checklist for the phase-2 knowledge corpus. It records where to obtain reference material; it does not redistribute IBM manual text or site-specific Synergy output.

## Official IBM documentation

IBM Docs exposes the Rational Synergy 7.2.0 documentation set here:

| Source | URL | Corpus use |
|---|---|---|
| Documentation landing page | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=rational-synergy-v720-documentation> | Start page for online manual extraction |
| Overview | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=overview> | `manual` |
| Installing | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=installing> | `manual` |
| Administering | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=administering> | `manual` |
| Managing change and releases | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=managing-change-releases> | `manual`, `query` |
| Troubleshooting and support | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=troubleshooting-support> | `manual` |
| Reference | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=reference> | `manual`, `query` |
| Glossary | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=glossary> | `manual` |
| Using the help | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?topic=using-help> | `manual` |
| Announcements and sales manuals | <https://www.ibm.com/docs/en/rational-synergy/7.2.0?announcement=all> | release/background metadata |

Related IBM access points:

| Source | URL | Use |
|---|---|---|
| IBM Support Portal | <https://www.ibm.com/support/entry/portal/support> | Entitled support notes and technotes |
| IBM Fix Central | <https://www.ibm.com/support/fixcentral> | Fix packs and release-note trail |
| IBM Passport Advantage | <https://www.ibm.com/software/passportadvantage/> | Entitled software and media downloads |

## Local CLI help

The most authoritative source for command syntax is the installed client at the site:

```bash
ccm version
ccm help
ccm help query
ccm help task
ccm help project_grouping
```

The harvest command captures `ccm help` plus all read-only verbs in the policy allowlist by default. Use `--verb` for a smaller targeted harvest.

## Licensed manuals

Product PDFs and offline manuals are IBM-licensed material. Keep source PDFs out of git, extract them locally to markdown or text, then ingest the extracted files. Commit extracted markdown only when redistribution rights are clear; otherwise keep it as a local harvest under `synergy-mcp-server/manuals/` and commit the source link, provenance and ingest procedure instead.

## Ingest commands

Run from the repo root:

```bash
py -m synergy_mcp.knowledge_cli harvest-cli --database prod-core --ccm-binary ccm
py -m synergy_mcp.knowledge_cli ingest-manual path/to/extracted/manuals --doc-id rational-synergy-72 --title "IBM Rational Synergy 7.2 manuals"
py -m synergy_mcp.knowledge_cli build
py -m synergy_mcp.knowledge_cli search "ccm query -u"
```

When installed from `synergy-mcp/`, the same commands are available as `synergy-knowledge harvest-cli`, `synergy-knowledge ingest-manual`, `synergy-knowledge build` and `synergy-knowledge search`.