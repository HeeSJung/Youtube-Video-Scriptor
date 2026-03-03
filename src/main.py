#!/usr/bin/env python3
"""
YouTube Scene Extractor - CLI Interface

Main entry point for the YouTube video scene segmentation and script extraction tool.
Orchestrates the full processing pipeline from URL input to formatted output files.
"""

import argparse
import json
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from src.url_validator import get_video_id_with_validation
from src.transcript_extractor import TranscriptExtractor
from src.output_formatter import OutputFormatter
from src.models import Video, ProcessingResult, CaptionType, Scene
from src.logger import (
    get_logger,
    setup_logger,
    InvalidURLError,
    VideoNotFoundError,
    TranscriptExtractionError,
)
from config.default_config import (
    DEFAULT_CONFIG,
    OutputFormatConfig,
)

logger = get_logger(__name__)

# Version info from pyproject.toml
__version__ = "0.1.0"


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="youtube-scene-extractor",
        description=(
            "YouTube Video Scene Segmentation and Script Extraction Tool\n\n"
            "Automatically divide YouTube videos into logical scene segments\n"
            "with extracted dialogue scripts for language learning and content analysis."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - process entire video with default settings
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

  # Extract specific time range (23 seconds to 51 seconds)
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 23 51

  # Extract with custom output directory
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 23 51 --output-dir ./my_videos

  # Process entire video
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

  # Extract specific time range (23s to 51s)
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 23 51

  # With custom output directory
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 23 51 \\
    --output-dir ./output \\
    --formats json,markdown

  # Process video without captions (generates empty transcript files)
  %(prog)s "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --ignore-caption-errors

Output:
  Creates a directory structure in the output folder:
    output/[video-id]/
    ├── segments.json       # Scene boundaries and metadata
    ├── speakers.json       # Speaker information (if detected)
    └── transcripts/
        ├── scene_01.md     # Markdown formatted scripts
        ├── scene_01.txt    # Plain text scripts
        └── ...

Requirements:
  - YouTube captions/subtitles must be available (auto-generated or manual)
  - Use --ignore-caption-errors to process videos without captions
  - Videos without captions will have empty transcript files with explanatory notes

For more information, see: https://github.com/youtube-scene-extractor
        """,
    )

    # Required argument
    parser.add_argument(
        "url",
        type=str,
        help="YouTube video URL to process (e.g., https://www.youtube.com/watch?v=VIDEO_ID)",
    )

    # Optional timestamp arguments for extracting specific time ranges
    parser.add_argument(
        "start_sec",
        type=int,
        nargs="?",
        default=None,
        help="Start timestamp in seconds (optional). Must be used with end_sec.",
    )

    parser.add_argument(
        "end_sec",
        type=int,
        nargs="?",
        default=None,
        help="End timestamp in seconds (optional). Must be used with start_sec.",
    )

    # Optional arguments
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_CONFIG.output_format.output_dir),
        help=f"Output directory for generated files (default: {DEFAULT_CONFIG.output_format.output_dir})",
    )

    # Build default formats list from config
    default_formats = []
    if DEFAULT_CONFIG.output_format.enable_json:
        default_formats.append("json")
    if DEFAULT_CONFIG.output_format.enable_markdown:
        default_formats.append("markdown")
    if DEFAULT_CONFIG.output_format.enable_text:
        default_formats.append("text")

    parser.add_argument(
        "--formats",
        type=str,
        default=",".join(default_formats),
        help=(
            f"Output formats to generate (comma-separated: json,markdown, "
            f"default: {','.join(default_formats)})"
        ),
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging output",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all output except errors",
    )

    parser.add_argument(
        "--ignore-caption-errors",
        action="store_true",
        help="Continue processing even if captions are unavailable (generates empty transcripts)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command-line arguments.

    Args:
        args: Parsed command-line arguments

    Raises:
        ValueError: If arguments are invalid
    """
    # Validate formats
    valid_formats = {"json", "markdown", "text"}
    requested_formats = set(args.formats.split(","))
    invalid_formats = requested_formats - valid_formats
    if invalid_formats:
        raise ValueError(
            f"Invalid output formats: {invalid_formats}. Valid formats: {valid_formats}"
        )

    # Validate conflicting flags
    if args.verbose and args.quiet:
        raise ValueError("Cannot specify both --verbose and --quiet")

    # Validate timestamp arguments
    if (args.start_sec is None) != (args.end_sec is None):
        raise ValueError(
            "Both start_sec and end_sec must be provided together, or neither. "
            f"Got start_sec={args.start_sec}, end_sec={args.end_sec}"
        )

    if args.start_sec is not None and args.end_sec is not None:
        # Both timestamps provided - validate them
        if args.start_sec < 0:
            raise ValueError(f"start_sec must be non-negative, got {args.start_sec}")

        if args.end_sec < 0:
            raise ValueError(f"end_sec must be non-negative, got {args.end_sec}")

        if args.end_sec <= args.start_sec:
            raise ValueError(
                f"end_sec must be greater than start_sec, got start_sec={args.start_sec}, end_sec={args.end_sec}"
            )

        # Validate segment duration (end - start), not just the end timestamp
        segment_duration = args.end_sec - args.start_sec
        max_duration = DEFAULT_CONFIG.processing.max_video_duration
        if segment_duration > max_duration:
            raise ValueError(
                f"Requested segment duration ({segment_duration}s = "
                f"{segment_duration / 3600:.2f} hours) exceeds the maximum of "
                f"{max_duration}s ({max_duration // 3600} hours). "
                f"The limit applies to the segment length (end_sec - start_sec), "
                f"not the end timestamp alone."
            )


def get_video_duration(video_url: str) -> Optional[float]:
    """
    Get video duration using yt-dlp without downloading the video.

    Args:
        video_url: YouTube video URL

    Returns:
        Video duration in seconds, or None if unavailable
    """
    logger.info(f"Fetching video duration for: {video_url}")

    try:
        # Use yt-dlp to get video metadata without downloading
        cmd = ["yt-dlp", "--dump-json", "--no-warnings", "--quiet", video_url]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout:
            metadata = json.loads(result.stdout)
            duration = metadata.get("duration")

            if duration:
                logger.info(f"Video duration: {duration}s ({duration/60:.1f} minutes)")
                return float(duration)

        logger.warning("Could not fetch video duration")
        return None

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger.warning(f"Error fetching video duration: {e}")
        return None


def print_progress(stage: str, message: str, verbose: bool = False) -> None:
    """
    Print progress indicator for processing stages.

    Args:
        stage: Stage name (e.g., "URL Validation", "Scene Detection")
        message: Progress message
        verbose: Whether verbose mode is enabled
    """
    if verbose:
        print(f"[{stage}] {message}")
    else:
        print(f"⏳ {stage}...", end=" ", flush=True)


def print_progress_done(verbose: bool = False) -> None:
    """
    Print completion indicator for processing stage.

    Args:
        verbose: Whether verbose mode is enabled
    """
    if not verbose:
        print("✓")


def process_video(
    url: str,
    output_dir: Path,
    output_formats: list,
    verbose: bool = False,
    quiet: bool = False,
    ignore_caption_errors: bool = False,
    start_sec: int = None,
    end_sec: int = None,
) -> ProcessingResult:
    """
    Main video processing pipeline.

    Orchestrates all processing steps:
    1. URL validation and video ID extraction
    2. Scene creation (from timestamps or full video)
    3. Transcript extraction
    4. Output file generation

    Args:
        url: YouTube video URL
        output_dir: Output directory path
        output_formats: List of output formats to generate
        verbose: Enable verbose logging
        quiet: Suppress non-error output
        ignore_caption_errors: Continue processing even if captions unavailable
        start_sec: Optional start timestamp in seconds (requires end_sec)
        end_sec: Optional end timestamp in seconds (requires start_sec)

    Returns:
        ProcessingResult with all processing data

    Raises:
        InvalidURLError: If URL is invalid
        VideoNotFoundError: If video cannot be accessed
        TranscriptExtractionError: If transcript extraction fails and ignore_caption_errors=False
        CaptionNotAvailableError: If captions unavailable and ignore_caption_errors=False
    """
    start_time = time.time()

    # Stage 1: URL Validation
    if not quiet:
        print_progress("URL Validation", f"Validating URL: {url}", verbose)

    video_id = get_video_id_with_validation(url)

    if not quiet:
        print_progress_done(verbose)
        if verbose:
            print(f"  Video ID: {video_id}")

    # Stage 2: Scene Creation
    if start_sec is not None and end_sec is not None:
        # User provided timestamps - create single scene from time range
        if not quiet:
            print_progress(
                "Scene Creation",
                f"Creating scene from timestamps: {start_sec}s - {end_sec}s",
                verbose,
            )

        scene = Scene(
            scene_id="scene_01",
            video_id=video_id,
            start_time=float(start_sec),
            end_time=float(end_sec),
            confidence=1.0,
        )
        scenes = [scene]

        if not quiet:
            print_progress_done(verbose)
            if verbose:
                print(
                    f"  Created 1 scene ({start_sec}s - {end_sec}s, duration: {end_sec - start_sec}s)"
                )
    else:
        # No timestamps - create scene for entire video
        if not quiet:
            print_progress("Scene Creation", "Creating scene for entire video", verbose)

        # Get video duration
        video_duration = get_video_duration(url)

        if not video_duration:
            # Fallback: use a large duration if we can't fetch it
            logger.warning("Could not determine video duration, using full video")
            video_duration = 10800  # 3 hours fallback

        max_duration = DEFAULT_CONFIG.processing.max_video_duration
        if video_duration > max_duration:
            raise ValueError(
                f"Video duration ({int(video_duration)}s = {video_duration / 3600:.2f} hours) "
                f"exceeds the maximum of {max_duration}s ({max_duration // 3600} hours) "
                f"for automatic (full-video) processing. "
                f"Please provide start and end timestamps to process a specific segment, e.g.: "
                f"yt-script URL 0 {max_duration}"
            )

        scene = Scene(
            scene_id="scene_01",
            video_id=video_id,
            start_time=0.0,
            end_time=video_duration,
            confidence=1.0,
        )
        scenes = [scene]

        if not quiet:
            print_progress_done(verbose)
            if verbose:
                print(f"  Created 1 scene (0s - {video_duration}s, full video)")

    # Stage 3: Transcript Extraction
    if not quiet:
        print_progress("Transcript Extraction", "Fetching video captions", verbose)

    transcript_extractor = TranscriptExtractor(enable_speaker_detection=True)
    transcripts, caption_type = transcript_extractor.process_video_transcript(
        video_id, scenes, start_time=start_sec, end_time=end_sec
    )

    # Get identified speakers from transcript extractor
    speakers = transcript_extractor.get_all_speakers()

    # Check if captions are unavailable and handle accordingly
    if caption_type == CaptionType.NONE:
        if not ignore_caption_errors:
            # Captions unavailable and user didn't specify --ignore-caption-errors
            if not quiet:
                print_progress_done(verbose)
                print("\n⚠️  Warning: No captions available for this video", file=sys.stderr)
                print("   Transcript files will be empty with explanatory notes", file=sys.stderr)
                print("\n   To suppress this error, use: --ignore-caption-errors", file=sys.stderr)
            # Still continue processing to generate scene boundaries
        else:
            # User explicitly wants to ignore caption errors
            if not quiet:
                print_progress_done(verbose)
                if verbose:
                    print("  ⚠️  No captions available - generating empty transcripts")
    else:
        # Captions are available
        if not quiet:
            print_progress_done(verbose)
            if verbose:
                print(f"  Caption type: {caption_type.value}")
                print(f"  Extracted {len(transcripts)} scene transcripts")
                if speakers:
                    print(f"  Identified {len(speakers)} speakers")

    # Create Video object
    # Calculate video duration
    if scenes:
        if start_sec is not None and end_sec is not None:
            # For timestamp mode: duration = end - start
            video_duration = int(end_sec - start_sec)
        else:
            # For automatic mode: duration = last scene's end time (assumes video starts at 0)
            video_duration = int(scenes[-1].end_time)
    else:
        video_duration = 0

    video = Video(
        video_id=video_id,
        url=url,
        duration=video_duration,
        has_captions=(caption_type.value != "none"),
        caption_type=caption_type,
    )

    # Create ProcessingResult
    processing_time = time.time() - start_time
    result = ProcessingResult(
        video=video,
        scenes=scenes,
        transcripts=transcripts,
        speakers=speakers,
        processing_time=processing_time,
    )

    # Stage 4: Output Generation
    if not quiet:
        print_progress("Output Generation", "Writing output files", verbose)

    output_config = OutputFormatConfig(
        output_dir=output_dir,
        enable_json="json" in output_formats,
        enable_markdown="markdown" in output_formats,
        enable_text="text" in output_formats,
    )
    output_formatter = OutputFormatter(config=output_config)
    generated_files = output_formatter.write_output_files(
        result, video_id=video_id, output_formats=output_formats
    )

    if not quiet:
        print_progress_done(verbose)
        if verbose:
            total_files = sum(len(files) for files in generated_files.values())
            print(f"  Generated {total_files} files")

    return result


def signal_handler(signum, frame):
    """
    Handle interrupt signals (Ctrl+C) for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    print("\n\n⚠️  Interrupted by user (Ctrl+C)", file=sys.stderr)
    print("Cleaning up and exiting...", file=sys.stderr)
    sys.exit(130)  # Standard exit code for SIGINT


def main() -> int:
    """
    Main entry point for the CLI application.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Setup signal handling for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create argument parser
    parser = create_argument_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING if args.quiet else logging.INFO
    setup_logger(level=log_level)

    try:
        # Validate arguments
        validate_arguments(args)

        # Parse formats
        output_formats = [f.strip() for f in args.formats.split(",")]

        # Convert output_dir to Path
        output_dir = Path(args.output_dir).resolve()

        # Print header
        if not args.quiet:
            print("=" * 70)
            print("YouTube Scene Extractor v" + __version__)
            print("=" * 70)
            print()

        # Process video
        result = process_video(
            url=args.url,
            output_dir=output_dir,
            output_formats=output_formats,
            verbose=args.verbose,
            quiet=args.quiet,
            ignore_caption_errors=args.ignore_caption_errors,
            start_sec=args.start_sec,
            end_sec=args.end_sec,
        )

        # Print summary
        if not args.quiet:
            print()
            print("=" * 70)
            print("✅ Processing Complete!")
            print("=" * 70)
            print(f"Video ID:       {result.video.video_id}")
            print(f"Duration:       {result.video.duration}s")
            print(f"Scenes:         {len(result.scenes)}")
            print(f"Captions:       {result.video.caption_type.value}")
            print(f"Processing Time: {result.processing_time:.2f}s")
            print(f"Output:         {output_dir / result.video.video_id}")
            print("=" * 70)

        logger.info(f"Successfully processed video {result.video.video_id}")
        return 0

    except InvalidURLError as e:
        logger.error(f"Invalid URL: {e}")
        print("❌ Error: Invalid YouTube URL", file=sys.stderr)
        print(f"   {e}", file=sys.stderr)
        print("\nValid URL formats:", file=sys.stderr)
        print("  - https://www.youtube.com/watch?v=VIDEO_ID", file=sys.stderr)
        print("  - https://youtu.be/VIDEO_ID", file=sys.stderr)
        print("  - https://m.youtube.com/watch?v=VIDEO_ID", file=sys.stderr)
        print("  - https://www.youtube.com/embed/VIDEO_ID", file=sys.stderr)
        return 1

    except VideoNotFoundError as e:
        logger.error(f"Video not found: {e}")
        print("❌ Error: Video not found or unavailable", file=sys.stderr)
        print(f"   {e}", file=sys.stderr)
        print("\nPossible reasons:", file=sys.stderr)
        print("  - Video is private or deleted", file=sys.stderr)
        print("  - Video is age-restricted", file=sys.stderr)
        print("  - Network connection issue", file=sys.stderr)
        return 1

    except TranscriptExtractionError as e:
        logger.error(f"Transcript extraction failed: {e}")
        print("❌ Error: Transcript extraction failed", file=sys.stderr)
        print(f"   {e}", file=sys.stderr)
        print("\nNote: Processing may continue with empty transcripts", file=sys.stderr)
        return 1

    except ValueError as e:
        logger.error(f"Invalid argument: {e}")
        print("❌ Error: Invalid argument", file=sys.stderr)
        print(f"   {e}", file=sys.stderr)
        print("\nUse --help for usage information", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        print("\n⚠️  Processing interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print("❌ Error: An unexpected error occurred", file=sys.stderr)
        print(f"   {e}", file=sys.stderr)
        print("\nPlease report this issue with the following details:", file=sys.stderr)
        print(f"  - Video URL: {args.url if 'args' in locals() else 'N/A'}", file=sys.stderr)
        print(f"  - Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
