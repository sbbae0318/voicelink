# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

from voicelink.devices import AudioDevice


def test_record_uses_best_loopback_device_when_not_provided(
    invoke_cli, monkeypatch, call_capture, tmp_path
):
    loopback = AudioDevice(
        index=7,
        name="BlackHole 2ch",
        max_input_channels=2,
        max_output_channels=2,
        default_samplerate=48000.0,
        is_input=True,
        is_output=True,
        is_loopback=True,
        is_virtual=True,
    )
    monkeypatch.setattr("voicelink.cli.find_best_loopback_device", lambda: loopback)

    def fake_record_audio(**kwargs):
        call_capture.record(**kwargs)
        return Path(kwargs["output_path"])

    monkeypatch.setattr("voicelink.cli.record_audio", fake_record_audio)

    out = tmp_path / "meeting.wav"
    result = invoke_cli(["record", "-o", str(out), "-d", "1"])
    assert result.exit_code == 0
    assert "Using loopback device: BlackHole 2ch" in result.output
    assert "Recording saved" in result.output
    assert call_capture.calls[0][1]["device"] == 7


def test_record_warns_when_no_loopback_device(invoke_cli, monkeypatch, call_capture, tmp_path):
    monkeypatch.setattr("voicelink.cli.find_best_loopback_device", lambda: None)

    def fake_record_audio(**kwargs):
        call_capture.record(**kwargs)
        return Path(kwargs["output_path"])

    monkeypatch.setattr("voicelink.cli.record_audio", fake_record_audio)

    out = tmp_path / "meeting.wav"
    result = invoke_cli(["record", "-o", str(out), "-d", "1"])
    assert result.exit_code == 0
    assert "Warning: No loopback device found" in result.output
    assert call_capture.calls[0][1]["device"] is None


def test_record_passes_through_explicit_device(invoke_cli, monkeypatch, call_capture, tmp_path):
    def fake_record_audio(**kwargs):
        call_capture.record(**kwargs)
        return Path(kwargs["output_path"])

    monkeypatch.setattr("voicelink.cli.record_audio", fake_record_audio)

    out = tmp_path / "meeting.wav"
    result = invoke_cli(["record", "-o", str(out), "-d", "1", "-D", "3", "-r", "48000", "-c", "1"])
    assert result.exit_code == 0
    kwargs = call_capture.calls[0][1]
    assert kwargs["device"] == 3
    assert kwargs["sample_rate"] == 48000
    assert kwargs["channels"] == 1


def test_record_nonzero_exit_on_failure(invoke_cli, monkeypatch, tmp_path):
    monkeypatch.setattr("voicelink.cli.find_best_loopback_device", lambda: None)
    monkeypatch.setattr("voicelink.cli.record_audio", lambda **kwargs: None)

    out = tmp_path / "meeting.wav"
    result = invoke_cli(["record", "-o", str(out), "-d", "1"])
    assert result.exit_code == 1
    assert "Recording failed" in result.output
