const RECENT_STORAGE_KEY = "omnidown_recent_items";
const MAX_RECENT_ITEMS = 5;

const SUPPORTED_DOMAINS = {
  "youtube.com": "YouTube",
  "www.youtube.com": "YouTube",
  "youtu.be": "YouTube",
  "m.youtube.com": "YouTube",
  "instagram.com": "Instagram",
  "www.instagram.com": "Instagram",
  "tiktok.com": "TikTok",
  "www.tiktok.com": "TikTok",
  "twitter.com": "X / Twitter",
  "www.twitter.com": "X / Twitter",
  "x.com": "X / Twitter",
  "www.x.com": "X / Twitter",
  "facebook.com": "Facebook",
  "www.facebook.com": "Facebook",
  "soundcloud.com": "SoundCloud"
};

const form = document.getElementById("download-form");
const analyzeButton = document.getElementById("analyze-button");
const downloadButton = document.getElementById("download-button");
const pasteButton = document.getElementById("paste-button");
const clearButton = document.getElementById("clear-button");
const clearRecentButton = document.getElementById("clear-recent-button");
const statusBox = document.getElementById("status");
const resultCard = document.getElementById("result-card");
const titleNode = document.getElementById("media-title");
const metaNode = document.getElementById("media-meta");
const badgeNode = document.getElementById("platform-badge");
const thumbNode = document.getElementById("thumbnail");
const formatSelect = document.getElementById("format-select");
const audioFormatSelect = document.getElementById("audio-format");
const urlInput = document.getElementById("video-url");
const selectionSummary = document.getElementById("selection-summary");
const mediaFacts = document.getElementById("media-facts");
const recentList = document.getElementById("recent-list");
const systemStatusBanner = document.getElementById("system-status-banner");
const urlHelper = document.getElementById("url-helper");
const downloadFrame = document.getElementById("download-frame");
const stepPills = Array.from(document.querySelectorAll(".step-pill"));

let latestPayload = null;
let isDownloading = false;

function setStatus(message, type = "info") {
  statusBox.textContent = message;
  statusBox.className = `status ${type}`.trim();
}

function setUrlHelper(message, type = "") {
  if (!urlHelper) return;
  urlHelper.textContent = message;
  urlHelper.className = `url-helper ${type}`.trim();
}

function formatDuration(seconds) {
  if (!seconds) return "Duracion no disponible";
  const total = Number(seconds);
  const hours = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) return `${hours}h ${mins.toString().padStart(2, "0")}m`;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
}

function formatNumber(value) {
  if (!value) return null;
  return new Intl.NumberFormat("es-ES").format(value);
}

function formatUploadDate(value) {
  if (!value || value.length !== 8) return null;
  const year = value.slice(0, 4);
  const month = value.slice(4, 6);
  const day = value.slice(6, 8);
  const date = new Date(`${year}-${month}-${day}T00:00:00`);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium" }).format(date);
}

function buildOptionLabel(format) {
  const size = format.filesize_mb ? ` · ${format.filesize_mb} MB aprox.` : "";
  const recommendation = format.recommended ? " · Recomendado" : "";
  return `${format.label}${size}${recommendation}`;
}

function setStepState(current) {
  const order = ["analyze", "choose", "download"];
  const currentIndex = order.indexOf(current);

  stepPills.forEach((pill) => {
    const step = pill.dataset.step;
    const stepIndex = order.indexOf(step);
    pill.classList.toggle("active", stepIndex === currentIndex);
    pill.classList.toggle("done", stepIndex > -1 && stepIndex < currentIndex);
  });
}

function getSelectedFormat() {
  return latestPayload?.formats.find((item) => item.format_id === formatSelect.value) || null;
}

function updateDownloadButtonState() {
  downloadButton.disabled = !latestPayload || isDownloading;
}

function describeSelection(format) {
  if (!format) {
    selectionSummary.textContent = "Elige una opcion para ver una recomendacion clara.";
    return;
  }

  const size = format.filesize_mb ? `${format.filesize_mb} MB aprox.` : "tamano no disponible";
  if (format.media_type === "audio") {
    selectionSummary.textContent = `Has elegido audio ${format.quality}. Se descargara el stream de origen y se convertira al formato final ${audioFormatSelect.value.toUpperCase()}. Peso estimado: ${size}.`;
    return;
  }

  const note = format.note ? ` ${format.note}.` : "";
  const recommendation = format.recommended ? " Esta es la opcion recomendada por equilibrio entre compatibilidad y calidad." : "";
  selectionSummary.textContent = `Has elegido video ${format.quality} en ${format.extension.toUpperCase()}. ${size}.${note}${recommendation}`;
}

function renderMediaFacts(data) {
  const facts = [];
  if (data.uploader) facts.push(`Canal: ${data.uploader}`);

  const views = formatNumber(data.view_count);
  if (views) facts.push(`${views} visualizaciones`);

  const uploadDate = formatUploadDate(data.upload_date);
  if (uploadDate) facts.push(`Publicado: ${uploadDate}`);

  mediaFacts.innerHTML = "";
  facts.forEach((fact) => {
    const chip = document.createElement("span");
    chip.className = "fact-chip";
    chip.textContent = fact;
    mediaFacts.appendChild(chip);
  });
}

function refreshAudioVisibility() {
  const selected = getSelectedFormat();
  const isAudio = selected?.media_type === "audio";
  audioFormatSelect.disabled = !isAudio;
  describeSelection(selected);
}

function resetResult() {
  resultCard.classList.add("hidden");
  latestPayload = null;
  formatSelect.innerHTML = "";
  mediaFacts.innerHTML = "";
  selectionSummary.textContent = "Elige una opcion para ver una recomendacion clara.";
  setStepState("analyze");
  updateDownloadButtonState();
}

function readRecentItems() {
  try {
    const raw = window.localStorage.getItem(RECENT_STORAGE_KEY);
    const items = raw ? JSON.parse(raw) : [];
    return Array.isArray(items) ? items : [];
  } catch {
    return [];
  }
}

function writeRecentItems(items) {
  window.localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(items));
}

function saveRecentItem(data) {
  const item = {
    source_url: data.source_url,
    title: data.title,
    platform: data.platform,
    duration_seconds: data.duration_seconds,
    uploader: data.uploader || null,
    saved_at: new Date().toISOString()
  };

  const items = readRecentItems().filter((entry) => entry.source_url !== item.source_url);
  items.unshift(item);
  writeRecentItems(items.slice(0, MAX_RECENT_ITEMS));
  renderRecentItems();
}

function fillUrlAndAnalyze(url) {
  urlInput.value = url;
  updateUrlHelper();
  form.requestSubmit();
}

function renderRecentItems() {
  const items = readRecentItems();
  recentList.innerHTML = "";
  recentList.classList.toggle("empty", items.length === 0);

  if (items.length === 0) {
    recentList.textContent = "Todavia no has analizado ningun enlace en este navegador.";
    return;
  }

  items.forEach((item) => {
    const row = document.createElement("article");
    row.className = "recent-item";

    const copy = document.createElement("div");
    copy.className = "recent-copy";

    const title = document.createElement("div");
    title.className = "recent-title";
    title.textContent = item.title || item.source_url;

    const meta = document.createElement("div");
    meta.className = "recent-meta";
    const metaParts = [item.platform || "Origen detectado", formatDuration(item.duration_seconds)];
    if (item.uploader) metaParts.push(item.uploader);
    meta.textContent = metaParts.filter(Boolean).join(" · ");

    const url = document.createElement("div");
    url.className = "recent-url";
    url.textContent = item.source_url;

    copy.append(title, meta, url);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button";
    button.textContent = "Reanalizar";
    button.addEventListener("click", () => fillUrlAndAnalyze(item.source_url));

    row.append(copy, button);
    recentList.appendChild(row);
  });
}

function hydrateResult(data) {
  latestPayload = data;
  titleNode.textContent = data.title;
  badgeNode.textContent = data.platform;
  metaNode.textContent = `Origen detectado · ${formatDuration(data.duration_seconds)} · ${data.formats.length} opciones`;
  thumbNode.src = data.thumbnail || "";
  thumbNode.classList.toggle("hidden", !data.thumbnail);
  renderMediaFacts(data);

  formatSelect.innerHTML = "";
  data.formats.forEach((format, index) => {
    const option = document.createElement("option");
    option.value = format.format_id;
    option.textContent = buildOptionLabel(format);
    option.dataset.mediaType = format.media_type;
    if (index === 0) option.selected = true;
    formatSelect.appendChild(option);
  });

  refreshAudioVisibility();
  resultCard.classList.remove("hidden");
  resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  setStepState("choose");
  updateDownloadButtonState();
}

function summarizeUrl(rawValue) {
  const value = rawValue.trim();
  if (!value) {
    return {
      message: "Pega una URL completa para detectar mejor la fuente y evitar errores innecesarios.",
      type: ""
    };
  }

  try {
    const parsed = new URL(value);
    const platform = SUPPORTED_DOMAINS[parsed.hostname];
    const path = parsed.pathname.toLowerCase();
    const isPlaylist = parsed.searchParams.has("list") || path.includes("/playlist");
    const isChannel = path.includes("/channel") || path.includes("/c/") || path.includes("/@");

    if (!platform) {
      return {
        message: `Dominio detectado: ${parsed.hostname}. Puede que funcione si la fuente es compatible con yt-dlp, pero no es una de las plataformas destacadas.`,
        type: ""
      };
    }

    if (isPlaylist) {
      return {
        message: `Detectado ${platform}. Parece una playlist; la app esta configurada para trabajar sobre un elemento individual.`,
        type: "warning"
      };
    }

    if (isChannel) {
      return {
        message: `Detectado ${platform}. Ese enlace parece de canal o perfil; suele funcionar mejor con la URL directa del video o post.`,
        type: "warning"
      };
    }

    return {
      message: `Fuente detectada: ${platform}. El enlace tiene buena pinta para analizarlo.`,
      type: "success"
    };
  } catch {
    return {
      message: "El texto pegado no parece una URL valida todavia. Revisa que incluya https://",
      type: "warning"
    };
  }
}

function updateUrlHelper() {
  const summary = summarizeUrl(urlInput.value);
  setUrlHelper(summary.message, summary.type);
}

async function analyzeUrl(event) {
  event.preventDefault();
  resetResult();
  analyzeButton.disabled = true;
  setStatus("Analizando URL y detectando formatos disponibles...", "info");

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

    hydrateResult(data);
    saveRecentItem(data);
    setStatus(`Analisis completado. Hemos encontrado ${data.formats.length} opciones listas para descargar.`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    analyzeButton.disabled = false;
  }
}

async function startDownload() {
  if (!latestPayload) {
    setStatus("Primero analiza una URL.", "error");
    return;
  }

  const selected = getSelectedFormat();
  if (!selected) {
    setStatus("Selecciona un formato valido.", "error");
    return;
  }

  isDownloading = true;
  updateDownloadButtonState();
  setStepState("download");
  setStatus("Validando la descarga y preparando el archivo...", "success");

  try {
    const response = await fetch("/api/download-intent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: urlInput.value.trim(),
        format_id: selected.format_id,
        media_type: selected.media_type,
        audio_format: audioFormatSelect.value
      })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "La descarga no se pudo preparar.");
    }

    downloadFrame.src = data.download_url;
    setStatus(`Descarga preparada: ${data.format_label}. El navegador gestionara el archivo directamente.`, "success");

    window.setTimeout(() => {
      isDownloading = false;
      updateDownloadButtonState();
      setStatus("Si no ves la descarga, revisa la carpeta de descargas o prueba otra calidad.", "info");
    }, 2500);
  } catch (error) {
    isDownloading = false;
    updateDownloadButtonState();
    setStatus(error.message, "error");
    setStepState("choose");
  }
}

async function pasteFromClipboard() {
  if (!navigator.clipboard?.readText) {
    setStatus("Tu navegador no permite leer el portapapeles desde aqui.", "error");
    return;
  }

  try {
    const text = (await navigator.clipboard.readText()).trim();
    if (!text) {
      setStatus("El portapapeles esta vacio o no contiene texto.", "error");
      return;
    }

    urlInput.value = text;
    urlInput.focus();
    updateUrlHelper();
    setStatus("Enlace pegado. Puedes analizarlo cuando quieras.", "info");
  } catch {
    setStatus("No se pudo acceder al portapapeles. Pega la URL manualmente.", "error");
  }
}

function clearUrl() {
  urlInput.value = "";
  urlInput.focus();
  resetResult();
  updateUrlHelper();
  setStatus("Campo limpiado. Pega otra URL para continuar.", "info");
}

function clearRecentItems() {
  writeRecentItems([]);
  renderRecentItems();
  setStatus("Historial local borrado en este navegador.", "info");
}

async function hydrateSystemStatus() {
  if (!systemStatusBanner) return;

  try {
    const response = await fetch("/api/system-status");
    if (!response.ok) return;
    const data = await response.json();
    const ttlSeconds = data?.cache?.ttl_seconds;
    const entries = data?.cache?.entries;
    if (!ttlSeconds && ttlSeconds !== 0) return;

    const ttlMinutes = Math.max(1, Math.round(ttlSeconds / 60));
    systemStatusBanner.textContent = `Sistema listo. Cache temporal activa (${entries} elementos ahora) para acelerar reanalisis durante ${ttlMinutes} min.`;
  } catch {
    // Silent fallback: the static message already explains the benefit.
  }
}

setStatus("Pega una URL para empezar el analisis.", "info");
updateDownloadButtonState();
renderRecentItems();
updateUrlHelper();
hydrateSystemStatus();
form.addEventListener("submit", analyzeUrl);
downloadButton.addEventListener("click", startDownload);
formatSelect.addEventListener("change", refreshAudioVisibility);
audioFormatSelect.addEventListener("change", refreshAudioVisibility);
pasteButton.addEventListener("click", pasteFromClipboard);
clearButton.addEventListener("click", clearUrl);
clearRecentButton.addEventListener("click", clearRecentItems);
urlInput.addEventListener("input", updateUrlHelper);
