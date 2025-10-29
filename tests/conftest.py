"""
Pytest configuration and shared fixtures for all tests
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.models import Video, Scene, Transcript, CaptionType
from config.default_config import DEFAULT_CONFIG


@pytest.fixture
def sample_video():
    """Create a sample Video object for testing"""
    return Video(
        video_id="dQw4w9WgXcQ",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        duration=213,
        has_captions=True,
        caption_type=CaptionType.MANUAL,
    )


@pytest.fixture
def sample_scenes():
    """Create sample Scene objects for testing"""
    return [
        Scene(scene_id="scene_01", video_id="dQw4w9WgXcQ", start_time=0.0, end_time=45.0),
        Scene(scene_id="scene_02", video_id="dQw4w9WgXcQ", start_time=45.0, end_time=90.0),
        Scene(scene_id="scene_03", video_id="dQw4w9WgXcQ", start_time=90.0, end_time=150.0),
        Scene(scene_id="scene_04", video_id="dQw4w9WgXcQ", start_time=150.0, end_time=213.0),
    ]


@pytest.fixture
def sample_transcripts():
    """Create sample Transcript objects for testing"""
    return {
        "scene_01": Transcript(
            scene_id="scene_01",
            raw_text="Hello and welcome to this video",
            formatted_text="**Speaker 1**: Hello and welcome to this video",
            language="en",
        ),
        "scene_02": Transcript(
            scene_id="scene_02",
            raw_text="Today we will discuss an important topic",
            formatted_text="**Speaker 1**: Today we will discuss an important topic",
            language="en",
        ),
        "scene_03": Transcript(
            scene_id="scene_03",
            raw_text="Let me show you some examples",
            formatted_text="**Speaker 1**: Let me show you some examples",
            language="en",
        ),
        "scene_04": Transcript(
            scene_id="scene_04",
            raw_text="Thank you for watching",
            formatted_text="**Speaker 1**: Thank you for watching",
            language="en",
        ),
    }


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_config():
    """Provide default configuration for tests"""
    return DEFAULT_CONFIG
