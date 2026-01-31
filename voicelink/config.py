"""VoiceLink 설정 관리 모듈."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class RecordingSettings:
    """녹음 관련 설정."""
    chunk_duration_seconds: int = 30
    sample_rate: int = 16000
    channels: int = 1
    format: str = "wav"
    silence_threshold: float = 0.001


@dataclass
class StorageSettings:
    """저장소 관련 설정."""
    data_dir: str = "~/voicelink_data"
    retention_days: int = 30
    auto_cleanup: bool = True

    @property
    def data_path(self) -> Path:
        """확장된 데이터 경로를 반환합니다."""
        return Path(os.path.expanduser(self.data_dir))


@dataclass
class SessionSettings:
    """세션 관련 설정."""
    silence_gap_seconds: int = 60
    min_session_duration: int = 30


@dataclass
class DeviceSettings:
    """장치 관련 설정."""
    auto_detect: bool = True
    auto_switch: bool = True  # 무음 시 자동 장치 전환
    silence_timeout_for_switch: float = 5.0  # 장치 전환을 시도할 무음 지속 시간 (초)
    preferred_device: Optional[str] = None
    fallback_devices: list[str] = field(default_factory=lambda: [
        "Voicemeeter Out B1",
        "Stereo Mix",
        "CABLE Output",
    ])


@dataclass
class TranscriptionSettings:
    """전사 관련 설정."""
    method: str = "whisper_api"  # whisper_api, whisper_local, external
    api_key: Optional[str] = None
    language: Optional[str] = None
    external_command: str = "whisper {input} --output_format txt -o {output}"


@dataclass
class VoiceLinkConfig:
    """VoiceLink 전체 설정."""
    recording: RecordingSettings = field(default_factory=RecordingSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    session: SessionSettings = field(default_factory=SessionSettings)
    device: DeviceSettings = field(default_factory=DeviceSettings)
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)

    @classmethod
    def get_default_config_path(cls) -> Path:
        """기본 설정 파일 경로를 반환합니다."""
        if os.name == "nt":  # Windows
            base = Path(os.environ.get("USERPROFILE", "~"))
        else:
            base = Path.home()
        return base / ".voicelink" / "config.yaml"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "VoiceLinkConfig":
        """설정 파일을 로드합니다."""
        if path is None:
            path = cls.get_default_config_path()

        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        if "recording" in data:
            for key, value in data["recording"].items():
                if hasattr(config.recording, key):
                    setattr(config.recording, key, value)

        if "storage" in data:
            for key, value in data["storage"].items():
                if hasattr(config.storage, key):
                    setattr(config.storage, key, value)

        if "session" in data:
            for key, value in data["session"].items():
                if hasattr(config.session, key):
                    setattr(config.session, key, value)

        if "device" in data:
            for key, value in data["device"].items():
                if hasattr(config.device, key):
                    setattr(config.device, key, value)

        if "transcription" in data:
            for key, value in data["transcription"].items():
                if hasattr(config.transcription, key):
                    setattr(config.transcription, key, value)

        return config

    def save(self, path: Optional[Path] = None) -> None:
        """설정 파일을 저장합니다."""
        if path is None:
            path = self.get_default_config_path()

        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "recording": {
                "chunk_duration_seconds": self.recording.chunk_duration_seconds,
                "sample_rate": self.recording.sample_rate,
                "channels": self.recording.channels,
                "format": self.recording.format,
                "silence_threshold": self.recording.silence_threshold,
            },
            "storage": {
                "data_dir": self.storage.data_dir,
                "retention_days": self.storage.retention_days,
                "auto_cleanup": self.storage.auto_cleanup,
            },
            "session": {
                "silence_gap_seconds": self.session.silence_gap_seconds,
                "min_session_duration": self.session.min_session_duration,
            },
            "device": {
                "auto_detect": self.device.auto_detect,
                "preferred_device": self.device.preferred_device,
                "fallback_devices": self.device.fallback_devices,
            },
            "transcription": {
                "method": self.transcription.method,
                "api_key": self.transcription.api_key,
                "language": self.transcription.language,
                "external_command": self.transcription.external_command,
            },
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# 전역 설정 인스턴스
_config: Optional[VoiceLinkConfig] = None


def get_config() -> VoiceLinkConfig:
    """전역 설정을 가져옵니다."""
    global _config
    if _config is None:
        _config = VoiceLinkConfig.load()
    return _config


def set_config(config: VoiceLinkConfig) -> None:
    """전역 설정을 설정합니다."""
    global _config
    _config = config
