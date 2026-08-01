from __future__ import annotations

from omnicompany.packages.services.recovery.entrypoint import _legacy_cli
from omnicompany.packages.services.recovery.providers import default_registry


def test_builtin_provider_registry_is_available() -> None:
    assert set(default_registry().definitions) >= {
        "codex",
        "claude",
        "kimi",
        "opencode",
    }


def test_wheel_legacy_cli_is_embedded() -> None:
    assert callable(_legacy_cli().main)
