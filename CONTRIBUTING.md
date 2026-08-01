# Contributing

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python scripts/release_gate.py
```
## Provider adapters

Keep provider discovery read-only. A provider adapter converts native session
records into normalized evidence and must not mutate the recovered workspace.
Add fixture coverage for exact text, empty files, binary bytes, ordering,
conflicting reads, delete/move intent and malformed input. Third-party packages
should expose a factory in the `omni_recover.providers` entry-point group.

## Safety invariants

- Never replay shell or PowerShell commands from a transcript.
- Never let an exact read supersede a later mutation.
- Never promote OCR, preview or screenshot bytes to an exact original.
- Never overwrite a present file during the alpha apply flow.
- Keep snapshot, journal, rollback and path-containment tests green.

After an intentional source change, regenerate the positive-only manifest:

```bash
python scripts/release_gate.py --write-manifest --skip-tests --skip-build
python scripts/release_gate.py
```
