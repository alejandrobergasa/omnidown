const form = document.getElementById("download-form");
const analyzeButton = document.getElementById("analyze-button");
const downloadButton = document.getElementById("download-button");
const statusBox = document.getElementById("status");
const resultCard = document.getElementById("result-card");
const titleNode = document.getElementById("media-title");
const metaNode = document.getElementById("media-meta");
const badgeNode = document.getElementById("platform-badge");
const thumbNode = document.getElementById("thumbnail");
const formatSelect = document.getElementById("format-select");
const audioFormatSelect = document.getElementById("audio-format");
const urlInput = document.getElementById("video-url");

let latestPayload = null;

function setStatus(message, type = "") {
  statusBox.textContent = message;
  statusBox.className = `status ${type}`.trim();
}

function formatDuration(seconds) {
  if (!seconds) return "Duracion no disponible";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
}

function buildOptionLabel(format) {
  const size = format.filesize_mb ? `, ${format.filesize_mb} MB aprox.` : "";
  return `${format.label}${size}`;
}

function refreshAudioVisibility() {
  const selected = latestPayload?.formats.find((item) => item.format_id === formatSelect.value);
  const isAudio = selected?.media_type === "audio";
  audioFormatSelect.disabled = !isAudio;
}

async function analyzeUrl(event) {
  event.preventDefault();
  resultCard.classList.add("hidden");
  latestPayload = null;
  analyzeButton.disabled = true;
  setStatus("Analizando URL y detectando formatos disponibles...");

  try {
    const response = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: urlInput.value.trim() })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "No se pudo analizar la URL.");
    }

    latestPayload = data;
    titleNode.textContent = data.title;
    badgeNode.textContent = data.platform;
    metaNode.textContent = `Origen detectado · ${formatDuration(data.duration_seconds)}`;
    thumbNode.src = data.thumbnail || "";
    thumbNode.classList.toggle("hidden", !data.thumbnail);

    formatSelect.innerHTML = "";
    data.formats.forEach((format) => {
      const option = document.createElement("option");
      option.value = format.format_id;
      option.textContent = buildOptionLabel(format);
      option.dataset.mediaType = format.media_type;
      formatSelect.appendChild(option);
    });

    refreshAudioVisibility();
    resultCard.classList.remove("hidden");
    setStatus(`Se han encontrado ${data.formats.length} opciones.`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    analyzeButton.disabled = false;
  }
}

function startDownload() {
  if (!latestPayload) {
    setStatus("Primero analiza una URL.", "error");
    return;
  }

  const selected = latestPayload.formats.find((item) => item.format_id === formatSelect.value);
  if (!selected) {
    setStatus("Selecciona un formato valido.", "error");
    return;
  }

  const params = new URLSearchParams({
    url: urlInput.value.trim(),
    format_id: selected.format_id,
    media_type: selected.media_type,
    audio_format: audioFormatSelect.value
  });

  setStatus("Preparando descarga. La respuesta puede tardar unos segundos...", "success");
  window.location.href = `/api/download?${params.toString()}`;
}

form.addEventListener("submit", analyzeUrl);
downloadButton.addEventListener("click", startDownload);
formatSelect.addEventListener("change", refreshAudioVisibility);
