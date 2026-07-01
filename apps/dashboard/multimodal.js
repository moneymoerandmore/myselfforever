const poeApiKeyInput = document.querySelector("#poeApiKey");
const poeModelInput = document.querySelector("#poeModel");
const clearPoeApiKeyButton = document.querySelector("#clearPoeApiKey");
const mediaFileInput = document.querySelector("#mediaFile");
const transcriptFileInput = document.querySelector("#transcriptFile");
const localAsrPathInput = document.querySelector("#localAsrPath");
const localAsrModelInput = document.querySelector("#localAsrModel");
const localAsrComputeInput = document.querySelector("#localAsrCompute");
const localAsrLanguageInput = document.querySelector("#localAsrLanguage");
const asrProviderInput = document.querySelector("#asrProvider");
const volcengineAppIdInput = document.querySelector("#volcengineAppId");
const volcengineTokenInput = document.querySelector("#volcengineToken");
const volcengineClusterInput = document.querySelector("#volcengineCluster");
const volcengineAudioUrlInput = document.querySelector("#volcengineAudioUrl");
const asrProviderPanels = Array.from(document.querySelectorAll("[data-asr-panel]"));
const funasrModelInput = document.querySelector("#funasrModel");
const funasrVadModelInput = document.querySelector("#funasrVadModel");
const funasrPuncModelInput = document.querySelector("#funasrPuncModel");
const funasrSpkModelInput = document.querySelector("#funasrSpkModel");
const funasrBatchSizeInput = document.querySelector("#funasrBatchSize");
const funasrHotwordInput = document.querySelector("#funasrHotword");
const hfTokenInput = document.querySelector("#hfToken");
const speakerDisplayNameInput = document.querySelector("#speakerDisplayName");
const targetInput = document.querySelector("#target");
const frameLimitInput = document.querySelector("#frameLimit");
const frameMaxEdgeInput = document.querySelector("#frameMaxEdge");
const jpegQualityInput = document.querySelector("#jpegQuality");
const noteInput = document.querySelector("#note");
const contextInput = document.querySelector("#context");
const timelineTextInput = document.querySelector("#timelineText");
const clearButton = document.querySelector("#clearButton");
const extractButton = document.querySelector("#extractButton");
const analyzeButton = document.querySelector("#analyzeButton");
const localAsrButton = document.querySelector("#localAsrButton");
const enrollSpeakerButton = document.querySelector("#enrollSpeakerButton");
const diarizedAsrButton = document.querySelector("#diarizedAsrButton");
const sourceMeta = document.querySelector("#sourceMeta");
const transcriptMeta = document.querySelector("#transcriptMeta");
const speakerProfileMeta = document.querySelector("#speakerProfileMeta");
const statusBadge = document.querySelector("#statusBadge");
const videoProbe = document.querySelector("#videoProbe");
const frameCanvas = document.querySelector("#frameCanvas");
const frameStrip = document.querySelector("#frameStrip");
const frameMeta = document.querySelector("#frameMeta");
const resultMeta = document.querySelector("#resultMeta");
const resultText = document.querySelector("#resultText");
const confirmationPanel = document.querySelector("#confirmationPanel");
const confirmationList = document.querySelector("#confirmationList");
const confirmSelectedButton = document.querySelector("#confirmSelectedButton");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";
const LOCAL_ASR_PATH_STORAGE_KEY = "digitalTwin.localAsrPath";
const LOCAL_ASR_MODEL_STORAGE_KEY = "digitalTwin.localAsrModel";
const ASR_PROVIDER_STORAGE_KEY = "digitalTwin.asrProvider";
const VOLCENGINE_APP_ID_STORAGE_KEY = "digitalTwin.volcengineAppId";
const VOLCENGINE_TOKEN_STORAGE_KEY = "digitalTwin.volcengineToken";
const VOLCENGINE_CLUSTER_STORAGE_KEY = "digitalTwin.volcengineCluster";
const VOLCENGINE_AUDIO_URL_STORAGE_KEY = "digitalTwin.volcengineAudioUrl";
const FUNASR_MODEL_STORAGE_KEY = "digitalTwin.funasrModel";
const FUNASR_VAD_MODEL_STORAGE_KEY = "digitalTwin.funasrVadModel";
const FUNASR_PUNC_MODEL_STORAGE_KEY = "digitalTwin.funasrPuncModel";
const FUNASR_SPK_MODEL_STORAGE_KEY = "digitalTwin.funasrSpkModel";
const FUNASR_BATCH_SIZE_STORAGE_KEY = "digitalTwin.funasrBatchSize";
const FUNASR_HOTWORD_STORAGE_KEY = "digitalTwin.funasrHotword";
const HF_TOKEN_STORAGE_KEY = "digitalTwin.hfToken";
const SPEAKER_DISPLAY_NAME_STORAGE_KEY = "digitalTwin.speakerDisplayName";
const MULTIMODAL_DEFAULT_MODEL = "GPT-4o";
const LEGACY_MULTIMODAL_DEFAULT_MODELS = new Set(["Claude-Sonnet-4", "Claude-Opus-4", "Claude-Opus"]);
const MAX_FRAME_BYTES = 675000;
const MAX_TOTAL_FRAME_BYTES = 6000000;
const MAX_TRANSCRIPT_CHARS = 50000;

let currentFile = null;
let extractedFrames = [];
let videoMetadata = {};
let transcriptText = "";
let lastAnalysisResult = null;

function updateAsrProviderPanels() {
  const provider = asrProviderInput.value || "volcengine";
  asrProviderPanels.forEach((panel) => {
    const active = panel.dataset.asrPanel === provider;
    panel.classList.toggle("hidden", !active);
    panel.setAttribute("aria-hidden", active ? "false" : "true");
  });
}

function restoreSettings() {
  try {
    poeApiKeyInput.value = localStorage.getItem(POE_API_KEY_STORAGE_KEY) || "";
    localAsrPathInput.value = localStorage.getItem(LOCAL_ASR_PATH_STORAGE_KEY) || "";
    localAsrModelInput.value = localStorage.getItem(LOCAL_ASR_MODEL_STORAGE_KEY) || localAsrModelInput.value;
    asrProviderInput.value = localStorage.getItem(ASR_PROVIDER_STORAGE_KEY) || asrProviderInput.value;
    volcengineAppIdInput.value = localStorage.getItem(VOLCENGINE_APP_ID_STORAGE_KEY) || "";
    volcengineTokenInput.value = localStorage.getItem(VOLCENGINE_TOKEN_STORAGE_KEY) || "";
    volcengineClusterInput.value = localStorage.getItem(VOLCENGINE_CLUSTER_STORAGE_KEY) || volcengineClusterInput.value;
    volcengineAudioUrlInput.value = localStorage.getItem(VOLCENGINE_AUDIO_URL_STORAGE_KEY) || "";
    funasrModelInput.value = localStorage.getItem(FUNASR_MODEL_STORAGE_KEY) || funasrModelInput.value;
    funasrVadModelInput.value = localStorage.getItem(FUNASR_VAD_MODEL_STORAGE_KEY) || funasrVadModelInput.value;
    funasrPuncModelInput.value = localStorage.getItem(FUNASR_PUNC_MODEL_STORAGE_KEY) || funasrPuncModelInput.value;
    funasrSpkModelInput.value = localStorage.getItem(FUNASR_SPK_MODEL_STORAGE_KEY) || funasrSpkModelInput.value;
    funasrBatchSizeInput.value = localStorage.getItem(FUNASR_BATCH_SIZE_STORAGE_KEY) || funasrBatchSizeInput.value;
    funasrHotwordInput.value = localStorage.getItem(FUNASR_HOTWORD_STORAGE_KEY) || "";
    hfTokenInput.value = localStorage.getItem(HF_TOKEN_STORAGE_KEY) || "";
    speakerDisplayNameInput.value =
      localStorage.getItem(SPEAKER_DISPLAY_NAME_STORAGE_KEY) || speakerDisplayNameInput.value || "我";
    const storedModel = localStorage.getItem(POE_MODEL_STORAGE_KEY) || "";
    poeModelInput.value =
      !storedModel || LEGACY_MULTIMODAL_DEFAULT_MODELS.has(storedModel)
        ? MULTIMODAL_DEFAULT_MODEL
        : storedModel;
  } catch {
    // Local storage can be unavailable in locked-down browser contexts.
  }
  updateAsrProviderPanels();
}

function cacheSettings() {
  try {
    const apiKey = poeApiKeyInput.value.trim();
    const model = poeModelInput.value.trim();
    if (apiKey) localStorage.setItem(POE_API_KEY_STORAGE_KEY, apiKey);
    else localStorage.removeItem(POE_API_KEY_STORAGE_KEY);
    if (model) localStorage.setItem(POE_MODEL_STORAGE_KEY, model);
    const localAsrPath = localAsrPathInput.value.trim();
    const localAsrModel = localAsrModelInput.value.trim();
    if (localAsrPath) localStorage.setItem(LOCAL_ASR_PATH_STORAGE_KEY, localAsrPath);
    else localStorage.removeItem(LOCAL_ASR_PATH_STORAGE_KEY);
    if (localAsrModel) localStorage.setItem(LOCAL_ASR_MODEL_STORAGE_KEY, localAsrModel);
    const asrProvider = asrProviderInput.value.trim();
    const volcengineAppId = volcengineAppIdInput.value.trim();
    const volcengineToken = volcengineTokenInput.value.trim();
    const volcengineCluster = volcengineClusterInput.value.trim();
    const volcengineAudioUrl = volcengineAudioUrlInput.value.trim();
    const funasrModel = funasrModelInput.value.trim();
    const funasrVadModel = funasrVadModelInput.value.trim();
    const funasrPuncModel = funasrPuncModelInput.value.trim();
    const funasrSpkModel = funasrSpkModelInput.value.trim();
    const funasrBatchSize = funasrBatchSizeInput.value.trim();
    const funasrHotword = funasrHotwordInput.value.trim();
    if (asrProvider) localStorage.setItem(ASR_PROVIDER_STORAGE_KEY, asrProvider);
    if (volcengineAppId) localStorage.setItem(VOLCENGINE_APP_ID_STORAGE_KEY, volcengineAppId);
    else localStorage.removeItem(VOLCENGINE_APP_ID_STORAGE_KEY);
    if (volcengineToken) localStorage.setItem(VOLCENGINE_TOKEN_STORAGE_KEY, volcengineToken);
    else localStorage.removeItem(VOLCENGINE_TOKEN_STORAGE_KEY);
    if (volcengineCluster) localStorage.setItem(VOLCENGINE_CLUSTER_STORAGE_KEY, volcengineCluster);
    if (volcengineAudioUrl) localStorage.setItem(VOLCENGINE_AUDIO_URL_STORAGE_KEY, volcengineAudioUrl);
    else localStorage.removeItem(VOLCENGINE_AUDIO_URL_STORAGE_KEY);
    if (funasrModel) localStorage.setItem(FUNASR_MODEL_STORAGE_KEY, funasrModel);
    if (funasrVadModel) localStorage.setItem(FUNASR_VAD_MODEL_STORAGE_KEY, funasrVadModel);
    if (funasrPuncModel) localStorage.setItem(FUNASR_PUNC_MODEL_STORAGE_KEY, funasrPuncModel);
    if (funasrSpkModel) localStorage.setItem(FUNASR_SPK_MODEL_STORAGE_KEY, funasrSpkModel);
    if (funasrBatchSize) localStorage.setItem(FUNASR_BATCH_SIZE_STORAGE_KEY, funasrBatchSize);
    if (funasrHotword) localStorage.setItem(FUNASR_HOTWORD_STORAGE_KEY, funasrHotword);
    else localStorage.removeItem(FUNASR_HOTWORD_STORAGE_KEY);
    const hfToken = hfTokenInput.value.trim();
    const speakerDisplayName = speakerDisplayNameInput.value.trim();
    if (hfToken) localStorage.setItem(HF_TOKEN_STORAGE_KEY, hfToken);
    else localStorage.removeItem(HF_TOKEN_STORAGE_KEY);
    if (speakerDisplayName) localStorage.setItem(SPEAKER_DISPLAY_NAME_STORAGE_KEY, speakerDisplayName);
  } catch {
    // Keep visible settings for this page session.
  }
}

function setStatus(text, state = "idle") {
  statusBadge.textContent = text;
  statusBadge.className = "badge";
  if (state === "ok") statusBadge.classList.add("badge-ok");
  if (state === "warn") statusBadge.classList.add("badge-warn");
  if (state === "error") statusBadge.classList.add("badge-error");
}

function setAsrBusy(isBusy) {
  localAsrButton.disabled = isBusy;
  enrollSpeakerButton.disabled = isBusy;
  diarizedAsrButton.disabled = isBusy;
  analyzeButton.disabled = isBusy;
  extractButton.disabled = isBusy;
}

function currentLocalMediaPath() {
  return localAsrPathInput.value.trim();
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function appendTranscriptToTimeline(label, text) {
  transcriptText = normalizeTranscriptText(text);
  timelineTextInput.value = [timelineTextInput.value.trim(), transcriptText ? `${label}：\n${transcriptText}` : ""]
    .filter(Boolean)
    .join("\n\n");
}

function speakerSummaryText(speakers = []) {
  if (!speakers.length) return "未检测到可用说话人。";
  return speakers
    .map((speaker) => {
      const name = speaker.display_name || speaker.speaker;
      const raw = speaker.speaker && speaker.speaker !== name ? `/${speaker.speaker}` : "";
      const score = speaker.identity?.score ? ` · 匹配 ${speaker.identity.score}` : "";
      return `${name}${raw} · ${speaker.turn_count || 0} 段 · ${formatTime(speaker.duration || 0)}${score}`;
    })
    .join("\n");
}

function formatBytes(value) {
  const size = Number(value || 0);
  if (size >= 1024 * 1024 * 1024) return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${size} B`;
}

function formatTime(seconds) {
  const value = Math.max(0, Number(seconds || 0));
  const minutes = Math.floor(value / 60);
  const rest = Math.floor(value % 60);
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function dataUrlSize(dataUrl) {
  return Math.round((String(dataUrl || "").length * 3) / 4);
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result || "")));
    reader.addEventListener("error", () => reject(reader.error || new Error("文件读取失败")));
    reader.readAsDataURL(file);
  });
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result || "")));
    reader.addEventListener("error", () => reject(reader.error || new Error("文件读取失败")));
    reader.readAsText(file, "utf-8");
  });
}

function normalizeTranscriptText(value) {
  return String(value || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\n{4,}/g, "\n\n\n")
    .trim()
    .slice(0, MAX_TRANSCRIPT_CHARS);
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", () => reject(new Error("图片无法读取")));
    image.src = src;
  });
}

function targetSize(width, height, maxEdge) {
  const edge = Math.max(width, height);
  if (!edge || edge <= maxEdge) return { width, height };
  const ratio = maxEdge / edge;
  return {
    width: Math.max(1, Math.round(width * ratio)),
    height: Math.max(1, Math.round(height * ratio)),
  };
}

function canvasToFrame(name, timestampSeconds, sourceWidth, sourceHeight) {
  const quality = Number(jpegQualityInput.value || 0.72);
  const dataUrl = frameCanvas.toDataURL("image/jpeg", quality);
  return {
    name,
    type: "image/jpeg",
    size: dataUrlSize(dataUrl),
    data_url: dataUrl,
    timestamp_seconds: timestampSeconds,
    source_width: sourceWidth,
    source_height: sourceHeight,
  };
}

function renderFrames() {
  frameStrip.innerHTML = "";
  if (!extractedFrames.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "选择图片或视频后，这里显示将送入模型的帧。";
    frameStrip.appendChild(empty);
    frameMeta.textContent = "等待材料";
    return;
  }
  for (const frame of extractedFrames) {
    const card = document.createElement("div");
    card.className = "frame-card";
    const image = document.createElement("img");
    image.src = frame.data_url;
    image.alt = frame.name;
    const label = document.createElement("span");
    label.textContent =
      frame.timestamp_seconds === null || frame.timestamp_seconds === undefined
        ? frame.name
        : `${formatTime(frame.timestamp_seconds)} · ${formatBytes(frame.size)}`;
    card.append(image, label);
    frameStrip.appendChild(card);
  }
  const totalSize = extractedFrames.reduce((sum, frame) => sum + (frame.size || 0), 0);
  frameMeta.textContent = `${extractedFrames.length} 帧 · 约 ${formatBytes(totalSize)} · 只上传这些抽样帧`;
}

function payloadWarning() {
  if (!extractedFrames.length) return "";
  const totalSize = extractedFrames.reduce((sum, frame) => sum + (frame.size || 0), 0);
  const oversizedFrame = extractedFrames.find((frame) => (frame.size || 0) > MAX_FRAME_BYTES);
  if (oversizedFrame) {
    return `单帧过大：${oversizedFrame.name} 约 ${formatBytes(oversizedFrame.size)}。请降低最长边或 JPEG 质量后重新抽帧。`;
  }
  if (totalSize > MAX_TOTAL_FRAME_BYTES) {
    return `抽样帧总量过大：约 ${formatBytes(totalSize)}。请减少抽帧数量、降低最长边或 JPEG 质量后重新抽帧。`;
  }
  return "";
}

function resetFrames() {
  extractedFrames = [];
  videoMetadata = {};
  renderFrames();
}

async function compressImageFile(file) {
  const dataUrl = await readFileAsDataUrl(file);
  const image = await loadImage(dataUrl);
  const maxEdge = Number(frameMaxEdgeInput.value || 960);
  const size = targetSize(image.naturalWidth || image.width, image.naturalHeight || image.height, maxEdge);
  frameCanvas.width = size.width;
  frameCanvas.height = size.height;
  const context = frameCanvas.getContext("2d");
  context.drawImage(image, 0, 0, size.width, size.height);
  return [
    canvasToFrame(
      `${file.name.replace(/\.[^.]+$/, "") || "image"}-frame.jpg`,
      null,
      image.naturalWidth || image.width,
      image.naturalHeight || image.height,
    ),
  ];
}

function waitForVideoEvent(eventName) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      videoProbe.removeEventListener(eventName, onEvent);
      videoProbe.removeEventListener("error", onError);
    };
    const onEvent = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      reject(new Error("视频无法读取，可能是编码不受浏览器支持"));
    };
    videoProbe.addEventListener(eventName, onEvent, { once: true });
    videoProbe.addEventListener("error", onError, { once: true });
  });
}

async function loadVideo(file) {
  if (videoProbe.src) URL.revokeObjectURL(videoProbe.src);
  const url = URL.createObjectURL(file);
  const loaded = waitForVideoEvent("loadedmetadata");
  videoProbe.src = url;
  videoProbe.load();
  await loaded;
  return url;
}

function sampleTimes(duration, count) {
  if (!Number.isFinite(duration) || duration <= 0) return [0];
  if (count <= 1) return [Math.min(duration * 0.5, Math.max(0, duration - 0.1))];
  const safeStart = Math.min(0.5, Math.max(0, duration * 0.02));
  const safeEnd = Math.max(safeStart, duration - Math.min(0.5, duration * 0.02));
  const times = [];
  for (let index = 0; index < count; index += 1) {
    const ratio = index / (count - 1);
    times.push(Number((safeStart + (safeEnd - safeStart) * ratio).toFixed(2)));
  }
  return times;
}

function normalizedFrameLimit() {
  const rawValue = Number.parseInt(frameLimitInput.value || "24", 10);
  const value = Number.isFinite(rawValue) ? rawValue : 24;
  const normalized = Math.min(240, Math.max(1, value));
  frameLimitInput.value = String(normalized);
  return normalized;
}

async function seekVideo(seconds) {
  const target = Math.min(Math.max(0, seconds), Math.max(0, videoProbe.duration - 0.05));
  if (Math.abs(videoProbe.currentTime - target) < 0.04) return;
  const seeked = waitForVideoEvent("seeked");
  videoProbe.currentTime = target;
  await seeked;
}

async function extractVideoFrames(file) {
  const objectUrl = await loadVideo(file);
  const duration = Number(videoProbe.duration || 0);
  const width = videoProbe.videoWidth || 0;
  const height = videoProbe.videoHeight || 0;
  const frameLimit = normalizedFrameLimit();
  const maxEdge = Number(frameMaxEdgeInput.value || 960);
  const times = sampleTimes(duration, frameLimit);
  const size = targetSize(width, height, maxEdge);
  const frames = [];
  frameCanvas.width = size.width;
  frameCanvas.height = size.height;
  const canvasContext = frameCanvas.getContext("2d");

  videoMetadata = {
    duration_seconds: Number(duration.toFixed(2)),
    width,
    height,
    source_size_bytes: file.size,
    extracted_frame_limit: frameLimit,
    frame_max_edge: maxEdge,
    sampling_strategy: "uniform-local-browser-sampling",
  };

  try {
    for (let index = 0; index < times.length; index += 1) {
      const seconds = times[index];
      setStatus(`抽帧 ${index + 1}/${times.length}`, "warn");
      await seekVideo(seconds);
      canvasContext.drawImage(videoProbe, 0, 0, size.width, size.height);
      frames.push(
        canvasToFrame(
          `${file.name.replace(/\.[^.]+$/, "") || "video"}-t${formatTime(seconds)}.jpg`,
          seconds,
          width,
          height,
        ),
      );
    }
  } finally {
    URL.revokeObjectURL(objectUrl);
    videoProbe.removeAttribute("src");
    videoProbe.load();
  }
  return frames;
}

async function extractFrames() {
  if (!currentFile) {
    setStatus("缺少文件", "warn");
    return;
  }
  extractButton.disabled = true;
  analyzeButton.disabled = true;
  resultText.textContent = "正在本地抽样，不上传原始文件。";
  try {
    if (currentFile.type.startsWith("image/")) {
      extractedFrames = await compressImageFile(currentFile);
      videoMetadata = {};
    } else if (currentFile.type.startsWith("video/")) {
      extractedFrames = await extractVideoFrames(currentFile);
    } else {
      extractedFrames = [];
      videoMetadata = {};
      throw new Error("当前只支持图片和视频文件");
    }
    renderFrames();
    setStatus("已抽样", "ok");
    resultText.textContent = "抽样完成，可以继续补充说明或直接分析。";
  } catch (error) {
    setStatus("抽样失败", "error");
    resultText.textContent = `抽样失败：${error.message}`;
  } finally {
    extractButton.disabled = false;
    analyzeButton.disabled = false;
  }
}

function formatAnalysisList(title, values) {
  if (!Array.isArray(values) || values.length === 0) return `${title}\n- 暂无`;
  return `${title}\n${values.map((item) => `- ${typeof item === "string" ? item : JSON.stringify(item)}`).join("\n")}`;
}

function candidateText(item) {
  if (typeof item === "string") return item;
  return String(item?.candidate || item?.text || "").trim();
}

function normalizeConfirmationCandidates(analysis) {
  const source = Array.isArray(analysis?.memory_candidates) ? analysis.memory_candidates : [];
  return source
    .map((item, index) => ({
      id: `candidate-${index}`,
      source_type: "memory_candidate",
      candidate: candidateText(item),
      scope: typeof item === "object" && item ? String(item.scope || "short_term") : "short_term",
      confidence: typeof item === "object" && item ? String(item.confidence || "medium") : "medium",
      needs_user_confirmation: typeof item === "object" && item ? item.needs_user_confirmation !== false : true,
      evidence: typeof item === "object" && item ? String(item.evidence || item.reason || "") : "",
    }))
    .filter((item) => item.candidate);
}

function option(value, label, selectedValue) {
  const node = document.createElement("option");
  node.value = value;
  node.textContent = label;
  node.selected = value === selectedValue;
  return node;
}

function hideConfirmationPanel() {
  confirmationList.innerHTML = "";
  confirmationPanel.classList.add("hidden");
  confirmSelectedButton.disabled = false;
}

function createCandidateCard(item) {
  const card = document.createElement("article");
  card.className = "confirm-card";
  card.dataset.sourceType = item.source_type;

  const head = document.createElement("div");
  head.className = "confirm-card-head";
  const checkLabel = document.createElement("label");
  checkLabel.className = "confirm-check";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "confirm-card-check";
  checkbox.checked = item.needs_user_confirmation;
  const labelText = document.createElement("span");
  labelText.textContent = item.needs_user_confirmation ? "确认后注入" : "候选，可选注入";
  checkLabel.append(checkbox, labelText);
  const pill = document.createElement("span");
  pill.className = "confirm-pill";
  pill.textContent = item.source_type === "memory_candidate" ? "记忆候选" : "确认补充";
  head.append(checkLabel, pill);

  const textarea = document.createElement("textarea");
  textarea.className = "confirm-candidate";
  textarea.value = item.candidate;

  const grid = document.createElement("div");
  grid.className = "confirm-grid";
  const scopeLabel = document.createElement("label");
  const scopeTitle = document.createElement("span");
  scopeTitle.textContent = "注入范围";
  const scopeSelect = document.createElement("select");
  scopeSelect.className = "confirm-scope";
  [["self_core_candidate", "SelfCore 候选"]].forEach(([value, label]) => scopeSelect.appendChild(option(value, label, "self_core_candidate")));
  scopeSelect.disabled = true;
  scopeLabel.append(scopeTitle, scopeSelect);

  const confidenceLabel = document.createElement("label");
  const confidenceTitle = document.createElement("span");
  confidenceTitle.textContent = "置信度";
  const confidenceSelect = document.createElement("select");
  confidenceSelect.className = "confirm-confidence";
  [
    ["low", "低"],
    ["medium", "中"],
    ["high", "高"],
  ].forEach(([value, label]) => confidenceSelect.appendChild(option(value, label, item.confidence)));
  confidenceLabel.append(confidenceTitle, confidenceSelect);
  grid.append(scopeLabel, confidenceLabel);

  card.append(head, textarea, grid);
  if (item.evidence) {
    const evidence = document.createElement("p");
    evidence.className = "confirm-evidence";
    evidence.textContent = `证据：${item.evidence}`;
    card.appendChild(evidence);
  }
  return card;
}

function createQuestionCard(question, index) {
  const card = document.createElement("article");
  card.className = "confirm-card question";
  card.dataset.sourceType = "question_answer";
  card.dataset.question = question;

  const head = document.createElement("div");
  head.className = "confirm-card-head";
  const label = document.createElement("label");
  label.className = "confirm-check";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "confirm-card-check";
  checkbox.checked = false;
  const labelText = document.createElement("span");
  labelText.textContent = `补充确认 ${index + 1}`;
  label.append(checkbox, labelText);
  const pill = document.createElement("span");
  pill.className = "confirm-pill";
  pill.textContent = "需要回答";
  head.append(label, pill);

  const prompt = document.createElement("p");
  prompt.className = "confirm-evidence";
  prompt.textContent = question;
  const textarea = document.createElement("textarea");
  textarea.className = "confirm-candidate";
  textarea.placeholder = "填写你的确认或修正；勾选后会作为补充证据注入";
  card.append(head, prompt, textarea);
  return card;
}

function renderConfirmationPanel(result) {
  const analysis = result?.analysis || {};
  const candidates = normalizeConfirmationCandidates(analysis);
  const questions = Array.isArray(analysis.questions_for_user) ? analysis.questions_for_user.filter(Boolean) : [];
  confirmationList.innerHTML = "";

  for (const item of candidates) {
    confirmationList.appendChild(createCandidateCard(item));
  }
  for (const [index, question] of questions.entries()) {
    confirmationList.appendChild(createQuestionCard(String(question), index));
  }

  if (!confirmationList.children.length) {
    const empty = document.createElement("div");
    empty.className = "confirm-message";
    empty.textContent = "这次没有需要页面确认的候选。";
    confirmationList.appendChild(empty);
  }
  confirmationPanel.classList.remove("hidden");
}

function collectConfirmations() {
  const confirmations = [];
  const questionAnswers = [];
  for (const card of confirmationList.querySelectorAll(".confirm-card")) {
    const checked = card.querySelector(".confirm-card-check")?.checked;
    if (!checked) continue;
    const text = card.querySelector(".confirm-candidate")?.value.trim() || "";
    if (!text) continue;
    const sourceType = card.dataset.sourceType || "memory_candidate";
    if (sourceType === "question_answer") {
      questionAnswers.push({
        question: card.dataset.question || "",
        answer: text,
      });
      continue;
    }
    confirmations.push({
      candidate: text,
      scope: "self_core_candidate",
      confidence: card.querySelector(".confirm-confidence")?.value || "medium",
      source_type: sourceType,
    });
  }
  return { confirmations, question_answers: questionAnswers };
}

async function confirmSelectedCandidates() {
  if (!lastAnalysisResult) {
    resultMeta.textContent = "先完成一次分析，再确认注入";
    return;
  }
  const payload = collectConfirmations();
  if (!payload.confirmations.length && !payload.question_answers.length) {
    resultMeta.textContent = "先勾选要注入的候选或补充确认";
    return;
  }
  confirmSelectedButton.disabled = true;
  resultMeta.textContent = "正在注入数字生命记忆层...";
  try {
    const response = await fetch("/api/multimodal/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target: targetInput.value,
        source_saved_path: lastAnalysisResult.saved_path || "",
        analysis_summary: lastAnalysisResult.analysis?.summary || "",
        ...payload,
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "确认注入失败");
    const count = data.result?.injected_count || 0;
    resultMeta.textContent = `已注入 ${count} 条确认特征`;
    setStatus("已注入", "ok");
  } catch (error) {
    resultMeta.textContent = `注入失败：${error.message}`;
    setStatus("注入失败", "error");
  } finally {
    confirmSelectedButton.disabled = false;
  }
}

function renderAnalysis(result) {
  if (result.error) {
    setStatus("分析失败", "error");
    resultMeta.textContent = "模型没有返回可用结果";
    hideConfirmationPanel();
    lastAnalysisResult = null;
    const attempts = Array.isArray(result.attempts)
      ? result.attempts
          .map((item) => {
            const size = formatBytes(item.total_bytes || 0);
            const error = item.error ? `：${item.error}` : "";
            return `- ${item.variant} / ${item.file_count} 帧 / ${size}${error}`;
          })
          .join("\n")
      : "";
    resultText.textContent = [`分析失败：${result.error}`, attempts ? `\n重试记录：\n${attempts}` : ""]
      .filter(Boolean)
      .join("\n");
    return;
  }
  lastAnalysisResult = result;
  const analysis = result.analysis || {};
  const candidates = Array.isArray(analysis.memory_candidates)
    ? analysis.memory_candidates.map((item) => {
        if (typeof item === "string") return item;
        return `${item.candidate || "--"}（${item.scope || "unknown"} / ${item.confidence || "unknown"} / ${
          item.needs_user_confirmation ? "需确认" : "可候选"
        }）`;
      })
    : [];
  resultText.textContent = [
    `摘要：${analysis.summary || "--"}`,
    "",
    formatAnalysisList("时间线事件", analysis.timeline_events),
    "",
    `交流内容：${analysis.conversation_summary || "--"}`,
    "",
    formatAnalysisList("沟通气氛", analysis.communication_atmosphere),
    "",
    formatAnalysisList("态度/立场信号", analysis.attitude_signals),
    "",
    formatAnalysisList("互动风格", analysis.interaction_style),
    "",
    formatAnalysisList("直接观察", analysis.observations),
    "",
    formatAnalysisList("自我理解信号", analysis.self_signals),
    "",
    formatAnalysisList("表达风格信号", analysis.expression_signals),
    "",
    formatAnalysisList("关系/场景信号", analysis.relationship_signals),
    "",
    formatAnalysisList("记忆候选", candidates),
    "",
    formatAnalysisList("风险标记", analysis.risk_flags),
    "",
    formatAnalysisList("需要你确认", analysis.questions_for_user),
    "",
    `建议动作：${analysis.recommended_next_action || "--"}`,
    result.saved_path ? `保存位置：${result.saved_path}` : "",
  ]
    .filter(Boolean)
    .join("\n");
  resultMeta.textContent = result.saved_path ? "已保存候选记录" : "未保存候选记录";
  renderConfirmationPanel(result);
  setStatus("已分析", "ok");
}

function frameTimelineText() {
  if (!extractedFrames.length) return "";
  return extractedFrames
    .map((frame, index) => {
      const label =
        frame.timestamp_seconds === null || frame.timestamp_seconds === undefined
          ? "image"
          : formatTime(frame.timestamp_seconds);
      return `${index + 1}. ${label} · ${frame.name}`;
    })
    .join("\n");
}

async function analyzeMaterial() {
  const apiKey = poeApiKeyInput.value.trim();
  const note = noteInput.value.trim();
  const context = contextInput.value.trim();
  const timelineText = timelineTextInput.value.trim();
  if (!apiKey) {
    setStatus("缺少 Key", "warn");
    resultText.textContent = "先输入 Poe API Key。";
    poeApiKeyInput.focus();
    return;
  }
  const currentIsAudio = currentFile?.type.startsWith("audio/");
  const currentIsVisual = currentFile?.type.startsWith("image/") || currentFile?.type.startsWith("video/");
  if (!currentFile && !note && !context && !timelineText && !transcriptText) {
    setStatus("缺少材料", "warn");
    resultText.textContent = "先选择文件，或者填写材料说明。";
    return;
  }
  if (currentIsAudio && !timelineText && !transcriptText) {
    setStatus("缺少转写", "warn");
    resultText.textContent = "音频文件请先点击 ASR 转写，或手动填写转写/时间线。";
    return;
  }
  if (currentIsVisual && !extractedFrames.length) {
    await extractFrames();
    if (!extractedFrames.length) return;
  }
  const warning = payloadWarning();
  if (warning) {
    setStatus("材料过大", "warn");
    resultText.textContent = warning;
    return;
  }

  analyzeButton.disabled = true;
  extractButton.disabled = true;
  setStatus("分析中", "warn");
  hideConfirmationPanel();
  lastAnalysisResult = null;
  resultText.textContent = "模型正在综合抽样帧、转写和说明，整理成可校对候选。";
  const mediaKind = currentFile?.type.startsWith("video/") ? "video_sampled_frames" : currentFile?.type.startsWith("image/") ? "image" : "text_only";
  const timelineHasTranscript =
    transcriptText && timelineText.includes(transcriptText.slice(0, Math.min(120, transcriptText.length)));
  const transcriptBlock = transcriptText && !timelineHasTranscript ? `字幕/ASR 转写：\n${transcriptText}` : "";
  try {
    const response = await fetch("/api/multimodal/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target: targetInput.value,
        media_kind: currentFile?.type.startsWith("audio/") ? "audio_asr" : mediaKind,
        source_name: currentFile?.name || "",
        note,
        context,
        timeline_text: [transcriptBlock, timelineText, frameTimelineText() ? `抽样帧：\n${frameTimelineText()}` : ""]
          .filter(Boolean)
          .join("\n\n"),
        video_metadata: videoMetadata,
        files: extractedFrames,
        poe_api_key: apiKey,
        poe_model: poeModelInput.value.trim(),
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "分析失败");
    renderAnalysis(data.result);
  } catch (error) {
    setStatus("分析失败", "error");
    resultText.textContent = `分析失败：${error.message}`;
  } finally {
    analyzeButton.disabled = false;
    extractButton.disabled = false;
  }
}

function onFileSelected() {
  currentFile = mediaFileInput.files?.[0] || null;
  resetFrames();
  if (!currentFile) {
    sourceMeta.textContent = "未选择文件";
    setStatus("待摄入");
    resultText.textContent = "等待分析。";
    hideConfirmationPanel();
    lastAnalysisResult = null;
    return;
  }
  sourceMeta.textContent = `${currentFile.name} · ${currentFile.type || "unknown"} · ${formatBytes(currentFile.size)}`;
  const isVideo = currentFile.type.startsWith("video/");
  const isAudio = currentFile.type.startsWith("audio/");
  setStatus(isVideo ? "待抽帧" : isAudio ? "待 ASR" : "待压缩", "warn");
  resultText.textContent = isVideo
    ? "视频会在浏览器本地抽帧；本地 Whisper 转写请在同一来源区填写磁盘路径。"
    : isAudio
      ? "音频文件可作为材料；本地 Whisper 转写请在同一来源区填写磁盘路径。"
    : "图片会在浏览器本地压缩后送入模型。";
}

function clearAll() {
  mediaFileInput.value = "";
  transcriptFileInput.value = "";
  currentFile = null;
  transcriptText = "";
  noteInput.value = "";
  contextInput.value = "";
  timelineTextInput.value = "";
  sourceMeta.textContent = "未选择文件";
  transcriptMeta.textContent = "可选：放入 ASR 转写、字幕或会议纪要，视频气氛和表达风格主要靠它还原";
  resultMeta.textContent = "不会直接改写 SelfCore";
  resultText.textContent = "等待分析。";
  hideConfirmationPanel();
  lastAnalysisResult = null;
  setStatus("待摄入");
  resetFrames();
}

async function onTranscriptSelected() {
  const file = transcriptFileInput.files?.[0] || null;
  transcriptText = "";
  if (!file) {
    transcriptMeta.textContent = "可选：放入 ASR 转写、字幕或会议纪要，视频气氛和表达风格主要靠它还原";
    return;
  }
  try {
    const rawText = await readFileAsText(file);
    transcriptText = normalizeTranscriptText(rawText);
    const clipped = rawText.length > transcriptText.length ? " · 已截取前 50000 字" : "";
    transcriptMeta.textContent = `${file.name} · ${formatBytes(file.size)} · ${transcriptText.length} 字${clipped}`;
  } catch (error) {
    transcriptMeta.textContent = `转写读取失败：${error.message}`;
    transcriptText = "";
  }
}

async function runLocalWhisperAsr() {
  const localPath = currentLocalMediaPath();
  if (!localPath) {
    setStatus("缺少路径", "warn");
    resultText.textContent = "把大视频复制到项目 tmp 目录或 C:\\tmp，然后在这里填完整本地路径。";
    localAsrPathInput.focus();
    return;
  }
  cacheSettings();
  setAsrBusy(true);
  setStatus("本地 ASR 中", "warn");
  resultText.textContent = [
    "本地 Whisper 正在读取磁盘文件并转写。",
    "首次使用某个模型会下载模型权重，会慢一些。",
    "长视频会阻塞一段时间，先别刷新页面。",
  ].join("\n");
  try {
    const response = await fetch("/api/multimodal/local-asr", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        local_path: localPath,
        local_model: localAsrModelInput.value,
        compute_type: localAsrComputeInput.value,
        language: localAsrLanguageInput.value || "zh",
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "本地 Whisper 转写失败");
    const text = data.result?.text || "";
    appendTranscriptToTimeline("本地 Whisper 转写", text);
    transcriptMeta.textContent = `本地 Whisper 完成 · ${data.result?.model || "--"} · ${transcriptText.length} 字`;
    resultText.textContent = [
      transcriptText || "本地 Whisper 完成，但没有识别到文字。",
      data.result?.saved_path ? `\n保存位置：${data.result.saved_path}` : "",
    ]
      .filter(Boolean)
      .join("\n");
    setStatus("本地 ASR 完成", "ok");
  } catch (error) {
    setStatus("本地 ASR 失败", "error");
    resultText.textContent = `本地 ASR 失败：${error.message}`;
  } finally {
    setAsrBusy(false);
  }
}

async function refreshSpeakerProfiles() {
  try {
    const response = await fetch("/api/speaker-profiles");
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "声纹库读取失败");
    const profiles = data.result?.profiles || [];
    const dependency = data.result?.dependency;
    const dependencyText = dependency?.available ? "pyannote 已就绪" : `pyannote 未安装 · ${dependency?.install_hint || ""}`;
    const profileText = profiles.length
      ? profiles.map((profile) => `${profile.display_name || profile.id} · ${profile.embedding_dimensions || 0} 维`).join("；")
      : "暂无声纹身份";
    speakerProfileMeta.textContent = `${dependencyText} · ${profileText}`;
  } catch (error) {
    speakerProfileMeta.textContent = `声纹库状态读取失败：${error.message}`;
  }
}

async function enrollCurrentSpeaker() {
  const localPath = currentLocalMediaPath();
  if (!localPath) {
    setStatus("缺少路径", "warn");
    resultText.textContent = "先填入一个本地视频/音频路径，再用这段材料登记声纹。";
    localAsrPathInput.focus();
    return;
  }
  const displayName = speakerDisplayNameInput.value.trim() || "我";
  cacheSettings();
  setAsrBusy(true);
  setStatus("声纹登记中", "warn");
  resultText.textContent = "正在从当前音频提取声纹向量，并写入本地声纹身份库。";
  try {
    const response = await fetch("/api/speaker-profiles/enroll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        local_path: localPath,
        display_name: displayName,
        role: displayName === "我" ? "self" : "contact",
        hf_token: hfTokenInput.value.trim(),
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "声纹登记失败");
    const profile = data.result?.profile || {};
    speakerProfileMeta.textContent = `已登记：${profile.display_name || profile.id} · ${profile.embedding_dimensions || 0} 维 · ${data.result?.path || ""}`;
    resultText.textContent = `声纹登记完成：${profile.display_name || profile.id}\n保存位置：${data.result?.path || ""}`;
    setStatus("声纹已登记", "ok");
  } catch (error) {
    setStatus("声纹登记失败", "error");
    resultText.textContent = `声纹登记失败：${error.message}`;
  } finally {
    setAsrBusy(false);
    refreshSpeakerProfiles();
  }
}

async function runDiarizedAsr() {
  const localPath = currentLocalMediaPath();
  const provider = asrProviderInput.value || "volcengine";
  const useVolcengine = provider === "volcengine";
  const useFunasr = provider === "funasr";
  if (!useVolcengine && !localPath) {
    setStatus("缺少路径", "warn");
    resultText.textContent = "先填入本地视频/音频路径。长期 ASR 会直接从磁盘读取大文件。";
    localAsrPathInput.focus();
    return;
  }
  if (useVolcengine && !volcengineAudioUrlInput.value.trim()) {
    setStatus("缺少火山 URL", "warn");
    resultText.textContent = "火山引擎需要一个公网可访问的音视频 URL；本地 C:\\tmp 路径不能直接提交给云端。";
    volcengineAudioUrlInput.focus();
    return;
  }
  if (useVolcengine && (!volcengineAppIdInput.value.trim() || !volcengineTokenInput.value.trim())) {
    setStatus("缺少火山凭证", "warn");
    resultText.textContent = "火山引擎模式需要填写 AppID 和 Access Token。";
    (!volcengineAppIdInput.value.trim() ? volcengineAppIdInput : volcengineTokenInput).focus();
    return;
  }
  cacheSettings();
  setAsrBusy(true);
  setStatus("说话人分离中", "warn");
  resultText.textContent = [
    useVolcengine
      ? "正在启动火山引擎 ASR：云端转写并返回说话人分离结果。"
      : useFunasr
        ? "正在启动 FunASR 本地 ASR：本地转写、VAD、标点，并尝试返回说话人分段。"
      : "正在跑长期 ASR：pyannote 先分离说话人，Whisper 再转写并按时间对齐。",
    "长视频会等待较久，后台任务会持续轮询状态。",
  ].join("\n");
  try {
    const response = await fetch("/api/multimodal/diarized-asr-job", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        local_path: localPath,
        local_model: localAsrModelInput.value,
        compute_type: localAsrComputeInput.value,
        language: localAsrLanguageInput.value || "zh",
        hf_token: hfTokenInput.value.trim(),
        asr_provider: provider,
        volcengine_app_id: volcengineAppIdInput.value.trim(),
        volcengine_token: volcengineTokenInput.value.trim(),
        volcengine_cluster: volcengineClusterInput.value.trim(),
        volcengine_audio_url: volcengineAudioUrlInput.value.trim(),
        funasr_model: funasrModelInput.value.trim(),
        funasr_vad_model: funasrVadModelInput.value.trim(),
        funasr_punc_model: funasrPuncModelInput.value.trim(),
        funasr_spk_model: funasrSpkModelInput.value.trim(),
        funasr_batch_size_s: Number(funasrBatchSizeInput.value || 300),
        funasr_hotword: funasrHotwordInput.value.trim(),
      }),
    });
    const jobData = await response.json();
    if (!jobData.ok) throw new Error(jobData.error || "说话人分离 ASR 启动失败");
    const jobId = jobData.result?.id;
    if (!jobId) throw new Error("说话人分离 ASR 启动失败：没有返回任务 ID");
    let job = jobData.result;
    resultText.textContent = `后台任务已启动：${jobId}\n${job.stage || job.status || "排队中"}`;
    while (job.status !== "completed" && job.status !== "failed") {
      await delay(3000);
      const pollResponse = await fetch(`/api/multimodal/asr-jobs/${encodeURIComponent(jobId)}`);
      const pollData = await pollResponse.json();
      if (!pollData.ok) throw new Error(pollData.error || "说话人分离 ASR 状态读取失败");
      job = pollData.result || {};
      resultText.textContent = [
        `后台任务：${jobId}`,
        `状态：${job.status || "--"}`,
        `阶段：${job.stage || "--"}`,
        "长视频会持续较久，可以保持页面打开等待结果。",
      ].join("\n");
    }
    if (job.status === "failed") throw new Error(job.error || "说话人分离 ASR 失败");
    const asrResult = job.result || {};
    const text = asrResult.text || "";
    appendTranscriptToTimeline("说话人分离 ASR", text);
    const speakers = asrResult.speakers || [];
    transcriptMeta.textContent = `说话人分离 ASR 完成 · ${speakers.length} 个说话人 · ${transcriptText.length} 字`;
    resultText.textContent = [
      "说话人：",
      speakerSummaryText(speakers),
      "",
      transcriptText || "ASR 完成，但没有识别到文字。",
      asrResult.saved_path ? `\n保存位置：${asrResult.saved_path}` : "",
    ]
      .filter(Boolean)
      .join("\n");
    setStatus("分离 ASR 完成", "ok");
  } catch (error) {
    setStatus("分离 ASR 失败", "error");
    resultText.textContent = `说话人分离 ASR 失败：${error.message}`;
  } finally {
    setAsrBusy(false);
    refreshSpeakerProfiles();
  }
}

clearPoeApiKeyButton.addEventListener("click", () => {
  poeApiKeyInput.value = "";
  cacheSettings();
  poeApiKeyInput.focus();
});
poeApiKeyInput.addEventListener("change", cacheSettings);
poeApiKeyInput.addEventListener("blur", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("blur", cacheSettings);
localAsrPathInput.addEventListener("change", cacheSettings);
localAsrPathInput.addEventListener("blur", cacheSettings);
localAsrModelInput.addEventListener("change", cacheSettings);
localAsrModelInput.addEventListener("blur", cacheSettings);
asrProviderInput.addEventListener("change", () => {
  updateAsrProviderPanels();
  cacheSettings();
});
volcengineAppIdInput.addEventListener("change", cacheSettings);
volcengineAppIdInput.addEventListener("blur", cacheSettings);
volcengineTokenInput.addEventListener("change", cacheSettings);
volcengineTokenInput.addEventListener("blur", cacheSettings);
volcengineClusterInput.addEventListener("change", cacheSettings);
volcengineClusterInput.addEventListener("blur", cacheSettings);
volcengineAudioUrlInput.addEventListener("change", cacheSettings);
volcengineAudioUrlInput.addEventListener("blur", cacheSettings);
funasrModelInput.addEventListener("change", cacheSettings);
funasrModelInput.addEventListener("blur", cacheSettings);
funasrVadModelInput.addEventListener("change", cacheSettings);
funasrVadModelInput.addEventListener("blur", cacheSettings);
funasrPuncModelInput.addEventListener("change", cacheSettings);
funasrPuncModelInput.addEventListener("blur", cacheSettings);
funasrSpkModelInput.addEventListener("change", cacheSettings);
funasrSpkModelInput.addEventListener("blur", cacheSettings);
funasrBatchSizeInput.addEventListener("change", cacheSettings);
funasrBatchSizeInput.addEventListener("blur", cacheSettings);
funasrHotwordInput.addEventListener("change", cacheSettings);
funasrHotwordInput.addEventListener("blur", cacheSettings);
hfTokenInput.addEventListener("change", cacheSettings);
hfTokenInput.addEventListener("blur", cacheSettings);
speakerDisplayNameInput.addEventListener("change", cacheSettings);
speakerDisplayNameInput.addEventListener("blur", cacheSettings);
mediaFileInput.addEventListener("change", onFileSelected);
transcriptFileInput.addEventListener("change", onTranscriptSelected);
extractButton.addEventListener("click", extractFrames);
localAsrButton.addEventListener("click", runLocalWhisperAsr);
enrollSpeakerButton.addEventListener("click", enrollCurrentSpeaker);
diarizedAsrButton.addEventListener("click", runDiarizedAsr);
analyzeButton.addEventListener("click", analyzeMaterial);
clearButton.addEventListener("click", clearAll);
confirmSelectedButton.addEventListener("click", confirmSelectedCandidates);

restoreSettings();
refreshSpeakerProfiles();
renderFrames();
