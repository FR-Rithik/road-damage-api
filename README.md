# Annotation Wizard
## Previously presented as Road Damage API.

**Automated Road Damage Dataset Annotation using YOLOv8 and FastAPI**

Annotation Wizard is a dataset annotation tool that automates object-detection labeling for road-damage images. Instead of manually drawing bounding boxes and labeling every image, users can upload a ZIP archive of images and let a trained YOLOv8 model generate annotations automatically.

The application processes the uploaded images, generates labels in YOLO format, and provides a downloadable ZIP containing the generated label files.

Previously presented as **Road Damage API**, this project has evolved from a road-damage detection API into a tool focused on automating dataset annotation.

## Features

* **Batch image processing:** Upload multiple images in a single ZIP archive.
* **Automatic annotation:** Detect road damage using a trained YOLOv8 model.
* **YOLO-format labels:** Generate annotation files containing class IDs and normalized bounding-box coordinates.
* **Lightweight downloads:** Download the generated label files without including the original images.
* **Multiple damage classes:** Detect four road-damage categories: D00, D10, D20, and D40.
* **REST API:** Access the annotation functionality through a FastAPI backend.
* **Containerized deployment:** Run the application using Docker and Docker Compose.

## How It Works

1. **Upload:** Submit a ZIP archive containing road images.
2. **Inference:** The trained YOLOv8 model processes the images and detects road damage.
3. **Annotation generation:** Convert the detections into YOLO-format label files.
4. **Download:** Receive a ZIP archive containing the generated annotations, ready for use in a compatible object-detection dataset.

## Technology Stack

* **Backend:** Python, FastAPI
* **Object detection:** YOLOv8
* **Model deployment:** ONNX Runtime where configured
* **Database:** PostgreSQL, SQLAlchemy
* **Database migrations:** Alembic
* **Containerization:** Docker, Docker Compose
* **Testing:** Pytest

## Supported Classes

| Class ID | Label                    |
| -------- | ------------------------ |
| 0        | D00 — Longitudinal crack |
| 1        | D10 — Transverse crack   |
| 2        | D20 — Alligator crack    |
| 3        | D40 — Pothole            |

The class IDs must match the class ordering configured in the trained model and used by the generated dataset labels.

## Requirements

* Docker
* Docker Compose

If you want to run or develop the application outside Docker, you will also need a compatible Python environment and the required dependencies.

## Getting Started

### 1. Clone the repository

The repository URL remains unchanged to preserve the link previously shared with recruiters.

```bash
git clone https://github.com/FR-Rithik/road-damage-api.git
cd road-damage-api
```

### 2. Configure environment variables

Create your local environment file:

```bash
cp .env.example .env
```

Configure the required database credentials, API settings, and model path according to your environment.

### 3. Start the application

```bash
docker compose up --build
```

### 4. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

### 5. Access the API

Once the application starts, visit:

* **API documentation:** http://localhost:8000/docs
* **Alternative API documentation:** http://localhost:8000/redoc
* **Health check:** http://localhost:8000/health

The availability of these endpoints depends on the application configuration.

## API Usage

The application exposes REST endpoints through FastAPI. The exact request fields and response schemas are available in the interactive API documentation at `/docs`.

### Authentication

Protected endpoints use an API key supplied through the `X-API-Key` HTTP header.

```http
X-API-Key: your-api-key-here
```

Use a valid API key configured for your deployment.

### Main Annotation Workflow

Submit a ZIP archive containing images to the batch annotation endpoint configured by the application.

The expected workflow is:

* Upload an image archive.
* Run automatic road-damage detection.
* Generate YOLO-format label files.
* Download the archive containing the generated labels.

Refer to `/docs` for the current batch-upload endpoint, accepted file format, request limits, and response details.

### Individual Image Detection

The existing API also supports individual-image detection through the `/predict` endpoint.

Example using the existing image-prediction endpoint:

```bash
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@road.jpg"
```

Check the API documentation for the exact response schema and any deployment-specific requirements.

## Model Configuration

The application uses a trained road-damage detection model to generate annotations.

Depending on the deployment configuration, the model may be loaded from a PyTorch checkpoint (`.pt`) or an exported ONNX model (`.onnx`).

Configure the model path using the environment variable supported by the application. The original PyTorch configuration uses `MODEL_PATH`; verify the active configuration when deploying the ONNX version.

The model is intended to detect these four classes:

* D00
* D10
* D20
* D40

The generated annotations depend on the model's predictions, confidence thresholds, class mapping, and inference configuration. Automatically generated labels should be reviewed before being treated as ground truth.

## Running Tests

Run the test suite inside the running API container:

```bash
docker compose exec api pytest -q
```

## Project Structure

The following is the known structure of the original backend. The batch-annotation implementation may introduce additional files or modules.

```text
app/
├── main.py
├── config.py
├── database.py
├── models.py
├── auth.py
├── errors.py
├── logger.py
└── routers/
    └── auth.py

tests/
└── test_auth.py

Dockerfile
docker-compose.yml
alembic/
pyproject.toml
```

## Project Evolution

This project was initially developed as a road-damage detection API. It is now being extended into **Annotation Wizard**, with a focus on automating the creation of object-detection datasets.

The existing road-damage detection model serves as the inference engine, while the batch-processing workflow makes it possible to generate annotations for multiple images at once.

## Future Improvements

Potential improvements include:

* A web interface for uploading archives and downloading annotations.
* Annotation previews with bounding boxes and confidence scores.
* Configurable confidence thresholds.
* Support for additional object-detection models and datasets.
* Progress reporting for large annotation jobs.
* Additional export formats and dataset-validation tools.

---

**Repository:** (https://github.com/FR-Rithik/annotation-wizard/tree/deployment/onnx-runtime)

**Project:** Annotation Wizard — Automated Road Damage Dataset Annotation
