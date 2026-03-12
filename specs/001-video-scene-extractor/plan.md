# Implementation Plan: YouTube Video Scene Segmentation and Script Extraction Tool

**Branch**: `001-video-scene-extractor` | **Date**: 2025-10-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-video-scene-extractor/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a tool that processes YouTube videos to automatically detect scene boundaries and extract formatted dialogue scripts for each segment, enabling language learners and content analysts to access video content in digestible, scene-based chunks. The solution leverages PySceneDetect for visual scene detection, youtube-transcript-api for caption extraction, and uv for modern Python package management, delivering a command-line tool that processes videos without downloading them.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: PySceneDetect[opencv]>=0.6, yt-dlp>=2024.1, youtube-transcript-api>=0.6
**Storage**: Local file system for output files (JSON, TXT, MD)
**Testing**: pytest>=7.0 with mocked API responses
**Target Platform**: Cross-platform CLI (Windows/Mac/Linux)
**Project Type**: Single project (command-line tool)
**Performance Goals**: Process 30-min video in 3-5 min scene detection + 1 min transcript extraction
**Constraints**: <500MB memory usage (streaming), no GPU requirement, respect YouTube ToS
**Scale/Scope**: Single video processing, output files per video, videos up to 3 hours

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Since no specific constitution principles are defined in the constitution.md file (template placeholders only), this section will focus on general best practices:

- ✅ **Simplicity First**: Single-purpose tool with clear input/output
- ✅ **CLI Interface**: Text-based command-line interface with JSON/text outputs
- ✅ **Testability**: Mocked API responses for CI/CD, unit and integration tests
- ✅ **No Over-Engineering**: Direct implementation without unnecessary abstractions
- ✅ **Observable**: Logging for debugging, clear error messages

## Project Structure

### Documentation (this feature)

```text
specs/001-video-scene-extractor/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Single project structure (Python CLI tool)
youtube-scene-extractor/
├── pyproject.toml          # uv project configuration
├── uv.lock                 # Locked dependencies
├── .python-version         # Python version (3.11)
├── README.md              # Project documentation
├── LICENSE                # License file
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point and CLI interface
│   ├── scene_detector.py       # PySceneDetect wrapper for boundary detection
│   ├── transcript_extractor.py # Caption fetching and formatting
│   ├── speaker_identifier.py   # Speaker detection and consistency logic
│   ├── url_validator.py        # YouTube URL validation and ID extraction
│   └── output_formatter.py     # JSON/TXT/MD file generation
│
├── tests/
│   ├── contract/
│   │   ├── test_api_contracts.py    # YouTube API response contracts
│   │   └── test_output_formats.py   # Output file format validation
│   ├── integration/
│   │   ├── test_end_to_end.py      # Full pipeline with sample video
│   │   └── test_error_handling.py   # Edge cases and error scenarios
│   └── unit/
│       ├── test_scene_detector.py
│       ├── test_transcript_extractor.py
│       ├── test_speaker_identifier.py
│       └── test_url_validator.py
│
├── config/
│   └── default_config.py     # Configuration settings and thresholds
│
└── output/                    # Generated output directory (gitignored)
    └── [video-id]/
        ├── segments.json      # Scene boundaries and metadata
        ├── speakers.json      # Speaker summary
        └── transcripts/
            ├── scene_01.md    # Formatted script with bold speakers
            └── scene_01.txt   # Plain text version
```

**Structure Decision**: Single project structure chosen as this is a standalone CLI tool without frontend/backend separation. All functionality is contained within a single Python package with clear module separation for scene detection, transcript extraction, and output formatting.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Not applicable - no constitution violations identified. The implementation follows simplicity principles with a straightforward single-project structure.