"""
Unit tests for duration validation fix

Tests that the segment duration check uses (end_sec - start_sec) instead of
checking end_sec alone, so videos that start past 3 hours can be processed
as long as the segment is within the limit.

Regression tests for: "script denies to run if youtube video timeline is ended
over 3 hours, not considering the starting timeline"
"""

import argparse
import pytest

from src.models import Video, CaptionType
from src.main import validate_arguments


class TestVideoDurationModel:
    """Tests for Video model duration validation"""

    def test_video_with_long_duration_is_allowed(self):
        """Video duration > 3 hours is no longer rejected at the model level"""
        video = Video(
            video_id="dQw4w9WgXcQ",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            duration=21600,  # 6 hours
            has_captions=True,
            caption_type=CaptionType.AUTO_GENERATED,
        )
        assert video.duration == 21600

    def test_video_with_exactly_3_hour_duration_is_allowed(self):
        """Video with exactly 3-hour duration (10800s) is accepted"""
        video = Video(
            video_id="dQw4w9WgXcQ",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            duration=10800,  # 3 hours
            has_captions=True,
            caption_type=CaptionType.AUTO_GENERATED,
        )
        assert video.duration == 10800

    def test_video_duration_must_be_positive(self):
        """Video duration must be a positive integer"""
        with pytest.raises(ValueError, match="duration must be a positive integer"):
            Video(
                video_id="dQw4w9WgXcQ",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                duration=0,
                has_captions=True,
                caption_type=CaptionType.AUTO_GENERATED,
            )

    def test_video_duration_must_not_be_negative(self):
        """Video duration must not be negative"""
        with pytest.raises(ValueError, match="duration must be a positive integer"):
            Video(
                video_id="dQw4w9WgXcQ",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                duration=-1,
                has_captions=True,
                caption_type=CaptionType.AUTO_GENERATED,
            )


class TestValidateArgumentsSegmentDuration:
    """Tests for segment duration validation in validate_arguments"""

    def _make_args(self, start_sec, end_sec):
        """Create a minimal Namespace for validate_arguments"""
        return argparse.Namespace(
            formats="json,markdown",
            verbose=False,
            quiet=False,
            start_sec=start_sec,
            end_sec=end_sec,
        )

    def test_segment_from_3hrs_to_6hrs_passes(self):
        """Core regression test: segment from 3hrs (10800s) to 6hrs (21600s) should pass.
        The segment duration is exactly 3 hours = 10800s which is within the limit."""
        args = self._make_args(start_sec=10800, end_sec=21600)
        # Should not raise
        validate_arguments(args)

    def test_segment_starting_after_3hrs_within_limit_passes(self):
        """Segment starting after 3hrs, with duration < 3hrs, should pass"""
        args = self._make_args(start_sec=14400, end_sec=21600)  # 4hrs to 6hrs = 2hr segment
        # Should not raise
        validate_arguments(args)

    def test_segment_exceeding_max_duration_fails(self):
        """Segment longer than 3 hours should fail with informative error"""
        args = self._make_args(start_sec=0, end_sec=14400)  # 0 to 4hrs = 4hr segment
        with pytest.raises(ValueError, match="segment duration"):
            validate_arguments(args)

    def test_error_message_mentions_segment_not_end_timestamp(self):
        """Error message should explain that the limit is on segment duration, not end_sec"""
        args = self._make_args(start_sec=0, end_sec=14400)
        with pytest.raises(ValueError) as exc_info:
            validate_arguments(args)
        error_msg = str(exc_info.value)
        assert "end_sec - start_sec" in error_msg or "segment" in error_msg.lower()

    def test_segment_exactly_at_max_duration_passes(self):
        """Segment of exactly max duration (10800s) should pass"""
        args = self._make_args(start_sec=0, end_sec=10800)
        # Should not raise
        validate_arguments(args)

    def test_no_timestamps_skips_segment_validation(self):
        """When no timestamps are provided, segment validation is skipped"""
        args = argparse.Namespace(
            formats="json,markdown",
            verbose=False,
            quiet=False,
            start_sec=None,
            end_sec=None,
        )
        # Should not raise
        validate_arguments(args)
