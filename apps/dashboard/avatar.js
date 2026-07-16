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
const speakButton = document.querySelector("#speakButton");
const runtimeSummary = document.querySelector("#runtimeSummary");
const providerBadge = document.querySelector("#providerBadge");
const runtimeBadge = document.querySelector("#runtimeBadge");
const providerGrid = document.querySelector("#providerGrid");
const runtimeFrame = document.querySelector("#runtimeFrame");
const runtimePlaceholder = document.querySelector("#runtimePlaceholder");
const avatarAudio = document.querySelector("#avatarAudio");
const jobSummary = document.querySelector("#jobSummary");
const jobBadge = document.querySelector("#jobBadge");
const replyText = document.querySelector("#replyText");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";

let people = [];
let runtimeStatus = null;
let visualSyncTimer = 0;

function setHealth(ok, text) {
  healthStatus.textContent = text;
  healthStatus.classList.toggle("ok", ok);
  healthStatus.classList.toggle("error", !ok);
}

function setBadge(element, status) {
  element.textContent = status || "--";
  element.className = "risk";
  if (!status) element.classList.add("risk-idle");
  else if (status === "ready" || status === "completed") element.classList.add("risk-r0");
  else if (status === "partial" || status === "configured" || status === "starting") element.classList.add("risk-r1");
  else if (status === "missing" || status === "failed") element.classList.add("risk-r2");
  else element.classList.add("risk-r3");
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
    // Keep visible form values as the source of truth for this session.
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
    // Storage may be blocked; the form still works.
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

function conversationHistory() {
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
        `中位字数 ${dyadic.median_chars}`,
        `话题 ${(dyadic.top_topics || []).join("、") || "不足"}`,
      ].join("；")
    : "暂无可用双人定向画像，生成时必须保守，不能用关系大类模板脑补。";

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
  if (!worker?.configured) return "not configured";
  if (worker.ok) return "ok";
  return `down: ${worker.error || "unknown"}`;
}

function renderRuntimeStatus(status) {
  runtimeStatus = status;
  const stream = status.stream || {};
  const voice = status.realtime_voice || {};
  const lipsync = status.lipsync || {};
  const tts = status.tts || {};
  const streamWorker = stream.worker || {};
  const lipsyncWorker = lipsync.worker || {};
  const ttsWorker = tts.worker || {};
  const streamReady = Boolean(stream.configured && streamWorker.ok && stream.idle_stream_url);
  const lipsyncReady = Boolean(lipsync.configured && lipsyncWorker.ok);
  const voiceReady = Boolean(voice.configured);
  const ttsReady = Boolean(tts.configured && (ttsWorker.ok || voice.provider === "indextts2"));
  const ready = streamReady && lipsyncReady && voiceReady && ttsReady;

  providerBadge.textContent = "musetalk";
  runtimeSummary.textContent = ready
    ? "MuseTalk、常驻 MJPEG 流和本地克隆语音都已接入。"
    : "MuseTalk 本地链路仍有未接入项。";
  setBadge(runtimeBadge, ready ? "ready" : streamReady || lipsyncReady || voiceReady ? "partial" : "missing");

  providerGrid.innerHTML = "";
  providerGrid.appendChild(providerItem("MuseTalk worker", lipsyncReady, `${lipsync.worker_url || "--"} / ${workerText(lipsyncWorker)}`));
  providerGrid.appendChild(providerItem("MJPEG stream", streamReady, stream.idle_stream_url || "stream worker not configured"));
  providerGrid.appendChild(providerItem("IndexTTS2 voice", voiceReady, `${voice.provider || "--"} / /api/avatar/streaming-voice`));
  providerGrid.appendChild(providerItem("TTS worker", ttsReady, `${tts.worker_url || "--"} / ${workerText(ttsWorker)}`));
  providerGrid.appendChild(providerItem("视觉路线", true, `${lipsync.provider || "musetalk"} / ${lipsync.mode || "realtime"}`));

  if (streamReady) {
    runtimeFrame.src = `${stream.idle_stream_url}${stream.idle_stream_url.includes("?") ? "&" : "?"}t=${Date.now()}`;
    runtimeFrame.hidden = false;
    runtimePlaceholder.hidden = true;
  } else {
    runtimeFrame.removeAttribute("src");
    runtimeFrame.hidden = true;
    runtimePlaceholder.hidden = false;
  }
}

function idleStreamUrl() {
  const url = runtimeStatus?.stream?.idle_stream_url || "";
  if (!url) return "";
  return `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`;
}

function showIdleStream() {
  const url = idleStreamUrl();
  if (!url) return;
  runtimeFrame.src = url;
  runtimeFrame.hidden = false;
  runtimePlaceholder.hidden = true;
}

async function loadRuntimeStatus() {
  const response = await fetch("/api/avatar/status");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "avatar status failed");
  renderRuntimeStatus(data.result);
}

function requestPayload() {
  const person = selectedPerson();
  return {
    poe_api_key: poeApiKeyInput.value.trim(),
    poe_model: poeModelInput.value.trim(),
    query: person?.query || person?.display_name || "",
    person_id: person?.id || "",
    intent: intentInput.value,
    mode: modeInput.value,
    scenario: scenarioInput.value.trim(),
    conversation_history: conversationHistory(),
    multimodal_output_surface: "avatar_musetalk",
  };
}

function renderReply(result) {
  const chunks = result.clone_voice?.audio_chunks || [];
  const visual = result.clone_voice?.visual_driver || {};
  const lines = [
    result.draft_text || "",
    "",
    `Visual: ${visual.provider || result.provider || "--"} / ${visual.status || "--"}`,
    `Stream: ${visual.stream_url || runtimeStatus?.stream?.idle_stream_url || "--"}`,
    `Voice: ${result.clone_voice?.provider || "--"} / ${result.clone_voice?.status || "--"}`,
    `Audio chunks: ${chunks.length}`,
  ];
  replyText.textContent = lines.join("\n");
  jobSummary.textContent = result.message || "MuseTalk runtime 指令已生成。";
  setBadge(jobBadge, result.status || "completed");
}

function stopVisualSync() {
  if (visualSyncTimer) {
    window.clearInterval(visualSyncTimer);
    visualSyncTimer = 0;
  }
}

function startVisualSync(result) {
  stopVisualSync();
  const visual = result.clone_voice?.visual_driver || {};
  const sessionId = visual.sessions?.[0]?.session_id || "";
  const streamWorkerUrl = visual.stream_worker_url || "";
  if (!sessionId || !streamWorkerUrl) {
    showIdleStream();
    return;
  }
  const baseUrl = `${streamWorkerUrl.replace(/\/$/, "")}/sync-frame`;
  const updateFrame = () => {
    if (!avatarAudio.paused && !avatarAudio.ended) {
      const t = Math.max(0, Math.floor((avatarAudio.currentTime || 0) * 1000));
      runtimeFrame.src = `${baseUrl}?session_id=${encodeURIComponent(sessionId)}&t=${t}&_=${Date.now()}`;
    }
  };
  updateFrame();
  visualSyncTimer = window.setInterval(updateFrame, 80);
  avatarAudio.addEventListener(
    "ended",
    () => {
      stopVisualSync();
      showIdleStream();
    },
    { once: true }
  );
}

async function playFirstAudioChunk(result) {
  const chunks = result.clone_voice?.audio_chunks || [];
  const firstUrl = chunks[0]?.audio_url || result.clone_voice?.audio_url;
  if (!firstUrl) return;
  avatarAudio.src = firstUrl;
  try {
    await avatarAudio.play();
    startVisualSync(result);
  } catch {
    jobSummary.textContent = "浏览器阻止了自动播放，再点一次回复或点页面后重试。";
  }
}

async function speakWithMuseRuntime() {
  cacheSettings();
  speakButton.disabled = true;
  jobSummary.textContent = "生成关系图谱回复，并下发 MuseTalk runtime...";
  setBadge(jobBadge, "partial");
  try {
    const response = await fetch("/api/avatar/realtime-reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload()),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "MuseTalk reply failed");
    renderReply(data.result);
    await playFirstAudioChunk(data.result);
    await loadRuntimeStatus();
  } catch (error) {
    jobSummary.textContent = error.message;
    setBadge(jobBadge, "failed");
    replyText.textContent = String(error.stack || error.message || error);
  } finally {
    speakButton.disabled = false;
  }
}

async function init() {
  restoreSettings();
  try {
    await Promise.all([loadPeople(), loadRuntimeStatus()]);
    setHealth(true, "已连接");
  } catch (error) {
    setHealth(false, error.message);
  }
}

personSelect.addEventListener("change", renderRelationProfile);
refreshButton.addEventListener("click", loadRuntimeStatus);
speakButton.addEventListener("click", speakWithMuseRuntime);
clearPoeApiKeyButton.addEventListener("click", clearPoeKey);
poeApiKeyInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);

init();
