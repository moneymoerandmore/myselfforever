const poeApiKeyInput = document.querySelector("#poeApiKey");
const poeModelInput = document.querySelector("#poeModel");
const clearPoeApiKeyButton = document.querySelector("#clearPoeApiKey");
const healthStatus = document.querySelector("#healthStatus");
const personSelect = document.querySelector("#personSelect");
const intentInput = document.querySelector("#intent");
const modeInput = document.querySelector("#mode");
const scenarioInput = document.querySelector("#scenario");
const contextTextInput = document.querySelector("#contextText");
const refreshButton = document.querySelector("#refreshButton");
const renderButton = document.querySelector("#renderButton");
const providerSummary = document.querySelector("#providerSummary");
const providerBadge = document.querySelector("#providerBadge");
const providerGrid = document.querySelector("#providerGrid");
const jobSummary = document.querySelector("#jobSummary");
const jobBadge = document.querySelector("#jobBadge");
const replyText = document.querySelector("#replyText");
const avatarVideo = document.querySelector("#avatarVideo");
const jobsList = document.querySelector("#jobsList");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";

let people = [];
let providerStatus = null;

function setHealth(ok, text) {
  healthStatus.textContent = text;
  healthStatus.classList.toggle("ok", ok);
  healthStatus.classList.toggle("error", !ok);
}

function setBadge(element, status) {
  element.textContent = status || "--";
  element.className = "risk";
  if (!status) {
    element.classList.add("risk-idle");
  } else if (status === "completed") {
    element.classList.add("risk-r0");
  } else if (status.startsWith("needs_")) {
    element.classList.add("risk-r2");
  } else if (status.includes("failed") || status.includes("timeout")) {
    element.classList.add("risk-r3");
  } else {
    element.classList.add("risk-r1");
  }
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
  const id = personSelect.value;
  return people.find((person) => person.id === id) || null;
}

function contextHistory() {
  return contextTextInput.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-40)
    .map((line) => {
      const normalized = line.replace(/^我[:：]/, "self:").replace(/^对方[:：]/, "contact:");
      if (normalized.startsWith("self:")) {
        return { role: "self", content: normalized.slice(5).trim() };
      }
      if (normalized.startsWith("contact:")) {
        return { role: "contact", content: normalized.slice(8).trim() };
      }
      return { role: "contact", content: line };
    });
}

function renderPeopleOptions() {
  personSelect.innerHTML = "";
  if (people.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "没有可用联系人";
    personSelect.appendChild(option);
    return;
  }
  for (const person of people) {
    const option = document.createElement("option");
    option.value = person.id;
    option.textContent = `${person.display_name || person.query} · ${person.category || "未分类"}`;
    personSelect.appendChild(option);
  }
}

async function loadPeople() {
  const response = await fetch("/api/people");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "联系人读取失败");
  people = data.people || [];
  renderPeopleOptions();
}

function providerItem(title, ready, detail) {
  const item = document.createElement("article");
  item.className = `avatar-status-item ${ready ? "avatar-status-ready" : "avatar-status-missing"}`;
  item.innerHTML = `<strong>${title}</strong><span>${detail}</span>`;
  return item;
}

function renderProviderStatus(status) {
  providerStatus = status;
  const sourceReady = Boolean(status.source_image?.configured && status.source_image?.exists);
  const ttsReady = Boolean(status.tts?.configured);
  const rendererReady = Boolean(status.renderer?.configured);
  const allReady = sourceReady && ttsReady && rendererReady;
  providerBadge.textContent = allReady ? "可渲染" : "待配置";
  providerBadge.className = `mode-badge ${allReady ? "mode-ok" : "mode-warn"}`;
  providerSummary.textContent = allReady
    ? "LivePortrait 本地形象层已具备文本到视频链路。"
    : "页面可生成回复；本地视频渲染需要补齐头像图、TTS 命令和 LivePortrait 命令。";
  providerGrid.innerHTML = "";
  providerGrid.append(
    providerItem(
      "我的形象",
      sourceReady,
      sourceReady ? status.source_image.path : "设置 DIGITAL_TWIN_AVATAR_IMAGE，指向一张本地正脸图。",
    ),
    providerItem(
      "我的声音",
      ttsReady,
      ttsReady ? "已配置 DIGITAL_TWIN_TTS_COMMAND。" : "设置 DIGITAL_TWIN_TTS_COMMAND，将 reply.txt 转成 reply.wav。",
    ),
    providerItem(
      "LivePortrait",
      rendererReady,
      rendererReady ? "已配置 LIVEPORTRAIT_RENDER_COMMAND。" : "设置 LIVEPORTRAIT_RENDER_COMMAND，将头像图和音频转成 avatar.mp4。",
    ),
  );
}

async function loadProviderStatus() {
  const response = await fetch("/api/avatar/status");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "形象层状态读取失败");
  renderProviderStatus(data.result);
}

function renderJobs(jobs) {
  jobsList.innerHTML = "";
  if (!jobs.length) {
    jobsList.innerHTML = '<div class="empty-list">还没有任务</div>';
    return;
  }
  for (const job of jobs) {
    const item = document.createElement("article");
    item.className = "avatar-job";
    const videoLink = job.files?.video ? `<a href="${job.files.video}" target="_blank" rel="noreferrer">视频</a>` : "";
    const audioLink = job.files?.audio ? `<a href="${job.files.audio}" target="_blank" rel="noreferrer">音频</a>` : "";
    item.innerHTML = `
      <div>
        <strong>${job.created_at || job.id} · ${job.status}</strong>
        <p>${job.person_query || "未指定联系人"}：${(job.draft_text || "").slice(0, 90)}</p>
      </div>
      <div>${videoLink || audioLink || ""}</div>
    `;
    jobsList.appendChild(item);
  }
}

async function loadJobs() {
  const response = await fetch("/api/avatar/jobs?limit=10");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "任务读取失败");
  renderJobs(data.result?.jobs || []);
}

function renderJob(job) {
  jobSummary.textContent = job.message || `任务 ${job.id}`;
  setBadge(jobBadge, job.status);
  replyText.textContent = [
    job.draft_text || "",
    "",
    `状态：${job.status}`,
    job.message ? `说明：${job.message}` : "",
    ...(job.steps || []).map(
      (step) => `${step.name}: code=${step.returncode}, ${step.duration_seconds}s${step.stderr ? `\n${step.stderr}` : ""}`,
    ),
  ]
    .filter(Boolean)
    .join("\n");
  if (job.files?.video) {
    avatarVideo.hidden = false;
    avatarVideo.src = job.files.video;
  } else {
    avatarVideo.hidden = true;
    avatarVideo.removeAttribute("src");
  }
}

async function renderAvatarReply() {
  const person = selectedPerson();
  const apiKey = poeApiKeyInput.value.trim();
  const scenario = scenarioInput.value.trim();
  if (!person) {
    setHealth(false, "先选择联系人");
    personSelect.focus();
    return;
  }
  if (!apiKey) {
    setHealth(false, "先输入 Poe API Key");
    poeApiKeyInput.focus();
    return;
  }
  if (!scenario) {
    setHealth(false, "先输入对方内容");
    scenarioInput.focus();
    return;
  }
  cacheSettings();
  renderButton.disabled = true;
  renderButton.textContent = "生成中";
  replyText.textContent = "正在生成数字我的回复，并尝试交给本地 LivePortrait 链路。";
  setBadge(jobBadge, "running");
  try {
    const response = await fetch("/api/avatar/reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: person.query,
        scenario,
        conversation_history: contextHistory(),
        poe_api_key: apiKey,
        poe_model: poeModelInput.value.trim(),
        intent: intentInput.value,
        mode: person.group === "direct" ? modeInput.value : "observe",
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "生成失败");
    renderJob(data.result);
    await loadJobs();
    setHealth(true, "数字人任务已生成");
  } catch (error) {
    replyText.textContent = `生成失败：${error.message}`;
    jobSummary.textContent = "任务失败";
    setBadge(jobBadge, "render_failed");
    setHealth(false, error.message);
  } finally {
    renderButton.disabled = false;
    renderButton.textContent = "生成数字人回复";
  }
}

async function refreshAll() {
  try {
    await Promise.all([loadProviderStatus(), loadJobs()]);
    setHealth(true, "已连接");
  } catch (error) {
    setHealth(false, error.message);
  }
}

clearPoeApiKeyButton.addEventListener("click", clearPoeKey);
poeApiKeyInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);
refreshButton.addEventListener("click", refreshAll);
renderButton.addEventListener("click", renderAvatarReply);

restoreSettings();
Promise.all([loadPeople(), refreshAll()]).catch((error) => setHealth(false, error.message));
