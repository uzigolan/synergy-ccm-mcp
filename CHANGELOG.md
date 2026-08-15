# Changelog

**Contents:** [Unreleased](#unreleased) · [Conventions](#conventions)

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Phase 1, read-only. Not yet released.

### Added

- Design documentation set under `synergy-mcp-server/docs/`, including the
  canonical architecture, the `ccm` safety contract, Synergy domain concepts,
  workflows, examples, performance notes and skills routing.
- Decision records `00`–`09` under `docs/plan/`, covering the read-only
  baseline, capability grouping, the untrusted-output boundary, session
  pooling, query as the primary tool surface, the knowledge corpus, prompts,
  the deferred write phase, package decomposition and the contribution model.
- `tool_profile.config.json` defining the `lean` and `legacy` profiles and the
  capability group flags.
- `synergy_core.safety` manifest of safety-critical paths.
- `synergy_core.paths` filesystem root resolution.
- Apache-2.0 license, `.gitignore` and project README.

### Notes

- No tools are registered yet; the package layout described in the docs is
  still being implemented.
- Target platform is IBM Rational Synergy 7.2 on Linux/UNIX, with the `ccm`
  client co-located with the server.

## Conventions

- `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`.
- A change to a safety-critical path is always listed under `Security`,
  regardless of how small it looks.
- Package versions move together; skills version independently and are not
  listed here. See `docs/VERSIONS.md`.
