const elements = {
  apiKey: document.querySelector("#api-key"),
  connect: document.querySelector("#connect-button"),
  connectionState: document.querySelector("#connection-state"),
  clientName: document.querySelector("#client-name"),
  healthDot: document.querySelector("#health-dot"),
  healthState: document.querySelector("#health-state"),
  today: document.querySelector("#today"),
  dropZone: document.querySelector("#drop-zone"),
  fileInput: document.querySelector("#file-input"),
  fileName: document.querySelector("#file-name"),
  previewImage: document.querySelector("#preview-image"),
  canvas: document.querySelector("#annotation-canvas"),
  analyze: document.querySelector("#analyze-button"),
  clear: document.querySelector("#clear-button"),
  saveReport: document.querySelector("#save-report"),
  formMessage: document.querySelector("#form-message"),
  reportState: document.querySelector("#report-state"),
  total: document.querySelector("#total-detections"),
  summary: document.querySelector("#report-summary"),
  damageTypes: document.querySelector("#damage-types"),
  activityList: document.querySelector("#activity-list"),
  sessionCount: document.querySelector("#session-count"),
};

const colors = ["#d35b45", "#f0aa20", "#3f83a8", "#4a998b"];
const classColors = { D00: colors[0], D10: colors[1], D20: colors[2], D40: colors[3] };
let selectedFile = null;
let previewUrl = null;
let assessmentCount = 0;

elements.apiKey.value = sessionStorage.getItem("roadwatch-api-key") || "";
elements.today.textContent = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
}).format(new Date());

function setMessage(message = "", isError = false) {
  elements.formMessage.textContent = message;
  elements.formMessage.classList.toggle("error", isError);
}

function getColor(className, classId = 0) {
  return classColors[className] || colors[classId % colors.length];
}

function resetCanvas() {
  const context = elements.canvas.getContext("2d");
  context.clearRect(0, 0, elements.canvas.width, elements.canvas.height);
}

function drawDetections(detections = [], imageWidth, imageHeight) {
  const image = elements.previewImage;
  const naturalWidth = image.naturalWidth || imageWidth;
  const naturalHeight = image.naturalHeight || imageHeight;
  if (!naturalWidth || !naturalHeight) return;

  const canvas = elements.canvas;
  canvas.width = naturalWidth;
  canvas.height = naturalHeight;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  const scaleX = naturalWidth / (imageWidth || naturalWidth);
  const scaleY = naturalHeight / (imageHeight || naturalHeight);
  const lineWidth = Math.max(2, Math.round(naturalWidth / 350));
  const fontSize = Math.max(13, Math.round(naturalWidth / 42));

  detections.forEach((detection, index) => {
    const [x1, y1, x2, y2] = detection.bbox || [];
    if (![x1, y1, x2, y2].every(Number.isFinite)) return;
    const x = x1 * scaleX;
    const y = y1 * scaleY;
    const width = Math.max(1, (x2 - x1) * scaleX);
    const height = Math.max(1, (y2 - y1) * scaleY);
    const color = getColor(detection.class_name, detection.class_id || index);
    const label = `${detection.class_name} ${Math.round((detection.confidence || 0) * 100)}%`;

    context.lineWidth = lineWidth;
    context.strokeStyle = color;
    context.strokeRect(x, y, width, height);
    context.font = `700 ${fontSize}px Inter, system-ui, sans-serif`;
    const labelWidth = context.measureText(label).width + fontSize;
    const labelY = Math.max(0, y - fontSize * 1.45);
    context.fillStyle = color;
    context.fillRect(x, labelY, labelWidth, fontSize * 1.45);
    context.fillStyle = "#ffffff";
    context.fillText(label, x + fontSize / 2, labelY + fontSize * 1.06);
  });
}

function renderRows(damageTypes) {
  elements.damageTypes.replaceChildren();
  if (!damageTypes.length) {
    const empty = document.createElement("p");
    empty.className = "empty-row";
    empty.textContent = "No damage classes detected.";
    elements.damageTypes.append(empty);
    return;
  }

  damageTypes.forEach((type) => {
    const row = document.createElement("div");
    row.className = "damage-row";
    const className = document.createElement("span");
    className.className = "damage-class";
    const swatch = document.createElement("i");
    swatch.style.background = getColor(type.class_name, type.class_id);
    className.append(swatch, document.createTextNode(type.class_name));
    const count = document.createElement("span");
    count.textContent = type.count;
    const confidence = document.createElement("span");
    confidence.textContent = `${Math.round(type.highest_confidence * 100)}%`;
    row.append(className, count, confidence);
    elements.damageTypes.append(row);
  });
}

function renderReport(report) {
  const isDamage = report.status === "damage_detected";
  elements.reportState.textContent = isDamage ? "Damage found" : "Clear result";
  elements.reportState.dataset.status = report.status;
  elements.total.textContent = report.total_detections;
  elements.summary.textContent = report.summary;
  renderRows(report.damage_types || []);
}

function addActivity(fileName, report) {
  assessmentCount += 1;
  elements.sessionCount.textContent = `${assessmentCount} completed`;
  const empty = elements.activityList.querySelector(".empty-activity");
  if (empty) empty.remove();

  const row = document.createElement("div");
  row.className = "activity-row";
  const name = document.createElement("span");
  name.className = "activity-file";
  name.textContent = fileName;
  const time = document.createElement("span");
  time.className = "activity-time";
  time.textContent = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date());
  const result = document.createElement("span");
  const damaged = report.status === "damage_detected";
  result.className = `activity-result ${damaged ? "damage" : "clear"}`;
  result.textContent = damaged ? `${report.total_detections} found` : "No damage";
  row.append(name, time, result);
  elements.activityList.prepend(row);
}

function selectFile(file) {
  if (!file) return;
  const allowed = ["image/jpeg", "image/png", "image/webp"];
  if (!allowed.includes(file.type)) {
    setMessage("Use a JPEG, PNG, or WebP image.", true);
    return;
  }
  if (file.size > 1024 * 1024) {
    setMessage("This image exceeds the 1 MB upload limit.", true);
    return;
  }

  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  elements.previewImage.src = previewUrl;
  elements.previewImage.alt = `Selected road image: ${file.name}`;
  elements.fileName.textContent = file.name;
  elements.dropZone.classList.add("has-upload");
  elements.analyze.disabled = false;
  resetCanvas();
  setMessage("");
  elements.previewImage.onload = resetCanvas;
}

function resetAssessment() {
  selectedFile = null;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  elements.fileInput.value = "";
  elements.previewImage.src = "/reference-image";
  elements.previewImage.alt = "Reference road damage examples";
  elements.fileName.textContent = "Reference image";
  elements.dropZone.classList.remove("has-upload");
  elements.analyze.disabled = true;
  elements.reportState.textContent = "Awaiting image";
  elements.reportState.dataset.status = "idle";
  elements.total.textContent = "0";
  elements.summary.textContent = "Choose an image to start a new road condition assessment.";
  elements.damageTypes.replaceChildren();
  const empty = document.createElement("p");
  empty.className = "empty-row";
  empty.textContent = "Results will appear here.";
  elements.damageTypes.append(empty);
  resetCanvas();
  setMessage("");
}

async function readError(response) {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : "The server could not process this image.";
  } catch {
    return "The server could not process this image.";
  }
}

async function connect() {
  const key = elements.apiKey.value.trim();
  if (!key) {
    elements.connectionState.textContent = "Enter an API key to connect.";
    elements.connectionState.dataset.state = "error";
    return;
  }

  elements.connect.disabled = true;
  elements.connect.textContent = "Checking";
  try {
    const response = await fetch("/auth/me", { headers: { "X-API-Key": key } });
    if (!response.ok) throw new Error(await readError(response));
    const client = await response.json();
    sessionStorage.setItem("roadwatch-api-key", key);
    elements.connectionState.textContent = `Connected as ${client.name}`;
    elements.connectionState.dataset.state = "connected";
    elements.clientName.textContent = client.name;
  } catch (error) {
    sessionStorage.removeItem("roadwatch-api-key");
    elements.connectionState.textContent = error.message || "Connection unavailable.";
    elements.connectionState.dataset.state = "error";
    elements.clientName.textContent = "Local session";
  } finally {
    elements.connect.disabled = false;
    elements.connect.textContent = "Connect";
  }
}

async function analyze() {
  if (!selectedFile) return;
  const apiKey = elements.apiKey.value.trim();
  if (!apiKey) {
    setMessage("Connect an API key before analyzing an image.", true);
    return;
  }

  elements.analyze.disabled = true;
  elements.analyze.textContent = "Analyzing";
  elements.reportState.textContent = "Processing";
  elements.reportState.dataset.status = "idle";
  setMessage("Running road-damage detection...");
  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const endpoint = elements.saveReport.checked ? "/images" : "/predict";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "X-API-Key": apiKey },
      body: formData,
    });
    if (!response.ok) throw new Error(await readError(response));
    const data = await response.json();
    const prediction = data.prediction || data;
    const report = data.report || prediction.report;
    renderReport(report);
    drawDetections(prediction.detections, prediction.image_width, prediction.image_height);
    addActivity(selectedFile.name, report);
    setMessage(elements.saveReport.checked ? "Assessment saved to the image register." : "Assessment complete.");
  } catch (error) {
    elements.reportState.textContent = "Request failed";
    elements.reportState.dataset.status = "error";
    setMessage(error.message, true);
  } finally {
    elements.analyze.disabled = false;
    elements.analyze.textContent = "Analyze image";
  }
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    const health = await response.json();
    const ready = response.ok && health.model === "ready";
    elements.healthDot.className = `status-dot ${ready ? "ready" : "degraded"}`;
    elements.healthState.textContent = ready ? "Service ready" : "Service degraded";
  } catch {
    elements.healthDot.className = "status-dot degraded";
    elements.healthState.textContent = "Service unavailable";
  }
}

elements.fileInput.addEventListener("change", (event) => selectFile(event.target.files[0]));
elements.dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  elements.dropZone.classList.add("dragging");
});
elements.dropZone.addEventListener("dragleave", () => elements.dropZone.classList.remove("dragging"));
elements.dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  elements.dropZone.classList.remove("dragging");
  selectFile(event.dataTransfer.files[0]);
});
elements.connect.addEventListener("click", connect);
elements.clear.addEventListener("click", resetAssessment);
elements.analyze.addEventListener("click", analyze);
elements.previewImage.addEventListener("load", resetCanvas);

checkHealth();
if (elements.apiKey.value) connect();
