# pyright: reportMissingImports=false

from __future__ import annotations

import click

from voicelink.devices import AudioDevice


def test_list_devices_prints_devices(invoke_cli, monkeypatch):
    fake_devices = [
        AudioDevice(
            index=0,
            name="Built-in Microphone",
            max_input_channels=1,
            max_output_channels=0,
            default_samplerate=44100.0,
            is_input=True,
            is_output=False,
            is_loopback=False,
            is_virtual=False,
        ),
        AudioDevice(
            index=7,
            name="BlackHole 2ch",
            max_input_channels=2,
            max_output_channels=2,
            default_samplerate=48000.0,
            is_input=True,
            is_output=True,
            is_loopback=True,
            is_virtual=True,
        ),
    ]

    monkeypatch.setattr("voicelink.cli.list_devices", lambda: fake_devices)

    def fake_print_devices(devices):
        click.echo("\nAvailable Audio Devices:")
        for d in devices:
            click.echo(f"[{d.index}] {d.name}")

    monkeypatch.setattr("voicelink.cli.print_devices", fake_print_devices)

    result = invoke_cli(["list-devices"])
    assert result.exit_code == 0
    assert "Available Audio Devices" in result.output
    assert "[0] Built-in Microphone" in result.output
    assert "[7] BlackHole 2ch" in result.output


def test_list_devices_loopback_filters(invoke_cli, monkeypatch):
    fake_devices = [
        AudioDevice(
            index=0,
            name="Built-in Microphone",
            max_input_channels=1,
            max_output_channels=0,
            default_samplerate=44100.0,
            is_input=True,
            is_output=False,
            is_loopback=False,
            is_virtual=False,
        ),
        AudioDevice(
            index=7,
            name="BlackHole 2ch",
            max_input_channels=2,
            max_output_channels=2,
            default_samplerate=48000.0,
            is_input=True,
            is_output=True,
            is_loopback=True,
            is_virtual=True,
        ),
    ]

    monkeypatch.setattr("voicelink.cli.list_devices", lambda: fake_devices)

    captured = {"count": 0, "names": []}

    def fake_print_devices(devices):
        captured["count"] += 1
        captured["names"] = [d.name for d in devices]

    monkeypatch.setattr("voicelink.cli.print_devices", fake_print_devices)

    result = invoke_cli(["list-devices", "--loopback"])
    assert result.exit_code == 0
    assert captured["count"] == 1
    assert captured["names"] == ["BlackHole 2ch"]


def test_list_devices_no_devices_shows_tip_when_loopback(invoke_cli, monkeypatch):
    monkeypatch.setattr("voicelink.cli.list_devices", lambda: [])
    result = invoke_cli(["list-devices", "--loopback"])
    assert result.exit_code == 0
    assert "No audio devices found." in result.output
    assert "Tip: Run 'voicelink setup'" in result.output
