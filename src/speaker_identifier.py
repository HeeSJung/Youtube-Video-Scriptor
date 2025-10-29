#!/usr/bin/env python3
"""
Speaker Identification Module

Identifies and tracks speakers across video scenes using pattern matching
and pause-based detection strategies.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from src.models import Speaker
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SpeakerChange:
    """
    Represents a detected speaker change within a caption sequence

    Attributes:
        caption_index: Index of caption where change occurs
        timestamp: Timestamp of the change
        speaker_id: Identified speaker ID
        confidence: Detection confidence (0-1)
        detection_method: How the change was detected ("pattern" or "pause")
    """

    caption_index: int
    timestamp: float
    speaker_id: str
    confidence: float = 0.8
    detection_method: str = "pattern"


class SpeakerIdentifier:
    """
    Detects and tracks speakers across video scenes

    Uses multiple detection strategies:
    1. Pattern matching: Detects "Speaker Name:", "[Speaker]" format
    2. Pause-based: Infers speaker changes from 2+ second gaps
    3. Cross-scene tracking: Maintains speaker consistency
    """

    def __init__(self):
        """Initialize speaker identifier with empty registry"""
        self.speaker_registry: Dict[str, Speaker] = {}
        self.speaker_counter = 0
        logger.info("Initialized SpeakerIdentifier")

    def detect_speaker_patterns(self, caption_text: str) -> Optional[str]:
        """
        Detect speaker name from caption text patterns

        Supported formats:
        - "Speaker Name:" or "Speaker Name :"
        - "[Speaker Name]" or "[Speaker Name] "
        - "SPEAKER NAME:" (uppercase)

        Args:
            caption_text: Caption text to analyze

        Returns:
            Detected speaker name or None if no pattern found

        Examples:
            >>> detect_speaker_patterns("John: Hello there")
            "John"
            >>> detect_speaker_patterns("[Mary] How are you?")
            "Mary"
            >>> detect_speaker_patterns("This is regular text")
            None
        """
        if not caption_text:
            return None

        # Pattern 1: "Name:" format (most common)
        # Matches: "John:", "Dr. Smith:", "Speaker 1:", "JOHN:" (converts to title case)
        pattern_colon = r"^([A-Z][a-zA-Z\s\.\d]+?):\s*"
        match = re.match(pattern_colon, caption_text.strip())
        if match:
            name = match.group(1).strip()
            # Convert all-uppercase names to title case
            if (
                name.replace(".", "")
                .replace(" ", "")
                .replace("0", "")
                .replace("1", "")
                .replace("2", "")
                .replace("3", "")
                .replace("4", "")
                .replace("5", "")
                .replace("6", "")
                .replace("7", "")
                .replace("8", "")
                .replace("9", "")
                .isupper()
            ):
                name = name.title()
            logger.debug(f"Detected speaker from colon pattern: '{name}'")
            return name

        # Pattern 2: "[Name]" format
        # Matches: "[John]", "[Dr. Smith]", "[Speaker 1]"
        pattern_brackets = r"^\[([A-Z][a-zA-Z\s\.]+?)\]\s*"
        match = re.match(pattern_brackets, caption_text.strip())
        if match:
            name = match.group(1).strip()
            logger.debug(f"Detected speaker from bracket pattern: '{name}'")
            return name

        # Pattern 3: Uppercase name at start (less reliable)
        # Matches: "JOHN:", "DR. SMITH:", "SPEAKER 1:"
        pattern_uppercase = r"^([A-Z][A-Z\s\.\d]+?):\s*"
        match = re.match(pattern_uppercase, caption_text.strip())
        if match:
            name = match.group(1).strip()
            # Convert to title case only if all uppercase (otherwise might be acronym)
            if name.isupper() or name.replace(".", "").replace(" ", "").isupper():
                name = name.title()
            logger.debug(f"Detected speaker from uppercase pattern: '{name}'")
            return name

        return None

    def detect_pause_based_changes(
        self, captions: List[Dict], min_pause_duration: float = 2.0
    ) -> List[SpeakerChange]:
        """
        Detect potential speaker changes based on pauses in speech

        A pause of 2+ seconds between captions often indicates a speaker change,
        especially in interviews, conversations, or presentations.

        Args:
            captions: List of caption dicts with 'text', 'start', 'duration'
            min_pause_duration: Minimum pause to consider as speaker change (default: 2.0s)

        Returns:
            List of detected speaker changes
        """
        changes = []

        for i in range(len(captions) - 1):
            current = captions[i]
            next_caption = captions[i + 1]

            # Calculate pause between current caption end and next caption start
            current_end = current["start"] + current["duration"]
            next_start = next_caption["start"]
            pause_duration = next_start - current_end

            # If pause is significant, mark as potential speaker change
            if pause_duration >= min_pause_duration:
                # Assign alternating speaker IDs based on change count
                speaker_num = (len(changes) + 1) % 2 + 1  # Alternates between 1 and 2
                speaker_id = f"speaker_{speaker_num}"

                change = SpeakerChange(
                    caption_index=i + 1,
                    timestamp=next_start,
                    speaker_id=speaker_id,
                    confidence=0.6,  # Lower confidence for pause-based detection
                    detection_method="pause",
                )
                changes.append(change)
                logger.debug(
                    f"Detected pause-based speaker change at {next_start:.1f}s "
                    f"(pause: {pause_duration:.1f}s) -> {speaker_id}"
                )

        return changes

    def assign_speaker_labels(
        self, captions: List[Dict], speaker_changes: List[SpeakerChange]
    ) -> List[Tuple[str, str]]:
        """
        Assign speaker labels to each caption based on detected changes

        Args:
            captions: List of caption dicts
            speaker_changes: List of detected speaker changes

        Returns:
            List of (caption_text, speaker_id) tuples
        """
        labeled_captions = []
        current_speaker_id = "speaker_1"  # Default to first speaker

        # Sort changes by caption index for sequential processing
        changes_sorted = sorted(speaker_changes, key=lambda c: c.caption_index)
        change_idx = 0

        for i, caption in enumerate(captions):
            # Check if there's a speaker change at this caption
            if change_idx < len(changes_sorted) and changes_sorted[change_idx].caption_index == i:
                current_speaker_id = changes_sorted[change_idx].speaker_id
                change_idx += 1

            labeled_captions.append((caption["text"], current_speaker_id))

        return labeled_captions

    def track_speakers_across_scenes(
        self, scene_speakers: Dict[str, List[str]]
    ) -> Dict[str, Speaker]:
        """
        Maintain speaker consistency across multiple scenes

        Builds a global speaker registry that tracks which speakers appear
        in which scenes, their first appearance, and line counts.

        Args:
            scene_speakers: Map of scene_id -> list of speaker_ids in that scene

        Returns:
            Global speaker registry mapping speaker_id to Speaker object
        """
        registry = {}
        speaker_appearances: Dict[str, List[str]] = {}  # speaker_id -> list of scene_ids
        speaker_first_appearance: Dict[str, str] = {}  # speaker_id -> first scene_id

        # Track which scenes each speaker appears in
        for scene_id, speakers in scene_speakers.items():
            for speaker_id in set(speakers):  # Use set to avoid duplicates
                if speaker_id not in speaker_appearances:
                    speaker_appearances[speaker_id] = []
                    speaker_first_appearance[speaker_id] = scene_id
                speaker_appearances[speaker_id].append(scene_id)

        # Build Speaker objects for registry
        for speaker_id, scenes in speaker_appearances.items():
            # Determine label (use generic "Speaker N" format)
            speaker_num = speaker_id.split("_")[1]
            label = f"Speaker {speaker_num}"

            # Count total lines across all scenes
            line_count = sum(scene_speakers[scene_id].count(speaker_id) for scene_id in scenes)

            speaker = Speaker(
                speaker_id=speaker_id,
                label=label,
                scenes=scenes,
                first_appearance=0.0,  # Will be set when integrating with transcript
                line_count=line_count,
            )
            registry[speaker_id] = speaker
            logger.info(
                f"Registered {speaker_id} ({label}) with {line_count} lines "
                f"across {len(scenes)} scenes"
            )

        return registry

    def get_or_create_speaker(self, speaker_id: str, label: Optional[str] = None) -> Speaker:
        """
        Get existing speaker from registry or create new one

        Args:
            speaker_id: Unique speaker identifier
            label: Display label (optional, will be generated if not provided)

        Returns:
            Speaker object from registry
        """
        if speaker_id not in self.speaker_registry:
            if not label:
                self.speaker_counter += 1
                label = f"Speaker {self.speaker_counter}"

            self.speaker_registry[speaker_id] = Speaker(
                speaker_id=speaker_id, label=label, scenes=[], first_appearance=0.0, line_count=0
            )
            logger.debug(f"Created new speaker: {speaker_id} ({label})")

        return self.speaker_registry[speaker_id]

    def identify_speakers_in_captions(
        self, captions: List[Dict], use_pause_detection: bool = True
    ) -> List[Tuple[str, str]]:
        """
        Main method to identify speakers in a sequence of captions

        Combines pattern matching and pause-based detection for best results.

        Args:
            captions: List of caption dicts with 'text', 'start', 'duration'
            use_pause_detection: Whether to use pause-based detection (default: True)

        Returns:
            List of (caption_text, speaker_id) tuples
        """
        speaker_changes = []

        # Step 1: Detect speakers from text patterns
        for i, caption in enumerate(captions):
            detected_name = self.detect_speaker_patterns(caption["text"])
            if detected_name:
                # Map detected name to speaker_id
                # For now, use simple numbering; could be enhanced with name matching
                speaker_id = f"speaker_{i % 2 + 1}"  # Alternate for demo
                change = SpeakerChange(
                    caption_index=i,
                    timestamp=caption["start"],
                    speaker_id=speaker_id,
                    confidence=0.9,
                    detection_method="pattern",
                )
                speaker_changes.append(change)

        # Step 2: Detect speakers from pauses (if enabled and no patterns found)
        if use_pause_detection and len(speaker_changes) == 0:
            pause_changes = self.detect_pause_based_changes(captions)
            speaker_changes.extend(pause_changes)

        # Step 3: Assign labels to all captions
        labeled_captions = self.assign_speaker_labels(captions, speaker_changes)

        return labeled_captions

    def get_all_speakers(self) -> List[Speaker]:
        """
        Get list of all speakers in the registry

        Returns:
            List of Speaker objects sorted by speaker_id
        """
        return sorted(self.speaker_registry.values(), key=lambda s: s.speaker_id)

    def clear_registry(self):
        """Clear the speaker registry (useful for processing new videos)"""
        self.speaker_registry.clear()
        self.speaker_counter = 0
        logger.info("Cleared speaker registry")
