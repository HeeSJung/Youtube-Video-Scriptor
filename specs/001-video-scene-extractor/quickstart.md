# Quick Start Guide

**YouTube Video Scene Segmentation and Script Extraction Tool**

## Prerequisites

- Python 3.11 or higher
- Internet connection for YouTube access
- 500MB free disk space
- macOS, Linux, or Windows

## Installation

### 1. Install uv (Python Package Manager)

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/youtube-scene-extractor.git
cd youtube-scene-extractor
```

### 3. Set Up Environment

```bash
# Install dependencies
uv sync

# Verify installation
uv run python --version  # Should show Python 3.11.x
```

## Basic Usage

### Process a YouTube Video

```bash
# Basic command
uv run python -m youtube_scene_extractor "https://www.youtube.com/watch?v=VIDEO_ID"

# Example with real video
uv run python -m youtube_scene_extractor "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Output Structure

After processing, you'll find:

```
output/
└── VIDEO_ID/
    ├── segments.json        # Scene boundaries and timestamps
    ├── speakers.json        # Speaker identification summary
    └── transcripts/
        ├── scene_01.md     # Formatted with **bold** speakers
        ├── scene_01.txt    # Plain text version
        ├── scene_02.md
        └── scene_02.txt
```

## Common Use Cases

### 1. Language Learning

Process an educational video for shadowing practice:

```bash
uv run python -m youtube_scene_extractor \
  "https://www.youtube.com/watch?v=EDUCATION_VIDEO" \
  --output-dir ./language_practice
```

### 2. Content Analysis

Extract dialogue with custom scene detection:

```bash
uv run python -m youtube_scene_extractor \
  "https://www.youtube.com/watch?v=INTERVIEW_VIDEO" \
  --scene-threshold 25 \
  --min-scene-duration 20
```

### 3. Batch Processing

Process multiple videos:

```bash
# Create a file with URLs (one per line)
echo "https://www.youtube.com/watch?v=VIDEO1
https://www.youtube.com/watch?v=VIDEO2
https://www.youtube.com/watch?v=VIDEO3" > urls.txt

# Process all videos
while IFS= read -r url; do
  uv run python -m youtube_scene_extractor "$url"
done < urls.txt
```

## Configuration Options

### Command-Line Arguments

| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| `--output-dir` | Output directory path | `./output` | Any valid path |
| `--scene-threshold` | Scene detection sensitivity | 30 | 20-40 |
| `--min-scene-duration` | Minimum scene length (seconds) | 15 | 5-60 |
| `--frame-skip` | Frame skip rate for speed | 2 | 1-5 |
| `--formats` | Output formats | `json,markdown,text` | Any combination |

### Examples with Options

```bash
# High sensitivity scene detection
uv run python -m youtube_scene_extractor \
  "URL" --scene-threshold 20

# Longer minimum scenes
uv run python -m youtube_scene_extractor \
  "URL" --min-scene-duration 30

# JSON output only
uv run python -m youtube_scene_extractor \
  "URL" --formats json

# Custom output location
uv run python -m youtube_scene_extractor \
  "URL" --output-dir ~/Documents/transcripts
```

## Understanding Output

### segments.json

```json
{
  "video_id": "dQw4w9WgXcQ",
  "scene_count": 5,
  "scenes": [
    {
      "scene_id": "scene_01",
      "start_timecode": "00:00:00",
      "end_timecode": "00:00:45",
      "duration": 45.5
    }
  ]
}
```

### scene_01.md

```markdown
# Scene 01
**Duration**: 00:00:00 - 00:00:45

---

**Speaker 1**: Welcome to our presentation...

**Speaker 2**: Thank you for having me...
```

## Troubleshooting

### Common Issues

**Issue**: "Video not found"
- **Solution**: Check URL is correct and video is public

**Issue**: "No captions available"
- **Solution**: Tool will still generate scene boundaries but transcripts will be empty

**Issue**: "Processing taking too long"
- **Solution**: Try increasing `--frame-skip` to 3 or 4 for faster processing

**Issue**: "Scenes too short/long"
- **Solution**: Adjust `--scene-threshold` (lower = more scenes, higher = fewer scenes)

### Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `INVALID_URL` | URL format incorrect | Use full YouTube URL with watch?v= |
| `VIDEO_TOO_LONG` | Video exceeds 3 hours | Process shorter videos |
| `NETWORK_ERROR` | Connection issues | Check internet connection |
| `NO_CAPTIONS` | Captions unavailable | Scenes generated without text |

## Performance Tips

1. **Faster Processing**:
   - Increase `--frame-skip` to 3-4
   - Use `--scene-threshold 35` for fewer scenes
   - Process shorter videos (<30 minutes) first

2. **Better Accuracy**:
   - Use default settings for most videos
   - Decrease `--scene-threshold` for videos with subtle transitions
   - Keep `--min-scene-duration` at 15 for readable segments

3. **Memory Usage**:
   - Tool uses <500MB RAM
   - Processes video in streaming mode
   - No temporary files created

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_scene_detector.py

# Run with coverage
uv run pytest --cov=src
```

### Code Formatting

```bash
# Format code
uv run black .

# Check linting
uv run ruff check

# Fix linting issues
uv run ruff check --fix
```

### Adding Dependencies

```bash
# Add new package
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update all packages
uv lock --upgrade
```

## Getting Help

```bash
# Show help message
uv run python -m youtube_scene_extractor --help

# Show version
uv run python -m youtube_scene_extractor --version
```

## Example Workflow

Complete example processing a language learning video:

```bash
# 1. Set up project
git clone https://github.com/yourusername/youtube-scene-extractor.git
cd youtube-scene-extractor
uv sync

# 2. Process video
uv run python -m youtube_scene_extractor \
  "https://www.youtube.com/watch?v=LEARN_SPANISH_01" \
  --output-dir ./spanish_lessons \
  --min-scene-duration 20

# 3. Check results
ls -la spanish_lessons/LEARN_SPANISH_01/

# 4. View first scene
cat spanish_lessons/LEARN_SPANISH_01/transcripts/scene_01.md
```

## Next Steps

- Read the [full documentation](../README.md)
- Check [API contracts](./contracts/cli-interface.yaml)
- Review [data model](./data-model.md)
- Contribute on [GitHub](https://github.com/yourusername/youtube-scene-extractor)