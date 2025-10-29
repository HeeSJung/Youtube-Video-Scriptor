"""
Output Formatting Module

Generates output files in JSON, Markdown, and Plain Text formats.
Handles file system operations and directory creation.
"""

import json
from typing import Dict, List
from datetime import datetime

from src.models import Video, Scene, Transcript, Speaker, ProcessingResult
from src.logger import get_logger
from config.default_config import OutputFormatConfig, DEFAULT_CONFIG

logger = get_logger(__name__)


class OutputFormatter:
    """
    Formats and writes output files for processed video scenes and transcripts.

    Generates:
    - segments.json: Scene metadata and boundaries
    - transcript.md: Markdown formatted transcript

    Example:
        formatter = OutputFormatter()
        formatter.write_output_files(processing_result, video_id="dQw4w9WgXcQ")
    """

    def __init__(self, config: OutputFormatConfig = None):
        """
        Initialize OutputFormatter with configuration.

        Args:
            config: Output format configuration (uses DEFAULT_CONFIG if None)
        """
        self.config = config if config is not None else DEFAULT_CONFIG.output_format
        logger.info(f"Initialized OutputFormatter with output_dir={self.config.output_dir}")

    def format_timecode(self, timestamp: float) -> str:
        """
        Format timestamp as HH:MM:SS.

        Args:
            timestamp: Time in seconds

        Returns:
            Formatted timecode string (e.g., "00:01:23")

        Example:
            >>> formatter.format_timecode(83.5)
            '00:01:23'
        """
        hours = int(timestamp // 3600)
        minutes = int((timestamp % 3600) // 60)
        seconds = int(timestamp % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def generate_segments_json(
        self, video: Video, scenes: List[Scene], processing_time: float
    ) -> dict:
        """
        Generate segments.json content per schema.

        Args:
            video: Video metadata
            scenes: List of detected scenes
            processing_time: Total processing time in seconds

        Returns:
            Dictionary containing segments data

        Schema:
            {
                "video_id": str,
                "video_url": str,
                "total_duration": int,
                "scene_count": int,
                "scenes": [
                    {
                        "scene_id": str,
                        "start_time": float,
                        "end_time": float,
                        "duration": float,
                        "start_timecode": str,
                        "end_timecode": str
                    }
                ],
                "generated_at": str (ISO 8601),
                "processing_time_seconds": float
            }
        """
        segments_data = {
            "video_id": video.video_id,
            "video_url": video.url,
            "total_duration": video.duration,
            "scene_count": len(scenes),
            "scenes": [
                {
                    "scene_id": scene.scene_id,
                    "start_time": scene.start_time,
                    "end_time": scene.end_time,
                    "duration": scene.duration,
                    "start_timecode": scene.start_timecode,
                    "end_timecode": scene.end_timecode,
                }
                for scene in scenes
            ],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "processing_time_seconds": round(processing_time, 2),
        }

        logger.info(f"Generated segments.json with {len(scenes)} scenes")
        return segments_data

    def generate_speakers_json(self, video_id: str, speakers: List[Speaker]) -> dict:
        """
        Generate speakers.json content per schema.

        Note: Speaker identification is a Phase 4 feature.
        For MVP (Phase 3), this returns minimal data.

        Args:
            video_id: YouTube video ID
            speakers: List of identified speakers

        Returns:
            Dictionary containing speaker data

        Schema:
            {
                "video_id": str,
                "speaker_count": int,
                "speakers": [
                    {
                        "speaker_id": str,
                        "label": str,
                        "scenes": [str],
                        "first_appearance": float,
                        "line_count": int
                    }
                ]
            }
        """
        speakers_data = {
            "video_id": video_id,
            "speaker_count": len(speakers),
            "speakers": [
                {
                    "speaker_id": speaker.speaker_id,
                    "label": speaker.label,
                    "scenes": speaker.scenes,
                    "first_appearance": speaker.first_appearance,
                    "line_count": speaker.line_count,
                }
                for speaker in speakers
            ],
        }

        logger.info(f"Generated speakers.json with {len(speakers)} speakers")
        return speakers_data

    def generate_markdown_script(self, scene: Scene, transcript: Transcript) -> str:
        """
        Generate Markdown formatted script for a scene.

        Args:
            scene: Scene metadata
            transcript: Transcript for the scene

        Returns:
            Markdown formatted string

        Format:
            # Scene 01
            **Duration**: 00:00:00 - 00:00:45

            ---

            **Speaker 1**: Dialog text here...

            **Speaker 2**: Response text...

        Note: For MVP without speaker identification, uses generic labels.
        """
        md_content = f"# {scene.scene_id.replace('_', ' ').title()}\n"
        md_content += f"**Duration**: {scene.start_timecode} - {scene.end_timecode}\n\n"
        md_content += "---\n\n"

        # Add transcript content
        if transcript.formatted_text:
            md_content += transcript.formatted_text
        else:
            md_content += "_[No transcript available for this scene]_"

        md_content += "\n"

        logger.debug(f"Generated Markdown for {scene.scene_id}")
        return md_content

    def write_output_files(
        self, result: ProcessingResult, video_id: str, output_formats: List[str] = None
    ) -> Dict[str, List[str]]:
        """
        Write all output files to disk.

        Creates directory structure:
        output/
        └── [video_id]/
            ├── segments.json
            └── transcript.md

        Args:
            result: Complete processing result
            video_id: YouTube video ID
            output_formats: List of formats to generate ['json', 'markdown']
                          (uses config default if None)

        Returns:
            Dictionary mapping format types to list of generated file paths

        Raises:
            OSError: If directory creation or file writing fails
            PermissionError: If insufficient permissions for file operations
        """
        if output_formats is None:
            output_formats = self.config.enabled_formats

        logger.info(f"Writing output files for video {video_id} in formats: {output_formats}")

        # Create directory structure
        video_output_dir = self.config.output_dir / video_id

        try:
            video_output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {video_output_dir}")
        except PermissionError as e:
            logger.error(f"Permission denied creating directory: {e}")
            raise
        except OSError as e:
            logger.error(f"Failed to create directory: {e}")
            raise

        generated_files = {"json": [], "markdown": []}

        # Generate segments.json
        if "json" in output_formats:
            segments_path = video_output_dir / "segments.json"
            segments_data = self.generate_segments_json(
                result.video, result.scenes, result.processing_time
            )

            try:
                with segments_path.open("w", encoding="utf-8") as f:
                    json.dump(segments_data, f, indent=2, ensure_ascii=False)
                generated_files["json"].append(str(segments_path))
                logger.info(f"Wrote segments.json to {segments_path}")
            except (OSError, PermissionError) as e:
                logger.error(f"Failed to write segments.json: {e}")
                raise

        # Generate combined transcript file
        if "markdown" in output_formats:
            transcript_path = video_output_dir / "transcript.md"

            # Combine all scenes into a single transcript
            combined_content = ""
            for scene in result.scenes:
                transcript = result.transcripts.get(scene.scene_id)

                if transcript is None:
                    logger.warning(f"No transcript found for {scene.scene_id}, skipping")
                    continue

                # Generate markdown content for this scene
                scene_content = self.generate_markdown_script(scene, transcript)
                combined_content += scene_content

                # Add separator between scenes if there are multiple
                if len(result.scenes) > 1:
                    combined_content += "\n---\n\n"

            # Remove trailing separator if added
            if combined_content.endswith("\n---\n\n"):
                combined_content = combined_content[:-7]

            # Write the combined transcript
            try:
                with transcript_path.open("w", encoding="utf-8") as f:
                    f.write(combined_content)
                generated_files["markdown"].append(str(transcript_path))
                logger.info(f"Wrote transcript.md")
            except (OSError, PermissionError) as e:
                logger.error(f"Failed to write transcript.md: {e}")
                raise

        total_files = sum(len(files) for files in generated_files.values())
        logger.info(f"Successfully wrote {total_files} output files to {video_output_dir}")

        return generated_files
