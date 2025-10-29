"""
Integration tests for error handling scenarios

Tests the system's behavior when processing videos with various error conditions:
- Videos without captions
- Invalid URLs
- Private/unavailable videos
- Edge cases
"""

import pytest
from unittest.mock import Mock, patch
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

from src.main import process_video
from src.url_validator import get_video_id_with_validation, InvalidURLError
from src.transcript_extractor import TranscriptExtractor
from src.logger import (
    CaptionNotAvailableError,
    TranscriptExtractionError,
)
from src.models import Scene, CaptionType


class TestVideosWithoutCaptions:
    """Test processing videos that don't have captions available"""

    def test_process_video_without_captions_creates_empty_transcripts(self, tmp_path):
        """Test that videos without captions still generate scene boundaries and empty transcripts"""
        # Mock URL validator
        with patch("src.main.get_video_id_with_validation") as mock_url_validator:
            mock_url_validator.return_value = "dQw4w9WgXcQ"  # Valid 11-char ID

            # Mock scene detection to return fake scenes
            with patch("src.main.SceneDetector") as mock_scene_detector_class:
                mock_detector = Mock()
                mock_scene_detector_class.return_value = mock_detector

                # Create mock scenes
                mock_scenes = [
                    Scene(
                        scene_id="scene_01", video_id="dQw4w9WgXcQ", start_time=0.0, end_time=30.0
                    ),
                    Scene(
                        scene_id="scene_02", video_id="dQw4w9WgXcQ", start_time=30.0, end_time=60.0
                    ),
                ]
                mock_detector.detect_scenes.return_value = mock_scenes

                # Mock transcript extractor to return no captions
                with patch("src.main.TranscriptExtractor") as mock_extractor_class:
                    mock_extractor = Mock()
                    mock_extractor_class.return_value = mock_extractor

                    # Simulate no captions available - return empty transcripts
                    empty_transcripts = {
                        "scene_01": Mock(
                            scene_id="scene_01",
                            raw_text="",
                            formatted_text="[No captions available]",
                            speakers=[],
                            word_count=0,
                        ),
                        "scene_02": Mock(
                            scene_id="scene_02",
                            raw_text="",
                            formatted_text="[No captions available]",
                            speakers=[],
                            word_count=0,
                        ),
                    }
                    mock_extractor.process_video_transcript.return_value = (
                        empty_transcripts,
                        CaptionType.NONE,
                    )
                    mock_extractor.get_all_speakers.return_value = []

                    # Process video
                    result = process_video(
                        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        output_dir=tmp_path,
                        scene_threshold=30.0,
                        min_scene_duration=15,
                        frame_skip=1,
                        output_formats=["json"],
                        quiet=True,
                        ignore_caption_errors=True,
                    )

                    # Verify result
                    assert result is not None
                    assert len(result.scenes) == 2
                    assert len(result.transcripts) == 2
                    assert result.video.has_captions is False
                    assert result.video.caption_type == CaptionType.NONE

    def test_transcript_extractor_handles_transcripts_disabled(self):
        """Test that TranscriptExtractor gracefully handles TranscriptsDisabled error"""
        extractor = TranscriptExtractor()

        with patch("src.transcript_extractor.YouTubeTranscriptApi") as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api
            mock_api.list.side_effect = TranscriptsDisabled(video_id="test123")

            # Should raise CaptionNotAvailableError
            with pytest.raises(CaptionNotAvailableError) as exc_info:
                extractor.fetch_captions("test123")

            assert "disabled" in str(exc_info.value).lower()

    def test_transcript_extractor_handles_no_transcript_found(self):
        """Test that TranscriptExtractor gracefully handles NoTranscriptFound error"""
        extractor = TranscriptExtractor()

        with patch("src.transcript_extractor.YouTubeTranscriptApi") as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api
            mock_api.list.side_effect = NoTranscriptFound(
                video_id="test123", requested_language_codes=["en"], transcript_data={}
            )

            # Should raise CaptionNotAvailableError
            with pytest.raises(CaptionNotAvailableError) as exc_info:
                extractor.fetch_captions("test123")

            assert "no captions available" in str(exc_info.value).lower()

    def test_empty_transcript_includes_explanatory_note(self):
        """Test that empty transcripts include helpful explanatory notes"""
        extractor = TranscriptExtractor()

        scenes = [
            Scene(scene_id="scene_01", video_id="test", start_time=0.0, end_time=30.0),
        ]

        empty_transcripts = extractor.create_empty_transcripts(
            scenes, note="No captions available for this video"
        )

        assert len(empty_transcripts) == 1
        assert "scene_01" in empty_transcripts
        assert (
            empty_transcripts["scene_01"].formatted_text == "[No captions available for this video]"
        )
        assert empty_transcripts["scene_01"].word_count == 0
        assert len(empty_transcripts["scene_01"].speakers) == 0


class TestInvalidURLs:
    """Test handling of invalid YouTube URLs"""

    def test_invalid_url_format_raises_error(self):
        """Test that invalid URL format raises InvalidURLError"""
        invalid_urls = [
            "not-a-url",
            "http://example.com",
            "https://vimeo.com/123456",
            "youtube.com/invalid",
            "",
        ]

        for url in invalid_urls:
            with pytest.raises(InvalidURLError):
                get_video_id_with_validation(url)

    def test_missing_video_id_raises_error(self):
        """Test that URLs without video IDs raise InvalidURLError"""
        with pytest.raises(InvalidURLError) as exc_info:
            get_video_id_with_validation("https://www.youtube.com/watch")
        # Should contain helpful error message
        assert (
            "Invalid YouTube URL" in str(exc_info.value)
            or "video ID" in str(exc_info.value).lower()
        )

    def test_malformed_video_id_raises_error(self):
        """Test that malformed video IDs raise InvalidURLError"""
        # Video IDs should be 11 characters
        with pytest.raises(InvalidURLError) as exc_info:
            get_video_id_with_validation("https://www.youtube.com/watch?v=short")
        # Should mention the format requirement
        assert "11" in str(exc_info.value) or "format" in str(exc_info.value).lower()


class TestUnavailableVideos:
    """Test handling of private, deleted, or unavailable videos"""

    def test_video_unavailable_raises_error(self):
        """Test that unavailable videos raise appropriate error"""
        extractor = TranscriptExtractor()

        with patch("src.transcript_extractor.YouTubeTranscriptApi") as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api
            mock_api.list.side_effect = VideoUnavailable(video_id="unavailable123")

            # Should raise TranscriptExtractionError
            with pytest.raises(TranscriptExtractionError) as exc_info:
                extractor.fetch_captions("unavailable123")

            assert "unavailable" in str(exc_info.value).lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_scenes_list_handles_gracefully(self):
        """Test that empty scenes list is handled gracefully"""
        extractor = TranscriptExtractor()

        empty_scenes = []
        transcripts = extractor.create_empty_transcripts(empty_scenes)

        assert len(transcripts) == 0

    def test_single_scene_video(self, tmp_path):
        """Test processing a video with only one scene"""
        with patch("src.main.get_video_id_with_validation") as mock_url_validator:
            mock_url_validator.return_value = "dQw4w9WgXcQ"

            with patch("src.main.SceneDetector") as mock_scene_detector_class:
                mock_detector = Mock()
                mock_scene_detector_class.return_value = mock_detector

                # Single scene spanning entire video
                mock_scenes = [
                    Scene(
                        scene_id="scene_01", video_id="dQw4w9WgXcQ", start_time=0.0, end_time=60.0
                    ),
                ]
                mock_detector.detect_scenes.return_value = mock_scenes

                with patch("src.main.TranscriptExtractor") as mock_extractor_class:
                    mock_extractor = Mock()
                    mock_extractor_class.return_value = mock_extractor

                    # Mock transcript
                    transcripts = {
                        "scene_01": Mock(
                            scene_id="scene_01",
                            raw_text="Test transcript",
                            formatted_text="Test transcript",
                            speakers=[],
                            word_count=2,
                        ),
                    }
                    mock_extractor.process_video_transcript.return_value = (
                        transcripts,
                        CaptionType.AUTO_GENERATED,
                    )
                    mock_extractor.get_all_speakers.return_value = []

                    result = process_video(
                        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        output_dir=tmp_path,
                        scene_threshold=30.0,
                        min_scene_duration=15,
                        frame_skip=1,
                        output_formats=["json"],
                        quiet=True,
                    )

                    assert len(result.scenes) == 1
                    assert len(result.transcripts) == 1

    def test_very_short_video_minimum_scene_duration(self):
        """Test that very short videos (< 15 seconds) create valid scenes"""
        # Note: Scene validation requires duration >= 15 seconds
        # This tests the boundary condition
        scene = Scene(
            scene_id="scene_01",
            video_id="test",
            start_time=0.0,
            end_time=15.0,  # Exactly minimum duration
        )

        assert scene.duration == 15.0
        assert scene.scene_id == "scene_01"

    def test_supported_url_formats(self):
        """Test that all supported YouTube URL formats are accepted"""
        supported_urls = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]

        for url, expected_id in supported_urls:
            video_id = get_video_id_with_validation(url)
            assert video_id == expected_id

    def test_url_with_additional_parameters(self):
        """Test that URLs with additional parameters are handled correctly"""
        urls_with_params = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
        ]

        for url in urls_with_params:
            video_id = get_video_id_with_validation(url)
            assert video_id == "dQw4w9WgXcQ"


class TestIgnoreCaptionErrorsFlag:
    """Test the --ignore-caption-errors flag behavior"""

    def test_ignore_caption_errors_suppresses_warning(self, tmp_path, capsys):
        """Test that --ignore-caption-errors flag suppresses warning messages"""
        with patch("src.main.get_video_id_with_validation") as mock_url_validator:
            mock_url_validator.return_value = "dQw4w9WgXcQ"

            with patch("src.main.SceneDetector") as mock_scene_detector_class:
                mock_detector = Mock()
                mock_scene_detector_class.return_value = mock_detector

                mock_scenes = [
                    Scene(
                        scene_id="scene_01", video_id="dQw4w9WgXcQ", start_time=0.0, end_time=30.0
                    ),
                ]
                mock_detector.detect_scenes.return_value = mock_scenes

                with patch("src.main.TranscriptExtractor") as mock_extractor_class:
                    mock_extractor = Mock()
                    mock_extractor_class.return_value = mock_extractor

                    # No captions
                    empty_transcripts = {
                        "scene_01": Mock(
                            scene_id="scene_01",
                            raw_text="",
                            formatted_text="[No captions available]",
                            speakers=[],
                            word_count=0,
                        ),
                    }
                    mock_extractor.process_video_transcript.return_value = (
                        empty_transcripts,
                        CaptionType.NONE,
                    )
                    mock_extractor.get_all_speakers.return_value = []

                    # With ignore_caption_errors=True
                    process_video(
                        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        output_dir=tmp_path,
                        scene_threshold=30.0,
                        min_scene_duration=15,
                        frame_skip=1,
                        output_formats=["json"],
                        quiet=False,  # Not quiet, but should suppress caption warning
                        ignore_caption_errors=True,
                    )

                    captured = capsys.readouterr()
                    # Should not contain the warning about using --ignore-caption-errors
                    assert "--ignore-caption-errors" not in captured.err

    def test_without_ignore_flag_shows_warning(self, tmp_path, capsys):
        """Test that without --ignore-caption-errors, warning is shown"""
        with patch("src.main.get_video_id_with_validation") as mock_url_validator:
            mock_url_validator.return_value = "dQw4w9WgXcQ"

            with patch("src.main.SceneDetector") as mock_scene_detector_class:
                mock_detector = Mock()
                mock_scene_detector_class.return_value = mock_detector

                mock_scenes = [
                    Scene(
                        scene_id="scene_01", video_id="dQw4w9WgXcQ", start_time=0.0, end_time=30.0
                    ),
                ]
                mock_detector.detect_scenes.return_value = mock_scenes

                with patch("src.main.TranscriptExtractor") as mock_extractor_class:
                    mock_extractor = Mock()
                    mock_extractor_class.return_value = mock_extractor

                    # No captions
                    empty_transcripts = {
                        "scene_01": Mock(
                            scene_id="scene_01",
                            raw_text="",
                            formatted_text="[No captions available]",
                            speakers=[],
                            word_count=0,
                        ),
                    }
                    mock_extractor.process_video_transcript.return_value = (
                        empty_transcripts,
                        CaptionType.NONE,
                    )
                    mock_extractor.get_all_speakers.return_value = []

                    # Without ignore_caption_errors
                    process_video(
                        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        output_dir=tmp_path,
                        scene_threshold=30.0,
                        min_scene_duration=15,
                        frame_skip=1,
                        output_formats=["json"],
                        quiet=False,
                        ignore_caption_errors=False,
                    )

                    captured = capsys.readouterr()
                    # Should contain warning and suggestion to use --ignore-caption-errors
                    assert "No captions available" in captured.err or "Warning" in captured.err
