"""
Transcript extraction module using youtube-transcript-api

This module provides functionality to fetch and process YouTube captions/transcripts,
including automatic detection of caption types and segmentation by scene boundaries.
"""

from typing import List, Dict, Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

from src.models import Scene, Transcript, Speaker, CaptionType
from src.logger import get_logger, TranscriptExtractionError, CaptionNotAvailableError
from src.speaker_identifier import SpeakerIdentifier
from config.default_config import TranscriptConfig

logger = get_logger(__name__)


class TranscriptExtractor:
    """Extracts and processes transcripts from YouTube videos"""

    def __init__(
        self, config: Optional[TranscriptConfig] = None, enable_speaker_detection: bool = True
    ):
        """
        Initialize TranscriptExtractor

        Args:
            config: Transcript configuration (uses defaults if None)
            enable_speaker_detection: Enable speaker identification (default: True)
        """
        from config.default_config import DEFAULT_CONFIG

        self.config = config or DEFAULT_CONFIG.transcript
        self.enable_speaker_detection = enable_speaker_detection
        self.speaker_identifier = SpeakerIdentifier() if enable_speaker_detection else None
        logger.info(
            f"Initialized TranscriptExtractor with languages={self.config.languages}, "
            f"prefer_manual={self.config.prefer_manual_captions}, "
            f"speaker_detection={enable_speaker_detection}"
        )

    def fetch_captions(self, video_id: str) -> Tuple[List[Dict], CaptionType]:
        """
        Fetch captions/transcript for a YouTube video

        Args:
            video_id: YouTube video ID (11 characters)

        Returns:
            Tuple of (caption data list, caption type)
            Caption data is list of dicts with 'text', 'start', 'duration' keys

        Raises:
            CaptionNotAvailableError: If no captions are available
            TranscriptExtractionError: If fetching fails for other reasons

        Example:
            >>> extractor = TranscriptExtractor()
            >>> captions, caption_type = extractor.fetch_captions("dQw4w9WgXcQ")
            >>> print(f"Got {len(captions)} captions of type {caption_type.value}")
        """
        logger.info(f"Fetching captions for video: {video_id}")

        try:
            # Get list of available transcripts
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)

            # Try to get captions based on configuration
            caption_data, caption_type = self._get_best_transcript(
                transcript_list, self.config.languages
            )

            logger.info(
                f"Successfully fetched {len(caption_data)} caption entries "
                f"(type: {caption_type.value})"
            )
            return caption_data, caption_type

        except TranscriptsDisabled:
            logger.warning(f"Transcripts are disabled for video: {video_id}")
            raise CaptionNotAvailableError(f"Captions are disabled for this video (ID: {video_id})")
        except NoTranscriptFound:
            logger.warning(f"No transcript found for video: {video_id}")
            raise CaptionNotAvailableError(
                f"No captions available for this video (ID: {video_id}) "
                f"in languages: {self.config.languages}"
            )
        except VideoUnavailable:
            logger.error(f"Video unavailable: {video_id}")
            raise TranscriptExtractionError(f"Video is unavailable (ID: {video_id})")
        except Exception as e:
            logger.error(f"Failed to fetch captions: {str(e)}")
            raise TranscriptExtractionError(f"Error fetching captions: {str(e)}")

    def _get_best_transcript(
        self, transcript_list, languages: List[str]
    ) -> Tuple[List[Dict], CaptionType]:
        """
        Get the best available transcript based on configuration

        Args:
            transcript_list: YouTubeTranscriptApi transcript list object
            languages: Preferred languages in priority order

        Returns:
            Tuple of (transcript data, caption type)

        Note:
            Prioritizes manual captions over auto-generated if prefer_manual_captions is True
        """
        # Try to find manual captions first if preferred
        if self.config.prefer_manual_captions:
            for language in languages:
                try:
                    # Try manual transcript
                    transcript = transcript_list.find_manually_created_transcript([language])
                    caption_data = transcript.fetch()
                    logger.info(f"Found manual captions in {language}")
                    return caption_data, CaptionType.MANUAL
                except NoTranscriptFound:
                    continue

        # Try auto-generated captions
        for language in languages:
            try:
                transcript = transcript_list.find_generated_transcript([language])
                caption_data = transcript.fetch()
                logger.info(f"Found auto-generated captions in {language}")
                return caption_data, CaptionType.AUTO_GENERATED
            except NoTranscriptFound:
                continue

        # If prefer_manual_captions is False, try any available transcript
        if not self.config.prefer_manual_captions:
            for language in languages:
                try:
                    transcript = transcript_list.find_manually_created_transcript([language])
                    caption_data = transcript.fetch()
                    logger.info(f"Found manual captions in {language}")
                    return caption_data, CaptionType.MANUAL
                except NoTranscriptFound:
                    continue

        # No captions found
        raise NoTranscriptFound(video_id="", requested_language_codes=languages, transcript_data={})

    def _normalize_caption(self, caption) -> Dict:
        """
        Normalize caption data to dict format (handles both dict and object formats)

        Args:
            caption: Caption data (either dict or FetchedTranscriptSnippet object)

        Returns:
            Dictionary with 'text', 'start', 'duration' keys
        """
        try:
            # Try dict format first (backwards compatibility)
            if isinstance(caption, dict):
                return caption

            # Handle object format (FetchedTranscriptSnippet)
            return {
                "text": caption.text if hasattr(caption, "text") else caption["text"],
                "start": caption.start if hasattr(caption, "start") else caption["start"],
                "duration": (
                    caption.duration if hasattr(caption, "duration") else caption["duration"]
                ),
            }
        except (AttributeError, KeyError, TypeError) as e:
            logger.warning(f"Unexpected caption format, using defaults: {e}")
            # Return safe defaults
            return {"text": "", "start": 0.0, "duration": 0.0}

    def segment_transcript_by_scenes(
        self, caption_data: List, scenes: List[Scene]
    ) -> Dict[str, List[Dict]]:
        """
        Segment transcript by scene boundaries

        Args:
            caption_data: List of captions (dicts or FetchedTranscriptSnippet objects)
            scenes: List of Scene objects with start/end times

        Returns:
            Dictionary mapping scene_id to list of caption entries (normalized to dicts)

        Example:
            >>> captions = [{'text': 'Hello', 'start': 1.0, 'duration': 2.0}]
            >>> scenes = [Scene('scene_01', 'video_id', 0.0, 30.0)]
            >>> segmented = extractor.segment_transcript_by_scenes(captions, scenes)
            >>> print(segmented['scene_01'])
        """
        logger.info(f"Segmenting {len(caption_data)} captions into {len(scenes)} scenes")

        scene_transcripts = {scene.scene_id: [] for scene in scenes}

        for caption in caption_data:
            # Normalize caption to dict format
            normalized_caption = self._normalize_caption(caption)
            caption_start = normalized_caption["start"]
            caption_end = caption_start + normalized_caption["duration"]

            # Find which scene(s) this caption belongs to
            for scene in scenes:
                # Caption overlaps with scene if:
                # caption_start < scene.end_time AND caption_end > scene.start_time
                if caption_start < scene.end_time and caption_end > scene.start_time:
                    scene_transcripts[scene.scene_id].append(normalized_caption)
                    # Caption could span multiple scenes, so don't break

        # Log statistics
        for scene_id, captions in scene_transcripts.items():
            logger.debug(f"{scene_id}: {len(captions)} caption entries")

        return scene_transcripts

    def create_transcript_objects(
        self,
        scene_transcripts: Dict[str, List[Dict]],
        caption_type: CaptionType,
        language: str = "en",
    ) -> Dict[str, Transcript]:
        """
        Create Transcript objects for each scene with speaker identification

        Args:
            scene_transcripts: Dictionary mapping scene_id to caption entries
            caption_type: Type of captions (manual or auto-generated)
            language: Language code

        Returns:
            Dictionary mapping scene_id to Transcript object

        Note:
            If speaker detection is enabled, identifies speakers using pattern matching
            and pause-based detection, then formats transcript with speaker labels.
        """
        logger.info(f"Creating Transcript objects for {len(scene_transcripts)} scenes")

        transcripts = {}
        scene_speakers_map: Dict[str, List[str]] = {}  # For tracking across scenes

        for scene_id, captions in scene_transcripts.items():
            if not captions:
                # Handle empty scenes
                transcript = Transcript(
                    scene_id=scene_id,
                    raw_text="",
                    formatted_text="",
                    speakers=[],
                    language=language,
                    word_count=0,
                )
                transcripts[scene_id] = transcript
                scene_speakers_map[scene_id] = []
                continue

            # Combine caption text for raw_text
            raw_text = " ".join(caption["text"] for caption in captions)

            # Speaker detection and formatting
            if self.enable_speaker_detection and self.speaker_identifier:
                # Identify speakers in this scene's captions
                labeled_captions = self.speaker_identifier.identify_speakers_in_captions(captions)

                # Format text with speaker labels
                formatted_lines = []
                current_speaker = None
                current_speaker_text = []

                for caption_text, speaker_id in labeled_captions:
                    if speaker_id != current_speaker:
                        # Speaker change - flush previous speaker's text
                        if current_speaker and current_speaker_text:
                            speaker_obj = self.speaker_identifier.get_or_create_speaker(
                                current_speaker
                            )
                            formatted_lines.append(
                                f"**{speaker_obj.label}**: {' '.join(current_speaker_text)}"
                            )
                            current_speaker_text = []

                        current_speaker = speaker_id

                    current_speaker_text.append(caption_text)

                # Flush remaining text
                if current_speaker and current_speaker_text:
                    speaker_obj = self.speaker_identifier.get_or_create_speaker(current_speaker)
                    formatted_lines.append(
                        f"**{speaker_obj.label}**: {' '.join(current_speaker_text)}"
                    )

                formatted_text = "\n\n".join(formatted_lines)

                # Track unique speakers in this scene
                unique_speakers = list(set(speaker_id for _, speaker_id in labeled_captions))
                scene_speakers_map[scene_id] = unique_speakers

                # Get Speaker objects for this scene
                speakers = [
                    self.speaker_identifier.get_or_create_speaker(speaker_id)
                    for speaker_id in unique_speakers
                ]
            else:
                # No speaker detection - use raw text
                formatted_text = raw_text
                speakers = []
                scene_speakers_map[scene_id] = []

            # Create Transcript object
            transcript = Transcript(
                scene_id=scene_id,
                raw_text=raw_text,
                formatted_text=formatted_text,
                speakers=speakers,
                language=language,
                word_count=len(raw_text.split()) if raw_text else 0,
            )

            transcripts[scene_id] = transcript

        # Track speakers across scenes for consistency
        if self.enable_speaker_detection and self.speaker_identifier:
            self.speaker_identifier.track_speakers_across_scenes(scene_speakers_map)

        logger.info(f"Created {len(transcripts)} Transcript objects")
        return transcripts

    def create_empty_transcripts(
        self, scenes: List[Scene], note: str = "No captions available"
    ) -> Dict[str, Transcript]:
        """
        Create empty transcript objects for videos without captions

        Args:
            scenes: List of Scene objects
            note: Explanatory note to include in transcripts

        Returns:
            Dictionary mapping scene_id to empty Transcript objects

        Note:
            This enables graceful handling when captions are not available
        """
        logger.warning(f"Creating empty transcripts for {len(scenes)} scenes")

        transcripts = {}

        for scene in scenes:
            transcript = Transcript(
                scene_id=scene.scene_id,
                raw_text="",
                formatted_text=f"[{note}]",
                speakers=[],
                language="",
                word_count=0,
            )
            transcripts[scene.scene_id] = transcript

        logger.info(f"Created {len(transcripts)} empty Transcript objects")
        return transcripts

    def process_video_transcript(
        self, video_id: str, scenes: List[Scene], start_time: float = None, end_time: float = None
    ) -> Tuple[Dict[str, Transcript], CaptionType]:
        """
        Complete workflow: fetch captions and create transcripts for all scenes

        Args:
            video_id: YouTube video ID
            scenes: List of Scene objects
            start_time: Optional start time in seconds to filter captions
            end_time: Optional end time in seconds to filter captions

        Returns:
            Tuple of (transcripts dictionary, caption type)

        Note:
            Returns empty transcripts if captions are not available
        """
        logger.info(f"Processing transcript for video {video_id} with {len(scenes)} scenes")

        try:
            # Fetch captions
            caption_data, caption_type = self.fetch_captions(video_id)

            # Filter by time range if provided
            if start_time is not None and end_time is not None:
                logger.info(f"Filtering captions to time range: {start_time}s - {end_time}s")
                original_count = len(caption_data)
                caption_data = [
                    c for c in caption_data
                    if start_time <= c.start < end_time
                ]
                logger.info(f"Filtered captions: {original_count} -> {len(caption_data)} entries")

            # Segment by scenes
            scene_transcripts = self.segment_transcript_by_scenes(caption_data, scenes)

            # Create Transcript objects
            transcripts = self.create_transcript_objects(
                scene_transcripts,
                caption_type,
                language=self.config.languages[0] if self.config.languages else "en",
            )

            return transcripts, caption_type

        except CaptionNotAvailableError as e:
            logger.warning(f"Captions not available: {str(e)}")
            # Return empty transcripts
            transcripts = self.create_empty_transcripts(
                scenes, note="No captions available for this video"
            )
            return transcripts, CaptionType.NONE

        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            raise TranscriptExtractionError(f"Failed to process transcript: {str(e)}")

    def get_all_speakers(self) -> List[Speaker]:
        """
        Get list of all identified speakers across the video

        Returns:
            List of Speaker objects sorted by speaker_id

        Note:
            This should be called after process_video_transcript() to get
            the full speaker registry
        """
        if not self.enable_speaker_detection or not self.speaker_identifier:
            return []

        return self.speaker_identifier.get_all_speakers()
