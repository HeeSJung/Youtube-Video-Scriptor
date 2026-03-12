"""
Default configuration for YouTube Scene Extractor

This module provides configuration dataclasses with default values and validation
for scene detection, transcript extraction, and output formatting.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class OutputFormatConfig:
    """Configuration for output formatting options"""

    # Output directory for generated files
    output_dir: Path = field(default_factory=lambda: Path("/Users/heesoojung/02 Dev/Transcripts"))

    # Enable JSON output (segments.json)
    enable_json: bool = True

    # Enable Markdown output (scene_XX.md files)
    enable_markdown: bool = True

    # Enable plain text output (scene_XX.txt files) - DEPRECATED, no longer used
    enable_text: bool = False

    def __post_init__(self):
        """Convert output_dir to Path if it's a string"""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

    @property
    def enabled_formats(self) -> list:
        """Get list of enabled output formats"""
        formats = []
        if self.enable_json:
            formats.append("json")
        if self.enable_markdown:
            formats.append("markdown")
        if self.enable_text:
            formats.append("text")
        return formats

    def validate(self) -> None:
        """Validate configuration values"""
        if not (self.enable_json or self.enable_markdown):
            raise ValueError("At least one output format must be enabled (json or markdown)")

        # Ensure output_dir is a Path object
        if not isinstance(self.output_dir, Path):
            raise ValueError(f"output_dir must be a Path object, got {type(self.output_dir)}")

        # Ensure output directory parent exists
        if not self.output_dir.parent.exists():
            raise ValueError(
                f"Parent directory of output_dir does not exist: {self.output_dir.parent}"
            )


@dataclass
class TranscriptConfig:
    """Configuration for transcript extraction"""

    # Prefer manual captions over auto-generated
    prefer_manual_captions: bool = True

    # Languages to try for captions (in order of preference)
    languages: List[str] = field(default_factory=lambda: ["en"])

    # Include timestamps in transcript metadata
    include_timestamps: bool = True

    def validate(self) -> None:
        """Validate configuration values"""
        if not self.languages:
            raise ValueError("At least one language must be specified")


@dataclass
class ProcessingConfig:
    """Configuration for video processing behavior"""

    # Maximum video duration to process (in seconds, 3 hours = 10800)
    max_video_duration: int = 10800

    # Number of retry attempts for network requests
    max_retries: int = 3

    # Timeout for network requests (in seconds)
    request_timeout: int = 30

    # Enable progress indicators during processing
    show_progress: bool = True

    def validate(self) -> None:
        """Validate configuration values"""
        if self.max_video_duration <= 0:
            raise ValueError(f"max_video_duration must be positive, got {self.max_video_duration}")

        if not 1 <= self.max_retries <= 10:
            raise ValueError(f"max_retries must be between 1 and 10, got {self.max_retries}")

        if self.request_timeout <= 0:
            raise ValueError(f"request_timeout must be positive, got {self.request_timeout}")


@dataclass
class Config:
    """Main configuration class combining all configuration sections"""

    output_format: OutputFormatConfig = field(default_factory=OutputFormatConfig)
    transcript: TranscriptConfig = field(default_factory=TranscriptConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)

    def validate(self) -> None:
        """Validate all configuration sections"""
        self.output_format.validate()
        self.transcript.validate()
        self.processing.validate()

    @classmethod
    def from_dict(cls, config_dict: dict) -> "Config":
        """Create Config instance from dictionary

        Args:
            config_dict: Dictionary with configuration values

        Returns:
            Config instance

        Example:
            config = Config.from_dict({
                "output_format": {"output_dir": "./my_output"},
                "transcript": {"languages": ["en", "es"]}
            })
        """
        output_format = OutputFormatConfig(**config_dict.get("output_format", {}))
        transcript = TranscriptConfig(**config_dict.get("transcript", {}))
        processing = ProcessingConfig(**config_dict.get("processing", {}))

        config = cls(
            output_format=output_format,
            transcript=transcript,
            processing=processing,
        )
        config.validate()
        return config


# Default configuration instance
DEFAULT_CONFIG = Config()
