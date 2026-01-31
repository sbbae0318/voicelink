# pyright: ignore

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest
from click.testing import CliRunner


def _install_sounddevice_stub() -> None:
    """Provide a minimal `sounddevice` module for test environments.

    The production package depends on `sounddevice`, but some CI/dev
    environments running these tests may not have the native dependency
    available. Our CLI/E2E-style tests mock higher-level seams, so a tiny
    stub is sufficient to allow imports.
    """

    sd = types.ModuleType("sounddevice")

    class _Default:
        device = (None, None)

    def query_devices():
        return []

    class CallbackFlags:
        def __str__(self) -> str:  # pragma: no cover
            return ""

    class InputStream:
        def __init__(self, *args: Any, **kwargs: Any):
            self._callback = kwargs.get("callback")

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

        def close(self) -> None:
            return None

    class Stream(InputStream):
        pass

    setattr(sd, "default", _Default())
    setattr(sd, "query_devices", query_devices)
    setattr(sd, "InputStream", InputStream)
    setattr(sd, "Stream", Stream)
    setattr(sd, "CallbackFlags", CallbackFlags)

    # Always stub for test determinism, even if `sounddevice` is installed.
    sys.modules["sounddevice"] = sd


_install_sounddevice_stub()


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def invoke_cli(runner: CliRunner) -> Callable[[list[str], dict[str, Any] | None], Any]:
    from voicelink.cli import main

    def _invoke(args: list[str], env: dict[str, Any] | None = None):
        return runner.invoke(main, args, env=env, color=False)

    return _invoke


@dataclass(frozen=True)
class CallCapture:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]]

    def record(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((args, kwargs))


@pytest.fixture()
def call_capture() -> CallCapture:
    return CallCapture(calls=[])
