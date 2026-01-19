"""Audio recording to file (WAV/MP3)."""

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
from scipy.io import wavfile

from .capture import AudioCapture, CaptureConfig


@dataclass
class RecordingConfig:
    """Configuration for audio recording."""

    output_path: Union[str, Path]
    duration: Optional[float] = None  # None for indefinite recording
    device: Optional[int] = None
    sample_rate: int = 44100
    channels: int = 2
    format: str = "wav"  # 'wav' or 'mp3'


@dataclass
class RecordingState:
    """Current state of recording."""

    is_recording: bool = False
    output_path: Optional[Path] = None
    duration_recorded: float = 0.0
    samples_recorded: int = 0
    error: Optional[str] = None


class AudioRecorder:
    """Records audio from capture to file."""

    def __init__(self, config: RecordingConfig):
        self.config = config
        self._state = RecordingState()
        self._capture: Optional[AudioCapture] = None
        self._audio_chunks: list[np.ndarray] = []
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def state(self) -> RecordingState:
        """Get current recording state."""
        return self._state

    @property
    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._state.is_recording

    def _collect_callback(self, data: np.ndarray) -> None:
        """Callback to collect audio data."""
        with self._lock:
            self._audio_chunks.append(data)
            self._state.samples_recorded += len(data)
            self._state.duration_recorded = (
                self._state.samples_recorded / self.config.sample_rate
            )

    def _recording_loop(self) -> None:
        """Main recording loop."""
        start_time = time.time()

        try:
            while not self._stop_event.is_set():
                # Check duration limit
                if self.config.duration is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= self.config.duration:
                        break

                time.sleep(0.1)

        except Exception as e:
            self._state.error = str(e)
        finally:
            self._finalize_recording()

    def _finalize_recording(self) -> None:
        """Finalize and save the recording."""
        if self._capture:
            self._capture.stop()

        # Combine all audio chunks
        with self._lock:
            if not self._audio_chunks:
                self._state.error = "No audio data recorded"
                return

            audio_data = np.concatenate(self._audio_chunks, axis=0)

        # Save to file
        output_path = Path(self.config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if self.config.format.lower() == "wav":
                self._save_wav(audio_data, output_path)
            elif self.config.format.lower() == "mp3":
                self._save_mp3(audio_data, output_path)
            else:
                self._state.error = f"Unsupported format: {self.config.format}"
                return

            self._state.output_path = output_path

        except Exception as e:
            self._state.error = f"Failed to save recording: {e}"

        self._state.is_recording = False

    def _save_wav(self, audio_data: np.ndarray, output_path: Path) -> None:
        """Save audio data as WAV file."""
        # Ensure correct path suffix
        if output_path.suffix.lower() != ".wav":
            output_path = output_path.with_suffix(".wav")

        # Convert float32 to int16 for WAV
        if audio_data.dtype == np.float32:
            audio_data = (audio_data * 32767).astype(np.int16)

        wavfile.write(str(output_path), self.config.sample_rate, audio_data)
        print(f"Saved WAV: {output_path}")

    def _save_mp3(self, audio_data: np.ndarray, output_path: Path) -> None:
        """Save audio data as MP3 file."""
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError(
                "MP3 support requires pydub. Install with: pip install voicelink[mp3]"
            )

        # Ensure correct path suffix
        if output_path.suffix.lower() != ".mp3":
            output_path = output_path.with_suffix(".mp3")

        # Convert to int16
        if audio_data.dtype == np.float32:
            audio_data = (audio_data * 32767).astype(np.int16)

        # Create AudioSegment from raw data
        audio_segment = AudioSegment(
            data=audio_data.tobytes(),
            sample_width=2,  # 16-bit = 2 bytes
            frame_rate=self.config.sample_rate,
            channels=self.config.channels,
        )

        audio_segment.export(str(output_path), format="mp3")
        print(f"Saved MP3: {output_path}")

    def start(self) -> bool:
        """Start recording."""
        if self._state.is_recording:
            print("Already recording.")
            return False

        # Reset state
        self._audio_chunks = []
        self._state = RecordingState(is_recording=True)
        self._stop_event.clear()

        # Create capture
        capture_config = CaptureConfig(
            device=self.config.device,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
        )
        self._capture = AudioCapture(capture_config)
        self._capture.add_callback(self._collect_callback)

        # Start capture
        if not self._capture.start():
            self._state.is_recording = False
            self._state.error = "Failed to start audio capture"
            return False

        # Start recording thread
        self._recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self._recording_thread.start()

        return True

    def stop(self) -> None:
        """Stop recording."""
        self._stop_event.set()
        if self._recording_thread:
            self._recording_thread.join(timeout=5.0)

    def wait(self) -> None:
        """Wait for recording to complete."""
        if self._recording_thread:
            self._recording_thread.join()

    def __enter__(self) -> "AudioRecorder":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
        self.wait()


def record_audio(
    output_path: Union[str, Path],
    duration: float,
    device: Optional[int] = None,
    sample_rate: int = 44100,
    channels: int = 2,
    format: str = "wav",
) -> Optional[Path]:
    """Record audio to a file.

    Args:
        output_path: Path to save the recording
        duration: Duration in seconds
        device: Device index (None for auto-detect)
        sample_rate: Sample rate in Hz
        channels: Number of channels
        format: Output format ('wav' or 'mp3')

    Returns:
        Path to saved file, or None on error
    """
    config = RecordingConfig(
        output_path=output_path,
        duration=duration,
        device=device,
        sample_rate=sample_rate,
        channels=channels,
        format=format,
    )

    recorder = AudioRecorder(config)

    print(f"Recording for {duration} seconds...")
    recorder.start()
    recorder.wait()

    if recorder.state.error:
        print(f"Recording error: {recorder.state.error}")
        return None

    return recorder.state.output_path
