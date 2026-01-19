"""Core audio capture functionality."""

import queue
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from .devices import AudioDevice, find_best_loopback_device, get_device_by_index


@dataclass
class CaptureConfig:
    """Configuration for audio capture."""

    device: Optional[int] = None  # Device index, None for auto-detect
    sample_rate: int = 44100
    channels: int = 2
    dtype: str = "float32"
    blocksize: int = 1024
    latency: str = "low"


@dataclass
class CaptureState:
    """Current state of audio capture."""

    is_capturing: bool = False
    device: Optional[AudioDevice] = None
    samples_captured: int = 0
    error: Optional[str] = None


class AudioCapture:
    """Captures audio from system audio devices."""

    def __init__(self, config: Optional[CaptureConfig] = None):
        self.config = config or CaptureConfig()
        self._state = CaptureState()
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._callbacks: list[Callable[[np.ndarray], None]] = []
        self._lock = threading.Lock()

    @property
    def state(self) -> CaptureState:
        """Get current capture state."""
        return self._state

    @property
    def is_capturing(self) -> bool:
        """Check if capture is active."""
        return self._state.is_capturing

    def add_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """Add a callback to receive audio data."""
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """Remove a callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
    ) -> None:
        """Internal callback for sounddevice stream."""
        if status:
            self._state.error = str(status)

        # Copy data to avoid issues with buffer reuse
        data = indata.copy()
        self._audio_queue.put(data)
        self._state.samples_captured += frames

        # Notify external callbacks
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Callback error: {e}")

    def _resolve_device(self) -> Optional[AudioDevice]:
        """Resolve the capture device to use."""
        if self.config.device is not None:
            device = get_device_by_index(self.config.device)
            if device and device.can_capture:
                return device
            print(f"Warning: Device {self.config.device} cannot capture audio")

        # Auto-detect best loopback device
        device = find_best_loopback_device()
        if device:
            return device

        print("Warning: No loopback device found. Falling back to default input.")
        return None

    def start(self) -> bool:
        """Start capturing audio."""
        if self._state.is_capturing:
            print("Already capturing.")
            return False

        device = self._resolve_device()
        if device:
            device_idx = device.index
            self._state.device = device
            print(f"Capturing from: {device.name}")
        else:
            device_idx = None
            print("Capturing from default input device")

        try:
            self._stream = sd.InputStream(
                device=device_idx,
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.config.blocksize,
                latency=self.config.latency,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._state.is_capturing = True
            self._state.error = None
            self._state.samples_captured = 0
            return True

        except Exception as e:
            self._state.error = str(e)
            print(f"Failed to start capture: {e}")
            return False

    def stop(self) -> None:
        """Stop capturing audio."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._state.is_capturing = False

    def get_audio_data(self, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """Get the next block of audio data from the queue."""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear_queue(self) -> None:
        """Clear any buffered audio data."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def get_all_queued_data(self) -> list[np.ndarray]:
        """Get all queued audio data."""
        data = []
        while not self._audio_queue.empty():
            try:
                data.append(self._audio_queue.get_nowait())
            except queue.Empty:
                break
        return data

    def __enter__(self) -> "AudioCapture":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


def capture_audio_sync(
    duration: float,
    device: Optional[int] = None,
    sample_rate: int = 44100,
    channels: int = 2,
) -> np.ndarray:
    """Capture audio synchronously for a specified duration.

    Args:
        duration: Duration in seconds
        device: Device index (None for auto-detect)
        sample_rate: Sample rate in Hz
        channels: Number of channels

    Returns:
        numpy array of captured audio data
    """
    config = CaptureConfig(
        device=device,
        sample_rate=sample_rate,
        channels=channels,
    )

    capture = AudioCapture(config)
    audio_chunks = []

    def collect_callback(data: np.ndarray) -> None:
        audio_chunks.append(data)

    capture.add_callback(collect_callback)

    with capture:
        # Wait for the specified duration
        import time

        time.sleep(duration)

    if audio_chunks:
        return np.concatenate(audio_chunks, axis=0)
    return np.array([], dtype=np.float32)
