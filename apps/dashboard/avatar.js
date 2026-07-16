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
  else if (status === "partial" || status === "configured") element.classList.add("risk-r1");
  else if (status === "missing" || status === "bridge_down") element.classList.add("risk-r2");
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
    // Keep the current page usable if storage is blocked.
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
    // Visible form values are enough for this session.
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

function bridgeText(bridge) {
  if (!bridge?.configured) return "bridge not configured";
  if (bridge.ok) return "bridge ok";
  return `bridge down: ${bridge.error || "unknown"}`;
}

function renderRuntimeStatus(status) {
  runtimeStatus = status;
  const runtime = status.runtime || {};
  const voice = status.realtime_voice || {};
  const bridge = runtime.bridge || {};
  const bridgeResult = bridge.result || {};
  const bridgeOk = Boolean(bridge.ok);
  const streamReady = Boolean(runtime.stream_url);
  const unrealReady = Boolean(runtime.unreal_ws_url || bridgeResult.unreal?.configured || bridgeResult.unreal?.pull_connected);
  const voiceReady = Boolean(voice.configured);
  const ready = bridgeOk && streamReady && unrealReady && voiceReady;

  providerBadge.textContent = status.provider || "--";
  runtimeSummary.textContent = ready
    ? "3D 常驻流、bridge 和克隆语音都已配置。"
    : "3D 路线已启用，但 runtime/流/语音仍有未接入项。";
  setBadge(runtimeBadge, ready ? "ready" : bridgeOk || streamReady || voiceReady ? "partial" : "missing");

  providerGrid.innerHTML = "";
  providerGrid.appendChild(providerItem("3D Bridge", bridgeOk, `${runtime.bridge_url || "--"} · ${bridgeText(bridge)}`));
  providerGrid.appendChild(
    providerItem(
      "Unreal WS",
      unrealReady,
      runtime.unreal_ws_url || bridgeResult.unreal?.ws_url || "UNREAL_WS_URL 未配置，可用 HTTP Pull"
    )
  );
  providerGrid.appendChild(
    providerItem(
      "Unreal Pull",
      Boolean(bridgeResult.unreal?.pull_connected),
      `${runtime.bridge_url || "--"}${bridgeResult.unreal?.pull_url || "/api/unreal/events"} · queued ${bridgeResult.unreal?.queued_events || 0}`
    )
  );
  providerGrid.appendChild(
    providerItem("常驻视频流", streamReady, runtime.stream_url || "AVATAR3D_STREAM_URL 未配置")
  );
  providerGrid.appendChild(
    providerItem("克隆语音", voiceReady, `${voice.provider || "--"} · ${voice.stream_endpoint || "--"}`)
  );
  providerGrid.appendChild(providerItem("视觉路线", true, `${status.provider} · ${runtime.render_transport || "--"}`));
  providerGrid.appendChild(
    providerItem("废弃 2D", Boolean(status.deprecated_2d_avatar_layer), "LivePortrait / MuseTalk 不再是主页面路径")
  );

  if (streamReady) {
    runtimeFrame.src = runtime.stream_url;
    runtimeFrame.hidden = false;
    runtimePlaceholder.hidden = true;
  } else {
    runtimeFrame.removeAttribute("src");
    runtimeFrame.hidden = true;
    runtimePlaceholder.hidden = false;
  }
}

async function loadRuntimeStatus() {
  const response = await fetch("/api/avatar3d/status");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "avatar3d status failed");
  renderRuntimeStatus(data.result);
}

function requestPayload() {
  const person = selectedPerson();
  return {
    poe_api_key: poeApiKeyInput.value.trim(),
    model: poeModelInput.value.trim(),
    query: person?.query || person?.display_name || "",
    person_id: person?.id || "",
    intent: intentInput.value,
    mode: modeInput.value,
    scenario: scenarioInput.value.trim(),
    conversation_history: conversationHistory(),
    multimodal_output_surface: "avatar_3d",
  };
}

function renderReply(result) {
  const bridge = result.runtime?.command || {};
  const workerResult = bridge.worker_result || {};
  const unrealEvent = workerResult.unreal_event || workerResult.last_unreal_event || {};
  const chunks = result.clone_voice?.audio_chunks || [];
  const lines = [
    result.draft_text || "",
    "",
    `3D provider: ${result.provider || "--"}`,
    `Bridge: ${bridge.ok ? "ok" : bridge.error || "not connected"}`,
    `Unreal WS: ${unrealEvent.ok ? "sent" : unrealEvent.error || result.runtime?.unreal_ws_url || "not configured"}`,
    `Stream: ${result.runtime?.stream_url || "not configured"}`,
    `Voice: ${result.clone_voice?.provider || "--"} / ${result.clone_voice?.status || "--"}`,
    `Audio chunks: ${chunks.length}`,
  ];
  replyText.textContent = lines.join("\n");
  jobSummary.textContent = result.message || "3D runtime 指令已生成。";
  setBadge(jobBadge, result.status || "completed");
}

async function playFirstAudioChunk(result) {
  const chunks = result.clone_voice?.audio_chunks || [];
  const firstUrl = chunks[0]?.audio_url || result.clone_voice?.audio_url;
  if (!firstUrl) return;
  avatarAudio.src = firstUrl;
  try {
    await avatarAudio.play();
  } catch {
    // Browser autoplay policies may require a second user gesture.
  }
}

async function speakWith3dRuntime() {
  cacheSettings();
  speakButton.disabled = true;
  jobSummary.textContent = "生成关系图谱回复，并下发 3D runtime...";
  setBadge(jobBadge, "partial");
  try {
    const response = await fetch("/api/avatar3d/realtime-reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload()),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "3D reply failed");
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
speakButton.addEventListener("click", speakWith3dRuntime);
clearPoeApiKeyButton.addEventListener("click", clearPoeKey);
poeApiKeyInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);

init();
