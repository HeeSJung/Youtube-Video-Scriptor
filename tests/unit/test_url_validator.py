"""
Unit tests for URL validator module

Tests cover:
- Valid URL formats (youtube.com/watch, youtu.be, embed, /v/)
- Invalid URL formats
- Edge cases and error handling
"""

import pytest
from src.url_validator import (
    validate_youtube_url,
    extract_video_id,
    format_youtube_url,
    get_video_id_with_validation,
    InvalidURLError,
)


class TestValidateYoutubeUrl:
    """Test cases for validate_youtube_url function"""

    def test_valid_watch_url(self):
        """Test standard youtube.com/watch?v= URL"""
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_valid_short_url(self):
        """Test shortened youtu.be URL"""
        assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_valid_embed_url(self):
        """Test youtube.com/embed URL"""
        assert validate_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ") is True

    def test_valid_v_url(self):
        """Test youtube.com/v/ URL"""
        assert validate_youtube_url("https://www.youtube.com/v/dQw4w9WgXcQ") is True

    def test_valid_mobile_url(self):
        """Test mobile m.youtube.com URL"""
        assert validate_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_url_with_additional_params(self):
        """Test URL with timestamp and other parameters"""
        assert (
            validate_youtube_url(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&feature=youtu.be"
            )
            is True
        )

    def test_invalid_url_wrong_domain(self):
        """Test URL from non-YouTube domain"""
        assert validate_youtube_url("https://www.vimeo.com/12345") is False

    def test_invalid_url_no_video_id(self):
        """Test YouTube URL without video ID"""
        assert validate_youtube_url("https://www.youtube.com/") is False

    def test_invalid_url_empty_string(self):
        """Test empty string"""
        assert validate_youtube_url("") is False

    def test_invalid_url_not_string(self):
        """Test non-string input"""
        assert validate_youtube_url(None) is False
        assert validate_youtube_url(12345) is False


class TestExtractVideoId:
    """Test cases for extract_video_id function"""

    def test_extract_from_watch_url(self):
        """Test extraction from standard watch URL"""
        video_id = extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_from_short_url(self):
        """Test extraction from youtu.be URL"""
        video_id = extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_from_embed_url(self):
        """Test extraction from embed URL"""
        video_id = extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_from_v_url(self):
        """Test extraction from /v/ URL"""
        video_id = extract_video_id("https://www.youtube.com/v/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_with_query_params(self):
        """Test extraction when URL has multiple query parameters"""
        video_id = extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=PLtest")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_11_chars(self):
        """Test that extracted video ID is exactly 11 characters"""
        video_id = extract_video_id("https://www.youtube.com/watch?v=_-012345678")
        assert len(video_id) == 11
        assert video_id == "_-012345678"

    def test_extract_invalid_url_raises_error(self):
        """Test that invalid URL raises InvalidURLError"""
        with pytest.raises(InvalidURLError):
            extract_video_id("https://www.vimeo.com/12345")

    def test_extract_empty_url_raises_error(self):
        """Test that empty URL raises InvalidURLError"""
        with pytest.raises(InvalidURLError):
            extract_video_id("")

    def test_extract_none_url_raises_error(self):
        """Test that None raises InvalidURLError"""
        with pytest.raises(InvalidURLError):
            extract_video_id(None)

    def test_extract_malformed_url_raises_error(self):
        """Test that malformed URL raises InvalidURLError"""
        with pytest.raises(InvalidURLError):
            extract_video_id("not-a-url")

    def test_extract_youtube_url_no_video_id(self):
        """Test YouTube URL without video ID raises error"""
        with pytest.raises(InvalidURLError):
            extract_video_id("https://www.youtube.com/")


class TestFormatYoutubeUrl:
    """Test cases for format_youtube_url function"""

    def test_format_valid_video_id(self):
        """Test formatting valid video ID"""
        url = format_youtube_url("dQw4w9WgXcQ")
        assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_format_video_id_with_special_chars(self):
        """Test formatting video ID with hyphens and underscores"""
        url = format_youtube_url("_-012345678")
        assert url == "https://www.youtube.com/watch?v=_-012345678"

    def test_format_invalid_video_id_length(self):
        """Test that invalid video ID length raises error"""
        with pytest.raises(InvalidURLError):
            format_youtube_url("short")

    def test_format_invalid_video_id_chars(self):
        """Test that invalid characters raise error"""
        with pytest.raises(InvalidURLError):
            format_youtube_url("invalid@#$%")


class TestGetVideoIdWithValidation:
    """Test cases for get_video_id_with_validation function"""

    def test_get_valid_video_id(self):
        """Test successful extraction and validation"""
        video_id = get_video_id_with_validation("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_get_video_id_from_various_formats(self):
        """Test extraction from all supported URL formats"""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
        ]

        for url in urls:
            video_id = get_video_id_with_validation(url)
            assert video_id == "dQw4w9WgXcQ"

    def test_get_video_id_invalid_url_detailed_error(self):
        """Test that invalid URL raises error with detailed message"""
        with pytest.raises(InvalidURLError) as exc_info:
            get_video_id_with_validation("invalid-url")

        error_message = str(exc_info.value)
        assert "Invalid YouTube URL" in error_message
        assert "Supported URL formats" in error_message
        assert "https://www.youtube.com/watch?v=" in error_message


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_url_with_whitespace(self):
        """Test URL with leading/trailing whitespace"""
        video_id = extract_video_id("  https://www.youtube.com/watch?v=dQw4w9WgXcQ  ")
        assert video_id == "dQw4w9WgXcQ"

    def test_http_vs_https(self):
        """Test both HTTP and HTTPS URLs"""
        video_id_https = extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        video_id_http = extract_video_id("http://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert video_id_https == "dQw4w9WgXcQ"
        assert video_id_http == "dQw4w9WgXcQ"

    def test_url_without_www(self):
        """Test URL without www subdomain"""
        video_id = extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_video_id_all_alphanumeric_types(self):
        """Test video IDs with various character types"""
        test_ids = [
            "0123456789A",  # numbers and uppercase
            "abcdefghijk",  # lowercase
            "ABCDEFGHIJK",  # uppercase
            "a1B2c3D4e5F",  # mixed
            "___________",  # all underscores
            "-----------",  # all hyphens
            "_-aZ09_-aZ0",  # mixed valid chars
        ]

        for test_id in test_ids:
            url = f"https://www.youtube.com/watch?v={test_id}"
            extracted_id = extract_video_id(url)
            assert extracted_id == test_id


class TestValidateYoutubeUrlIntegration:
    """Integration tests combining multiple functions"""

    def test_validate_extract_format_roundtrip(self):
        """Test full cycle: validate -> extract -> format"""
        original_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Validate
        assert validate_youtube_url(original_url) is True

        # Extract
        video_id = extract_video_id(original_url)
        assert video_id == "dQw4w9WgXcQ"

        # Format
        formatted_url = format_youtube_url(video_id)
        assert formatted_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_validation_workflow_for_user_input(self):
        """Test typical workflow for processing user input"""
        user_inputs = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "  https://youtu.be/abc123XYZ-_  ",  # with whitespace
            "https://m.youtube.com/watch?v=test1234567",
        ]

        for user_input in user_inputs:
            # Step 1: Validate
            is_valid = validate_youtube_url(user_input)
            assert is_valid is True

            # Step 2: Extract with validation
            video_id = get_video_id_with_validation(user_input)
            assert len(video_id) == 11

            # Step 3: Create canonical URL
            canonical_url = format_youtube_url(video_id)
            assert canonical_url.startswith("https://www.youtube.com/watch?v=")
