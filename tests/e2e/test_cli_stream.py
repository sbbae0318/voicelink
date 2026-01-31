# pyright: reportMissingImports=false

from __future__ import annotations

import time

from dataclasses import dataclass

from voicelink.devices import AudioDevice


def test_stream_requires_api_key(invoke_cli):
    result = invoke_cli(["stream", "--duration", "0.1"])
    assert result.exit_code == 1
    assert "Error: OpenAI API key required" in result.output


def test_stream_runs_and_stops_with_duration(invoke_cli, monkeypatch):
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

    sleep_calls: list[float] = []

    def fake_sleep(duration: float):
        sleep_calls.append(duration)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    @dataclass
    class FakeState:
        error: str | None = None

    stream_holder: dict[str, object] = {}

    class FakeStream:
        def __init__(self, config):
            self._state = FakeState(error=None)
            self._started = False
            self.stopped = False
            self._callbacks = []
            stream_holder["obj"] = self

        @property
        def state(self):
            return self._state

        @property
        def is_streaming(self) -> bool:
            return self._started

        def add_response_callback(self, callback):
            self._callbacks.append(callback)

        def start(self):
            self._started = True
            # Simulate a response event
            for cb in self._callbacks:
                cb({"type": "response.audio_transcript.done", "transcript": "hello"})
            return True

        def stop(self):
            self._started = False
            self.stopped = True

    import voicelink.stream as stream_mod

    monkeypatch.setattr(stream_mod, "OpenAIRealtimeStream", FakeStream)

    result = invoke_cli(["stream", "--api-key", "sk-test", "--duration", "0.1"])
    assert result.exit_code == 0
    assert "Streaming to OpenAI" in result.output
    assert "Duration: 0.1s" in result.output
    assert "[Assistant]: hello" in result.output
    assert sleep_calls == [0.1]
    assert getattr(stream_holder["obj"], "stopped") is True
