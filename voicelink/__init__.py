"""VoiceLink - Cross-platform system audio capture and streaming.

A Python tool for capturing system audio (Zoom calls, YouTube, etc.) that works
as both a standalone Python program and a Claude Skill.
"""

from pathlib import Path
from typing import Callable, Optional, Union

from .auto_detect import (
    DeviceProbeResult,
    auto_select_capture_device,
    find_active_audio_device,
    probe_device,
)
from .capture import AudioCapture, CaptureConfig, capture_audio_sync
from .devices import (
    AudioDevice,
    find_best_loopback_device,
    get_device_by_index,
    get_device_by_name,
    list_capture_devices,
    list_devices,
    list_loopback_devices,
)
from .logging_config import get_logger, log, setup_logging
from .platform_utils import (
    Platform,
    check_blackhole_installed,
    get_driver_status,
    get_platform,
    get_system_info,
    setup_driver,
)
from .recorder import AudioRecorder, RecordingConfig, record_audio
from .virtual_mic import (
    VirtualMicRouter,
    check_virtual_mic_ready,
    find_virtual_mic_devices,
    get_virtual_mic_setup_instructions,
)

# Optional imports (require extra dependencies)
try:
    from .vad import (
        VADConfig,
        extract_voice_segments,
        is_silent,
        process_wav_file,
        remove_silence,
    )
    _VAD_AVAILABLE = True
except ImportError:
    _VAD_AVAILABLE = False

try:
    from .whisper import (
        TranscriptionResult,
        WhisperConfig,
        get_optimal_sample_rate,
        prepare_audio_for_whisper,
        transcribe_audio,
        transcribe_directory,
    )
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False

__version__ = "0.1.0"
__all__ = [
    # Main class
    "VoiceLink",
    # Capture
    "AudioCapture",
    "CaptureConfig",
    "capture_audio_sync",
    # Devices
    "AudioDevice",
    "list_devices",
    "list_capture_devices",
    "list_loopback_devices",
    "find_best_loopback_device",
    "get_device_by_index",
    "get_device_by_name",
    # Recording
    "AudioRecorder",
    "RecordingConfig",
    "record_audio",
    # Platform
    "Platform",
    "get_platform",
    "get_driver_status",
    "get_system_info",
    "check_blackhole_installed",
    "setup_driver",
    # Virtual Mic
    "VirtualMicRouter",
    "check_virtual_mic_ready",
    "find_virtual_mic_devices",
    "get_virtual_mic_setup_instructions",
    # Auto Detection
    "DeviceProbeResult",
    "find_active_audio_device",
    "auto_select_capture_device",
    "probe_device",
    # Logging
    "setup_logging",
    "get_logger",
    "log",
    # VAD (Voice Activity Detection)
    "VADConfig",
    "is_silent",
    "extract_voice_segments",
    "remove_silence",
    "process_wav_file",
    # Whisper
    "WhisperConfig",
    "TranscriptionResult",
    "transcribe_audio",
    "transcribe_directory",
    "get_optimal_sample_rate",
    "prepare_audio_for_whisper",
]



class VoiceLink:
    """Main interface for VoiceLink functionality.

    This class provides a unified API for audio capture, recording, and streaming
    that can be used both as a Python library and via Claude Skills.

    Example:
        >>> from voicelink import VoiceLink
        >>> vl = VoiceLink()
        >>> vl.list_devices()
        >>> vl.capture_to_file("output.wav", duration=30)
    """

    def __init__(self, device: Optional[int] = None, auto_detect: bool = False):
        """Initialize VoiceLink.

        Args:
            device: Default device index for capture. None for auto-detection.
            auto_detect: If True, automatically find device with active audio signal.
        """
        self._auto_detect = auto_detect
        self._default_device = device
        self._capture: Optional[AudioCapture] = None
        self._recorder: Optional[AudioRecorder] = None
        
        # 자동 탐지 모드일 경우 활성 장치 찾기
        if auto_detect and device is None:
            detected = auto_select_capture_device(verbose=True)
            if detected:
                self._default_device = detected.index

    @staticmethod
    def list_devices() -> list[AudioDevice]:
        """List all available audio devices.

        Returns:
            List of AudioDevice objects.
        """
        return list_devices()

    @staticmethod
    def list_loopback_devices() -> list[AudioDevice]:
        """List devices suitable for system audio capture.

        Returns:
            List of loopback/virtual AudioDevice objects.
        """
        return list_loopback_devices()

    @staticmethod
    def find_best_device() -> Optional[AudioDevice]:
        """Find the best device for system audio capture.

        Returns:
            Best AudioDevice for loopback capture, or None.
        """
        return find_best_loopback_device()

    @staticmethod
    def find_active_device(verbose: bool = True) -> Optional[AudioDevice]:
        """Find a device with active audio signal.

        Scans all input devices and returns the one with the highest audio level.

        Args:
            verbose: Print scanning progress.

        Returns:
            AudioDevice with active signal, or None.
        """
        return find_active_audio_device(verbose=verbose)

    def detect_and_set_device(self, verbose: bool = True) -> Optional[AudioDevice]:
        """Detect active audio device and set it as default.

        Args:
            verbose: Print scanning progress.

        Returns:
            Detected AudioDevice, or None.
        """
        device = auto_select_capture_device(verbose=verbose)
        if device:
            self._default_device = device.index
        return device

    @staticmethod
    def check_setup() -> dict:
        """Check if the system is properly configured for audio capture.

        Returns:
            Dictionary with setup status information.
        """
        driver = get_driver_status()
        mic_status = check_virtual_mic_ready()

        return {
            "driver_installed": driver.installed,
            "driver_name": driver.driver_name,
            "device_name": driver.device_name,
            "virtual_mic_ready": mic_status["ready"],
            "loopback_device": mic_status.get("loopback_device"),
            "install_instructions": driver.install_instructions,
            "platform": get_platform().value,
        }

    @staticmethod
    def setup(auto_install: bool = False) -> bool:
        """Setup virtual audio drivers.

        Args:
            auto_install: If True, attempt automatic installation on macOS.

        Returns:
            True if drivers are installed after setup.
        """
        status = setup_driver(auto_install=auto_install)
        return status.installed

    def capture_to_file(
        self,
        output_path: Union[str, Path],
        duration: float,
        sample_rate: int = 44100,
        channels: int = 2,
        format: str = "wav",
    ) -> Optional[Path]:
        """Capture system audio to a file.

        Args:
            output_path: Path for the output file.
            duration: Recording duration in seconds.
            sample_rate: Sample rate in Hz.
            channels: Number of audio channels.
            format: Output format ('wav' or 'mp3').

        Returns:
            Path to saved file, or None on error.
        """
        return record_audio(
            output_path=output_path,
            duration=duration,
            device=self._default_device,
            sample_rate=sample_rate,
            channels=channels,
            format=format,
        )

    def start_capture(
        self,
        callback: Optional[Callable] = None,
        sample_rate: int = 44100,
        channels: int = 2,
    ) -> bool:
        """Start continuous audio capture.

        Args:
            callback: Optional callback function for audio data.
            sample_rate: Sample rate in Hz.
            channels: Number of channels.

        Returns:
            True if capture started successfully.
        """
        config = CaptureConfig(
            device=self._default_device,
            sample_rate=sample_rate,
            channels=channels,
        )
        self._capture = AudioCapture(config)

        if callback:
            self._capture.add_callback(callback)

        return self._capture.start()

    def stop_capture(self) -> None:
        """Stop continuous audio capture."""
        if self._capture:
            self._capture.stop()
            self._capture = None

    @property
    def is_capturing(self) -> bool:
        """Check if capture is active."""
        return self._capture is not None and self._capture.is_capturing

    def start_streaming(
        self,
        api_key: str,
        on_response: Optional[Callable[[dict], None]] = None,
        model: str = "gpt-4o-realtime-preview",
        voice: str = "alloy",
        instructions: Optional[str] = None,
    ):
        """Start streaming audio to OpenAI Realtime API.

        Args:
            api_key: OpenAI API key.
            on_response: Callback for API responses.
            model: OpenAI model to use.
            voice: Voice for responses.
            instructions: System instructions.

        Returns:
            OpenAIRealtimeStream instance.
        """
        from .stream import OpenAIRealtimeStream, StreamConfig

        config = StreamConfig(
            api_key=api_key,
            device=self._default_device,
            model=model,
            voice=voice,
            instructions=instructions,
        )

        stream = OpenAIRealtimeStream(config)
        if on_response:
            stream.add_response_callback(on_response)

        stream.start()
        return stream

    # Claude Skills compatible functions
    @staticmethod
    def skill_list_audio_devices() -> list[dict]:
        """List audio devices (Claude Skills compatible).

        Returns:
            List of device dictionaries.
        """
        devices = list_devices()
        return [
            {
                "index": d.index,
                "name": d.name,
                "is_input": d.is_input,
                "is_output": d.is_output,
                "is_loopback": d.is_loopback,
                "is_virtual": d.is_virtual,
                "can_capture": d.can_capture,
            }
            for d in devices
        ]

    @staticmethod
    def skill_check_setup() -> dict:
        """Check setup status (Claude Skills compatible).

        Returns:
            Setup status dictionary.
        """
        return VoiceLink.check_setup()

    def skill_record_audio(
        self,
        output_path: str,
        duration: float,
        format: str = "wav",
    ) -> dict:
        """Record audio (Claude Skills compatible).

        Args:
            output_path: Path for output file.
            duration: Duration in seconds.
            format: Output format.

        Returns:
            Recording result dictionary.
        """
        result = self.capture_to_file(
            output_path=output_path,
            duration=duration,
            format=format,
        )

        if result:
            return {
                "success": True,
                "output_path": str(result),
                "duration": duration,
                "format": format,
            }
        return {
            "success": False,
            "error": "Recording failed",
        }

    @staticmethod
    def skill_get_recording_status() -> dict:
        """Get recording status (Claude Skills compatible).

        Returns:
            Status dictionary.
        """
        return {
            "platform": get_platform().value,
            "driver_status": get_driver_status().__dict__,
            "virtual_mic_status": check_virtual_mic_ready(),
        }
