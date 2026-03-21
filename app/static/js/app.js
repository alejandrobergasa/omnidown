const DOWNLOAD_POLL_INTERVAL_MS = 1200;
const SUPPORTED_LOCALES = new Set(["es", "en"]);

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
const statusBox = document.getElementById("status");
const resultCard = document.getElementById("result-card");
const titleNode = document.getElementById("media-title");
const metaNode = document.getElementById("media-meta");
const badgeNode = document.getElementById("platform-badge");
const thumbNode = document.getElementById("thumbnail");
const urlInput = document.getElementById("video-url");
const selectionSummary = document.getElementById("selection-summary");
const mediaFacts = document.getElementById("media-facts");
const urlHelper = document.getElementById("url-helper");
const videoFormatGrid = document.getElementById("video-format-grid");
const audioFormatGrid = document.getElementById("audio-format-grid");
const audioFormatSelect = document.getElementById("audio-format");
const audioFormatChips = Array.from(document.querySelectorAll("[data-audio-format]"));
const progressCard = document.getElementById("download-progress");
const progressTitle = document.getElementById("progress-title");
const progressPercent = document.getElementById("progress-percent");
const progressText = document.getElementById("progress-text");
const progressFill = document.getElementById("progress-fill");
const downloadLink = document.getElementById("download-link");
const skipLink = document.getElementById("skip-link");
const brandTag = document.getElementById("brand-tag");
const heroEyebrow = document.getElementById("hero-eyebrow");
const heroTitle = document.getElementById("hero-title");
const heroText = document.getElementById("hero-text");
const studioKicker = document.getElementById("studio-kicker");
const studioTitle = document.getElementById("studio-title");
const urlLabel = document.getElementById("url-label");
const formatTitle = document.getElementById("format-title");
const formatPanelText = document.getElementById("format-panel-text");
const videoGroupTitle = document.getElementById("video-group-title");
const videoGroupText = document.getElementById("video-group-text");
const audioGroupTitle = document.getElementById("audio-group-title");
const audioGroupText = document.getElementById("audio-group-text");
const outputTitle = document.getElementById("output-title");
const outputText = document.getElementById("output-text");
const audioFormatLabel = document.getElementById("audio-format-label");
const progressLabel = document.getElementById("progress-label");

const I18N = {
  es: {
    appTitle: "OmniDown | Descarga video y audio",
    appDescription: "Descarga contenido en MP4 o audio pegando una URL.",
    skipLink: "Ir al contenido principal",
    brandTag: "Descarga limpia ✨",
    heroEyebrow: "Minimal downloader",
    heroTitle: "Pega la URL. Elige formato.\nDescarga 🚀",
    heroText: "Una experiencia limpia para descargar video o audio sin rodeos.",
    studioKicker: "Descarga segura 🔒",
    studioTitle: "Pega el enlace y elige una opcion",
    urlLabel: "Enlace",
    paste: "Pegar",
    analyze: "Analizar",
    clear: "Limpiar",
    urlHelperEmpty: "Pega una URL valida.",
    formatTitle: "Formato",
    formatText: "Filtra la descarga paso a paso.",
    videoGroupTitle: "Video",
    videoGroupText: "Primero formato, luego resolucion y por ultimo FPS.",
    audioGroupTitle: "Audio",
    audioGroupText: "Primero formato y despues calidad.",
    formatEmptyVideo: "No hay opciones de video seguras para este enlace.",
    formatEmptyAudio: "No hay opciones de audio seguras para este enlace.",
    formatSplitAudio: "audio compatible aparte",
    filterExtension: "Formato",
    filterResolution: "Resolucion",
    filterFps: "FPS",
    filterAudioQuality: "Calidad",
    filterSelectedOption: "Opcion elegida",
    filterStandardFps: "Estandar",
    outputTitle: "Salida",
    outputText: "Ajustes finales.",
    audioFormatLabel: "Audio final",
    audioFormatAria: "Formato final de audio",
    selectionEmpty: "Selecciona un formato para ver el resumen.",
    progressLabel: "Progreso",
    progressWaiting: "Esperando descarga",
    progressEmpty: "La descarga aparecera aqui.",
    saveFile: "Guardar archivo",
    download: "Descargar",
    statusStart: "Pega una URL para empezar.",
    statusAnalyze: "Analizando enlace...",
    statusReady: "Listo para descargar.",
    statusDownloadReady: "Archivo listo.",
    statusAnalyzeFirst: "Primero analiza una URL.",
    statusChooseFormat: "Selecciona un formato.",
    statusDownloadStarting: "Descarga iniciada.",
    statusInitDownload: "Iniciando descarga...",
    clipboardUnsupported: "Tu navegador no permite leer el portapapeles aqui.",
    clipboardEmpty: "El portapapeles esta vacio.",
    clipboardSuccess: "Enlace pegado.",
    clipboardError: "No se pudo acceder al portapapeles.",
    fieldCleared: "Campo limpiado.",
    durationUnknown: "Duracion desconocida",
    audioLabel: "Audio {quality}",
    videoLabel: "Video {quality}",
    videoType: "video",
    audioType: "audio",
    recommended: "Recomendado",
    approxMb: "{size} MB aprox.",
    unavailableSize: "tamano no disponible",
    selectionAudio: "Audio {quality}. Se convertira a {audioFormat} y el peso estimado es {size}.",
    selectionVideoRecommended: "recomendado",
    channelLabel: "Canal {name}",
    viewsLabel: "{count} vistas",
    resultMeta: "{duration} · {count} opciones",
    helperPasteValid: "Pega una URL valida.",
    helperDomain: "Dominio detectado: {hostname}. Puede funcionar si yt-dlp lo soporta.",
    helperPlatformDetected: "{platform} detectado.",
    helperPlaylist: "{platform} detectado. Usa un enlace de video individual para evitar errores.",
    helperChannel: "{platform} detectado. Mejor usa el enlace directo del video o post.",
    helperInvalidUrl: "La URL no parece valida todavia.",
    processing: "Procesando...",
    eta: "ETA {seconds} s",
    perSecondMb: "{speed} MB/s",
    untitled: "Sin titulo"
  },
  en: {
    appTitle: "OmniDown | Download video and audio",
    appDescription: "Download MP4 video or audio by pasting a URL.",
    skipLink: "Skip to main content",
    brandTag: "Clean downloads ✨",
    heroEyebrow: "Minimal downloader",
    heroTitle: "Paste the URL. Choose format.\nDownload 🚀",
    heroText: "A clean way to download video or audio without the clutter.",
    studioKicker: "Reliable download 🔒",
    studioTitle: "Paste the link and choose an option",
    urlLabel: "Link",
    paste: "Paste",
    analyze: "Analyze",
    clear: "Clear",
    urlHelperEmpty: "Paste a valid URL.",
    formatTitle: "Format",
    formatText: "Filter the download step by step.",
    videoGroupTitle: "Video",
    videoGroupText: "Choose format first, then resolution, then FPS.",
    audioGroupTitle: "Audio",
    audioGroupText: "Choose format first, then quality.",
    formatEmptyVideo: "No safe video options were found for this link.",
    formatEmptyAudio: "No safe audio options were found for this link.",
    formatSplitAudio: "compatible audio added separately",
    filterExtension: "Format",
    filterResolution: "Resolution",
    filterFps: "FPS",
    filterAudioQuality: "Quality",
    filterSelectedOption: "Selected option",
    filterStandardFps: "Standard",
    outputTitle: "Output",
    outputText: "Final settings.",
    audioFormatLabel: "Final audio",
    audioFormatAria: "Final audio format",
    selectionEmpty: "Select a format to see the summary.",
    progressLabel: "Progress",
    progressWaiting: "Waiting for download",
    progressEmpty: "The download will appear here.",
    saveFile: "Save file",
    download: "Download",
    statusStart: "Paste a URL to begin.",
    statusAnalyze: "Analyzing link...",
    statusReady: "Ready to download.",
    statusDownloadReady: "File ready.",
    statusAnalyzeFirst: "Analyze a URL first.",
    statusChooseFormat: "Select a format.",
    statusDownloadStarting: "Download started.",
    statusInitDownload: "Starting download...",
    clipboardUnsupported: "Your browser cannot read the clipboard here.",
    clipboardEmpty: "The clipboard is empty.",
    clipboardSuccess: "Link pasted.",
    clipboardError: "Could not access the clipboard.",
    fieldCleared: "Field cleared.",
    durationUnknown: "Unknown duration",
    audioLabel: "Audio {quality}",
    videoLabel: "Video {quality}",
    videoType: "video",
    audioType: "audio",
    recommended: "Recommended",
    approxMb: "{size} MB approx.",
    unavailableSize: "size unavailable",
    selectionAudio: "Audio {quality}. It will be converted to {audioFormat} and the estimated size is {size}.",
    selectionVideoRecommended: "recommended",
    channelLabel: "Channel {name}",
    viewsLabel: "{count} views",
    resultMeta: "{duration} · {count} options",
    helperPasteValid: "Paste a valid URL.",
    helperDomain: "Detected domain: {hostname}. It may work if yt-dlp supports it.",
    helperPlatformDetected: "{platform} detected.",
    helperPlaylist: "{platform} detected. Use a single video link to avoid errors.",
    helperChannel: "{platform} detected. It works better with a direct video or post link.",
    helperInvalidUrl: "The URL does not look valid yet.",
    processing: "Processing...",
    eta: "ETA {seconds} s",
    perSecondMb: "{speed} MB/s",
    untitled: "Untitled"
  }
};

let latestPayload = null;
let selectedFormatKey = null;
let isDownloading = false;
let currentJobId = null;
let downloadPollTimer = null;
let videoFilterState = { extension: null, resolution: null, fps: null };
let audioFilterState = { extension: null, quality: null };
const currentLocale = getPreferredLocale();
const VIDEO_EXTENSION_ORDER = ["mp4", "webm", "mkv"];
const AUDIO_EXTENSION_ORDER = ["m4a", "mp4", "webm"];

function getPreferredLocale() {
  const browserLocale = navigator.language || navigator.languages?.[0] || window.APP_CONFIG?.locale || "en";
  const primary = browserLocale.toLowerCase().split("-")[0];
  return SUPPORTED_LOCALES.has(primary) ? primary : "en";
}

function t(key, variables = {}) {
  const dictionary = I18N[currentLocale] || I18N.en;
  const template = dictionary[key] || I18N.en[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, token) => String(variables[token] ?? ""));
}

function applyStaticTranslations() {
  document.documentElement.lang = currentLocale;
  document.title = t("appTitle");
  document.querySelector('meta[name="description"]')?.setAttribute("content", t("appDescription"));
  if (skipLink) skipLink.textContent = t("skipLink");
  if (brandTag) brandTag.textContent = t("brandTag");
  if (heroEyebrow) heroEyebrow.textContent = t("heroEyebrow");
  if (heroTitle) heroTitle.innerHTML = t("heroTitle").replace(/\n/g, "<br>");
  if (heroText) heroText.textContent = t("heroText");
  if (studioKicker) studioKicker.textContent = t("studioKicker");
  if (studioTitle) studioTitle.textContent = t("studioTitle");
  if (urlLabel) urlLabel.textContent = t("urlLabel");
  if (pasteButton) pasteButton.textContent = t("paste");
  if (analyzeButton) analyzeButton.textContent = t("analyze");
  if (clearButton) clearButton.textContent = t("clear");
  if (formatTitle) formatTitle.textContent = t("formatTitle");
  if (formatPanelText) formatPanelText.textContent = t("formatText");
  if (videoGroupTitle) videoGroupTitle.textContent = t("videoGroupTitle");
  if (videoGroupText) videoGroupText.textContent = t("videoGroupText");
  if (audioGroupTitle) audioGroupTitle.textContent = t("audioGroupTitle");
  if (audioGroupText) audioGroupText.textContent = t("audioGroupText");
  if (outputTitle) outputTitle.textContent = t("outputTitle");
  if (outputText) outputText.textContent = t("outputText");
  if (audioFormatLabel) audioFormatLabel.textContent = t("audioFormatLabel");
  document.getElementById("audio-format-chips")?.setAttribute("aria-label", t("audioFormatAria"));
  if (progressLabel) progressLabel.textContent = t("progressLabel");
  if (downloadButton) downloadButton.textContent = t("download");
  if (downloadLink) downloadLink.textContent = t("saveFile");
  if (thumbNode) thumbNode.alt = currentLocale === "es" ? "Miniatura del contenido" : "Content thumbnail";
}

function setStatus(message, type = "info") {
  statusBox.textContent = message;
  statusBox.className = `status ${type}`.trim();
}

function setUrlHelper(message, type = "") {
  urlHelper.textContent = message;
  urlHelper.className = `url-helper ${type}`.trim();
}

function formatDuration(seconds) {
  if (!seconds) return t("durationUnknown");
  const total = Number(seconds);
  const hours = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) return `${hours}h ${mins.toString().padStart(2, "0")}m`;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
}

function formatNumber(value) {
  if (!value) return null;
  return new Intl.NumberFormat(currentLocale).format(value);
}

function formatUploadDate(value) {
  if (!value || value.length !== 8) return null;
  const year = value.slice(0, 4);
  const month = value.slice(4, 6);
  const day = value.slice(6, 8);
  const date = new Date(`${year}-${month}-${day}T00:00:00`);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(currentLocale, { dateStyle: "medium" }).format(date);
}

function buildOptionLabel(format) {
  if (format.media_type === "audio") {
    return t("audioLabel", { quality: format.quality });
  }
  return `${format.quality} ${format.extension.toUpperCase()}`;
}

function getFormatKey(format) {
  return `${format.media_type}:${format.format_id}`;
}

function getSelectedFormat() {
  return latestPayload?.formats.find((item) => getFormatKey(item) === selectedFormatKey) || null;
}

function updateDownloadButtonState() {
  downloadButton.disabled = !latestPayload || !selectedFormatKey || isDownloading;
}

function resetProgressCard() {
  progressCard.classList.add("hidden");
  progressTitle.textContent = t("progressWaiting");
  progressPercent.textContent = "0%";
  progressText.textContent = t("progressEmpty");
  progressFill.style.width = "0%";
  downloadLink.classList.add("hidden");
  downloadLink.removeAttribute("href");
}

function renderProgress(data) {
  progressCard.classList.remove("hidden");
  progressTitle.textContent = data.format_label || t("download");
  progressPercent.textContent = `${Math.round(data.progress_percent)}%`;
  progressText.textContent = data.status_text || t("processing");
  progressFill.style.width = `${Math.max(0, Math.min(100, data.progress_percent || 0))}%`;

  if (data.file_url) {
    downloadLink.href = data.file_url;
    downloadLink.classList.remove("hidden");
  } else {
    downloadLink.classList.add("hidden");
    downloadLink.removeAttribute("href");
  }
}

function describeSelection(format) {
  if (!format) {
    selectionSummary.textContent = t("selectionEmpty");
    return;
  }

  const size = format.filesize_mb ? t("approxMb", { size: format.filesize_mb }) : t("unavailableSize");
  if (format.media_type === "audio") {
    selectionSummary.textContent = t("selectionAudio", {
      quality: format.quality,
      audioFormat: audioFormatSelect.value.toUpperCase(),
      size
    });
    return;
  }

  const parts = [t("videoLabel", { quality: format.quality }), format.extension.toUpperCase(), size];
  if (format.note) parts.push(format.note);
  if (!format.has_embedded_audio) parts.push(t("formatSplitAudio"));
  if (format.recommended) parts.push(t("selectionVideoRecommended"));
  selectionSummary.textContent = parts.join(" · ");
}

function renderMediaFacts(data) {
  const facts = [];
  if (data.uploader) facts.push(t("channelLabel", { name: data.uploader }));

  const views = formatNumber(data.view_count);
  if (views) facts.push(t("viewsLabel", { count: views }));

  const uploadDate = formatUploadDate(data.upload_date);
  if (uploadDate) facts.push(uploadDate);

  mediaFacts.innerHTML = "";
  facts.forEach((fact) => {
    const chip = document.createElement("span");
    chip.className = "fact-chip";
    chip.textContent = fact;
    mediaFacts.appendChild(chip);
  });
}

function getVideoResolution(format) {
  const match = /(\d+)p/i.exec(format.quality || "");
  return match ? `${match[1]}p` : format.quality;
}

function getVideoFps(format) {
  const match = /(\d+)fps/i.exec(format.quality || "");
  return match ? `${match[1]}fps` : t("filterStandardFps");
}

function getVideoFilterSnapshot(format) {
  return {
    extension: format.extension,
    resolution: getVideoResolution(format),
    fps: getVideoFps(format)
  };
}

function getAudioFilterSnapshot(format) {
  return {
    extension: format.extension,
    quality: format.quality
  };
}

function syncFilterStatesFromFormat(format) {
  if (!format) return;
  if (format.media_type === "video") {
    videoFilterState = getVideoFilterSnapshot(format);
    return;
  }
  audioFilterState = getAudioFilterSnapshot(format);
}

function applySelection(format, { syncFilters = true, resetProgress = true } = {}) {
  selectedFormatKey = format ? getFormatKey(format) : null;
  if (syncFilters && format) {
    syncFilterStatesFromFormat(format);
  }
  updateAudioChipState();
  updateDownloadButtonState();
  if (format && resetProgress) {
    resetProgressCard();
  }
}

function sortByPreferredOrder(values, order) {
  return [...values].sort((left, right) => {
    const leftIndex = order.indexOf(left);
    const rightIndex = order.indexOf(right);
    if (leftIndex !== -1 || rightIndex !== -1) {
      return (leftIndex === -1 ? order.length : leftIndex) - (rightIndex === -1 ? order.length : rightIndex);
    }
    return left.localeCompare(right);
  });
}

function sortNumericLabelDescending(values, suffix) {
  return [...values].sort((left, right) => {
    const leftValue = Number.parseInt(left.replace(suffix, ""), 10) || 0;
    const rightValue = Number.parseInt(right.replace(suffix, ""), 10) || 0;
    return rightValue - leftValue;
  });
}

function sortAudioQualityValues(values) {
  return [...values].sort((left, right) => {
    const leftValue = Number.parseInt(left, 10) || 0;
    const rightValue = Number.parseInt(right, 10) || 0;
    return rightValue - leftValue;
  });
}

function pickPreferredFormat(formats) {
  return [...formats].sort((left, right) => {
    if (left.recommended !== right.recommended) {
      return Number(right.recommended) - Number(left.recommended);
    }
    if (left.has_embedded_audio !== right.has_embedded_audio) {
      return Number(right.has_embedded_audio) - Number(left.has_embedded_audio);
    }
    return (right.filesize_mb || 0) - (left.filesize_mb || 0);
  })[0] || null;
}

function filterVideoFormats(formats, filters) {
  return formats.filter((format) => {
    if (filters.extension && format.extension !== filters.extension) return false;
    if (filters.resolution && getVideoResolution(format) !== filters.resolution) return false;
    if (filters.fps && getVideoFps(format) !== filters.fps) return false;
    return true;
  });
}

function filterAudioFormats(formats, filters) {
  return formats.filter((format) => {
    if (filters.extension && format.extension !== filters.extension) return false;
    if (filters.quality && format.quality !== filters.quality) return false;
    return true;
  });
}

function updateAudioChipState() {
  const selected = getSelectedFormat();
  const isAudio = selected?.media_type === "audio";
  audioFormatChips.forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.audioFormat === audioFormatSelect.value);
    chip.disabled = !isAudio;
    chip.setAttribute("aria-pressed", chip.classList.contains("active") ? "true" : "false");
  });
  describeSelection(selected);
}

function ensureVideoFilterState(videoFormats) {
  if (videoFormats.length === 0) {
    videoFilterState = { extension: null, resolution: null, fps: null };
    return null;
  }

  const fallback = getSelectedFormat()?.media_type === "video"
    ? getSelectedFormat()
    : pickPreferredFormat(videoFormats);
  const fallbackState = getVideoFilterSnapshot(fallback);

  const extensionOptions = sortByPreferredOrder(
    [...new Set(videoFormats.map((format) => format.extension))],
    VIDEO_EXTENSION_ORDER
  );
  if (!extensionOptions.includes(videoFilterState.extension)) {
    videoFilterState.extension = extensionOptions.includes(fallbackState.extension) ? fallbackState.extension : extensionOptions[0];
  }

  const resolutionOptions = sortNumericLabelDescending(
    [...new Set(videoFormats
      .filter((format) => format.extension === videoFilterState.extension)
      .map((format) => getVideoResolution(format)))],
    "p"
  );
  if (!resolutionOptions.includes(videoFilterState.resolution)) {
    videoFilterState.resolution = resolutionOptions.includes(fallbackState.resolution) ? fallbackState.resolution : resolutionOptions[0];
  }

  const fpsOptions = sortNumericLabelDescending(
    [...new Set(videoFormats
      .filter((format) => format.extension === videoFilterState.extension && getVideoResolution(format) === videoFilterState.resolution)
      .map((format) => getVideoFps(format)))],
    "fps"
  );
  if (!fpsOptions.includes(videoFilterState.fps)) {
    videoFilterState.fps = fpsOptions.includes(fallbackState.fps) ? fallbackState.fps : fpsOptions[0];
  }

  return pickPreferredFormat(filterVideoFormats(videoFormats, videoFilterState));
}

function ensureAudioFilterState(audioFormats) {
  if (audioFormats.length === 0) {
    audioFilterState = { extension: null, quality: null };
    return null;
  }

  const fallback = getSelectedFormat()?.media_type === "audio"
    ? getSelectedFormat()
    : pickPreferredFormat(audioFormats);
  const fallbackState = getAudioFilterSnapshot(fallback);

  const extensionOptions = sortByPreferredOrder(
    [...new Set(audioFormats.map((format) => format.extension))],
    AUDIO_EXTENSION_ORDER
  );
  if (!extensionOptions.includes(audioFilterState.extension)) {
    audioFilterState.extension = extensionOptions.includes(fallbackState.extension) ? fallbackState.extension : extensionOptions[0];
  }

  const qualityOptions = sortAudioQualityValues(
    [...new Set(audioFormats
      .filter((format) => format.extension === audioFilterState.extension)
      .map((format) => format.quality))]
  );
  if (!qualityOptions.includes(audioFilterState.quality)) {
    audioFilterState.quality = qualityOptions.includes(fallbackState.quality) ? fallbackState.quality : qualityOptions[0];
  }

  return pickPreferredFormat(filterAudioFormats(audioFormats, audioFilterState));
}

function renderEmptyFormatState(container, message) {
  const empty = document.createElement("div");
  empty.className = "format-empty";
  empty.textContent = message;
  container.appendChild(empty);
}

function createFilterStep(title, options, selectedValue, onSelect) {
  const step = document.createElement("div");
  step.className = "filter-step";

  const heading = document.createElement("div");
  heading.className = "filter-step-title";
  heading.textContent = title;
  step.appendChild(heading);

  const row = document.createElement("div");
  row.className = "filter-chip-row";

  options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "filter-chip";
    button.classList.toggle("active", option.value === selectedValue);
    button.setAttribute("aria-pressed", option.value === selectedValue ? "true" : "false");
    button.innerHTML = `
      <span>${option.label}</span>
      <span class="filter-chip-count">${option.count}</span>
    `;
    button.addEventListener("click", () => onSelect(option.value));
    row.appendChild(button);
  });

  step.appendChild(row);
  return step;
}

function buildPreviewMetaBits(format) {
  const bits = [format.extension.toUpperCase()];
  if (format.filesize_mb) bits.push(`${format.filesize_mb} MB`);
  if (format.note) bits.push(format.note);
  if (format.media_type === "video" && !format.has_embedded_audio) {
    bits.push(t("formatSplitAudio"));
  }
  return bits;
}

function renderSelectedFormatPreview(container, format) {
  const selected = getSelectedFormat();
  const isActive = selected && getFormatKey(format) === getFormatKey(selected);
  const preview = document.createElement("div");
  preview.className = `format-preview ${isActive ? "active" : ""}`.trim();
  preview.innerHTML = `
    <div class="format-preview-head">
      <span class="format-preview-label">${t("filterSelectedOption")}</span>
      ${format.recommended ? `<span class="recommended-pill">${t("recommended")}</span>` : ""}
    </div>
    <strong class="format-preview-title">${buildOptionLabel(format)}</strong>
    <div class="format-preview-meta">${buildPreviewMetaBits(format).join(" · ")}</div>
  `;
  container.appendChild(preview);
}

function renderVideoFormatControls(videoFormats) {
  if (videoFormats.length === 0) {
    renderEmptyFormatState(videoFormatGrid, t("formatEmptyVideo"));
    return;
  }

  const selectedVideo = ensureVideoFilterState(videoFormats);
  const extensionOptions = sortByPreferredOrder(
    [...new Set(videoFormats.map((format) => format.extension))],
    VIDEO_EXTENSION_ORDER
  ).map((value) => ({
    value,
    label: value.toUpperCase(),
    count: videoFormats.filter((format) => format.extension === value).length
  }));

  const resolutionOptions = sortNumericLabelDescending(
    [...new Set(videoFormats
      .filter((format) => format.extension === videoFilterState.extension)
      .map((format) => getVideoResolution(format)))],
    "p"
  ).map((value) => ({
    value,
    label: value,
    count: videoFormats.filter((format) => format.extension === videoFilterState.extension && getVideoResolution(format) === value).length
  }));

  const fpsOptions = sortNumericLabelDescending(
    [...new Set(videoFormats
      .filter((format) => format.extension === videoFilterState.extension && getVideoResolution(format) === videoFilterState.resolution)
      .map((format) => getVideoFps(format)))],
    "fps"
  ).map((value) => ({
    value,
    label: value,
    count: videoFormats.filter((format) => (
      format.extension === videoFilterState.extension
      && getVideoResolution(format) === videoFilterState.resolution
      && getVideoFps(format) === value
    )).length
  }));

  videoFormatGrid.appendChild(createFilterStep(t("filterExtension"), extensionOptions, videoFilterState.extension, (value) => {
    videoFilterState.extension = value;
    videoFilterState.resolution = null;
    videoFilterState.fps = null;
    const format = ensureVideoFilterState(videoFormats);
    applySelection(format, { syncFilters: false });
    renderFormatOptions(latestPayload.formats);
  }));

  videoFormatGrid.appendChild(createFilterStep(t("filterResolution"), resolutionOptions, videoFilterState.resolution, (value) => {
    videoFilterState.resolution = value;
    videoFilterState.fps = null;
    const format = ensureVideoFilterState(videoFormats);
    applySelection(format, { syncFilters: false });
    renderFormatOptions(latestPayload.formats);
  }));

  videoFormatGrid.appendChild(createFilterStep(t("filterFps"), fpsOptions, videoFilterState.fps, (value) => {
    videoFilterState.fps = value;
    const format = ensureVideoFilterState(videoFormats);
    applySelection(format, { syncFilters: false });
    renderFormatOptions(latestPayload.formats);
  }));

  if (selectedVideo) {
    renderSelectedFormatPreview(videoFormatGrid, selectedVideo);
  }
}

function renderAudioFormatControls(audioFormats) {
  if (audioFormats.length === 0) {
    renderEmptyFormatState(audioFormatGrid, t("formatEmptyAudio"));
    return;
  }

  const selectedAudio = ensureAudioFilterState(audioFormats);
  const extensionOptions = sortByPreferredOrder(
    [...new Set(audioFormats.map((format) => format.extension))],
    AUDIO_EXTENSION_ORDER
  ).map((value) => ({
    value,
    label: value.toUpperCase(),
    count: audioFormats.filter((format) => format.extension === value).length
  }));

  const qualityOptions = sortAudioQualityValues(
    [...new Set(audioFormats
      .filter((format) => format.extension === audioFilterState.extension)
      .map((format) => format.quality))]
  ).map((value) => ({
    value,
    label: value,
    count: audioFormats.filter((format) => format.extension === audioFilterState.extension && format.quality === value).length
  }));

  audioFormatGrid.appendChild(createFilterStep(t("filterExtension"), extensionOptions, audioFilterState.extension, (value) => {
    audioFilterState.extension = value;
    audioFilterState.quality = null;
    const format = ensureAudioFilterState(audioFormats);
    applySelection(format, { syncFilters: false });
    renderFormatOptions(latestPayload.formats);
  }));

  audioFormatGrid.appendChild(createFilterStep(t("filterAudioQuality"), qualityOptions, audioFilterState.quality, (value) => {
    audioFilterState.quality = value;
    const format = ensureAudioFilterState(audioFormats);
    applySelection(format, { syncFilters: false });
    renderFormatOptions(latestPayload.formats);
  }));

  if (selectedAudio) {
    renderSelectedFormatPreview(audioFormatGrid, selectedAudio);
  }
}

function renderFormatOptions(formats) {
  videoFormatGrid.innerHTML = "";
  audioFormatGrid.innerHTML = "";

  const videoFormats = formats.filter((format) => format.media_type === "video");
  const audioFormats = formats.filter((format) => format.media_type === "audio");

  renderVideoFormatControls(videoFormats);
  renderAudioFormatControls(audioFormats);
}

function resetResult() {
  resultCard.classList.add("hidden");
  latestPayload = null;
  selectedFormatKey = null;
  videoFilterState = { extension: null, resolution: null, fps: null };
  audioFilterState = { extension: null, quality: null };
  videoFormatGrid.innerHTML = "";
  audioFormatGrid.innerHTML = "";
  mediaFacts.innerHTML = "";
  selectionSummary.textContent = t("selectionEmpty");
  stopDownloadPolling();
  currentJobId = null;
  resetProgressCard();
  updateDownloadButtonState();
}

function hydrateResult(data) {
  latestPayload = data;
  titleNode.textContent = data.title;
  badgeNode.textContent = data.platform;
  metaNode.textContent = t("resultMeta", {
    duration: formatDuration(data.duration_seconds),
    count: data.formats.length
  });
  thumbNode.src = data.thumbnail || "";
  thumbNode.classList.toggle("hidden", !data.thumbnail);
  renderMediaFacts(data);
  const recommendedVideo = data.formats.find((item) => item.media_type === "video" && item.recommended);
  const fallbackFormat = recommendedVideo || data.formats.find((item) => item.recommended) || data.formats[0];
  applySelection(fallbackFormat, { syncFilters: true, resetProgress: false });
  renderFormatOptions(data.formats);
  resultCard.classList.remove("hidden");
  resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function summarizeUrl(rawValue) {
  const value = rawValue.trim();
  if (!value) {
    return { message: t("helperPasteValid"), type: "" };
  }

  try {
    const parsed = new URL(value);
    const platform = SUPPORTED_DOMAINS[parsed.hostname];
    const path = parsed.pathname.toLowerCase();
    const isPlaylist = parsed.searchParams.has("list") || path.includes("/playlist");
    const isChannel = path.includes("/channel") || path.includes("/c/") || path.includes("/@");

    if (!platform) {
      return {
        message: t("helperDomain", { hostname: parsed.hostname }),
        type: ""
      };
    }

    if (isPlaylist) {
      return {
        message: t("helperPlaylist", { platform }),
        type: "warning"
      };
    }

    if (isChannel) {
      return {
        message: t("helperChannel", { platform }),
        type: "warning"
      };
    }

    return {
      message: t("helperPlatformDetected", { platform }),
      type: "success"
    };
  } catch {
    return {
      message: t("helperInvalidUrl"),
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
  setStatus(t("statusAnalyze"), "info");

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
    setStatus(t("statusReady"), "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    analyzeButton.disabled = false;
  }
}

function stopDownloadPolling() {
  if (downloadPollTimer) {
    window.clearTimeout(downloadPollTimer);
    downloadPollTimer = null;
  }
}

async function pollDownloadJob(jobId) {
  try {
    const response = await fetch(`/api/download-jobs/${jobId}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || t("processing"));
    }

    renderProgress(data);

    if (data.status === "completed") {
      isDownloading = false;
      updateDownloadButtonState();
      setStatus(t("statusDownloadReady"), "success");
      return;
    }

    if (data.status === "failed") {
      isDownloading = false;
      updateDownloadButtonState();
      setStatus(data.status_text || t("processing"), "error");
      return;
    }

    downloadPollTimer = window.setTimeout(() => pollDownloadJob(jobId), DOWNLOAD_POLL_INTERVAL_MS);
  } catch (error) {
    isDownloading = false;
    updateDownloadButtonState();
    setStatus(error.message, "error");
  }
}

async function startDownload() {
  if (!latestPayload) {
    setStatus(t("statusAnalyzeFirst"), "error");
    return;
  }

  const selected = getSelectedFormat();
  if (!selected) {
    setStatus(t("statusChooseFormat"), "error");
    return;
  }

  stopDownloadPolling();
  isDownloading = true;
  currentJobId = null;
  updateDownloadButtonState();
  renderProgress({
    format_label: selected.label,
    progress_percent: 0,
    status_text: t("statusInitDownload")
  });
  setStatus(t("statusDownloadStarting"), "success");

  try {
    const response = await fetch("/api/download-jobs", {
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
      throw new Error(data.detail || "No se pudo iniciar la descarga.");
    }

    currentJobId = data.job_id;
    renderProgress(data);
    pollDownloadJob(currentJobId);
  } catch (error) {
    isDownloading = false;
    updateDownloadButtonState();
    setStatus(error.message, "error");
  }
}

async function pasteFromClipboard() {
  if (!navigator.clipboard?.readText) {
    setStatus(t("clipboardUnsupported"), "error");
    return;
  }

  try {
    const text = (await navigator.clipboard.readText()).trim();
    if (!text) {
      setStatus(t("clipboardEmpty"), "error");
      return;
    }

    urlInput.value = text;
    urlInput.focus();
    updateUrlHelper();
    setStatus(t("clipboardSuccess"), "info");
  } catch {
    setStatus(t("clipboardError"), "error");
  }
}

function clearUrl() {
  urlInput.value = "";
  urlInput.focus();
  resetResult();
  updateUrlHelper();
  setStatus(t("fieldCleared"), "info");
}

function setAudioFormat(value) {
  audioFormatSelect.value = value;
  updateAudioChipState();
}

applyStaticTranslations();
setStatus(t("statusStart"), "info");
updateDownloadButtonState();
updateUrlHelper();

form.addEventListener("submit", analyzeUrl);
downloadButton.addEventListener("click", startDownload);
pasteButton.addEventListener("click", pasteFromClipboard);
clearButton.addEventListener("click", clearUrl);
urlInput.addEventListener("input", updateUrlHelper);
audioFormatChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    if (chip.disabled) return;
    setAudioFormat(chip.dataset.audioFormat);
  });
});
