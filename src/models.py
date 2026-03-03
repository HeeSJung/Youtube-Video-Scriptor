"""
Data models for YouTube Scene Extractor

This module defines dataclasses for all core entities: Video, Scene, Transcript,
Speaker, and ProcessingResult.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class CaptionType(Enum):
    """Type of captions available for a video"""

    MANUAL = "manual"
    AUTO_GENERATED = "auto-generated"
    NONE = "none"


@dataclass
class Video:
    """
    Represents a YouTube video being processed

    Attributes:
        video_id: YouTube video identifier (11 characters)
        url: Original YouTube URL provided by user
        title: Video title from YouTube metadata (optional)
        duration: Total video duration in seconds
        has_captions: Whether captions are available
        caption_type: Type of captions (manual, auto-generated, or none)
        processed_at: Timestamp of when processing occurred
    """

    video_id: str
    url: str
    duration: int
    has_captions: bool
    caption_type: CaptionType
    title: Optional[str] = None
    processed_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate video attributes after initialization"""
        # Validate video_id format (11 characters)
        if not self.video_id or len(self.video_id) != 11:
            raise ValueError(
                f"video_id must be 11 characters, got {len(self.video_id)}: {self.video_id}"
            )

        # Validate URL format
        if not self.url or not isinstance(self.url, str):
            raise ValueError("url must be a non-empty string")

        # Validate duration (positive integer)
        if not isinstance(self.duration, int) or self.duration <= 0:
            raise ValueError(f"duration must be a positive integer, got {self.duration}")

        # Ensure caption_type is CaptionType enum
        if isinstance(self.caption_type, str):
            self.caption_type = CaptionType(self.caption_type)


@dataclass
class Scene:
    """
    A logical segment of video with detected boundaries

    Attributes:
        scene_id: Unique identifier (format: "scene_01", "scene_02", etc.)
        video_id: Reference to parent Video
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds
        duration: Scene duration in seconds (computed property)
        confidence: Detection confidence score 0-1 (optional)
    """

    scene_id: str
    video_id: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None

    @property
    def duration(self) -> float:
        """Computed duration of the scene"""
        return self.end_time - self.start_time

    def __post_init__(self):
        """Validate scene attributes after initialization"""
        # Validate scene_id format
        if not self.scene_id or not self.scene_id.startswith("scene_"):
            raise ValueError(f"scene_id must start with 'scene_', got {self.scene_id}")

        # Validate start_time
        if self.start_time < 0:
            raise ValueError(f"start_time must be >= 0, got {self.start_time}")

        # Validate end_time
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time must be > start_time, got start={self.start_time}, end={self.end_time}"
            )

        # Note: Duration validation (>= 15s) is enforced by merge_short_scenes()
        # in scene_detector.py, not here, to allow temporary creation of short scenes

        # Validate confidence if provided
        if self.confidence is not None:
            if not 0 <= self.confidence <= 1:
                raise ValueError(f"confidence must be between 0 and 1, got {self.confidence}")

    def format_timecode(self, timestamp: float) -> str:
        """Format timestamp as HH:MM:SS"""
        hours = int(timestamp // 3600)
        minutes = int((timestamp % 3600) // 60)
        seconds = int(timestamp % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def start_timecode(self) -> str:
        """Start time in HH:MM:SS format"""
        return self.format_timecode(self.start_time)

    @property
    def end_timecode(self) -> str:
        """End time in HH:MM:SS format"""
        return self.format_timecode(self.end_time)


@dataclass
class Speaker:
    """
    An identified voice in the video

    Attributes:
        speaker_id: Unique identifier (e.g., "speaker_1", "speaker_2")
        label: Display label (e.g., "Speaker 1", or detected name)
        scenes: List of scene_ids where speaker appears
        first_appearance: First timestamp where speaker is detected
        line_count: Total number of dialogue lines
    """

    speaker_id: str
    label: str
    scenes: List[str] = field(default_factory=list)
    first_appearance: float = 0.0
    line_count: int = 0

    def __post_init__(self):
        """Validate speaker attributes after initialization"""
        # Validate speaker_id format
        if not self.speaker_id or not self.speaker_id.startswith("speaker_"):
            raise ValueError(f"speaker_id must start with 'speaker_', got {self.speaker_id}")

        # Validate label format
        if not self.label:
            raise ValueError("label must be a non-empty string")

        # Validate first_appearance
        if self.first_appearance < 0:
            raise ValueError(f"first_appearance must be >= 0, got {self.first_appearance}")

        # Validate line_count
        if self.line_count < 0:
            raise ValueError(f"line_count must be >= 0, got {self.line_count}")


@dataclass
class Transcript:
    """
    Extracted dialogue text for a scene

    Attributes:
        scene_id: Reference to parent Scene
        raw_text: Original caption text with timestamps
        formatted_text: Processed text with speaker labels
        speakers: List of identified speakers in this scene
        word_count: Total words in transcript
        language: Language code (e.g., "en")
    """

    scene_id: str
    raw_text: str
    formatted_text: str
    speakers: List[Speaker] = field(default_factory=list)
    language: str = "en"
    word_count: int = 0

    def __post_init__(self):
        """Validate transcript attributes and compute word count"""
        # Validate scene_id
        if not self.scene_id or not self.scene_id.startswith("scene_"):
            raise ValueError(f"scene_id must start with 'scene_', got {self.scene_id}")

        # Validate that formatted_text includes speaker labels if speakers exist
        if self.speakers and self.formatted_text:
            # Check for at least one speaker label pattern in formatted text
            has_speaker_label = any(
                speaker.label in self.formatted_text for speaker in self.speakers
            )
            if not has_speaker_label:
                raise ValueError(
                    "formatted_text must include speaker labels when speakers are present"
                )

        # Compute word count if not provided
        # Use raw_text for word counting to avoid counting placeholder text
        if self.word_count == 0 and self.raw_text:
            self.word_count = len(self.raw_text.split())


@dataclass
class ProcessingResult:
    """
    Complete output of video processing

    Attributes:
        video: Processed video metadata
        scenes: List of detected scene boundaries
        transcripts: Map of scene_id to Transcript
        speakers: List of all identified speakers
        processing_time: Total processing duration in seconds
        errors: List of non-fatal errors encountered (optional)
    """

    video: Video
    scenes: List[Scene]
    transcripts: Dict[str, Transcript]
    speakers: List[Speaker]
    processing_time: float
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate processing result"""
        # Validate processing_time
        if self.processing_time < 0:
            raise ValueError(f"processing_time must be >= 0, got {self.processing_time}")

        # Validate that all scenes have corresponding transcripts
        scene_ids = {scene.scene_id for scene in self.scenes}
        transcript_scene_ids = set(self.transcripts.keys())

        if scene_ids != transcript_scene_ids:
            missing_transcripts = scene_ids - transcript_scene_ids
            extra_transcripts = transcript_scene_ids - scene_ids
            error_parts = []
            if missing_transcripts:
                error_parts.append(f"missing transcripts for scenes: {missing_transcripts}")
            if extra_transcripts:
                error_parts.append(
                    f"extra transcripts for non-existent scenes: {extra_transcripts}"
                )
            raise ValueError("; ".join(error_parts))

    @property
    def scene_count(self) -> int:
        """Total number of scenes"""
        return len(self.scenes)

    @property
    def speaker_count(self) -> int:
        """Total number of unique speakers"""
        return len(self.speakers)

    @property
    def has_errors(self) -> bool:
        """Whether any errors were encountered during processing"""
        return len(self.errors) > 0
