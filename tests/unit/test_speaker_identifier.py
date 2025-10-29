"""
Unit tests for speaker_identifier module

Tests speaker pattern detection, pause-based changes, and speaker consistency.
"""

from src.speaker_identifier import SpeakerIdentifier, SpeakerChange


class TestSpeakerPatternDetection:
    """Test speaker name pattern detection from captions"""

    def setup_method(self):
        """Initialize speaker identifier for each test"""
        self.identifier = SpeakerIdentifier()

    def test_detect_colon_pattern(self):
        """Test detection of 'Name:' pattern"""
        # Standard format
        assert self.identifier.detect_speaker_patterns("John: Hello there") == "John"
        assert self.identifier.detect_speaker_patterns("Mary: How are you?") == "Mary"

        # With space before colon
        assert self.identifier.detect_speaker_patterns("Dr. Smith : Good morning") == "Dr. Smith"

        # Multiple words
        assert self.identifier.detect_speaker_patterns("Jane Doe: Nice to meet you") == "Jane Doe"

    def test_detect_bracket_pattern(self):
        """Test detection of '[Name]' pattern"""
        assert self.identifier.detect_speaker_patterns("[John] Hello there") == "John"
        assert self.identifier.detect_speaker_patterns("[Mary] How are you?") == "Mary"
        assert self.identifier.detect_speaker_patterns("[Dr. Smith] Good morning") == "Dr. Smith"

    def test_detect_uppercase_pattern(self):
        """Test detection of 'UPPERCASE NAME:' pattern"""
        assert self.identifier.detect_speaker_patterns("JOHN: Hello there") == "John"
        assert self.identifier.detect_speaker_patterns("MARY JANE: How are you?") == "Mary Jane"
        assert self.identifier.detect_speaker_patterns("DR. SMITH: Good morning") == "Dr. Smith"

    def test_no_pattern_detected(self):
        """Test that None is returned when no pattern is found"""
        assert self.identifier.detect_speaker_patterns("This is regular text") is None
        assert self.identifier.detect_speaker_patterns("hello world") is None
        assert self.identifier.detect_speaker_patterns("") is None
        assert self.identifier.detect_speaker_patterns("1234: numbers") is None

    def test_pattern_priority(self):
        """Test that colon pattern takes priority over bracket pattern"""
        # Colon pattern should be detected first
        result = self.identifier.detect_speaker_patterns("John: [Mary] Hello")
        assert result == "John"


class TestPauseBasedDetection:
    """Test pause-based speaker change detection"""

    def setup_method(self):
        """Initialize speaker identifier for each test"""
        self.identifier = SpeakerIdentifier()

    def test_detect_single_pause(self):
        """Test detection of single pause between captions"""
        captions = [
            {"text": "Hello there", "start": 0.0, "duration": 2.0},
            {"text": "How are you?", "start": 4.5, "duration": 2.0},  # 2.5s pause
        ]

        changes = self.identifier.detect_pause_based_changes(captions, min_pause_duration=2.0)

        assert len(changes) == 1
        assert changes[0].caption_index == 1
        assert changes[0].timestamp == 4.5
        assert changes[0].detection_method == "pause"

    def test_detect_multiple_pauses(self):
        """Test detection of multiple pauses"""
        captions = [
            {"text": "First", "start": 0.0, "duration": 2.0},
            {"text": "Second", "start": 4.0, "duration": 2.0},  # 2.0s pause
            {"text": "Third", "start": 8.5, "duration": 2.0},  # 2.5s pause
        ]

        changes = self.identifier.detect_pause_based_changes(captions, min_pause_duration=2.0)

        assert len(changes) == 2
        assert changes[0].caption_index == 1
        assert changes[1].caption_index == 2

    def test_no_pause_detection(self):
        """Test that no changes are detected when pauses are small"""
        captions = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "World", "start": 2.5, "duration": 2.0},  # 0.5s pause
            {"text": "Test", "start": 5.0, "duration": 2.0},  # 0.5s pause
        ]

        changes = self.identifier.detect_pause_based_changes(captions, min_pause_duration=2.0)

        assert len(changes) == 0

    def test_custom_pause_duration(self):
        """Test custom minimum pause duration"""
        captions = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "World", "start": 5.0, "duration": 2.0},  # 3.0s pause
        ]

        # With 4.0s threshold, no change should be detected
        changes = self.identifier.detect_pause_based_changes(captions, min_pause_duration=4.0)
        assert len(changes) == 0

        # With 2.0s threshold, change should be detected
        changes = self.identifier.detect_pause_based_changes(captions, min_pause_duration=2.0)
        assert len(changes) == 1


class TestSpeakerLabelAssignment:
    """Test speaker label assignment to captions"""

    def setup_method(self):
        """Initialize speaker identifier for each test"""
        self.identifier = SpeakerIdentifier()

    def test_assign_single_speaker(self):
        """Test assignment when no speaker changes detected"""
        captions = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "World", "start": 2.0, "duration": 2.0},
        ]
        changes = []  # No speaker changes

        labeled = self.identifier.assign_speaker_labels(captions, changes)

        assert len(labeled) == 2
        assert labeled[0] == ("Hello", "speaker_1")
        assert labeled[1] == ("World", "speaker_1")

    def test_assign_with_speaker_changes(self):
        """Test assignment with speaker changes"""
        captions = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "How are you?", "start": 2.0, "duration": 2.0},
            {"text": "Good thanks", "start": 4.0, "duration": 2.0},
        ]

        changes = [
            SpeakerChange(
                caption_index=1,
                timestamp=2.0,
                speaker_id="speaker_2",
                confidence=0.8,
                detection_method="pause",
            )
        ]

        labeled = self.identifier.assign_speaker_labels(captions, changes)

        assert len(labeled) == 3
        assert labeled[0] == ("Hello", "speaker_1")
        assert labeled[1] == ("How are you?", "speaker_2")
        assert labeled[2] == ("Good thanks", "speaker_2")

    def test_assign_multiple_changes(self):
        """Test assignment with multiple speaker changes"""
        captions = [
            {"text": "First", "start": 0.0, "duration": 1.0},
            {"text": "Second", "start": 1.0, "duration": 1.0},
            {"text": "Third", "start": 2.0, "duration": 1.0},
            {"text": "Fourth", "start": 3.0, "duration": 1.0},
        ]

        changes = [
            SpeakerChange(caption_index=1, timestamp=1.0, speaker_id="speaker_2"),
            SpeakerChange(caption_index=3, timestamp=3.0, speaker_id="speaker_1"),
        ]

        labeled = self.identifier.assign_speaker_labels(captions, changes)

        assert labeled[0][1] == "speaker_1"
        assert labeled[1][1] == "speaker_2"
        assert labeled[2][1] == "speaker_2"
        assert labeled[3][1] == "speaker_1"


class TestSpeakerTracking:
    """Test speaker tracking across scenes"""

    def setup_method(self):
        """Initialize speaker identifier for each test"""
        self.identifier = SpeakerIdentifier()

    def test_track_single_speaker_across_scenes(self):
        """Test tracking single speaker across multiple scenes"""
        scene_speakers = {
            "scene_01": ["speaker_1", "speaker_1", "speaker_1"],
            "scene_02": ["speaker_1", "speaker_1"],
        }

        registry = self.identifier.track_speakers_across_scenes(scene_speakers)

        assert len(registry) == 1
        assert "speaker_1" in registry
        assert registry["speaker_1"].speaker_id == "speaker_1"
        assert registry["speaker_1"].label == "Speaker 1"
        assert len(registry["speaker_1"].scenes) == 2
        assert registry["speaker_1"].line_count == 5

    def test_track_multiple_speakers_across_scenes(self):
        """Test tracking multiple speakers across scenes"""
        scene_speakers = {
            "scene_01": ["speaker_1", "speaker_2", "speaker_1"],
            "scene_02": ["speaker_2", "speaker_1"],
            "scene_03": ["speaker_1"],
        }

        registry = self.identifier.track_speakers_across_scenes(scene_speakers)

        assert len(registry) == 2
        assert "speaker_1" in registry
        assert "speaker_2" in registry

        # Check speaker_1
        assert len(registry["speaker_1"].scenes) == 3
        assert registry["speaker_1"].line_count == 4

        # Check speaker_2
        assert len(registry["speaker_2"].scenes) == 2
        assert registry["speaker_2"].line_count == 2

    def test_track_empty_scenes(self):
        """Test tracking with empty scenes"""
        scene_speakers = {
            "scene_01": [],
            "scene_02": ["speaker_1"],
        }

        registry = self.identifier.track_speakers_across_scenes(scene_speakers)

        assert len(registry) == 1
        assert registry["speaker_1"].line_count == 1


class TestSpeakerRegistry:
    """Test speaker registry management"""

    def setup_method(self):
        """Initialize speaker identifier for each test"""
        self.identifier = SpeakerIdentifier()

    def test_get_or_create_new_speaker(self):
        """Test creating new speaker in registry"""
        speaker = self.identifier.get_or_create_speaker("speaker_1", "John")

        assert speaker.speaker_id == "speaker_1"
        assert speaker.label == "John"
        assert "speaker_1" in self.identifier.speaker_registry

    def test_get_existing_speaker(self):
        """Test getting existing speaker from registry"""
        # Create speaker first
        speaker1 = self.identifier.get_or_create_speaker("speaker_1", "John")

        # Get same speaker again
        speaker2 = self.identifier.get_or_create_speaker("speaker_1", "Different Name")

        # Should return same speaker instance
        assert speaker1 is speaker2
        assert speaker1.label == "John"  # Original label preserved

    def test_get_or_create_without_label(self):
        """Test creating speaker without providing label"""
        speaker = self.identifier.get_or_create_speaker("speaker_5")

        assert speaker.speaker_id == "speaker_5"
        assert speaker.label == "Speaker 1"  # Auto-generated label

    def test_get_all_speakers(self):
        """Test getting all speakers from registry"""
        self.identifier.get_or_create_speaker("speaker_2", "Alice")
        self.identifier.get_or_create_speaker("speaker_1", "Bob")
        self.identifier.get_or_create_speaker("speaker_3", "Carol")

        all_speakers = self.identifier.get_all_speakers()

        assert len(all_speakers) == 3
        # Should be sorted by speaker_id
        assert all_speakers[0].speaker_id == "speaker_1"
        assert all_speakers[1].speaker_id == "speaker_2"
        assert all_speakers[2].speaker_id == "speaker_3"

    def test_clear_registry(self):
        """Test clearing the speaker registry"""
        self.identifier.get_or_create_speaker("speaker_1", "John")
        self.identifier.get_or_create_speaker("speaker_2", "Mary")

        assert len(self.identifier.speaker_registry) == 2

        self.identifier.clear_registry()

        assert len(self.identifier.speaker_registry) == 0
        assert self.identifier.speaker_counter == 0


class TestIntegratedSpeakerIdentification:
    """Test full speaker identification workflow"""

    def setup_method(self):
        """Initialize speaker identifier for each test"""
        self.identifier = SpeakerIdentifier()

    def test_identify_with_name_patterns(self):
        """Test identification using name patterns in captions"""
        captions = [
            {"text": "John: Hello there", "start": 0.0, "duration": 2.0},
            {"text": "How are you doing?", "start": 2.0, "duration": 2.0},
            {"text": "Mary: I am good thanks", "start": 4.0, "duration": 2.0},
        ]

        labeled = self.identifier.identify_speakers_in_captions(captions)

        assert len(labeled) == 3
        # Note: Current implementation uses simple speaker numbering
        assert all(speaker_id in ["speaker_1", "speaker_2"] for _, speaker_id in labeled)

    def test_identify_with_pause_detection(self):
        """Test identification using pause-based detection"""
        captions = [
            {"text": "Hello there", "start": 0.0, "duration": 2.0},
            {"text": "How are you?", "start": 4.5, "duration": 2.0},  # 2.5s pause
            {"text": "I am good", "start": 7.0, "duration": 2.0},  # 0.5s pause
        ]

        labeled = self.identifier.identify_speakers_in_captions(captions, use_pause_detection=True)

        assert len(labeled) == 3
        # Should detect speaker change at pause
        assert labeled[0][1] != labeled[1][1] or len(set(sid for _, sid in labeled)) > 1

    def test_identify_without_pause_detection(self):
        """Test identification with pause detection disabled"""
        captions = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "World", "start": 4.0, "duration": 2.0},  # 2.0s pause
        ]

        labeled = self.identifier.identify_speakers_in_captions(captions, use_pause_detection=False)

        assert len(labeled) == 2
        # Without pause detection and no patterns, should all be same speaker
        assert labeled[0][1] == labeled[1][1]
