# pyright: reportMissingImports=false

from __future__ import annotations

from voicelink.platform_utils import DriverStatus


def test_setup_installed_and_virtual_mic_ready(invoke_cli, monkeypatch):
    monkeypatch.setattr(
        "voicelink.cli.get_system_info",
        lambda: {
            "platform": "darwin",
            "system": "Darwin",
            "release": "24.0.0",
            "machine": "arm64",
            "python_version": "3.12.0 (main, ...)\n",
        },
    )

    monkeypatch.setattr(
        "voicelink.cli.setup_driver",
        lambda auto_install: DriverStatus(
            installed=True,
            driver_name="BlackHole",
            device_name="BlackHole 2ch",
            install_instructions=None,
        ),
    )

    monkeypatch.setattr(
        "voicelink.cli.check_virtual_mic_ready",
        lambda: {
            "ready": True,
            "loopback_device": "[7] BlackHole 2ch (input, loopback, virtual)",
            "virtual_output_device": None,
        },
    )

    result = invoke_cli(["setup"])
    assert result.exit_code == 0
    assert "[OK] BlackHole is installed" in result.output
    assert "[OK] Virtual microphone is ready" in result.output


def test_setup_missing_driver_prints_instructions(invoke_cli, monkeypatch):
    monkeypatch.setattr(
        "voicelink.cli.get_system_info",
        lambda: {
            "platform": "darwin",
            "system": "Darwin",
            "release": "24.0.0",
            "machine": "arm64",
            "python_version": "3.12.0 (main, ...)\n",
        },
    )

    monkeypatch.setattr(
        "voicelink.cli.setup_driver",
        lambda auto_install: DriverStatus(
            installed=False,
            driver_name="BlackHole",
            device_name=None,
            install_instructions="Install BlackHole using Homebrew:\n  brew install blackhole-2ch",
        ),
    )

    result = invoke_cli(["setup"])
    assert result.exit_code == 0
    assert "[MISSING] BlackHole" in result.output
    assert "brew install blackhole-2ch" in result.output
