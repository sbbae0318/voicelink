"""Stream audio to APIs (OpenAI Realtime API)."""

import asyncio
import base64
import json
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np

from .capture import AudioCapture, CaptureConfig


@dataclass
class StreamConfig:
    """Configuration for audio streaming."""

    api_key: str
    device: Optional[int] = None
    sample_rate: int = 24000  # OpenAI Realtime API uses 24kHz
    channels: int = 1  # Mono for speech
    model: str = "gpt-4o-realtime-preview"
    voice: str = "alloy"
    instructions: Optional[str] = None


@dataclass
class StreamState:
    """Current state of audio streaming."""

    is_streaming: bool = False
    is_connected: bool = False
    chunks_sent: int = 0
    error: Optional[str] = None


class OpenAIRealtimeStream:
    """Stream audio to OpenAI Realtime API."""

    REALTIME_API_URL = "wss://api.openai.com/v1/realtime"

    def __init__(self, config: StreamConfig):
        self.config = config
        self._state = StreamState()
        self._capture: Optional[AudioCapture] = None
        self._websocket = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._response_callbacks: list[Callable[[dict], None]] = []

    @property
    def state(self) -> StreamState:
        """Get current stream state."""
        return self._state

    @property
    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        return self._state.is_streaming

    def add_response_callback(self, callback: Callable[[dict], None]) -> None:
        """Add callback for API responses."""
        self._response_callbacks.append(callback)

    def _audio_to_base64(self, audio_data: np.ndarray) -> str:
        """Convert audio data to base64 for API transmission."""
        # Convert float32 to int16
        if audio_data.dtype == np.float32:
            audio_data = (audio_data * 32767).astype(np.int16)

        # Ensure mono
        if audio_data.ndim == 2:
            audio_data = audio_data.mean(axis=1).astype(np.int16)

        return base64.b64encode(audio_data.tobytes()).decode("utf-8")

    def _on_audio_data(self, data: np.ndarray) -> None:
        """Handle incoming audio data from capture."""
        if not self._state.is_connected or self._websocket is None:
            return

        try:
            audio_base64 = self._audio_to_base64(data)
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64,
            }

            if self._loop and self._websocket:
                asyncio.run_coroutine_threadsafe(
                    self._websocket.send(json.dumps(message)), self._loop
                )
                self._state.chunks_sent += 1

        except Exception as e:
            self._state.error = f"Send error: {e}"

    async def _connect(self) -> bool:
        """Connect to OpenAI Realtime API."""
        try:
            import websockets
        except ImportError:
            self._state.error = "websockets library required: pip install websockets"
            return False

        url = f"{self.REALTIME_API_URL}?model={self.config.model}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        try:
            self._websocket = await websockets.connect(url, extra_headers=headers)
            self._state.is_connected = True

            # Send session configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "voice": self.config.voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                    },
                },
            }

            if self.config.instructions:
                session_config["session"]["instructions"] = self.config.instructions

            await self._websocket.send(json.dumps(session_config))
            return True

        except Exception as e:
            self._state.error = f"Connection failed: {e}"
            self._state.is_connected = False
            return False

    async def _receive_loop(self) -> None:
        """Receive and process API responses."""
        if not self._websocket:
            return

        try:
            async for message in self._websocket:
                if self._stop_event.is_set():
                    break

                try:
                    data = json.loads(message)
                    self._handle_response(data)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            if not self._stop_event.is_set():
                self._state.error = f"Receive error: {e}"

    def _handle_response(self, data: dict) -> None:
        """Handle API response."""
        event_type = data.get("type", "")

        # Log important events
        if event_type == "error":
            error_info = data.get("error", {})
            self._state.error = error_info.get("message", "Unknown error")
            print(f"API Error: {self._state.error}")

        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = data.get("transcript", "")
            if transcript:
                print(f"Transcription: {transcript}")

        elif event_type == "response.audio_transcript.done":
            transcript = data.get("transcript", "")
            if transcript:
                print(f"Assistant: {transcript}")

        # Notify callbacks
        for callback in self._response_callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"Callback error: {e}")

    async def _stream_loop(self) -> None:
        """Main streaming loop."""
        if not await self._connect():
            return

        # Start receiving responses
        receive_task = asyncio.create_task(self._receive_loop())

        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)
        finally:
            receive_task.cancel()
            if self._websocket:
                await self._websocket.close()
            self._state.is_connected = False

    def _run_async_loop(self) -> None:
        """Run async event loop in thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._stream_loop())
        finally:
            self._loop.close()

    def start(self) -> bool:
        """Start streaming to OpenAI Realtime API."""
        if self._state.is_streaming:
            print("Already streaming.")
            return False

        self._stop_event.clear()
        self._state = StreamState(is_streaming=True)

        # Setup audio capture
        capture_config = CaptureConfig(
            device=self.config.device,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
        )
        self._capture = AudioCapture(capture_config)
        self._capture.add_callback(self._on_audio_data)

        # Start capture
        if not self._capture.start():
            self._state.is_streaming = False
            self._state.error = "Failed to start audio capture"
            return False

        # Start streaming thread
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()

        return True

    def stop(self) -> None:
        """Stop streaming."""
        self._stop_event.set()

        if self._capture:
            self._capture.stop()

        if self._thread:
            self._thread.join(timeout=5.0)

        self._state.is_streaming = False

    def commit_audio(self) -> None:
        """Commit current audio buffer (triggers response)."""
        if not self._state.is_connected or not self._websocket:
            return

        message = {"type": "input_audio_buffer.commit"}
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._websocket.send(json.dumps(message)), self._loop
            )

    def create_response(self) -> None:
        """Request a response from the model."""
        if not self._state.is_connected or not self._websocket:
            return

        message = {"type": "response.create"}
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._websocket.send(json.dumps(message)), self._loop
            )


async def stream_to_openai(
    api_key: str,
    duration: Optional[float] = None,
    device: Optional[int] = None,
    on_response: Optional[Callable[[dict], None]] = None,
) -> None:
    """Stream audio to OpenAI Realtime API.

    Args:
        api_key: OpenAI API key
        duration: Duration in seconds (None for indefinite)
        device: Device index (None for auto-detect)
        on_response: Callback for API responses
    """
    config = StreamConfig(api_key=api_key, device=device)
    stream = OpenAIRealtimeStream(config)

    if on_response:
        stream.add_response_callback(on_response)

    print("Starting stream to OpenAI Realtime API...")
    stream.start()

    try:
        if duration:
            await asyncio.sleep(duration)
        else:
            # Run indefinitely until interrupted
            while stream.is_streaming:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping stream...")
    finally:
        stream.stop()
