"""
YouTube URL validation and video ID extraction

This module provides functions to validate YouTube URLs and extract video IDs
from various YouTube URL formats.
"""

import re
from urllib.parse import urlparse, parse_qs


class InvalidURLError(Exception):
    """Raised when a YouTube URL is invalid or cannot be parsed"""

    pass


def validate_youtube_url(url: str) -> bool:
    """
    Validate if a given URL is a valid YouTube video URL

    Args:
        url: URL string to validate

    Returns:
        True if URL is a valid YouTube video URL, False otherwise

    Examples:
        >>> validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        True
        >>> validate_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        True
        >>> validate_youtube_url("https://example.com")
        False
    """
    try:
        video_id = extract_video_id(url)
        return video_id is not None
    except InvalidURLError:
        return False


def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from various URL formats

    Supported formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&feature=...

    Args:
        url: YouTube URL string

    Returns:
        Video ID (11 character string)

    Raises:
        InvalidURLError: If URL is not a valid YouTube URL or video ID cannot be extracted

    Examples:
        >>> extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL must be a non-empty string")

    # Remove whitespace
    url = url.strip()

    # Pattern for YouTube video ID (11 characters: alphanumeric, underscore, hyphen)
    video_id_pattern = r"[A-Za-z0-9_-]{11}"

    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if not hostname:
            raise InvalidURLError(f"Invalid URL format: {url}")

        # Normalize hostname
        hostname = hostname.lower()

        # Check if it's a YouTube domain
        youtube_domains = [
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
        ]

        if not any(
            hostname == domain or hostname.endswith(f".{domain}") for domain in youtube_domains
        ):
            raise InvalidURLError(
                f"URL is not a YouTube domain. Expected youtube.com or youtu.be, got {hostname}"
            )

        # Extract video ID based on URL format
        video_id = None

        # Format: https://www.youtube.com/watch?v=VIDEO_ID
        if "/watch" in parsed_url.path:
            query_params = parse_qs(parsed_url.query)
            video_ids = query_params.get("v", [])
            if video_ids:
                video_id = video_ids[0]

        # Format: https://youtu.be/VIDEO_ID
        elif hostname == "youtu.be":
            path_parts = parsed_url.path.strip("/").split("/")
            if path_parts:
                video_id = path_parts[0]

        # Format: https://www.youtube.com/v/VIDEO_ID or /embed/VIDEO_ID or /shorts/VIDEO_ID
        elif (
            "/v/" in parsed_url.path
            or "/embed/" in parsed_url.path
            or "/shorts/" in parsed_url.path
        ):
            path_parts = parsed_url.path.strip("/").split("/")
            if len(path_parts) >= 2:
                video_id = path_parts[1]

        # Validate extracted video ID
        if video_id:
            # Clean query parameters if present (e.g., video_id?feature=share)
            video_id = video_id.split("?")[0].split("&")[0]

            # Verify format (11 characters)
            if re.fullmatch(video_id_pattern, video_id):
                return video_id
            else:
                raise InvalidURLError(
                    f"Extracted video ID '{video_id}' does not match YouTube video ID format "
                    f"(expected 11 alphanumeric characters)"
                )

        raise InvalidURLError(
            f"Could not extract video ID from URL: {url}. "
            f"Supported formats: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/v/ID, youtube.com/embed/ID, youtube.com/shorts/ID"
        )

    except InvalidURLError:
        raise
    except Exception as e:
        raise InvalidURLError(f"Error parsing URL '{url}': {str(e)}")


def format_youtube_url(video_id: str) -> str:
    """
    Format a video ID into a standard YouTube watch URL

    Args:
        video_id: YouTube video ID (11 characters)

    Returns:
        Standard YouTube watch URL

    Raises:
        InvalidURLError: If video ID format is invalid

    Example:
        >>> format_youtube_url("dQw4w9WgXcQ")
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    """
    video_id_pattern = r"[A-Za-z0-9_-]{11}"

    if not re.fullmatch(video_id_pattern, video_id):
        raise InvalidURLError(
            f"Invalid video ID format: '{video_id}'. Expected 11 alphanumeric characters."
        )

    return f"https://www.youtube.com/watch?v={video_id}"


def get_video_id_with_validation(url: str) -> str:
    """
    Extract and validate video ID from URL with detailed error messages

    This is a convenience function that combines extraction and validation
    with user-friendly error messages.

    Args:
        url: YouTube URL string

    Returns:
        Validated video ID

    Raises:
        InvalidURLError: With descriptive error message if URL is invalid

    Example:
        >>> get_video_id_with_validation("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    try:
        return extract_video_id(url)
    except InvalidURLError as e:
        raise InvalidURLError(
            f"Invalid YouTube URL provided.\n"
            f"Error: {str(e)}\n\n"
            f"Supported URL formats:\n"
            f"  - https://www.youtube.com/watch?v=VIDEO_ID\n"
            f"  - https://youtu.be/VIDEO_ID\n"
            f"  - https://www.youtube.com/v/VIDEO_ID\n"
            f"  - https://www.youtube.com/embed/VIDEO_ID\n"
            f"  - https://www.youtube.com/shorts/VIDEO_ID\n\n"
            f"Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
