from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.model_service import predict_image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_IMAGE = PROJECT_ROOT / "image.png"


def _model_path() -> Path:
    path = Path(settings.model_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def test_predict_image_runs_real_model_on_sample_image():
    """Smoke-test the real checkpoint and the result normalization path."""
    if not SAMPLE_IMAGE.exists():
        pytest.skip("Real-model sample image is not available")
    if not _model_path().exists():
        pytest.skip("Real-model checkpoint is not available")

    with Image.open(SAMPLE_IMAGE) as image:
        expected_size = image.size

    prediction = predict_image(SAMPLE_IMAGE.read_bytes(), SAMPLE_IMAGE.name)

    assert prediction["filename"] == SAMPLE_IMAGE.name
    assert (prediction["image_width"], prediction["image_height"]) == expected_size
    assert prediction["num_detections"] == len(prediction["detections"])
    assert prediction["report"]["total_detections"] == prediction["num_detections"]
    for detection in prediction["detections"]:
        assert {"class_id", "class_name", "confidence", "bbox"} == set(detection)
        assert len(detection["bbox"]) == 4
