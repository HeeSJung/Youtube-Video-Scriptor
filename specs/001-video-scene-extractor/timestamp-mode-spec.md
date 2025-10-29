# Timestamp-Based Extraction Mode - Specification

**Status**: 🟡 In Progress
**Created**: 2025-10-28
**Purpose**: Allow users to extract specific sections of YouTube videos using timestamps

---

## Overview

This specification defines changes to enable timestamp-based video extraction, replacing the automatic scene detection workflow with user-specified time ranges.

---

## Current Workflow (Before Changes)

```bash
# Current usage
uv run python src/main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Process:
1. URL Validation
2. Get Video Duration
3. Scene Detection (or fallback to 60s intervals)
4. Merge Short Scenes
5. Extract Transcripts for ALL scenes
6. Speaker Identification
7. Generate Output (segments.json, speakers.json, scene_XX.md, scene_XX.txt)
```

**Output**:
```
output/VIDEO_ID/
├── segments.json
├── speakers.json
└── transcripts/
    ├── scene_01.md
    ├── scene_01.txt
    ├── scene_02.md
    ├── scene_02.txt
    └── ...
```

---

## New Workflow (After Changes)

```bash
# New usage with timestamps
uv run python src/main.py "URL" [start_sec] [end_sec]

# Examples:
uv run python src/main.py "https://www.youtube.com/watch?v=YL2k4PsAPt0" 23 51
uv run python src/main.py "https://www.youtube.com/watch?v=YL2k4PsAPt0"  # Full video
```

**Process**:
1. URL Validation
2. Parse Timestamps (if provided)
3. Get Video Duration
4. **SKIP Scene Detection** - Create single scene from timestamps
5. Extract Transcripts **ONLY for specified time range**
6. Speaker Identification (if ">>" separators present)
7. Generate Output (**segments.json** + **scene_01.md** only)

**Output**:
```
output/VIDEO_ID/
├── segments.json       ✅ Single scene metadata
└── transcripts/
    └── scene_01.md     ✅ Markdown transcript only (NO .txt, NO speakers.json)
```

---

## Change #1: CLI Arguments

### Current
```python
# Positional arguments
parser.add_argument("url", help="YouTube video URL")
```

### New
```python
# Positional arguments
parser.add_argument("url", help="YouTube video URL")
parser.add_argument("start_sec", type=int, nargs="?", default=None,
                    help="Start timestamp in seconds (optional)")
parser.add_argument("end_sec", type=int, nargs="?", default=None,
                    help="End timestamp in seconds (optional)")
```

### Validation Rules
- Both `start_sec` and `end_sec` must be provided together, or neither
- `start_sec` must be >= 0
- `end_sec` must be > `start_sec`
- `end_sec` must be <= video duration
- Error if only one timestamp provided

### Usage Examples
```bash
# Valid
uv run python src/main.py "URL" 23 51           # Extract 23s-51s
uv run python src/main.py "URL"                 # Full video (backward compatible)

# Invalid
uv run python src/main.py "URL" 23              # Missing end_sec - ERROR
uv run python src/main.py "URL" 100 50          # end < start - ERROR
uv run python src/main.py "URL" -5 10           # Negative timestamp - ERROR
```

**File**: `src/main.py` - `create_argument_parser()` function

---

## Change #2: Skip Scene Detection

### Current Behavior
```python
# Always run scene detection
scenes = detector.detect_scenes(video_id, video_url)
# Falls back to 60s intervals if detection fails
```

### New Behavior
```python
if start_sec is not None and end_sec is not None:
    # User provided timestamps - create single scene
    scene = Scene(
        scene_id="scene_01",
        video_id=video_id,
        start_time=float(start_sec),
        end_time=float(end_sec),
        confidence=1.0  # User-specified, always confident
    )
    scenes = [scene]
else:
    # No timestamps - use original workflow
    scenes = detector.detect_scenes(video_id, video_url)
```

**File**: `src/main.py` - `process_video()` function

---

## Change #3: Time-Range Transcript Extraction

### Current Behavior
```python
# Extracts ALL captions from video
transcripts, caption_type = extractor.process_video_transcript(
    video_id=video_id,
    scenes=scenes
)
```

### New Behavior
```python
# Filter captions by time range
def process_video_transcript(
    self,
    video_id: str,
    scenes: List[Scene],
    start_time: Optional[float] = None,  # NEW
    end_time: Optional[float] = None      # NEW
) -> Tuple[Dict[str, Transcript], CaptionType]:
    # Fetch captions
    captions = self._fetch_captions(video_id)

    # Filter by time range if provided
    if start_time is not None and end_time is not None:
        captions = [
            c for c in captions
            if start_time <= c.start < end_time
        ]

    # Continue with normal processing...
```

**File**: `src/transcript_extractor.py` - `process_video_transcript()` method

---

## Change #4: Remove Unnecessary Outputs

### Files to Remove
1. **❌ `.txt` files** - Remove text format generation
2. **❌ `speakers.json`** - Remove speaker summary file

### Files to Keep
1. **✅ `segments.json`** - Scene metadata
2. **✅ `scene_01.md`** - Markdown transcript

### Implementation

**In `src/output_formatter.py`**:

```python
def write_output(
    self,
    video: Video,
    scenes: List[Scene],
    transcripts: Dict[str, Transcript],
    speakers: List[Speaker],
    output_formats: List[str] = ["json", "markdown"]  # Remove "text" default
) -> None:
    # ... existing code ...

    # Remove this section:
    # if "text" in output_formats:
    #     self._write_text_transcripts(transcripts, output_dir)

    # Remove this section:
    # self._write_speakers_json(video.video_id, speakers, output_dir)
```

**File**: `src/output_formatter.py` - `write_output()` method

---

## Change #5: ">>" Separator Handling

### Finding
The ">>" appears in YouTube captions as dialogue separators. Example:

```markdown
**Speaker 1**: Hey, hun. Would you help me get the plates down? >> Yeah.
Hey, here's an idea. Why don't we use our wedding china today? >> I think
we should save our china for something really special.
```

### Decision
**✅ NO CHANGES NEEDED**

Reasoning:
- The ">>" is part of the original YouTube caption data
- `speaker_identifier.py` currently processes the text as-is
- Removing ">>" would alter the original transcript
- Users can post-process if they want to clean up separators

**File**: No changes to `src/speaker_identifier.py`

---

## Implementation Order

### Phase 1: Core Changes (High Priority)
1. ✅ Update CLI argument parser (`src/main.py`)
2. ✅ Add timestamp validation logic (`src/main.py`)
3. ✅ Skip scene detection when timestamps provided (`src/main.py`)
4. ✅ Pass time range to transcript extractor (`src/main.py`)

### Phase 2: Transcript Filtering (High Priority)
5. ✅ Add time range parameters to `process_video_transcript()` (`src/transcript_extractor.py`)
6. ✅ Filter captions by time range (`src/transcript_extractor.py`)

### Phase 3: Output Cleanup (High Priority)
7. ✅ Remove `.txt` file generation (`src/output_formatter.py`)
8. ✅ Remove `speakers.json` generation (`src/output_formatter.py`)
9. ✅ Update default output formats to exclude "text"

### Phase 4: Testing & Documentation (Medium Priority)
10. ✅ Test with timestamps: `URL 23 51`
11. ✅ Test without timestamps: `URL` (backward compatibility)
12. ✅ Test invalid timestamps
13. ✅ Update README.md with new usage examples

---

## Test Cases

### Test 1: With Timestamps
```bash
uv run python src/main.py "https://www.youtube.com/watch?v=YL2k4PsAPt0" 23 51
```

**Expected Output**:
```
output/YL2k4PsAPt0/
├── segments.json       # Single scene: 23s-51s
└── transcripts/
    └── scene_01.md     # Transcript from 23s-51s only
```

**segments.json**:
```json
{
  "video_id": "YL2k4PsAPt0",
  "scene_count": 1,
  "scenes": [{
    "scene_id": "scene_01",
    "start_time": 23.0,
    "end_time": 51.0,
    "duration": 28.0,
    "start_timecode": "00:00:23",
    "end_timecode": "00:00:51"
  }]
}
```

### Test 2: Without Timestamps (Backward Compatibility)
```bash
uv run python src/main.py "https://www.youtube.com/watch?v=YL2k4PsAPt0"
```

**Expected**: Works as before with fallback scenes, but without `.txt` and `speakers.json`

### Test 3: Invalid Timestamps
```bash
# Missing end timestamp
uv run python src/main.py "URL" 23
# Expected: Error - "Both start_sec and end_sec must be provided"

# End before start
uv run python src/main.py "URL" 100 50
# Expected: Error - "end_sec must be greater than start_sec"

# Negative timestamp
uv run python src/main.py "URL" -5 10
# Expected: Error - "Timestamps must be non-negative"
```

---

## Backward Compatibility

✅ **Fully backward compatible**

When no timestamps are provided, the tool works exactly as before (minus removed outputs):
- Scene detection runs normally
- Full video is processed
- All scenes are generated
- Only difference: no `.txt` files, no `speakers.json`

---

## Files Modified Summary

| File | Lines Changed | Changes |
|------|---------------|---------|
| `src/main.py` | ~50 lines | Add timestamp args, validation, skip scene detection |
| `src/transcript_extractor.py` | ~20 lines | Add time filtering |
| `src/output_formatter.py` | ~30 lines | Remove .txt and speakers.json generation |
| `specs/001-video-scene-extractor/timestamp-mode-spec.md` | New file | This specification document |

---

## Related Documents

- [Feature Specification](spec.md)
- [Implementation Plan](plan.md)
- [Task List](tasks.md)
- [New Workflow Diagram](https://todiagram.com/editor?doc=1ccf6fb4b988cf3ee85466f7)

---

## Status Tracking

- [ ] Phase 1: Core Changes (CLI + Scene Detection Skip)
- [ ] Phase 2: Transcript Filtering
- [ ] Phase 3: Output Cleanup
- [ ] Phase 4: Testing & Documentation
- [ ] Final Review & Merge

---

**Last Updated**: 2025-10-28
**Author**: Claude (AI Assistant)
**Reviewer**: Heesoo Jung
