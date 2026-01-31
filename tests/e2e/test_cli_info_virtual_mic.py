# pyright: reportMissingImports=false

from __future__ import annotations

from voicelink.platform_utils import DriverStatus


def test_info_prints_system_and_driver(invoke_cli, monkeypatch):
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
        "voicelink.cli.get_driver_status",
        lambda: DriverStatus(
            installed=True,
            driver_name="BlackHole",
            device_name="BlackHole 2ch",
            install_instructions=None,
        ),
    )

    result = invoke_cli(["info"])
    assert result.exit_code == 0
    assert "System Information:" in result.output
    assert "Audio Driver:" in result.output
    assert "Driver: BlackHole" in result.output
    assert "Installed: Yes" in result.output


def test_virtual_mic_ready_prints_devices(invoke_cli, monkeypatch):
    monkeypatch.setattr(
        "voicelink.cli.check_virtual_mic_ready",
        lambda: {
            "ready": True,
            "loopback_device": "[7] BlackHole 2ch",
            "virtual_output_device": "[8] BlackHole 2ch",
            "instructions": None,
        },
    )
    result = invoke_cli(["virtual-mic"])
    assert result.exit_code == 0
    assert "Virtual microphone is ready" in result.output
    assert "Loopback device" in result.output
    assert "Virtual output" in result.output


def test_virtual_mic_not_ready_prints_instructions(invoke_cli, monkeypatch):
    monkeypatch.setattr(
        "voicelink.cli.check_virtual_mic_ready",
        lambda: {
            "ready": False,
            "loopback_device": None,
            "virtual_output_device": None,
            "instructions": "Do setup",
        },
    )
    result = invoke_cli(["virtual-mic"])
    assert result.exit_code == 0
    assert "Virtual microphone needs setup" in result.output
    assert "Do setup" in result.output
