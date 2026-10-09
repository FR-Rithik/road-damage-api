from __future__ import annotations

import io
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from app.config import settings
from app.logger import get_logger
from app.model_service import get_model, predict_image

logger = get_logger(__name__)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CHUNK_SIZE = 1024 * 1024  # 1 MB


def _validate_member_path(filename: str) -> Path:
    """
    Validate a ZIP member path and return a safe relative Path.

    Rejects:
    - absolute paths
    - '..' path traversal
    - Windows drive-style paths
    """
    normalized = filename.replace("\\", "/")
    path = PurePosixPath(normalized)

    if path.is_absolute():
        raise ValueError(f"Unsafe absolute path in ZIP: {filename}")

    if any(part == ".." for part in path.parts):
        raise ValueError(f"Unsafe path traversal in ZIP: {filename}")

    if path.parts and ":" in path.parts[0]:
        raise ValueError(f"Unsafe drive path in ZIP: {filename}")

    if not path.parts:
        raise ValueError("ZIP contains an empty filename")

    return Path(*path.parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    """
    Detect Unix symlink entries stored inside a ZIP.
    """
    mode = (info.external_attr >> 16) & 0o170000
    return mode == stat.S_IFLNK

def _validate_unique_label_paths(
    image_infos: list[tuple[zipfile.ZipInfo, Path]],
) -> None:
    """
    Reject images that would generate the same YOLO label path.
    """
    seen_labels: dict[str, str] = {}

    for _, relative_path in image_infos:
        label_relative_path = relative_path.with_suffix(".txt")
        label_key = label_relative_path.as_posix().casefold()

        previous_image = seen_labels.get(label_key)

        if previous_image is not None:
            raise ValueError(
                "Multiple images would overwrite the same label file: "
                f"'{previous_image}' and '{relative_path.as_posix()}'. "
                "Rename one of the images or remove the duplicate."
            )

        seen_labels[label_key] = relative_path.as_posix()

def _read_member_with_limit(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    max_bytes: int,
) -> bytes:
    """
    Read one ZIP entry while enforcing a hard uncompressed size limit.
    """
    buffer = io.BytesIO()
    total = 0

    with archive.open(info, "r") as source:
        while True:
            chunk = source.read(CHUNK_SIZE)

            if not chunk:
                break

            total += len(chunk)

            if total > max_bytes:
                raise ValueError(
                    f"ZIP entry '{info.filename}' exceeds the "
                    f"{max_bytes // (1024 * 1024)} MB file limit"
                )

            buffer.write(chunk)

    return buffer.getvalue()


def _get_model_names() -> dict[int, str]:
    """
    Get class names from the loaded YOLO model.
    """
    model = get_model()
    names = getattr(model, "names", {}) or {}

    if isinstance(names, dict):
        return {
            int(class_id): str(class_name)
            for class_id, class_name in names.items()
        }

    if isinstance(names, list):
        return {
            class_id: str(class_name)
            for class_id, class_name in enumerate(names)
        }

    raise ValueError("Unable to read class names from the YOLO model")


def _convert_detections_to_yolo(
    detections: list[dict[str, Any]],
    image_width: int,
    image_height: int,
) -> list[str]:
    """
    Convert xyxy bounding boxes into normalized YOLO format.

    YOLO format:
        class_id x_center y_center width height
    """
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Invalid image dimensions")

    lines: list[str] = []

    for detection in detections:
        try:
            class_id = int(detection["class_id"])
            x1, y1, x2, y2 = (
                float(value)
                for value in detection["bbox"]
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed detection: %s", detection)
            continue

        # Clamp coordinates to image boundaries.
        x1 = max(0.0, min(x1, float(image_width)))
        y1 = max(0.0, min(y1, float(image_height)))
        x2 = max(0.0, min(x2, float(image_width)))
        y2 = max(0.0, min(y2, float(image_height)))

        box_width = x2 - x1
        box_height = y2 - y1

        if box_width <= 0 or box_height <= 0:
            logger.warning("Skipping invalid bounding box: %s", detection)
            continue

        x_center = (x1 + x2) / 2.0
        y_center = (y1 + y2) / 2.0

        # Normalize to [0, 1].
        x_center /= image_width
        y_center /= image_height
        box_width /= image_width
        box_height /= image_height

        lines.append(
            f"{class_id} "
            f"{x_center:.6f} "
            f"{y_center:.6f} "
            f"{box_width:.6f} "
            f"{box_height:.6f}"
        )

    return lines


def _write_class_files(
    output_root: Path,
    class_names: dict[int, str],
) -> None:
    """
    Create classes.txt and data.yaml.
    """
    classes_path = output_root / "classes.txt"

    with classes_path.open("w", encoding="utf-8") as file:
        for class_id in sorted(class_names):
            file.write(f"{class_names[class_id]}\n")

    data_yaml_path = output_root / "data.yaml"

    yaml_lines = [
        "# Generated by Annotation Wizard",
        "# This dataset has not been split into train/validation sets.",
        "path: .",
        "names:",
    ]

    for class_id in sorted(class_names):
        # JSON strings are valid YAML strings.
        yaml_lines.append(
            f"  {class_id}: {json.dumps(class_names[class_id])}"
        )

    with data_yaml_path.open("w", encoding="utf-8") as file:
        file.write("\n".join(yaml_lines))
        file.write("\n")


def _write_dataset_info(
    output_root: Path,
    processed_images: int,
    images_with_detections: int,
    total_detections: int,
    failed_images: list[dict[str, str]],
) -> None:
    """
    Create a small metadata file describing the labeling result.
    """
    info_path = output_root / "dataset_info.txt"

    with info_path.open("w", encoding="utf-8") as file:
        file.write("Annotation Wizard Dataset\n")
        file.write("========================\n\n")

        file.write(f"Processed images: {processed_images}\n")
        file.write(
            f"Images with detections: {images_with_detections}\n"
        )
        file.write(f"Total detections: {total_detections}\n")
        file.write(f"Failed images: {len(failed_images)}\n")

        if failed_images:
            file.write("\nFailed images:\n")

            for failure in failed_images:
                file.write(
                    f"- {failure['filename']}: {failure['error']}\n"
                )


def _create_output_zip(
    output_root: Path,
    zip_path: Path,
) -> None:
    """
    Create the final downloadable ZIP.
    """
    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for file_path in output_root.rglob("*"):
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(output_root)

            archive.write(
                file_path,
                relative_path.as_posix(),
            )


def save_uploaded_zip(
    source,
    destination: Path,
) -> None:
    """
    Save UploadFile content to disk without loading the entire ZIP
    into memory.
    """
    total = 0

    with destination.open("wb") as output:
        while True:
            chunk = source.read(CHUNK_SIZE)

            if not chunk:
                break

            total += len(chunk)

            if total > settings.max_dataset_zip_bytes:
                raise ValueError(
                    "Dataset ZIP is too large. "
                    f"Maximum size is "
                    f"{settings.max_dataset_zip_bytes // (1024 * 1024)} MB"
                )

            output.write(chunk)


def label_dataset_zip(
    zip_path: Path,
    working_directory: Path,
) -> tuple[Path, dict[str, int]]:
    """
    Main dataset auto-labeling pipeline.

    Input:
        zip_path

    Output:
        labeled ZIP containing:
            labels/
            classes.txt
            data.yaml
            dataset_info.txt
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Uploaded file is not a valid ZIP archive")

    output_root = working_directory / "labeled_dataset"
    labels_root = output_root / "labels"

    labels_root.mkdir(parents=True, exist_ok=True)

    try:
        archive = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("Uploaded file is not a valid ZIP archive") from exc

    with archive:
        infos = archive.infolist()

        if not infos:
            raise ValueError("The ZIP archive is empty")

        seen_paths: set[str] = set()
        image_infos: list[tuple[zipfile.ZipInfo, Path]] = []

        total_uncompressed_bytes = 0

        for info in infos:
            if info.is_dir():
                continue

            if _is_symlink(info):
                raise ValueError(
                    f"ZIP contains an unsupported symbolic link: "
                    f"{info.filename}"
                )

            safe_path = _validate_member_path(info.filename)

            key = safe_path.as_posix().lower()

            if key in seen_paths:
                raise ValueError(
                    f"ZIP contains duplicate paths: {info.filename}"
                )

            seen_paths.add(key)

            total_uncompressed_bytes += info.file_size

            if (
                total_uncompressed_bytes
                > settings.max_dataset_uncompressed_bytes
            ):
                raise ValueError(
                    "The uncompressed dataset is too large. "
                    f"Maximum is "
                    f"{settings.max_dataset_uncompressed_bytes // (1024 * 1024)} MB"
                )

            extension = safe_path.suffix.lower()

            if extension not in ALLOWED_IMAGE_EXTENSIONS:
                # Ignore non-image files such as existing .txt labels,
                # README files, metadata, etc.
                continue

            if info.file_size > settings.max_dataset_image_bytes:
                raise ValueError(
                    f"Image '{info.filename}' is too large. "
                    f"Maximum image size is "
                    f"{settings.max_dataset_image_bytes // (1024 * 1024)} MB"
                )

            image_infos.append((info, safe_path))

        if not image_infos:
            raise ValueError(
                "No supported images found. "
                "Use JPG, JPEG, PNG or WebP images."
            )
        _validate_unique_label_paths(image_infos)
        if len(image_infos) > settings.max_dataset_images:
            raise ValueError(
                f"Dataset contains {len(image_infos)} images. "
                f"Maximum is {settings.max_dataset_images}."
            )

        # Load the model once to obtain the class list.
        class_names = _get_model_names()

        processed_images = 0
        images_with_detections = 0
        total_detections = 0
        failed_images: list[dict[str, str]] = []

        for index, (info, relative_path) in enumerate(
            image_infos,
            start=1,
        ):
            logger.info(
                "Processing image %d/%d: %s",
                index,
                len(image_infos),
                relative_path.as_posix(),
            )

            try:
                image_bytes = _read_member_with_limit(
                    archive,
                    info,
                    settings.max_dataset_image_bytes,
                )

                prediction = predict_image(
                    image_bytes,
                    relative_path.as_posix(),
                )

                image_width = int(prediction["image_width"])
                image_height = int(prediction["image_height"])

                detections = prediction["detections"]

                label_lines = _convert_detections_to_yolo(
                    detections,
                    image_width,
                    image_height,
                )

                # Save the YOLO label.
                label_relative_path = relative_path.with_suffix(
                    ".txt"
                )

                destination_label = (
                    labels_root / label_relative_path
                ).resolve()

                destination_label.relative_to(
                    labels_root.resolve()
                )

                destination_label.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                destination_label.write_text(
                    (
                        "\n".join(label_lines)
                        + ("\n" if label_lines else "")
                    ),
                    encoding="utf-8",
                )

                processed_images += 1

                if detections:
                    images_with_detections += 1

                total_detections += len(detections)

            except ValueError as exc:
                # Bad image files should not destroy the entire job.
                failed_images.append(
                    {
                        "filename": relative_path.as_posix(),
                        "error": str(exc),
                    }
                )

                logger.warning(
                    "Skipping image %s: %s",
                    relative_path.as_posix(),
                    exc,
                )

            except FileNotFoundError:
                # Usually means the model checkpoint is unavailable.
                logger.exception(
                    "Road-damage model checkpoint is unavailable"
                )
                raise

            except Exception:
                logger.exception(
                    "Unexpected error while processing %s",
                    relative_path.as_posix(),
                )
                raise

        if processed_images == 0:
            raise ValueError(
                "No images could be successfully processed."
            )

        _write_class_files(
            output_root,
            class_names,
        )

        _write_dataset_info(
            output_root,
            processed_images,
            images_with_detections,
            total_detections,
            failed_images,
        )

        output_zip = working_directory / "annotation-wizard-labeled.zip"

        _create_output_zip(
            output_root,
            output_zip,
        )

    stats = {
        "total_images": len(image_infos),
        "processed_images": processed_images,
        "images_with_detections": images_with_detections,
        "total_detections": total_detections,
        "failed_images": len(failed_images),
    }

    logger.info(
        "Dataset labeling completed: %s",
        stats,
    )

    return output_zip, stats


def create_working_directory() -> Path:
    """
    Create a temporary directory for one labeling request.
    """
    return Path(
        tempfile.mkdtemp(
            prefix="annotation_wizard_"
        )
    )


def cleanup_working_directory(path: Path) -> None:
    """
    Remove temporary job files.
    """
    shutil.rmtree(
        path,
        ignore_errors=True,
    )