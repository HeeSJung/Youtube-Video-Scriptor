# Research & Technical Decisions

**Feature**: YouTube Video Scene Segmentation and Script Extraction Tool
**Date**: 2025-10-22
**Status**: Complete

## Executive Summary

This document consolidates technical research and decisions for implementing the YouTube video scene segmentation and script extraction tool. All technical clarifications have been resolved based on the provided architecture specifications.

## Package Management & Environment

### Decision: uv for Python Package Management
**Rationale**:
- Significantly faster than traditional pip/venv (10-100x speed improvements)
- Built-in dependency resolution and lock file support
- Single tool for version management and virtual environments
- Modern Python packaging with pyproject.toml support
- Reproducible builds across all environments

**Alternatives Considered**:
- Poetry: More mature but slower, additional complexity
- pip-tools: Requires multiple tools, less integrated
- conda: Overkill for pure Python project, slower

## Scene Detection Technology

### Decision: PySceneDetect with ContentDetector Algorithm
**Rationale**:
- Purpose-built for scene boundary detection
- ContentDetector analyzes frame-by-frame visual changes
- Supports streaming video without full download
- Configurable thresholds for different video types
- Well-maintained with active community

**Configuration**:
- Threshold: 30.0 (adjustable 20-40 range)
- Minimum scene length: 15 seconds
- Frame skip: 2 (balance speed/accuracy)
- Process at 360p for optimal performance

**Alternatives Considered**:
- OpenCV raw: More complex, requires custom algorithms
- FFmpeg scene detection: Less accurate for content changes
- ML-based (TransNetV2): Requires GPU, overkill for MVP

## Video Streaming Strategy

### Decision: yt-dlp for Streaming Without Download
**Rationale**:
- Actively maintained fork of youtube-dl
- Supports piping video to stdout for streaming
- Respects YouTube ToS by not storing content
- Handles various URL formats and edge cases
- Built-in error handling and retry logic

**Implementation**:
- Stream at 360p quality for scene detection
- Pipe directly to PySceneDetect
- No temporary files or storage

**Alternatives Considered**:
- youtube-dl: Original but less maintained
- Direct YouTube API: Doesn't provide video stream
- Selenium scraping: Fragile, violates ToS

## Transcript Extraction Method

### Decision: youtube-transcript-api
**Rationale**:
- Official API wrapper for YouTube captions
- Prioritizes manual captions over auto-generated
- No video download required
- Simple, focused library
- Returns structured timestamp data

**Fallback Strategy**:
1. Try manually-created captions (highest quality)
2. Fall back to auto-generated if unavailable
3. Return empty transcripts with explanation if none

**Alternatives Considered**:
- Whisper ASR: Requires video audio, computationally expensive
- YouTube Data API v3: Doesn't provide transcript access
- Web scraping: Unreliable, against ToS

## Speaker Identification Approach

### Decision: Heuristic Pattern Matching
**Rationale**:
- Simple and sufficient for MVP
- No additional dependencies
- Works with existing caption data
- Fast processing

**Implementation**:
- Parse patterns: "NAME:", "[Name]", etc.
- 2+ second pauses indicate speaker changes
- Assign generic labels (Speaker 1, 2, etc.)
- Maintain consistency within scenes

**Future Enhancement**:
- pyannote.audio for ML-based diarization when needed

**Alternatives Considered**:
- pyannote.audio: Requires audio processing, complex setup
- Google Speech-to-Text: Costly, requires audio extraction
- Manual annotation: Not scalable

## Output Format Decisions

### Decision: Multiple Complementary Formats
**Rationale**:
- JSON for programmatic access (segments.json)
- Markdown for formatted reading (scene_XX.md)
- Plain text for maximum compatibility (scene_XX.txt)
- Covers all user needs identified in spec

**Structure**:
```
output/[video-id]/
├── segments.json      # Machine-readable boundaries
├── speakers.json      # Speaker summary
└── transcripts/
    ├── scene_01.md    # **Bold** speaker names
    └── scene_01.txt   # Plain text
```

## Error Handling Strategy

### Decision: Graceful Degradation
**Rationale**:
- User experience over perfection
- Partial results better than none
- Clear communication of limitations

**Implementation**:
1. Network errors: 3 retry attempts with exponential backoff
2. No captions: Continue with scene detection only
3. Scene detection failure: Fall back to fixed intervals
4. Invalid URL: Clear error message with examples

## Performance Optimization

### Decision: Streaming and Frame Skipping
**Rationale**:
- Memory efficiency (<500MB usage)
- No GPU requirement for accessibility
- Balance speed and accuracy

**Targets Validated**:
- 30-min video: 3-5 min scene + 1 min transcript
- Single-threaded to reduce complexity
- Frame skip rate of 2 for 2x speedup

## Testing Strategy

### Decision: Comprehensive Test Coverage
**Rationale**:
- Ensure reliability without YouTube dependency
- Enable CI/CD pipeline
- Catch regressions early

**Implementation**:
- Unit tests: Individual component validation
- Integration tests: Sample video with known output
- Contract tests: YouTube API response formats
- Mocked responses for CI/CD

## Development Workflow

### Decision: uv-Centric Commands
**Rationale**:
- Consistency across all operations
- Single tool to learn
- Fast iteration cycles

**Commands**:
- Setup: `uv sync`
- Run: `uv run python main.py <url>`
- Test: `uv run pytest`
- Format: `uv run black .`
- Lint: `uv run ruff check`

## Configuration Management

### Decision: Python Config Module with Defaults
**Rationale**:
- Type safety with Python
- Easy testing and overrides
- No external config files for MVP

**Configurable Parameters**:
- Scene detection threshold (20-40)
- Minimum scene duration (default 15s)
- Frame skip rate (1-5)
- Speaker detection patterns (regex)
- Output formats enabled

## Installation & Distribution

### Decision: Wheel/sdist via uv build
**Rationale**:
- Standard Python packaging
- Cross-platform compatibility
- Simple installation process

**Installation Steps**:
1. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Clone repository
3. Run: `uv sync`
4. Execute: `uv run python main.py <youtube-url>`

## Future Enhancements (Post-MVP)

Documented for roadmap planning:
1. **Whisper Integration**: For videos without any captions
2. **pyannote.audio**: ML-based speaker diarization
3. **Batch Processing**: Multiple URLs in parallel
4. **Web UI**: Browser-based interface
5. **Cloud Integration**: Direct upload to Notion/Google Drive
6. **Real-time Mode**: Process during playback
7. **Language Support**: Multi-language caption handling

## Risk Mitigation

### YouTube API Changes
- **Mitigation**: Abstraction layer for easy adaptation
- **Monitoring**: Version pinning with regular updates

### Copyright Concerns
- **Mitigation**: Educational use disclaimer
- **No storage**: Stream-only processing
- **User responsibility**: Terms of use agreement

### Performance Degradation
- **Mitigation**: Progress indicators
- **Cancellation**: Graceful shutdown support
- **Timeout**: Configurable max processing time

## Conclusion

All technical decisions have been made with clear rationales. The architecture prioritizes:
1. **Simplicity**: Single Python package, minimal dependencies
2. **Performance**: Streaming approach, optimized settings
3. **Reliability**: Comprehensive error handling, test coverage
4. **User Experience**: Multiple output formats, clear feedback

No unresolved technical clarifications remain. Ready to proceed with Phase 1 design artifacts.