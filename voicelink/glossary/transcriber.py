"""Audio transcription using OpenAI Whisper API."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


@dataclass
class TranscriptionConfig:
    """Configuration for audio transcription."""

    api_key: str
    model: str = "whisper-1"
    language: Optional[str] = None  # Auto-detect if None
    prompt: Optional[str] = None  # Optional context hint
    response_format: str = "text"  # 'text', 'json', 'verbose_json', 'srt', 'vtt'
    temperature: float = 0.0


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""

    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    segments: Optional[list] = None  # For verbose_json format


class AudioTranscriber:
    """Transcribe audio files using OpenAI Whisper API."""

    def __init__(self, config: TranscriptionConfig):
        """Initialize the transcriber.

        Args:
            config: Transcription configuration.
        """
        self.config = config
        self._client = None

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI library required. Install with: pip install voicelink[openai]"
                )
            self._client = OpenAI(api_key=self.config.api_key)
        return self._client

    def transcribe(self, audio_path: Union[str, Path]) -> TranscriptionResult:
        """Transcribe an audio file.

        Args:
            audio_path: Path to the audio file.

        Returns:
            TranscriptionResult with the transcribed text.
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        client = self._get_client()

        # Build transcription parameters
        params = {
            "model": self.config.model,
            "response_format": self.config.response_format,
            "temperature": self.config.temperature,
        }

        if self.config.language:
            params["language"] = self.config.language

        if self.config.prompt:
            params["prompt"] = self.config.prompt

        # Transcribe
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(file=audio_file, **params)

        # Parse response based on format
        if self.config.response_format == "text":
            return TranscriptionResult(text=response)

        elif self.config.response_format in ("json", "verbose_json"):
            result = TranscriptionResult(
                text=response.text,
                language=getattr(response, "language", None),
                duration=getattr(response, "duration", None),
            )

            if self.config.response_format == "verbose_json":
                result.segments = getattr(response, "segments", None)

            return result

        else:
            # For srt/vtt formats, return as text
            return TranscriptionResult(text=response)

    def transcribe_with_timestamps(
        self, audio_path: Union[str, Path]
    ) -> TranscriptionResult:
        """Transcribe with word-level timestamps.

        Args:
            audio_path: Path to audio file.

        Returns:
            TranscriptionResult with segments containing timestamps.
        """
        # Use verbose_json for timestamps
        original_format = self.config.response_format
        self.config.response_format = "verbose_json"

        try:
            return self.transcribe(audio_path)
        finally:
            self.config.response_format = original_format


def transcribe_audio(
    audio_path: Union[str, Path],
    api_key: str,
    language: Optional[str] = None,
) -> str:
    """Simple function to transcribe an audio file.

    Args:
        audio_path: Path to the audio file.
        api_key: OpenAI API key.
        language: Optional language code.

    Returns:
        Transcribed text.
    """
    config = TranscriptionConfig(api_key=api_key, language=language)
    transcriber = AudioTranscriber(config)
    result = transcriber.transcribe(audio_path)
    return result.text
