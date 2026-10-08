const state = {
  files: [],
  activeFileId: null,
  measurements: [],
  filteredMeasurements: [],
};

const elements = {
  uploadForm: document.querySelector("#uploadForm"),
  fileInput: document.querySelector("#fileInput"),
  dropZone: document.querySelector("#dropZone"),
  uploadButton: document.querySelector("#uploadButton"),
  uploadStatus: document.querySelector("#uploadStatus"),
  refreshButton: document.querySelector("#refreshButton"),
  fileList: document.querySelector("#fileList"),
  emptyState: document.querySelector("#emptyState"),
  fileDetail: document.querySelector("#fileDetail"),
  detailStatus: document.querySelector("#detailStatus"),
  detailFilename: document.querySelector("#detailFilename"),
  detailMeta: document.querySelector("#detailMeta"),
  featureCount: document.querySelector("#featureCount"),
  polygonCount: document.querySelector("#polygonCount"),
  lineCount: document.querySelector("#lineCount"),
  previewCount: document.querySelector("#previewCount"),
  geometryCanvas: document.querySelector("#geometryCanvas"),
  totalArea: document.querySelector("#totalArea"),
  totalLength: document.querySelector("#totalLength"),
  crsLabel: document.querySelector("#crsLabel"),
  measurementsBody: document.querySelector("#measurementsBody"),
  featureSearch: document.querySelector("#featureSearch"),
};

function formatNumber(value, fractionDigits = 2) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en", {
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

function setStatus(message, isError = false) {
  elements.uploadStatus.textContent = message;
  elements.uploadStatus.classList.toggle("error", isError);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const message = payload?.detail || `Request failed with ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

async function loadFiles() {
  state.files = await fetchJson("/api/files/");
  renderFileList();

  if (!state.activeFileId && state.files.length > 0) {
    await selectFile(state.files[0].id);
  }
}

function renderFileList() {
  elements.fileList.innerHTML = "";

  if (state.files.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No uploads yet.";
    elements.fileList.append(empty);
    return;
  }

  for (const file of state.files) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "file-item";
    item.classList.toggle("is-active", file.id === state.activeFileId);
    item.innerHTML = `
      <strong>${escapeHtml(file.filename)}</strong>
      <span>${file.feature_count} features · ${file.status}</span>
    `;
    item.addEventListener("click", () => selectFile(file.id));
    elements.fileList.append(item);
  }
}

async function selectFile(fileId) {
  state.activeFileId = fileId;
  renderFileList();

  const file = await fetchJson(`/api/files/${fileId}/`);
  const measurements = await fetchJson(`/api/files/${fileId}/measurements/`);
  state.measurements = measurements.features;
  state.filteredMeasurements = measurements.features;
  elements.featureSearch.value = "";

  renderDetail(file);
}

function renderDetail(file) {
  elements.emptyState.classList.add("hidden");
  elements.fileDetail.classList.remove("hidden");

  elements.detailStatus.textContent = file.status;
  elements.detailStatus.classList.toggle("failed", file.status === "FAILED");
  elements.detailFilename.textContent = file.filename;
  elements.detailMeta.textContent = `${file.id} · ${file.crs || "CRS unavailable"}`;
  elements.featureCount.textContent = file.feature_count;
  elements.crsLabel.textContent = file.crs || "-";

  const polygonCount = state.measurements.filter((feature) =>
    feature.geometry_type.toLowerCase().includes("polygon")
  ).length;
  const lineCount = state.measurements.filter((feature) =>
    feature.geometry_type.toLowerCase().includes("line")
  ).length;
  const totalArea = state.measurements.reduce(
    (sum, feature) => sum + (feature.measurement.area_square_meters || 0),
    0
  );
  const totalLength = state.measurements.reduce(
    (sum, feature) => sum + (feature.measurement.length_meters || 0),
    0
  );

  elements.polygonCount.textContent = polygonCount;
  elements.lineCount.textContent = lineCount;
  elements.previewCount.textContent = `${state.measurements.length} features`;
  elements.totalArea.textContent = `${formatNumber(totalArea)} m²`;
  elements.totalLength.textContent = `${formatNumber(totalLength)} m`;

  renderMeasurementsTable();
  drawGeometryPreview(state.measurements);
}

function renderMeasurementsTable() {
  elements.measurementsBody.innerHTML = "";

  for (const feature of state.filteredMeasurements) {
    const row = document.createElement("tr");
    const properties = JSON.stringify(feature.properties || {}, null, 2);
    row.innerHTML = `
      <td>${feature.feature_id}</td>
      <td>${escapeHtml(feature.geometry_type)}</td>
      <td>${formatNumber(feature.measurement.area_square_meters)} m²</td>
      <td>${formatNumber(feature.measurement.length_meters)} m</td>
      <td><div class="properties">${escapeHtml(properties)}</div></td>
      <td>${escapeHtml(feature.measurement.message || "-")}</td>
    `;
    elements.measurementsBody.append(row);
  }
}

function drawGeometryPreview(features) {
  const canvas = elements.geometryCanvas;
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.max(640, Math.floor(rect.width * scale));
  canvas.height = Math.max(360, Math.floor(rect.height * scale));

  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = "#f5f7f2";
  ctx.fillRect(0, 0, rect.width, rect.height);

  const allPoints = features.flatMap((feature) => geometryPoints(feature.geometry));
  if (allPoints.length === 0) {
    ctx.fillStyle = "#697169";
    ctx.font = "600 14px system-ui";
    ctx.fillText("No preview geometry", 22, 32);
    return;
  }

  const bounds = getBounds(allPoints);
  const project = createProjector(bounds, rect.width, rect.height);

  ctx.lineWidth = 2;
  for (const feature of features) {
    drawGeometry(ctx, feature.geometry, project);
  }
}

function drawGeometry(ctx, geometry, project) {
  if (!geometry) return;
  const type = geometry.type;
  const coordinates = geometry.coordinates;

  ctx.strokeStyle = "#11756f";
  ctx.fillStyle = "rgba(17, 117, 111, 0.18)";

  if (type === "Point") {
    drawPoint(ctx, project(coordinates));
  } else if (type === "MultiPoint") {
    coordinates.forEach((point) => drawPoint(ctx, project(point)));
  } else if (type === "LineString") {
    drawLine(ctx, coordinates, project);
  } else if (type === "MultiLineString") {
    coordinates.forEach((line) => drawLine(ctx, line, project));
  } else if (type === "Polygon") {
    drawPolygon(ctx, coordinates, project);
  } else if (type === "MultiPolygon") {
    coordinates.forEach((polygon) => drawPolygon(ctx, polygon, project));
  }
}

function drawPoint(ctx, point) {
  ctx.beginPath();
  ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
  ctx.fillStyle = "#c48122";
  ctx.fill();
}

function drawLine(ctx, coordinates, project) {
  if (coordinates.length < 2) return;
  ctx.beginPath();
  coordinates.forEach((coordinate, index) => {
    const point = project(coordinate);
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.stroke();
}

function drawPolygon(ctx, rings, project) {
  ctx.beginPath();
  rings.forEach((ring) => {
    ring.forEach((coordinate, index) => {
      const point = project(coordinate);
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    });
    ctx.closePath();
  });
  ctx.fill();
  ctx.stroke();
}

function geometryPoints(geometry) {
  if (!geometry) return [];
  const type = geometry.type;
  const coordinates = geometry.coordinates;

  if (type === "Point") return [coordinates];
  if (type === "MultiPoint" || type === "LineString") return coordinates;
  if (type === "MultiLineString" || type === "Polygon") return coordinates.flat();
  if (type === "MultiPolygon") return coordinates.flat(2);
  return [];
}

function getBounds(points) {
  const xs = points.map((point) => point[0]);
  const ys = points.map((point) => point[1]);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function createProjector(bounds, width, height) {
  const padding = 28;
  const rangeX = Math.max(bounds.maxX - bounds.minX, 0.000001);
  const rangeY = Math.max(bounds.maxY - bounds.minY, 0.000001);
  const drawWidth = Math.max(width - padding * 2, 1);
  const drawHeight = Math.max(height - padding * 2, 1);
  const ratio = Math.min(drawWidth / rangeX, drawHeight / rangeY);
  const offsetX = (width - rangeX * ratio) / 2;
  const offsetY = (height - rangeY * ratio) / 2;

  return ([x, y]) => ({
    x: offsetX + (x - bounds.minX) * ratio,
    y: height - (offsetY + (y - bounds.minY) * ratio),
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

elements.uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = elements.fileInput.files[0];
  if (!file) {
    setStatus("Select a KML or ZIP file.", true);
    return;
  }

  const formData = new FormData();
  formData.append("upload", file);

  elements.uploadButton.disabled = true;
  setStatus("Processing file...");

  try {
    const result = await fetchJson("/api/files/", {
      method: "POST",
      body: formData,
    });
    setStatus("File processed.");
    elements.fileInput.value = "";
    await loadFiles();
    await selectFile(result.id);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    elements.uploadButton.disabled = false;
  }
});

elements.refreshButton.addEventListener("click", loadFiles);

elements.featureSearch.addEventListener("input", () => {
  const query = elements.featureSearch.value.trim().toLowerCase();
  state.filteredMeasurements = state.measurements.filter((feature) => {
    const properties = JSON.stringify(feature.properties || {}).toLowerCase();
    return (
      String(feature.feature_id).includes(query) ||
      feature.geometry_type.toLowerCase().includes(query) ||
      properties.includes(query)
    );
  });
  renderMeasurementsTable();
});

for (const eventName of ["dragenter", "dragover"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("is-dragging");
  });
}

elements.dropZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (!file) return;

  const transfer = new DataTransfer();
  transfer.items.add(file);
  elements.fileInput.files = transfer.files;
  setStatus(file.name);
});

elements.fileInput.addEventListener("change", () => {
  const file = elements.fileInput.files[0];
  setStatus(file ? file.name : "");
});

window.addEventListener("resize", () => {
  if (state.measurements.length > 0) drawGeometryPreview(state.measurements);
});

loadFiles().catch((error) => setStatus(error.message, true));
