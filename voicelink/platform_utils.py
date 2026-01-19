"""Platform-specific utilities for audio driver detection and installation."""

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Platform(Enum):
    MACOS = "darwin"
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"


@dataclass
class DriverStatus:
    """Status of virtual audio driver installation."""

    installed: bool
    driver_name: str
    device_name: Optional[str] = None
    install_instructions: Optional[str] = None


def get_platform() -> Platform:
    """Detect the current operating system."""
    system = platform.system().lower()
    if system == "darwin":
        return Platform.MACOS
    elif system == "windows":
        return Platform.WINDOWS
    elif system == "linux":
        return Platform.LINUX
    return Platform.UNKNOWN


def check_blackhole_installed() -> bool:
    """Check if BlackHole virtual audio driver is installed on macOS."""
    if get_platform() != Platform.MACOS:
        return False

    try:
        import sounddevice as sd

        devices = sd.query_devices()
        for device in devices:
            if isinstance(device, dict):
                name = device.get("name", "").lower()
                if "blackhole" in name:
                    return True
        return False
    except Exception:
        return False


def check_vbcable_installed() -> bool:
    """Check if VB-CABLE is installed on Windows."""
    if get_platform() != Platform.WINDOWS:
        return False

    try:
        import sounddevice as sd

        devices = sd.query_devices()
        for device in devices:
            if isinstance(device, dict):
                name = device.get("name", "").lower()
                if "cable" in name and ("vb" in name or "virtual" in name):
                    return True
        return False
    except Exception:
        return False


def check_pulseaudio_monitor() -> bool:
    """Check if PulseAudio monitor source is available on Linux."""
    if get_platform() != Platform.LINUX:
        return False

    try:
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return ".monitor" in result.stdout
    except Exception:
        return False


def get_driver_status() -> DriverStatus:
    """Get the status of virtual audio driver for current platform."""
    current_platform = get_platform()

    if current_platform == Platform.MACOS:
        installed = check_blackhole_installed()
        return DriverStatus(
            installed=installed,
            driver_name="BlackHole",
            device_name="BlackHole 2ch" if installed else None,
            install_instructions=(
                "Install BlackHole using Homebrew:\n"
                "  brew install blackhole-2ch\n\n"
                "Or download from: https://existential.audio/blackhole/"
            )
            if not installed
            else None,
        )

    elif current_platform == Platform.WINDOWS:
        installed = check_vbcable_installed()
        return DriverStatus(
            installed=installed,
            driver_name="VB-CABLE",
            device_name="CABLE Output (VB-Audio Virtual Cable)" if installed else None,
            install_instructions=(
                "Download VB-CABLE from: https://vb-audio.com/Cable/\n"
                "Run the installer as Administrator."
            )
            if not installed
            else None,
        )

    elif current_platform == Platform.LINUX:
        installed = check_pulseaudio_monitor()
        return DriverStatus(
            installed=installed,
            driver_name="PulseAudio Monitor",
            device_name=None,  # Determined dynamically
            install_instructions=(
                "PulseAudio should be pre-installed. If not:\n"
                "  Ubuntu/Debian: sudo apt install pulseaudio\n"
                "  Fedora: sudo dnf install pulseaudio\n"
                "  Arch: sudo pacman -S pulseaudio"
            )
            if not installed
            else None,
        )

    return DriverStatus(
        installed=False,
        driver_name="Unknown",
        install_instructions="Unsupported platform.",
    )


def install_blackhole() -> bool:
    """Attempt to install BlackHole on macOS using Homebrew."""
    if get_platform() != Platform.MACOS:
        return False

    if not shutil.which("brew"):
        print("Homebrew is not installed. Please install Homebrew first:")
        print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False

    try:
        print("Installing BlackHole via Homebrew...")
        result = subprocess.run(
            ["brew", "install", "blackhole-2ch"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("BlackHole installed successfully!")
            print("Note: You may need to restart your audio applications.")
            return True
        else:
            print(f"Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error during installation: {e}")
        return False


def setup_driver(auto_install: bool = False) -> DriverStatus:
    """Check and optionally install the virtual audio driver."""
    status = get_driver_status()

    if status.installed:
        print(f"{status.driver_name} is already installed.")
        return status

    print(f"{status.driver_name} is not installed.")

    if status.install_instructions:
        print("\nInstallation instructions:")
        print(status.install_instructions)

    if auto_install and get_platform() == Platform.MACOS:
        response = input("\nWould you like to install BlackHole now? [y/N]: ")
        if response.lower() in ("y", "yes"):
            if install_blackhole():
                return get_driver_status()

    return status


def get_system_info() -> dict:
    """Get system information for debugging."""
    return {
        "platform": get_platform().value,
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python_version": sys.version,
    }
