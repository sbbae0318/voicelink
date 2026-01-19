"""Virtual microphone management and audio routing."""

import subprocess
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd

from .devices import AudioDevice, get_device_by_name, list_devices
from .platform_utils import Platform, get_platform


@dataclass
class VirtualMicConfig:
    """Configuration for virtual microphone routing."""

    input_device: Optional[int] = None  # Source device (e.g., BlackHole)
    output_device: Optional[int] = None  # Virtual mic output
    sample_rate: int = 44100
    channels: int = 2
    buffer_size: int = 1024


@dataclass
class VirtualMicState:
    """State of virtual microphone routing."""

    is_active: bool = False
    input_device: Optional[AudioDevice] = None
    output_device: Optional[AudioDevice] = None
    error: Optional[str] = None


class VirtualMicRouter:
    """Routes audio from one device to another (e.g., system audio to virtual mic)."""

    def __init__(self, config: VirtualMicConfig):
        self.config = config
        self._state = VirtualMicState()
        self._stream = None

    @property
    def state(self) -> VirtualMicState:
        """Get current state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Check if routing is active."""
        return self._state.is_active

    def _audio_callback(
        self, indata: np.ndarray, outdata: np.ndarray, frames: int, time_info: dict, status
    ) -> None:
        """Route audio from input to output."""
        if status:
            self._state.error = str(status)
        outdata[:] = indata

    def start(self) -> bool:
        """Start audio routing."""
        if self._state.is_active:
            print("Already routing.")
            return False

        try:
            self._stream = sd.Stream(
                device=(self.config.input_device, self.config.output_device),
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                blocksize=self.config.buffer_size,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._state.is_active = True
            return True

        except Exception as e:
            self._state.error = str(e)
            print(f"Failed to start routing: {e}")
            return False

    def stop(self) -> None:
        """Stop audio routing."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._state.is_active = False

    def __enter__(self) -> "VirtualMicRouter":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


def get_virtual_mic_setup_instructions() -> str:
    """Get platform-specific instructions for virtual mic setup."""
    current_platform = get_platform()

    if current_platform == Platform.MACOS:
        return """
Virtual Microphone Setup for macOS:

1. Install BlackHole (if not already installed):
   brew install blackhole-2ch

2. Create a Multi-Output Device:
   a. Open "Audio MIDI Setup" (Applications > Utilities)
   b. Click "+" at bottom left and select "Create Multi-Output Device"
   c. Check both your speakers/headphones AND BlackHole 2ch
   d. Right-click and select "Use This Device For Sound Output"

3. In your browser/app, select "BlackHole 2ch" as the microphone input

This allows system audio to be routed to apps expecting microphone input.
"""

    elif current_platform == Platform.WINDOWS:
        return """
Virtual Microphone Setup for Windows:

1. Install VB-CABLE:
   Download from: https://vb-audio.com/Cable/

2. Configure audio routing:
   a. Right-click speaker icon > Sound settings
   b. Set VB-CABLE as default playback device
   c. In your app, select "CABLE Output" as microphone input

Alternative: Use VoiceMeeter for more advanced routing options.
"""

    elif current_platform == Platform.LINUX:
        return """
Virtual Microphone Setup for Linux:

1. Create a virtual sink (PulseAudio):
   pactl load-module module-null-sink sink_name=VirtualMic sink_properties=device.description=VirtualMic

2. Route audio to the virtual sink:
   pactl load-module module-loopback source=<your_source>.monitor sink=VirtualMic

3. In your app, select the VirtualMic monitor as input.

For PipeWire: Use pw-link to connect audio nodes.
"""

    return "Unsupported platform for virtual microphone setup."


def find_virtual_mic_devices() -> dict[str, Optional[AudioDevice]]:
    """Find available virtual microphone devices."""
    devices = list_devices()
    result = {
        "loopback_input": None,  # Device to capture system audio
        "virtual_output": None,  # Device that apps can use as "mic"
    }

    current_platform = get_platform()

    if current_platform == Platform.MACOS:
        for device in devices:
            name_lower = device.name.lower()
            if "blackhole" in name_lower:
                if device.is_input:
                    result["loopback_input"] = device
                if device.is_output:
                    result["virtual_output"] = device

    elif current_platform == Platform.WINDOWS:
        for device in devices:
            name_lower = device.name.lower()
            if "cable" in name_lower:
                if "output" in name_lower and device.is_input:
                    result["loopback_input"] = device
                if "input" in name_lower and device.is_output:
                    result["virtual_output"] = device

    elif current_platform == Platform.LINUX:
        for device in devices:
            name_lower = device.name.lower()
            if ".monitor" in name_lower and device.is_input:
                result["loopback_input"] = device
            if "virtual" in name_lower and device.is_output:
                result["virtual_output"] = device

    return result


def create_aggregate_device_macos(
    name: str = "VoiceLinkAggregate",
    devices: Optional[list[str]] = None,
) -> bool:
    """Create an aggregate device on macOS (requires AudioDevice UID).

    Note: This is a simplified helper. For production use, consider using
    the Audio MIDI Setup app or a library like pyobjc-framework-CoreAudio.
    """
    if get_platform() != Platform.MACOS:
        print("Aggregate devices are only available on macOS.")
        return False

    print("To create an aggregate device on macOS:")
    print("1. Open 'Audio MIDI Setup' (Applications > Utilities)")
    print("2. Click '+' at the bottom left")
    print("3. Select 'Create Aggregate Device' or 'Create Multi-Output Device'")
    print("4. Select the devices you want to combine")
    print()
    print("Note: Multi-Output Device sends audio to multiple outputs simultaneously.")
    print("      Aggregate Device combines inputs/outputs for recording software.")

    return False  # Manual setup required


def check_virtual_mic_ready() -> dict:
    """Check if virtual microphone is properly configured."""
    devices = find_virtual_mic_devices()
    status = {
        "ready": False,
        "loopback_available": devices["loopback_input"] is not None,
        "virtual_output_available": devices["virtual_output"] is not None,
        "loopback_device": str(devices["loopback_input"]) if devices["loopback_input"] else None,
        "virtual_output_device": (
            str(devices["virtual_output"]) if devices["virtual_output"] else None
        ),
        "instructions": None,
    }

    if status["loopback_available"]:
        status["ready"] = True
    else:
        status["instructions"] = get_virtual_mic_setup_instructions()

    return status
