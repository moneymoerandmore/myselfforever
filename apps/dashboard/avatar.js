const poeApiKeyInput = document.querySelector("#poeApiKey");
const poeModelInput = document.querySelector("#poeModel");
const clearPoeApiKeyButton = document.querySelector("#clearPoeApiKey");
const healthStatus = document.querySelector("#healthStatus");
const personSelect = document.querySelector("#personSelect");
const intentInput = document.querySelector("#intent");
const modeInput = document.querySelector("#mode");
const scenarioInput = document.querySelector("#scenario");
const contextTextInput = document.querySelector("#contextText");
const relationName = document.querySelector("#relationName");
const relationSubtitle = document.querySelector("#relationSubtitle");
const permissionSummary = document.querySelector("#permissionSummary");
const dyadicSummary = document.querySelector("#dyadicSummary");
const refreshButton = document.querySelector("#refreshButton");
const renderButton = document.querySelector("#renderButton");
const providerSummary = document.querySelector("#providerSummary");
const providerBadge = document.querySelector("#providerBadge");
const providerGrid = document.querySelector("#providerGrid");
const jobSummary = document.querySelector("#jobSummary");
const jobBadge = document.querySelector("#jobBadge");
const replyText = document.querySelector("#replyText");
const avatarLiveStream = document.querySelector("#avatarLiveStream");
const avatarSyncCanvas = document.querySelector("#avatarSyncCanvas");
const avatarAudio = document.querySelector("#avatarAudio");
const avatarVideo = document.querySelector("#avatarVideo");
const jobsList = document.querySelector("#jobsList");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";

let people = [];
let activeJobId = null;
let activeJobTimer = null;
let currentStreamWorkerUrl = "";
let currentSyncSessionId = "";
let syncPlaybackTimer = null;
let syncObjectUrl = "";
let realtimeAnimationTimer = null;
let realtimeSpeaking = false;
let realtimeMouthLevel = 0;
let realtimeChunkAudios = [];

const realtimeFaceRig = {
  focusX: 0.345,
  focusY: 0.55,
  zoom: 2.05,
  mouthX: 0.345,
  mouthY: 0.525,
  mouthWidth: 0.034,
};

const realtimePortrait = new Image();
realtimePortrait.src = `/api/avatar/portrait?t=${Date.now()}`;
realtimePortrait.onload = () => {
  if (!avatarSyncCanvas.hidden) drawRealtimeAvatar();
};

function setHealth(ok, text) {
  healthStatus.textContent = text;
  healthStatus.classList.toggle("ok", ok);
  healthStatus.classList.toggle("error", !ok);
}

function setBadge(element, status) {
  element.textContent = status || "--";
  element.className = "risk";
  if (!status) element.classList.add("risk-idle");
  else if (status === "completed") element.classList.add("risk-r0");
  else if (status.startsWith("needs_")) element.classList.add("risk-r2");
  else if (status.includes("failed") || status.includes("timeout")) element.classList.add("risk-r3");
  else element.classList.add("risk-r1");
}

function compactText(value, fallback = "--") {
  const text = String(value || "").trim();
  return text || fallback;
}

function restoreSettings() {
  try {
    poeApiKeyInput.value = localStorage.getItem(POE_API_KEY_STORAGE_KEY) || "";
    poeModelInput.value = localStorage.getItem(POE_MODEL_STORAGE_KEY) || poeModelInput.value;
  } catch {
    // Browser storage may be disabled.
  }
}

function cacheSettings() {
  try {
    const apiKey = poeApiKeyInput.value.trim();
    const model = poeModelInput.value.trim();
    if (apiKey) localStorage.setItem(POE_API_KEY_STORAGE_KEY, apiKey);
    else localStorage.removeItem(POE_API_KEY_STORAGE_KEY);
    if (model) localStorage.setItem(POE_MODEL_STORAGE_KEY, model);
  } catch {
    // Keep visible values for this page session.
  }
}

function clearPoeKey() {
  poeApiKeyInput.value = "";
  try {
    localStorage.removeItem(POE_API_KEY_STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
  poeApiKeyInput.focus();
}

function selectedPerson() {
  return people.find((person) => person.id === personSelect.value) || null;
}

function contextHistory() {
  return contextTextInput.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-40)
    .map((line) => {
      const normalized = line
        .replace(/^我[:：]/, "self:")
        .replace(/^对方[:：]/, "contact:")
        .replace(/^self[:：]/i, "self:")
        .replace(/^contact[:：]/i, "contact:");
      if (normalized.startsWith("self:")) return { role: "self", content: normalized.slice(5).trim() };
      if (normalized.startsWith("contact:")) return { role: "contact", content: normalized.slice(8).trim() };
      return { role: "contact", content: line };
    });
}

function avatarConversationHistory() {
  const history = contextHistory();
  const scenario = scenarioInput.value.trim();
  if (scenario) history.push({ role: "contact", content: scenario });
  return history.slice(-40);
}

function renderRelationProfile() {
  const person = selectedPerson();
  if (!person) {
    relationName.textContent = "未选择联系人";
    relationSubtitle.textContent = "关系图谱画像会显示在这里";
    permissionSummary.textContent = "--";
    dyadicSummary.textContent = "--";
    modeInput.disabled = false;
    return;
  }

  const permission = person.permission || {};
  const dyadic = person.dyadic_profile || {};
  relationName.textContent = person.display_name || person.query || "未命名联系人";
  relationSubtitle.textContent = [
    compactText(person.objective_relationship, "关系未知"),
    compactText(person.node_type, "节点类型未知"),
    `样本 ${person.communication_total || 0} 条`,
    `日均 ${Number(person.communication_daily_average || 0).toFixed(2)} 条`,
  ].join(" / ");
  permissionSummary.textContent = [
    permission.note || "--",
    `生成草稿：${permission.can_generate_draft ? "是" : "否"}`,
    `主动建议：${permission.can_proactively_suggest ? "是" : "否"}`,
    `自动发送：${permission.can_auto_send ? "是" : "否"}`,
  ].join("；");
  dyadicSummary.textContent = dyadic.available
    ? [
        `双人画像：${dyadic.confidence_level}`,
        `私聊 ${dyadic.private_outgoing_count}/${dyadic.private_incoming_count}`,
        `均/中位字数 ${dyadic.average_chars}/${dyadic.median_chars}`,
        `话题 ${(dyadic.top_topics || []).join("、") || "不足"}`,
      ].join("；")
    : "暂无可用双人定向画像，生成时必须保守，不用关系大类模板脑补。";

  if (person.group === "direct" && permission.can_generate_draft !== false) {
    modeInput.disabled = false;
  } else {
    modeInput.value = "observe";
    modeInput.disabled = true;
  }
}

function renderPeopleOptions() {
  personSelect.innerHTML = "";
  if (!people.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No contacts";
    personSelect.appendChild(option);
    renderRelationProfile();
    return;
  }
  for (const person of people) {
    const option = document.createElement("option");
    option.value = person.id;
    option.textContent = `${person.display_name || person.query} / ${person.category || "uncategorized"}`;
    personSelect.appendChild(option);
  }
  renderRelationProfile();
}

async function loadPeople() {
  const response = await fetch("/api/people");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "people read failed");
  people = data.people || [];
  renderPeopleOptions();
}

function providerItem(title, ready, detail) {
  const item = document.createElement("article");
  item.className = `avatar-status-item ${ready ? "avatar-status-ready" : "avatar-status-missing"}`;
  item.innerHTML = `<strong>${title}</strong><span>${detail}</span>`;
  return item;
}

function workerText(worker) {
  if (!worker?.configured) return "worker not configured";
  return worker.ok ? `worker ok, load ${worker.result?.model_load_seconds || 0}s` : `worker down: ${worker.error || "unknown"}`;
}

function renderProviderStatus(status) {
  const sourceReady = Boolean(status.source_image?.configured && status.source_image?.exists);
  const baseReady = Boolean(status.base_video?.configured && status.base_video?.exists);
  const streamReady = Boolean(status.stream?.configured && status.stream?.worker?.ok && status.stream?.idle_stream_url);
  currentStreamWorkerUrl = status.stream?.worker_url || "";
  const ttsReady = Boolean(status.tts?.configured);
  const lipsyncReady = Boolean(status.lipsync?.configured);
  const speechReady = "speechSynthesis" in window;
  const realtimeReady = sourceReady && speechReady;
  const allReady = realtimeReady;
  providerBadge.textContent = allReady ? "ready" : "missing";
  providerBadge.className = `mode-badge ${allReady ? "mode-ok" : "mode-warn"}`;
  providerSummary.textContent = allReady
    ? "形象层已进入永续直播态；表达内容仍由关系图谱交流内核生成。"
    : "形象层需要头像、永续直播流、TTS、基础视频或渲染器、口型模块。";
  if (streamReady) {
    const streamUrl = `${status.stream.idle_stream_url}?t=${Date.now()}`;
    if (avatarLiveStream.src !== streamUrl) avatarLiveStream.src = streamUrl;
    avatarLiveStream.hidden = Boolean(currentSyncSessionId);
  } else {
    avatarLiveStream.hidden = true;
    avatarLiveStream.removeAttribute("src");
  }
  providerGrid.innerHTML = "";
  providerGrid.append(
    providerItem("Realtime lane", realtimeReady, speechReady ? "browser speech + lightweight mouth motion" : "browser speech unavailable"),
    providerItem("Portrait", sourceReady, sourceReady ? status.source_image.path : "set DIGITAL_TWIN_AVATAR_IMAGE"),
    providerItem("Idle stream", streamReady, streamReady ? status.stream.idle_stream_url : "optional idle surface"),
    providerItem("Fidelity base", baseReady, baseReady ? "cached base video enabled" : "optional offline render"),
    providerItem("Fidelity TTS", ttsReady, status.tts?.worker_url ? workerText(status.tts.worker) : "optional command mode"),
    providerItem("Fidelity LipSync", lipsyncReady, status.lipsync?.worker_url ? workerText(status.lipsync.worker) : "optional command mode"),
  );
}

function stopSynchronizedPlayback() {
  if (syncPlaybackTimer) clearTimeout(syncPlaybackTimer);
  syncPlaybackTimer = null;
  currentSyncSessionId = "";
  if (syncObjectUrl) URL.revokeObjectURL(syncObjectUrl);
  syncObjectUrl = "";
  avatarSyncCanvas.hidden = true;
  avatarLiveStream.hidden = !avatarLiveStream.src;
  avatarAudio.hidden = true;
  avatarVideo.hidden = true;
}

function stopRealtimePlayback() {
  if (realtimeAnimationTimer) clearTimeout(realtimeAnimationTimer);
  realtimeAnimationTimer = null;
  realtimeSpeaking = false;
  realtimeMouthLevel = 0;
  avatarAudio.pause();
  realtimeChunkAudios.forEach((audio) => audio.pause());
  realtimeChunkAudios = [];
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

function realtimePortraitGeometry(width, height) {
  const baseScale = Math.max(width / realtimePortrait.naturalWidth, height / realtimePortrait.naturalHeight);
  const scale = baseScale * realtimeFaceRig.zoom;
  const drawWidth = realtimePortrait.naturalWidth * scale;
  const drawHeight = realtimePortrait.naturalHeight * scale;
  const drawX = width / 2 - realtimeFaceRig.focusX * drawWidth;
  const drawY = height / 2 - realtimeFaceRig.focusY * drawHeight;
  return { drawX, drawY, drawWidth, drawHeight };
}

function portraitPoint(geometry, imageX, imageY) {
  return {
    x: geometry.drawX + imageX * geometry.drawWidth,
    y: geometry.drawY + imageY * geometry.drawHeight,
  };
}

function drawRealtimeMouth(context, x, y, width, openness) {
  const open = Math.max(0, Math.min(1, openness));
  const mouthWidth = width;
  const mouthHeight = 2 + open * 14;
  const smile = 3 + open * 2;
  const cornerLift = 1.5 - open * 1.2;

  context.save();
  context.globalAlpha = 0.2;
  context.fillStyle = "rgba(84, 42, 35, 0.34)";
  context.beginPath();
  context.ellipse(x, y + 5, mouthWidth * 0.45, mouthHeight * 0.42 + 5, 0, 0, Math.PI * 2);
  context.fill();

  context.globalAlpha = 0.8;
  context.fillStyle = `rgba(35, 14, 16, ${0.25 + open * 0.35})`;
  context.beginPath();
  context.moveTo(x - mouthWidth / 2, y + cornerLift);
  context.bezierCurveTo(x - mouthWidth * 0.25, y - mouthHeight * 0.42, x + mouthWidth * 0.25, y - mouthHeight * 0.42, x + mouthWidth / 2, y + cornerLift);
  context.bezierCurveTo(x + mouthWidth * 0.3, y + mouthHeight * 0.62, x - mouthWidth * 0.3, y + mouthHeight * 0.62, x - mouthWidth / 2, y + cornerLift);
  context.closePath();
  context.fill();

  context.strokeStyle = "rgba(96, 45, 43, 0.9)";
  context.lineWidth = 3;
  context.lineCap = "round";
  context.beginPath();
  context.moveTo(x - mouthWidth / 2, y + cornerLift);
  context.bezierCurveTo(x - mouthWidth * 0.23, y - smile, x + mouthWidth * 0.23, y - smile, x + mouthWidth / 2, y + cornerLift);
  context.stroke();

  context.strokeStyle = "rgba(210, 132, 118, 0.38)";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(x - mouthWidth * 0.38, y - 3);
  context.bezierCurveTo(x - mouthWidth * 0.12, y - 8, x + mouthWidth * 0.12, y - 8, x + mouthWidth * 0.38, y - 3);
  context.stroke();

  if (open > 0.55) {
    context.globalAlpha = 0.18 * open;
    context.fillStyle = "rgba(235, 220, 205, 0.85)";
    context.fillRect(x - mouthWidth * 0.25, y - mouthHeight * 0.12, mouthWidth * 0.5, Math.max(1.5, mouthHeight * 0.08));
  }
  context.restore();
}

function drawRealtimeAvatar() {
  const canvas = avatarSyncCanvas;
  const context = canvas.getContext("2d");
  const width = 960;
  const height = 540;
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  context.fillStyle = "#101418";
  context.fillRect(0, 0, width, height);

  let mouthPoint = { x: width / 2, y: height * 0.58 };
  let mouthWidth = 68;
  if (realtimePortrait.complete && realtimePortrait.naturalWidth) {
    const geometry = realtimePortraitGeometry(width, height);
    context.drawImage(realtimePortrait, geometry.drawX, geometry.drawY, geometry.drawWidth, geometry.drawHeight);
    mouthPoint = portraitPoint(geometry, realtimeFaceRig.mouthX, realtimeFaceRig.mouthY);
    mouthWidth = geometry.drawWidth * realtimeFaceRig.mouthWidth;

    const jawOpen = realtimeSpeaking ? realtimeMouthLevel : 0;
    context.save();
    context.beginPath();
    context.ellipse(mouthPoint.x, mouthPoint.y + 23, mouthWidth * 1.15, 38, 0, 0, Math.PI * 2);
    context.clip();
    context.globalAlpha = 0.22 * jawOpen;
    context.drawImage(realtimePortrait, geometry.drawX, geometry.drawY + jawOpen * 7, geometry.drawWidth, geometry.drawHeight);
    context.restore();
  }

  const pulse = realtimeSpeaking ? 0.18 + realtimeMouthLevel * 0.82 : 0.03;
  drawRealtimeMouth(context, mouthPoint.x, mouthPoint.y, mouthWidth, pulse);

  if (realtimeSpeaking) {
    realtimeMouthLevel = realtimeMouthLevel * 0.35 + Math.random() * 0.65;
    realtimeAnimationTimer = setTimeout(drawRealtimeAvatar, 70);
  }
}

function withCacheBust(url) {
  const cacheJoiner = url.includes("?") ? "&" : "?";
  return `${url}${cacheJoiner}t=${Date.now()}`;
}

function playRealtimeAudioElement(audio, syncSessionId = "") {
  return new Promise((resolve, reject) => {
    let syncStopped = false;
    const stopSync = () => {
      syncStopped = true;
      if (syncPlaybackTimer) clearTimeout(syncPlaybackTimer);
      syncPlaybackTimer = null;
    };
    const tickSyncFrame = async () => {
      if (syncStopped || !syncSessionId || !currentStreamWorkerUrl) return;
      try {
        await drawSyncFrame(syncSessionId, audio.currentTime * 1000);
      } catch {
        // The next poll usually catches up while MuseTalk is still pushing frames.
      }
      if (!syncStopped && !audio.ended) syncPlaybackTimer = setTimeout(tickSyncFrame, 40);
    };
    audio.onplay = () => {
      realtimeSpeaking = true;
      if (syncSessionId && currentStreamWorkerUrl) {
        currentSyncSessionId = syncSessionId;
        avatarSyncCanvas.hidden = false;
        avatarLiveStream.hidden = true;
        tickSyncFrame();
      } else {
        drawRealtimeAvatar();
      }
    };
    audio.onended = () => {
      stopSync();
      resolve();
    };
    audio.onerror = () => {
      stopSync();
      reject(new Error("clone voice chunk failed"));
    };
    const start = async () => {
      if (syncSessionId && currentStreamWorkerUrl) {
        avatarSyncCanvas.hidden = false;
        avatarLiveStream.hidden = true;
        await waitForSyncBuffer(syncSessionId, 1, 2600);
        await drawSyncFrame(syncSessionId, 0).catch(() => {});
      }
      await audio.play();
    };
    start().catch((error) => {
      stopSync();
      reject(error);
    });
  });
}

async function playRealtimeAudioChunks(text, audioChunks) {
  const chunks = audioChunks.filter((chunk) => chunk?.audio_url);
  realtimeChunkAudios = chunks.map((chunk) => {
    const audio = new Audio(withCacheBust(chunk.audio_url));
    audio.preload = "auto";
    return audio;
  });
  if (realtimeChunkAudios[1]) realtimeChunkAudios[1].load();
  for (let index = 0; index < realtimeChunkAudios.length; index += 1) {
    const nextAudio = realtimeChunkAudios[index + 1];
    if (nextAudio) nextAudio.load();
    await playRealtimeAudioElement(realtimeChunkAudios[index], chunks[index]?.visual_session_id || "");
  }
  currentSyncSessionId = "";
  realtimeSpeaking = false;
  if (!chunks.some((chunk) => chunk?.visual_session_id)) drawRealtimeAvatar();
}

async function speakRealtimeText(text, audioUrl = "", audioChunks = [], visualDriver = {}) {
  stopRealtimePlayback();
  const normalizedVisualDriver = typeof visualDriver === "string" ? { stream_url: visualDriver } : (visualDriver || {});
  const visualStreamUrl = normalizedVisualDriver.stream_url || "";
  const syncEnabled = Boolean(
    normalizedVisualDriver.sync_mode === "per_audio_chunk"
      && (normalizedVisualDriver.stream_worker_url || currentStreamWorkerUrl)
      && audioChunks.some((chunk) => chunk?.visual_session_id),
  );
  if (normalizedVisualDriver.stream_worker_url) currentStreamWorkerUrl = normalizedVisualDriver.stream_worker_url;
  avatarSyncCanvas.hidden = !syncEnabled && Boolean(visualStreamUrl);
  avatarLiveStream.hidden = syncEnabled || !visualStreamUrl;
  if (!syncEnabled && visualStreamUrl) avatarLiveStream.src = withCacheBust(visualStreamUrl);
  avatarVideo.hidden = true;
  avatarAudio.hidden = true;
  avatarAudio.controls = false;
  realtimeSpeaking = true;
  realtimeMouthLevel = 0.35;
  if (!visualStreamUrl && !syncEnabled) drawRealtimeAvatar();

  if (audioChunks.length) {
    try {
      await playRealtimeAudioChunks(text, audioChunks);
      return;
    } catch {
      setHealth(false, "clone voice stream failed; falling back to browser speech");
      speakRealtimeText(text);
      return;
    }
  }

  if (audioUrl) {
    avatarAudio.src = withCacheBust(audioUrl);
    avatarAudio.onplay = () => {
      realtimeSpeaking = true;
      if (!syncEnabled) drawRealtimeAvatar();
    };
    avatarAudio.onended = () => {
      realtimeSpeaking = false;
      if (!syncEnabled) drawRealtimeAvatar();
    };
    avatarAudio.onerror = () => {
      setHealth(false, "clone voice failed; falling back to browser speech");
      speakRealtimeText(text);
    };
    try {
      await avatarAudio.play();
      return;
    } catch {
      setHealth(false, "Clone voice is ready. Click the avatar once to allow playback.");
      return;
    }
  }

  if (!("speechSynthesis" in window)) {
    setTimeout(() => {
      realtimeSpeaking = false;
      if (!visualStreamUrl) drawRealtimeAvatar();
    }, Math.max(900, text.length * 150));
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = 1.18;
  utterance.pitch = 1.0;
  const voices = window.speechSynthesis.getVoices();
  const zhVoice = voices.find((voice) => /zh|Chinese|中文/i.test(`${voice.lang} ${voice.name}`));
  if (zhVoice) utterance.voice = zhVoice;
  utterance.onboundary = () => {
    realtimeMouthLevel = Math.random();
  };
  utterance.onend = () => {
    realtimeSpeaking = false;
    if (!visualStreamUrl && !syncEnabled) drawRealtimeAvatar();
  };
  utterance.onerror = () => {
    realtimeSpeaking = false;
    if (!visualStreamUrl && !syncEnabled) drawRealtimeAvatar();
  };
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

async function syncStatus(sessionId) {
  if (!currentStreamWorkerUrl || !sessionId) return null;
  const response = await fetch(`${currentStreamWorkerUrl}/sync-status?session_id=${encodeURIComponent(sessionId)}`);
  if (!response.ok) return null;
  return response.json();
}

async function drawSyncFrame(sessionId, timeMs) {
  const response = await fetch(
    `${currentStreamWorkerUrl}/sync-frame?session_id=${encodeURIComponent(sessionId)}&t=${Math.max(0, Math.floor(timeMs))}`,
    { cache: "no-store" },
  );
  if (!response.ok) return false;
  const blob = await response.blob();
  const bitmap = await createImageBitmap(blob);
  const canvas = avatarSyncCanvas;
  const context = canvas.getContext("2d");
  if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
  }
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return true;
}

async function waitForSyncBuffer(sessionId, minFrames = 8, timeoutMs = 12000) {
  const started = performance.now();
  while (performance.now() - started < timeoutMs) {
    const status = await syncStatus(sessionId);
    if (status?.ok && (status.frame_count >= minFrames || status.complete)) return status;
    await new Promise((resolve) => setTimeout(resolve, 180));
  }
  return null;
}

async function startSynchronizedPlayback(job) {
  const sessionId = job.id;
  if (!currentStreamWorkerUrl || !job.files?.audio || currentSyncSessionId === sessionId) return;
  currentSyncSessionId = sessionId;
  if (syncPlaybackTimer) clearTimeout(syncPlaybackTimer);
  avatarSyncCanvas.hidden = false;
  avatarLiveStream.hidden = true;
  avatarAudio.hidden = true;
  avatarAudio.controls = false;
  avatarAudio.src = `${job.files.audio}?t=${Date.now()}`;

  const buffered = await waitForSyncBuffer(sessionId);
  if (currentSyncSessionId !== sessionId) return;
  if (!buffered?.ok) {
    setHealth(false, "sync frames are not ready yet");
    return;
  }

  const tick = async () => {
    if (currentSyncSessionId !== sessionId) return;
    const ok = await drawSyncFrame(sessionId, avatarAudio.currentTime * 1000);
    if (!ok && !avatarAudio.paused) avatarAudio.pause();
    if (ok && avatarAudio.paused && !avatarAudio.ended) {
      try {
        await avatarAudio.play();
      } catch {
        setHealth(false, "Audio is ready. Click the avatar once to continue unified playback.");
      }
    }
    if (avatarAudio.ended) {
      syncPlaybackTimer = null;
      return;
    }
    syncPlaybackTimer = setTimeout(tick, 40);
  };

  try {
    await drawSyncFrame(sessionId, 0);
    await avatarAudio.play();
  } catch {
    setHealth(false, "Audio is ready. Click the avatar once to continue unified playback.");
  }
  tick();
}

async function resumeUnifiedPlayback() {
  if (!avatarAudio.src || !avatarAudio.paused || avatarAudio.ended) return;
  try {
    await avatarAudio.play();
    setHealth(true, "unified avatar playback resumed");
  } catch (error) {
    setHealth(false, error.message);
  }
}

async function loadProviderStatus() {
  const response = await fetch("/api/avatar/status");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "avatar status failed");
  renderProviderStatus(data.result);
}

function renderJobs(jobs) {
  jobsList.innerHTML = "";
  if (!jobs.length) {
    jobsList.innerHTML = '<div class="empty-list">No jobs yet</div>';
    return;
  }
  for (const job of jobs) {
    const item = document.createElement("article");
    item.className = "avatar-job";
    const videoLink = job.files?.video ? `<a href="${job.files.video}" target="_blank" rel="noreferrer">video</a>` : "";
    const audioLink = job.files?.audio ? `<a href="${job.files.audio}" target="_blank" rel="noreferrer">audio</a>` : "";
    item.innerHTML = `
      <div>
        <strong>${job.created_at || job.id} / ${job.status}</strong>
        <p>${job.person_query || "unknown"}: ${(job.draft_text || "").slice(0, 90)}</p>
      </div>
      <div>${videoLink || audioLink || ""}</div>
    `;
    jobsList.appendChild(item);
  }
}

async function loadJobs() {
  const response = await fetch("/api/avatar/jobs?limit=10");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "jobs read failed");
  renderJobs(data.result?.jobs || []);
}

function terminalJobStatus(status) {
  return status === "completed" || status?.includes("failed") || status?.includes("timeout") || status?.startsWith("needs_");
}

function renderJob(job) {
  const metrics = job.metrics || {};
  const slowest = metrics.slowest_step;
  const draftResult = job.draft_result || {};
  const stepLines = (job.steps || []).flatMap((step) => {
    const lines = [`${step.name}: ${step.mode || "command"}, code=${step.returncode}, ${step.duration_seconds}s`];
    const timings = step.worker_result?.timings;
    if (timings) {
      lines.push(
        `  audio_feature=${timings.audio_feature_seconds}s, model_frames=${timings.model_and_frame_seconds}s, encode=${timings.encode_seconds}s, mux=${timings.mux_seconds}s`,
      );
    }
    return lines;
  });
  jobSummary.textContent = job.message || `job ${job.id}`;
  setBadge(jobBadge, job.status);
  replyText.textContent = [
    job.draft_text || "",
    "",
    `status: ${job.status}`,
    job.message ? `message: ${job.message}` : "",
    draftResult.tone_basis ? `tone_basis: ${draftResult.tone_basis}` : "",
    draftResult.risk_level ? `risk: ${draftResult.risk_level}` : "",
    draftResult.relationship_basis ? `relationship: ${draftResult.relationship_basis}` : "",
    draftResult.topic_basis ? `topic: ${draftResult.topic_basis}` : "",
    draftResult.personality_guard?.status ? `personality_guard: ${draftResult.personality_guard.status}` : "",
    metrics.elapsed_seconds ? `elapsed: ${metrics.elapsed_seconds}s / target ${metrics.target_seconds || 2.5}s` : "",
    slowest ? `slowest: ${slowest.name}, ${slowest.duration_seconds}s` : "",
    metrics.latency_note ? `latency: ${metrics.latency_note}` : "",
    ...stepLines,
  ]
    .filter(Boolean)
    .join("\n");
  if (job.files?.audio && (job.status === "lipsyncing" || job.status === "completed")) {
    startSynchronizedPlayback(job).catch((error) => setHealth(false, error.message));
  } else if (job.files?.video && !currentSyncSessionId) {
    avatarVideo.hidden = false;
    avatarVideo.src = `${job.files.video}?t=${Date.now()}`;
  } else {
    avatarVideo.hidden = true;
    avatarVideo.removeAttribute("src");
  }
}

async function pollAvatarJob(jobId) {
  const response = await fetch(`/api/avatar/jobs/${jobId}`);
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "job read failed");
  const job = data.result;
  renderJob(job);
  await loadJobs();
  if (terminalJobStatus(job.status)) {
    if (activeJobTimer) clearInterval(activeJobTimer);
    activeJobTimer = null;
    activeJobId = null;
    renderButton.disabled = false;
    renderButton.textContent = "生成数字人回复";
    setHealth(job.status === "completed", job.status === "completed" ? "avatar job completed" : job.message || job.status);
  }
}

function startAvatarJobPolling(jobId) {
  activeJobId = jobId;
  if (activeJobTimer) clearInterval(activeJobTimer);
  activeJobTimer = setInterval(() => {
    if (!activeJobId) return;
    pollAvatarJob(activeJobId).catch((error) => setHealth(false, error.message));
  }, 900);
  pollAvatarJob(jobId).catch((error) => setHealth(false, error.message));
}

function resetPlayback() {
  if (activeJobTimer) clearInterval(activeJobTimer);
  activeJobTimer = null;
  activeJobId = null;
  stopRealtimePlayback();
  stopSynchronizedPlayback();
  avatarAudio.pause();
  avatarAudio.hidden = true;
  avatarAudio.removeAttribute("src");
  avatarVideo.hidden = true;
  avatarVideo.removeAttribute("src");
}

async function renderAvatarReply() {
  const person = selectedPerson();
  const apiKey = poeApiKeyInput.value.trim();
  const scenario = scenarioInput.value.trim();
  const history = avatarConversationHistory();
  if (!person) {
    setHealth(false, "select a contact first");
    personSelect.focus();
    return;
  }
  if (!apiKey) {
    setHealth(false, "enter Poe API key first");
    poeApiKeyInput.focus();
    return;
  }
  if (!scenario) {
    setHealth(false, "enter incoming message first");
    scenarioInput.focus();
    return;
  }
  cacheSettings();
  resetPlayback();
  renderButton.disabled = true;
  renderButton.textContent = "Thinking...";
  replyText.textContent = "Realtime lane: relationship graph drafts first; speech and mouth motion run locally without IndexTTS2/MuseTalk blocking.";
  setBadge(jobBadge, "running");
  try {
    const response = await fetch("/api/avatar/realtime-reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: person.query,
        scenario,
        conversation_history: history,
        poe_api_key: apiKey,
        poe_model: poeModelInput.value.trim(),
        intent: intentInput.value,
        mode: person.group === "direct" && person.permission?.can_generate_draft !== false ? modeInput.value : "observe",
        relationship_graph_surface: true,
        multimodal_output_surface: "avatar",
        latency_profile: "fast_avatar",
        streaming: true,
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "realtime avatar generation failed");
    renderJob(data.result);
    const cloneVoice = data.result.clone_voice || {};
    const visualDriver = cloneVoice.visual_driver || {};
    speakRealtimeText(
      data.result.draft_text || "",
      cloneVoice.audio_url || "",
      cloneVoice.audio_chunks || [],
      visualDriver.enabled ? visualDriver : {},
    );
    renderButton.disabled = false;
    renderButton.textContent = "生成数字人回复";
    const voiceStatus = cloneVoice.status || "";
    const voiceHealth =
      visualDriver.enabled
        ? "MuseTalk visual stream + cloned voice started"
        : voiceStatus === "streaming"
          ? ((cloneVoice.audio_chunks || []).length > 1 ? "chunked clone voice stream started" : "streaming clone voice started")
        : voiceStatus === "cached"
          ? "clone voice reply started"
          : "clone voice warming; browser voice used now";
    setHealth(true, voiceHealth);
  } catch (error) {
    replyText.textContent = `generation failed: ${error.message}`;
    jobSummary.textContent = "job failed";
    setBadge(jobBadge, "render_failed");
    setHealth(false, error.message);
    renderButton.disabled = false;
    renderButton.textContent = "生成数字人回复";
  }
}

async function refreshAll() {
  try {
    await Promise.all([loadProviderStatus(), loadJobs()]);
    setHealth(true, "connected");
  } catch (error) {
    setHealth(false, error.message);
  }
}

clearPoeApiKeyButton.addEventListener("click", clearPoeKey);
poeApiKeyInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);
refreshButton.addEventListener("click", refreshAll);
renderButton.addEventListener("click", renderAvatarReply);
personSelect.addEventListener("change", renderRelationProfile);
avatarSyncCanvas.addEventListener("click", resumeUnifiedPlayback);
avatarLiveStream.addEventListener("click", resumeUnifiedPlayback);

restoreSettings();
Promise.all([loadPeople(), refreshAll()]).catch((error) => setHealth(false, error.message));
