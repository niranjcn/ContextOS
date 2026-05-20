"""
ContextOS Meeting Transcriber.

Uses OpenAI Whisper to transcribe audio recordings to text,
then feeds the transcript into the ingestion pipeline.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".mp3", ".mp4", ".wav", ".m4a", ".webm"}
DEFAULT_MODEL_SIZE = "base"


@dataclass
class TranscriptionSegment:
    """A timed segment from the transcription."""
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    text: str = ""
    segments: list[TranscriptionSegment] = field(default_factory=list)
    language: str = ""
    duration_seconds: float = 0.0


class MeetingTranscriber:
    """
    Whisper-based audio transcriber for meeting recordings.

    Loads the Whisper model lazily and provides methods to transcribe
    audio files and optionally ingest the transcripts.
    """

    def __init__(self, model_size: str = DEFAULT_MODEL_SIZE) -> None:
        self._model_size = model_size
        self._model = None
        logger.info("MeetingTranscriber configured (model: %s).", model_size)

    def _ensure_model(self) -> None:
        """Lazily load the Whisper model."""
        if self._model is not None:
            return
        try:
            import whisper
            from rich.console import Console

            console = Console()
            with console.status(f"[bold green]Loading Whisper {self._model_size} model..."):
                self._model = whisper.load_model(self._model_size)
            logger.info("Whisper %s model loaded.", self._model_size)
        except ImportError:
            logger.error(
                "openai-whisper not installed. Install with: pip install openai-whisper"
            )
            raise

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file.

        Returns:
            TranscriptionResult with text, segments, language, and duration.

        Raises:
            FileNotFoundError: If the audio file doesn't exist.
            ValueError: If the file format is unsupported.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if audio_path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{audio_path.suffix}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )

        self._ensure_model()

        try:
            from rich.console import Console
            from rich.progress import Progress

            console = Console()
            console.print(f"[bold]Transcribing:[/bold] {audio_path.name}")

            with Progress() as progress:
                task = progress.add_task("Transcribing...", total=None)
                result = self._model.transcribe(str(audio_path))
                progress.update(task, completed=True)

            segments = [
                TranscriptionSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                )
                for seg in result.get("segments", [])
            ]

            duration = segments[-1].end if segments else 0.0

            transcription = TranscriptionResult(
                text=result.get("text", "").strip(),
                segments=segments,
                language=result.get("language", "unknown"),
                duration_seconds=duration,
            )

            logger.info(
                "Transcribed %s: %d chars, %d segments, %.1fs duration, lang=%s.",
                audio_path.name,
                len(transcription.text),
                len(transcription.segments),
                transcription.duration_seconds,
                transcription.language,
            )
            return transcription

        except Exception as exc:
            logger.error("Transcription failed for %s: %s", audio_path, exc)
            raise

    def transcribe_and_ingest(
        self, audio_path: Path, pipeline: Any
    ) -> dict[str, Any]:
        """
        Transcribe audio and immediately ingest the transcript.

        Args:
            audio_path: Path to the audio file.
            pipeline: IngestionPipeline instance.

        Returns:
            Dict with transcription and ingestion results.
        """
        transcription = self.transcribe(audio_path)

        if not transcription.text:
            logger.warning("Empty transcription for %s.", audio_path)
            return {"transcription": transcription, "ingestion": None}

        import hashlib
        content_hash = hashlib.sha256(transcription.text.encode()).hexdigest()[:16]

        result = pipeline.process_text(
            text=transcription.text,
            doc_id=f"transcript_{content_hash}",
            source="whisper_transcription",
            metadata={
                "filename": audio_path.name,
                "duration_seconds": transcription.duration_seconds,
                "language": transcription.language,
                "segment_count": len(transcription.segments),
            },
        )

        logger.info("Transcription ingested: %s", result.get("status"))
        return {"transcription": transcription, "ingestion": result}
