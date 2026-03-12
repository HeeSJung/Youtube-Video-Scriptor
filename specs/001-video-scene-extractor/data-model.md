# Data Model

**Feature**: YouTube Video Scene Segmentation and Script Extraction Tool
**Date**: 2025-10-22

## Core Entities

### Video

Represents a YouTube video being processed.

**Attributes**:
- `video_id` (string): YouTube video identifier extracted from URL
- `url` (string): Original YouTube URL provided by user
- `title` (string, optional): Video title from YouTube metadata
- `duration` (integer): Total video duration in seconds
- `has_captions` (boolean): Whether captions are available
- `caption_type` (enum): "manual" | "auto-generated" | "none"
- `processed_at` (datetime): Timestamp of processing

**Validation**:
- `video_id` must match YouTube ID format (11 characters)
- `url` must be valid YouTube URL format
- `duration` must be positive integer, max 10800 (3 hours)

### Scene

A logical segment of video with detected boundaries.

**Attributes**:
- `scene_id` (string): Unique identifier (format: "scene_01", "scene_02")
- `video_id` (string): Reference to parent Video
- `start_time` (float): Start timestamp in seconds
- `end_time` (float): End timestamp in seconds
- `duration` (float): Scene duration in seconds (computed)
- `confidence` (float, optional): Detection confidence score (0-1)

**Validation**:
- `duration` must be >= 15 seconds (after merging)
- `start_time` must be >= 0
- `end_time` must be > `start_time`
- `end_time` must be <= video.duration

**State Transitions**:
- Created → Detected → Merged (if < 15s) → Finalized

### Transcript

Extracted dialogue text for a scene.

**Attributes**:
- `scene_id` (string): Reference to parent Scene
- `raw_text` (string): Original caption text with timestamps
- `formatted_text` (string): Processed text with speaker labels
- `speakers` (array[Speaker]): List of identified speakers
- `word_count` (integer): Total words in transcript
- `language` (string): Language code (e.g., "en")

**Validation**:
- `formatted_text` must include speaker labels
- `word_count` must match actual word count

### Speaker

An identified voice in the video.

**Attributes**:
- `speaker_id` (string): Unique identifier (e.g., "speaker_1")
- `label` (string): Display label (e.g., "Speaker 1", or detected name)
- `scenes` (array[string]): List of scene_ids where speaker appears
- `first_appearance` (float): First timestamp where speaker is detected
- `line_count` (integer): Total number of dialogue lines

**Validation**:
- `speaker_id` must be consistent across all scenes
- `label` format: "Speaker N" or detected name

### ProcessingResult

Complete output of video processing.

**Attributes**:
- `video` (Video): Processed video metadata
- `scenes` (array[Scene]): Detected scene boundaries
- `transcripts` (map[scene_id, Transcript]): Scene transcripts
- `speakers` (array[Speaker]): All identified speakers
- `processing_time` (float): Total processing duration in seconds
- `errors` (array[Error], optional): Non-fatal errors encountered

## Data Relationships

```
Video (1) ──────> (*) Scene
                      │
                      ├──> (1) Transcript
                      │         │
                      │         └──> (*) Speaker
                      │
                      └──> Timeline (computed view)
```

## Output File Schemas

### segments.json

```json
{
  "video_id": "dQw4w9WgXcQ",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "total_duration": 213,
  "scene_count": 5,
  "scenes": [
    {
      "scene_id": "scene_01",
      "start_time": 0.0,
      "end_time": 45.5,
      "duration": 45.5,
      "start_timecode": "00:00:00",
      "end_timecode": "00:00:45"
    }
  ],
  "generated_at": "2025-10-22T10:00:00Z",
  "processing_time_seconds": 240
}
```

### speakers.json

```json
{
  "video_id": "dQw4w9WgXcQ",
  "speaker_count": 2,
  "speakers": [
    {
      "speaker_id": "speaker_1",
      "label": "Speaker 1",
      "scenes": ["scene_01", "scene_02", "scene_04"],
      "first_appearance": 0.0,
      "line_count": 45
    }
  ]
}
```

### scene_XX.md (Markdown format)

```markdown
# Scene 01
**Duration**: 00:00:00 - 00:00:45

---

**Speaker 1**: Hello and welcome to today's presentation about video processing.

**Speaker 2**: Thank you for having me. I'm excited to discuss this technology.

**Speaker 1**: Let's begin with the basics of scene detection...
```

### scene_XX.txt (Plain text format)

```text
Scene 01
Duration: 00:00:00 - 00:00:45

Speaker 1: Hello and welcome to today's presentation about video processing.

Speaker 2: Thank you for having me. I'm excited to discuss this technology.

Speaker 1: Let's begin with the basics of scene detection...
```

## Validation Rules

### Business Rules

1. **Scene Merging**: Scenes < 15 seconds must be merged with adjacent scene
2. **Speaker Consistency**: Same speaker must have same ID across all scenes
3. **Caption Priority**: Manual captions preferred over auto-generated
4. **Output Completeness**: All scenes must have corresponding transcript files

### Data Integrity

1. **Temporal Continuity**: Scene end_time must equal next scene's start_time
2. **No Overlaps**: Scenes cannot overlap in time
3. **Complete Coverage**: Scenes must cover entire video duration
4. **Speaker Presence**: Speaker can only appear in scenes where detected

## Error Handling

### Graceful Degradation States

1. **No Captions Available**:
   - Generate scenes with empty transcripts
   - Include explanatory note in transcript files

2. **Scene Detection Failure**:
   - Fall back to fixed 60-second intervals
   - Mark as "fallback" in metadata

3. **Partial Caption Coverage**:
   - Process available portions
   - Mark gaps in transcript files

## Performance Considerations

### Memory Optimization

- Stream video frames, don't load entire video
- Process transcripts in chunks
- Write output files incrementally

### Storage Estimates

Per 30-minute video:
- segments.json: ~2 KB
- speakers.json: ~1 KB
- Transcript files: ~5-10 KB each
- Total: ~50-100 KB for typical video

## Future Extensions

Reserved fields for future enhancements:
- `Scene.thumbnail_path`: For visual preview
- `Speaker.voice_signature`: For ML-based identification
- `Transcript.sentiment`: For emotion analysis
- `Video.tags`: For content categorization