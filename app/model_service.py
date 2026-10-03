from __future__ import annotations

import io
from pathlib import Path
from threading import Lock
from typing import Any

from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)
_model = None

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

_model_load_lock = Lock()
_inference_lock = Lock()


def get_model() -> Any:
    global _model
    if _model is not None:
        return _model

    # Startup normally loads the model, but retain this guard for direct callers
    # (including scripts) and make concurrent first calls safe.
    with _model_load_lock:
        if _model is not None:
            return _model

        model_path = Path(settings.model_path)
        if not model_path.is_absolute():
            model_path = (Path(__file__).resolve().parent.parent / model_path).resolve()

        if not model_path.exists():
            raise FileNotFoundError(
                "Model not found at "
                f"{model_path}. Add the trained checkpoint as best.pt "
                "or set MODEL_PATH."
            )

        from ultralytics import YOLO

        logger.info("Loading YOLO model from %s", model_path)
        _model = YOLO(str(model_path))
    return _model


def is_model_ready() -> bool:
    """Return whether this process has successfully initialized the model."""
    return _model is not None


def _normalize_box(box: Any) -> list[float]:
    if hasattr(box, "tolist"):
        values = box.tolist()
        if isinstance(values, list) and values:
            return [float(v) for v in values[0]]
        return [float(v) for v in values]
    if isinstance(box, (list, tuple)) and box:
        return [float(v) for v in box]
    return [0.0, 0.0, 0.0, 0.0]


def _normalize_detections(result: Any) -> list[dict[str, Any]]:
    detections: list[dict[str, Any]] = []
    names = getattr(result, "names", {}) or {}
    boxes = getattr(result, "boxes", None)

    if boxes is None:
        return detections

    cls_values = (
        boxes.cls.tolist() if hasattr(boxes.cls, "tolist") else list(boxes.cls)
    )
    conf_values = (
        boxes.conf.tolist() if hasattr(boxes.conf, "tolist") else list(boxes.conf)
    )
    xyxy_values = (
        boxes.xyxy.tolist() if hasattr(boxes.xyxy, "tolist") else list(boxes.xyxy)
    )

    for idx, cls in enumerate(cls_values):
        class_id = int(cls)
        confidence = float(conf_values[idx]) if idx < len(conf_values) else 0.0
        bbox = (
            _normalize_box(xyxy_values[idx])
            if idx < len(xyxy_values)
            else [0.0, 0.0, 0.0, 0.0]
        )

        detections.append(
            {
                "class_id": class_id,
                "class_name": names.get(class_id, str(class_id)),
                "confidence": round(confidence, 4),
                "bbox": bbox,
            }
        )

    return detections


def _build_report(detections: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a compact, display-ready summary of model detections."""
    by_class: dict[tuple[int, str], list[float]] = {}
    for detection in detections:
        key = (detection["class_id"], detection["class_name"])
        by_class.setdefault(key, []).append(detection["confidence"])

    damage_types = [
        {
            "class_id": class_id,
            "class_name": class_name,
            "count": len(confidences),
            "highest_confidence": round(max(confidences), 4),
        }
        for (class_id, class_name), confidences in sorted(by_class.items())
    ]
    total_detections = len(detections)

    if not total_detections:
        summary = "No road damage was detected."
    else:
        breakdown = ", ".join(
            f"{item['class_name']}: {item['count']}" for item in damage_types
        )
        summary = f"Detected {total_detections} road-damage instance(s) ({breakdown})."

    return {
        "status": "damage_detected" if total_detections else "no_damage_detected",
        "total_detections": total_detections,
        "damage_types": damage_types,
        "summary": summary,
    }


def predict_image(image_bytes: bytes, filename: str = "image.jpg") -> dict[str, Any]:

    try:
        image = Image.open(io.BytesIO(image_bytes))  # lazy: reads the header only

        if image.format not in ALLOWED_FORMATS:
            raise ValueError("Unsupported image format. Use JPEG, PNG or WebP")

        width, height = image.size
        if width * height > settings.max_image_pixels:
            raise ValueError(
                f"Image too large ({width}x{height}). "
                f"Maximum is {settings.max_image_pixels:,} pixels"
            )

        image.load()  # the expensive full decode, only after the checks pass
    except Image.DecompressionBombError as exc:
        raise ValueError("Image dimensions are too large") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The uploaded file is not a valid image") from exc    
    image_width, image_height = image.size
    # Ultralytics inference mutates model state internally. Keep use of the
    # shared model serialized instead of allowing the FastAPI threadpool to
    # invoke it concurrently.
    with _inference_lock:
        model = get_model()
        results = model(
            image,
            conf=settings.model_confidence_threshold,
            imgsz=settings.model_imgsz,
            verbose=False,
        )

    detections: list[dict[str, Any]] = []
    if isinstance(results, (list, tuple)):
        for result in results:
            detections.extend(_normalize_detections(result))
    else:
        detections.extend(_normalize_detections(results))

    return {
        "filename": filename,
        "image_width": image_width,
        "image_height": image_height,
        "num_detections": len(detections),
        "detections": detections,
        "report": _build_report(detections),
    }
