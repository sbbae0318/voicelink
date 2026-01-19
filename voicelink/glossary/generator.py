"""GlossaryGenerator - Main class for generating glossaries from audio."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .extractor import GlossaryCompiler, setup_dspy
from .transcriber import AudioTranscriber, TranscriptionConfig


@dataclass
class GlossaryEntry:
    """A single glossary entry."""

    term: str
    explanation: str
    category: str = "General"
    related_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "term": self.term,
            "explanation": self.explanation,
            "category": self.category,
            "related_terms": self.related_terms,
        }

    def to_markdown(self) -> str:
        """Format as markdown."""
        md = f"### {self.term}\n\n"
        md += f"{self.explanation}\n"
        if self.related_terms:
            related = ", ".join(self.related_terms)
            md += f"\n*Related: {related}*\n"
        return md


@dataclass
class GlossaryDocument:
    """A complete glossary document."""

    title: str
    entries: list[GlossaryEntry]
    source_file: Optional[str] = None
    transcript: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    @property
    def categories(self) -> list[str]:
        """Get unique categories in the glossary."""
        return sorted(set(e.category for e in self.entries))

    def get_by_category(self, category: str) -> list[GlossaryEntry]:
        """Get entries by category."""
        return [e for e in self.entries if e.category == category]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "entries": [e.to_dict() for e in self.entries],
            "source_file": self.source_file,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        lines = [
            f"# {self.title}",
            "",
            f"*Generated: {self.created_at.strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]

        if self.source_file:
            lines.append(f"*Source: {self.source_file}*")
            lines.append("")

        lines.append(f"**{len(self.entries)} terms defined**")
        lines.append("")

        # Group by category
        for category in self.categories:
            entries = self.get_by_category(category)
            lines.append(f"## {category}")
            lines.append("")

            for entry in sorted(entries, key=lambda e: e.term.lower()):
                lines.append(entry.to_markdown())

        return "\n".join(lines)

    def save(self, path: Union[str, Path], format: Optional[str] = None) -> Path:
        """Save glossary to file.

        Args:
            path: Output path.
            format: Format ('md', 'json'). Auto-detected from extension if None.

        Returns:
            Path to saved file.
        """
        path = Path(path)

        if format is None:
            format = path.suffix.lstrip(".").lower()
            if format not in ("md", "json", "markdown"):
                format = "md"

        if format in ("md", "markdown"):
            content = self.to_markdown()
            if path.suffix.lower() not in (".md", ".markdown"):
                path = path.with_suffix(".md")
        else:
            content = self.to_json()
            if path.suffix.lower() != ".json":
                path = path.with_suffix(".json")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return path


class GlossaryGenerator:
    """Generate technical glossaries from audio files.

    Uses OpenAI Whisper for transcription and DSPy for term extraction
    and explanation generation.

    Example:
        >>> generator = GlossaryGenerator(api_key="sk-...")
        >>> glossary = generator.from_audio("meeting.wav")
        >>> glossary.save("glossary.md")
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        whisper_model: str = "whisper-1",
        max_terms: int = 50,
    ):
        """Initialize the glossary generator.

        Args:
            api_key: OpenAI API key.
            model: Model for term extraction/explanation.
            whisper_model: Model for transcription.
            max_terms: Maximum terms to extract.
        """
        self.api_key = api_key
        self.model = model
        self.whisper_model = whisper_model
        self.max_terms = max_terms

        # Configure DSPy
        setup_dspy(api_key=api_key, model=model)

        # Initialize components
        self._transcriber = AudioTranscriber(
            TranscriptionConfig(api_key=api_key, model=whisper_model)
        )
        self._compiler = GlossaryCompiler(max_terms=max_terms)

    def from_audio(
        self,
        audio_path: Union[str, Path],
        title: Optional[str] = None,
        context: str = "",
        domain: str = "",
    ) -> GlossaryDocument:
        """Generate glossary from an audio file.

        Args:
            audio_path: Path to audio file.
            title: Title for the glossary document.
            context: Context about the audio content.
            domain: Domain/field of the content.

        Returns:
            GlossaryDocument with extracted terms.
        """
        audio_path = Path(audio_path)

        if title is None:
            title = f"Glossary: {audio_path.stem}"

        print(f"Transcribing: {audio_path}")
        transcript_result = self._transcriber.transcribe(audio_path)
        transcript = transcript_result.text

        print(f"Transcribed {len(transcript)} characters")
        print("Extracting and explaining terms...")

        return self.from_transcript(
            transcript=transcript,
            title=title,
            source_file=str(audio_path),
            context=context,
            domain=domain,
        )

    def from_transcript(
        self,
        transcript: str,
        title: str = "Glossary",
        source_file: Optional[str] = None,
        context: str = "",
        domain: str = "",
    ) -> GlossaryDocument:
        """Generate glossary from a transcript.

        Args:
            transcript: The transcript text.
            title: Title for the glossary.
            source_file: Optional source file name.
            context: Context about the content.
            domain: Domain/field of the content.

        Returns:
            GlossaryDocument with extracted terms.
        """
        # Run the DSPy pipeline
        raw_entries = self._compiler(
            transcript=transcript,
            context=context,
            domain=domain,
        )

        # Convert to GlossaryEntry objects
        entries = [
            GlossaryEntry(
                term=e["term"],
                explanation=e["explanation"],
                category=e.get("category", "General"),
                related_terms=e.get("related_terms", []),
            )
            for e in raw_entries
        ]

        print(f"Extracted {len(entries)} terms")

        return GlossaryDocument(
            title=title,
            entries=entries,
            source_file=source_file,
            transcript=transcript,
            metadata={
                "model": self.model,
                "whisper_model": self.whisper_model,
                "context": context,
                "domain": domain,
            },
        )

    def from_text(
        self,
        text: str,
        title: str = "Glossary",
        context: str = "",
        domain: str = "",
    ) -> GlossaryDocument:
        """Generate glossary from plain text (not audio).

        Args:
            text: The text to analyze.
            title: Title for the glossary.
            context: Context about the content.
            domain: Domain/field.

        Returns:
            GlossaryDocument.
        """
        return self.from_transcript(
            transcript=text,
            title=title,
            context=context,
            domain=domain,
        )


def generate_glossary(
    audio_path: Union[str, Path],
    api_key: str,
    output_path: Optional[Union[str, Path]] = None,
    model: str = "gpt-4o",
) -> GlossaryDocument:
    """Convenience function to generate a glossary from audio.

    Args:
        audio_path: Path to audio file.
        api_key: OpenAI API key.
        output_path: Optional path to save the glossary.
        model: Model for generation.

    Returns:
        GlossaryDocument.
    """
    generator = GlossaryGenerator(api_key=api_key, model=model)
    glossary = generator.from_audio(audio_path)

    if output_path:
        glossary.save(output_path)
        print(f"Saved glossary to: {output_path}")

    return glossary
