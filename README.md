# YouTube Transcript Extractor

Extract transcripts from YouTube videos with timestamps. Simple, fast, and easy to use.

## What It Does

- Extract transcripts from specific time ranges (e.g., 10s to 45s)
- Extract transcripts from entire videos
- Automatically identify speakers
- Output in JSON and Markdown formats

## Quick Start

### Installation

1. **Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Clone and setup**:
```bash
git clone <your-repo-url>
cd P-YOUTUBE-VIDEO-SCRIPTOR
uv sync
```

### Usage

**Extract specific time range** (recommended):
```bash
uv run python src/main.py "https://www.youtube.com/watch?v=VIDEO_ID" 10 45
# Extracts transcript from 10 seconds to 45 seconds
```

**Extract entire video**:
```bash
uv run python src/main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Custom output directory**:
```bash
uv run python src/main.py "URL" 10 45 --output-dir ./my_output
```

### Output

Files are saved in `output/VIDEO_ID/`:
```
output/
└── VIDEO_ID/
    ├── segments.json    # Scene metadata and timestamps
    └── transcript.md    # Formatted transcript with speakers
```

## Requirements

- Python 3.11 or higher
- Internet connection
- Video must have captions (auto-generated or manual)

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `start_sec` | Start timestamp in seconds | None |
| `end_sec` | End timestamp in seconds | None |
| `--output-dir` | Output directory | `./output` |
| `--formats` | Output formats (json,markdown) | `json,markdown` |
| `--verbose` | Show detailed progress | Off |
| `--quiet` | Suppress output | Off |

## Examples

```bash
# Extract 30 seconds from 1 minute mark
uv run python src/main.py "https://youtube.com/watch?v=abc123" 60 90

# Extract full video with verbose output
uv run python src/main.py "https://youtube.com/watch?v=abc123" --verbose

# Only generate JSON output
uv run python src/main.py "https://youtube.com/watch?v=abc123" 10 30 --formats json
```


## Troubleshooting

**"No captions available"**
- Check if the video has captions on YouTube (CC button)
- Try a different video

**"Permission denied"**
- Check output directory write permissions
- Try a different output directory with `--output-dir`

**"Invalid URL"**
- Make sure you're using a valid YouTube URL
- Supported formats: youtube.com/watch?v=, youtu.be/, youtube.com/shorts/

## Development

Run tests:
```bash
uv run pytest
```

Format code:
```bash
uv run ruff check .
```

## License

See LICENSE file for details.
