#!/usr/bin/env python3
"""Positive-only public release gate for omni-recover."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "PUBLIC-ASSEMBLY-MANIFEST.json"
POLICY_VERSION = "omni-recover-public-2026-08-01.1"
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist"}
FORBIDDEN_PARTS = {
    ".claude",
    ".codex",
    ".env",
    ".omni",
    "archives",
    "artifacts",
    "evidence-index",
    "logs",
    "output",
    "sandbox",
    "sessions",
}
TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
PRIVATE_TERMS = (
    "lilith" + "games",
    "lilith" + "game.com",
    "haowen" + "zhou",
    "Color" + "Zhou",
)
LOCAL_ROOT = re.compile(r"(?i)(?:[A-Z]:[\\/](?:Users|WindowsWorkspace|P4)[\\/])")
MARKDOWN_LINK = re.compile(r"\[[^]]*\]\(([^)]+)\)")


def public_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path == MANIFEST or path.name == "release-gate-report.json":
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_payload() -> dict[str, object]:
    return {
        "schema": "omni-recover-public-assembly.v1",
        "policy_version": POLICY_VERSION,
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in public_files()
        ],
    }


def check_manifest(*, write: bool) -> list[str]:
    payload = manifest_payload()
    if write:
        MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return []
    if not MANIFEST.is_file():
        return ["PUBLIC-ASSEMBLY-MANIFEST.json is missing"]
    current = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [] if current == payload else ["PUBLIC-ASSEMBLY-MANIFEST.json is stale"]


def scan_public_tree() -> list[str]:
    findings: list[str] = []
    for path in public_files():
        rel = path.relative_to(ROOT)
        if any(part.lower() in FORBIDDEN_PARTS for part in rel.parts):
            findings.append(f"forbidden path: {rel.as_posix()}")
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE", ".gitignore"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"non-UTF-8 public text: {rel.as_posix()}")
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                findings.append(f"credential-shaped value: {rel.as_posix()}:{line_no}")
            if any(term.lower() in line.lower() for term in PRIVATE_TERMS):
                findings.append(f"private identity term: {rel.as_posix()}:{line_no}")
            if LOCAL_ROOT.search(line):
                findings.append(f"machine-specific path: {rel.as_posix()}:{line_no}")
    return findings


def scan_markdown_links() -> list[str]:
    findings: list[str] = []
    for path in public_files():
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            candidate = (path.parent / target).resolve()
            try:
                candidate.relative_to(ROOT)
            except ValueError:
                findings.append(f"escaping Markdown link: {path.relative_to(ROOT)} -> {target}")
                continue
            if not candidate.exists():
                findings.append(f"dead Markdown link: {path.relative_to(ROOT)} -> {target}")
    return findings


def run(command: Iterable[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    rendered = [str(part) for part in command]
    print("+", " ".join(rendered))
    subprocess.run(rendered, cwd=cwd, env=env, check=True)


def build_and_smoke() -> dict[str, str]:
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = "1704067200"
    with tempfile.TemporaryDirectory(prefix="omni-recover-release-") as temp:
        temp_root = Path(temp)
        first = temp_root / "first"
        second = temp_root / "second"
        build_command = [sys.executable, "-m", "build", "--no-isolation", "--sdist", "--wheel"]
        run([*build_command, "--outdir", first], env=env)
        run([*build_command, "--outdir", second], env=env)
        first_hashes = {path.name: sha256(path) for path in first.iterdir()}
        second_hashes = {path.name: sha256(path) for path in second.iterdir()}
        if first_hashes != second_hashes:
            raise RuntimeError(f"package builds are not reproducible: {first_hashes} != {second_hashes}")
        wheel = next(first.glob("*.whl"))
        clean_env = temp_root / "clean-venv"
        try:
            run([sys.executable, "-m", "venv", clean_env])
        except subprocess.CalledProcessError:
            run([sys.executable, "-m", "virtualenv", clean_env])
        python = clean_env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = clean_env / ("Scripts/omni-recover.exe" if os.name == "nt" else "bin/omni-recover")
        run([python, "-m", "pip", "install", "--disable-pip-version-check", wheel])
        run([cli, "providers"])
        run([cli, "--help"])
        return first_hashes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    checks: dict[str, object] = {}
    findings = scan_public_tree()
    checks["public_tree_scan"] = {"ok": not findings, "findings": findings}
    links = scan_markdown_links()
    checks["markdown_links"] = {"ok": not links, "findings": links}
    manifest_findings = check_manifest(write=args.write_manifest)
    checks["manifest"] = {"ok": not manifest_findings, "findings": manifest_findings}

    failed = bool(findings or links or manifest_findings)
    try:
        run([sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"])
        checks["compileall"] = {"ok": True}
        if not args.skip_tests:
            run([sys.executable, "-m", "ruff", "check", ".", "--no-cache"])
            run([sys.executable, "-m", "pytest", "-q"])
            checks["tests"] = {"ok": True}
        if not args.skip_build:
            checks["reproducible_build"] = {"ok": True, "sha256": build_and_smoke()}
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        checks["runtime_failure"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        failed = True

    report = {"schema": "omni-recover-release-gate.v1", "ok": not failed, "checks": checks}
    report_path = args.report
    if report_path:
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
