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
  const rendererReady = Boolean(baseReady || status.renderer?.configured);
  const lipsyncReady = Boolean(status.lipsync?.configured);
  const allReady = sourceReady && streamReady && ttsReady && rendererReady && lipsyncReady;
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
    providerItem("Portrait", sourceReady, sourceReady ? status.source_image.path : "set DIGITAL_TWIN_AVATAR_IMAGE"),
    providerItem("Live stream", streamReady, streamReady ? status.stream.idle_stream_url : "start avatar stream worker on :8813"),
    providerItem("Base video", baseReady, baseReady ? "cached base video enabled" : "will render with LivePortrait"),
    providerItem("TTS", ttsReady, status.tts?.worker_url ? workerText(status.tts.worker) : "command mode"),
    providerItem("LipSync", lipsyncReady, status.lipsync?.worker_url ? workerText(status.lipsync.worker) : "command mode"),
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
  avatarAudio.hidden = false;
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
        setHealth(false, "Audio is ready. Press play once to allow synchronized playback.");
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
    setHealth(false, "Audio is ready. Press play once to allow synchronized playback.");
  }
  tick();
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
  if (job.files?.video) {
    avatarVideo.hidden = false;
    avatarVideo.src = `${job.files.video}?t=${Date.now()}`;
  } else {
    avatarVideo.hidden = true;
    avatarVideo.removeAttribute("src");
  }
  if (job.files?.audio && terminalJobStatus(job.status)) {
    avatarAudio.hidden = false;
    avatarAudio.src = `${job.files.audio}?t=${Date.now()}`;
  }
  if (job.files?.audio && (job.status === "lipsyncing" || job.status === "completed")) {
    startSynchronizedPlayback(job).catch((error) => setHealth(false, error.message));
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
  renderButton.textContent = "Generating...";
  replyText.textContent = "Starting relationship-graph avatar job. Speaking output will be published back into the live stream when ready.";
  setBadge(jobBadge, "running");
  try {
    const response = await fetch("/api/avatar/reply", {
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
    if (!data.ok) throw new Error(data.error || "avatar generation failed");
    renderJob(data.result);
    startAvatarJobPolling(data.result.id);
    setHealth(true, "relationship graph avatar job started");
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

restoreSettings();
Promise.all([loadPeople(), refreshAll()]).catch((error) => setHealth(false, error.message));
