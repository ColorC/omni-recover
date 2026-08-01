# omni-recover

[![CI](https://github.com/ColorC/omni-recover/actions/workflows/ci.yml/badge.svg)](https://github.com/ColorC/omni-recover/actions/workflows/ci.yml)

`omni-recover` reconstructs missing workspace files from byte evidence already
recorded by AI coding sessions. The alpha release understands Codex, Claude
Code, Kimi Code and OpenCode, and exposes extension points for other providers.

It is deliberately conservative: it restores exact bytes only when the
timeline and path evidence support them, never replays historical shell
commands, and never overwrites an existing file by default.

## Install

Python 3.10 or newer is required.

```bash
git clone https://github.com/ColorC/omni-recover.git
cd omni-recover
python -m pip install .
omni-recover providers
```

For isolated CLI installation, use `pipx install .` from a checkout or install
the wheel attached to a GitHub prerelease.

## Recovery workflow

Start read-only and keep every generated artifact outside the damaged
workspace:

```powershell
omni-recover providers
omni-recover index build --source codex=C:\path\to\sessions --out recovered-index
omni-recover plan --index recovered-index --workspace-root C:\workspace --out plan.json
omni-recover snapshot create --plan plan.json --out preapply-snapshot
omni-recover apply --plan plan.json --snapshot preapply-snapshot --confirm-workspace C:\workspace
```

`apply` is still a dry run until `--apply` is supplied. Inspect the plan first.
Only missing files and quarantined pathless artifacts are writable in this
alpha. Existing files, deletes, moves, conflicting reads and ambiguous
candidates remain review items. Use `omni-recover rollback` with the generated
journal to remove files created by an apply run.

## What counts as recoverable

The evidence model distinguishes mutation post-images, proved command
post-images, exact reads, exact attachments, derived artifacts and intent-only
records. A later write outranks an older read; a disagreeing later read blocks
read fallback. Images and other binary files are preserved as bytes when the
session contains exact content and path evidence. Screenshots, OCR and previews
remain derivatives and cannot silently replace an original.

See the [unified evidence contract](docs/UNIFIED-EVIDENCE-CONTRACT.md) and the
[live CLI recovery contract](docs/LIVE-CLI-RECOVERY-CONTRACT-2026-08-01.md).

## Extend another provider

Simple archive locations can be added with JSON manifests under
`config/recovery/providers.d`. Parsers register a read-only `ProviderAdapter`
factory through the `omni_recover.providers` Python entry-point group. An
adapter must emit normalized evidence; it never writes into the target
workspace. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Release quality

`python scripts/release_gate.py` runs the public-source allowlist checks,
credential and private-path scan, manifest verification, Markdown link scan,
Ruff, tests, compilation, two reproducible package builds and a clean-venv CLI
smoke test. The same gate runs on GitHub Actions.

## Safety

Session transcripts and recovery indexes can contain source code, prompts,
local paths, tool output and credentials. `omni-recover` does not encrypt them.
Store them on access-controlled encrypted storage and never publish an archive
or index without reviewing it. See [SECURITY.md](SECURITY.md).

This is alpha incident-recovery software, not a substitute for version control
or backups. Always restore into a disposable workspace first and run the
project's own semantic probes before accepting a result.
