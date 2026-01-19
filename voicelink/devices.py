"""Audio device enumeration and selection."""

from dataclasses import dataclass
from typing import Optional

import sounddevice as sd

from .platform_utils import Platform, get_platform


@dataclass
class AudioDevice:
    """Represents an audio device."""

    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    is_input: bool
    is_output: bool
    is_loopback: bool = False
    is_virtual: bool = False

    @property
    def can_capture(self) -> bool:
        """Check if this device can be used for capturing audio."""
        return self.is_input or self.is_loopback

    def __str__(self) -> str:
        device_type = []
        if self.is_input:
            device_type.append("input")
        if self.is_output:
            device_type.append("output")
        if self.is_loopback:
            device_type.append("loopback")
        if self.is_virtual:
            device_type.append("virtual")
        type_str = ", ".join(device_type) if device_type else "unknown"
        return f"[{self.index}] {self.name} ({type_str})"


def _is_virtual_device(name: str) -> bool:
    """Check if a device is a virtual audio device."""
    name_lower = name.lower()
    virtual_indicators = [
        "blackhole",
        "soundflower",
        "loopback",
        "virtual",
        "vb-audio",
        "cable",
        "aggregate",
    ]
    return any(indicator in name_lower for indicator in virtual_indicators)


def _is_loopback_device(name: str, platform: Platform) -> bool:
    """Check if a device is a loopback/monitor device."""
    name_lower = name.lower()

    if platform == Platform.LINUX:
        return ".monitor" in name_lower or "monitor of" in name_lower

    if platform == Platform.MACOS:
        return "blackhole" in name_lower or "loopback" in name_lower

    if platform == Platform.WINDOWS:
        return "cable" in name_lower and "output" in name_lower

    return False


def list_devices() -> list[AudioDevice]:
    """List all available audio devices."""
    current_platform = get_platform()
    devices = []

    try:
        raw_devices = sd.query_devices()

        for idx, device in enumerate(raw_devices):
            if isinstance(device, dict):
                name = device.get("name", f"Device {idx}")
                max_in = device.get("max_input_channels", 0)
                max_out = device.get("max_output_channels", 0)
                sample_rate = device.get("default_samplerate", 44100.0)

                audio_device = AudioDevice(
                    index=idx,
                    name=name,
                    max_input_channels=max_in,
                    max_output_channels=max_out,
                    default_samplerate=sample_rate,
                    is_input=max_in > 0,
                    is_output=max_out > 0,
                    is_loopback=_is_loopback_device(name, current_platform),
                    is_virtual=_is_virtual_device(name),
                )
                devices.append(audio_device)

    except Exception as e:
        print(f"Error querying devices: {e}")

    return devices


def list_capture_devices() -> list[AudioDevice]:
    """List devices that can capture audio (input or loopback)."""
    return [d for d in list_devices() if d.can_capture]


def list_loopback_devices() -> list[AudioDevice]:
    """List loopback/virtual devices for system audio capture."""
    return [d for d in list_devices() if d.is_loopback or d.is_virtual]


def get_device_by_index(index: int) -> Optional[AudioDevice]:
    """Get a device by its index."""
    devices = list_devices()
    for device in devices:
        if device.index == index:
            return device
    return None


def get_device_by_name(name: str, partial_match: bool = True) -> Optional[AudioDevice]:
    """Get a device by its name."""
    devices = list_devices()
    name_lower = name.lower()

    for device in devices:
        if partial_match:
            if name_lower in device.name.lower():
                return device
        else:
            if device.name.lower() == name_lower:
                return device
    return None


def find_best_loopback_device() -> Optional[AudioDevice]:
    """Find the best loopback device for system audio capture."""
    current_platform = get_platform()
    devices = list_devices()

    # Priority order for each platform
    if current_platform == Platform.MACOS:
        # Prefer BlackHole
        for device in devices:
            if "blackhole" in device.name.lower() and device.is_input:
                return device
        # Fall back to any loopback device
        for device in devices:
            if device.is_loopback and device.is_input:
                return device

    elif current_platform == Platform.WINDOWS:
        # Prefer VB-CABLE output (which appears as input for capture)
        for device in devices:
            if "cable output" in device.name.lower() and device.is_input:
                return device

    elif current_platform == Platform.LINUX:
        # Prefer monitor sources
        for device in devices:
            if ".monitor" in device.name.lower() and device.is_input:
                return device

    # Generic fallback: any virtual input device
    for device in devices:
        if device.is_virtual and device.is_input:
            return device

    return None


def get_default_input_device() -> Optional[AudioDevice]:
    """Get the system default input device."""
    try:
        default_idx = sd.default.device[0]
        if default_idx is not None:
            return get_device_by_index(int(default_idx))
    except Exception:
        pass
    return None


def get_default_output_device() -> Optional[AudioDevice]:
    """Get the system default output device."""
    try:
        default_idx = sd.default.device[1]
        if default_idx is not None:
            return get_device_by_index(int(default_idx))
    except Exception:
        pass
    return None


def print_devices(devices: Optional[list[AudioDevice]] = None) -> None:
    """Print a formatted list of devices."""
    if devices is None:
        devices = list_devices()

    if not devices:
        print("No audio devices found.")
        return

    print("\nAvailable Audio Devices:")
    print("-" * 60)

    for device in devices:
        flags = []
        if device.is_virtual:
            flags.append("virtual")
        if device.is_loopback:
            flags.append("loopback")

        channels = f"in:{device.max_input_channels} out:{device.max_output_channels}"
        sample_rate = f"{int(device.default_samplerate)}Hz"

        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  [{device.index:2d}] {device.name}")
        print(f"       {channels}, {sample_rate}{flag_str}")

    print("-" * 60)

    # Show recommended device
    best = find_best_loopback_device()
    if best:
        print(f"\nRecommended for system audio capture: [{best.index}] {best.name}")
