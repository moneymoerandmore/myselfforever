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
const avatarAudio = document.querySelector("#avatarAudio");
const avatarVideo = document.querySelector("#avatarVideo");
const jobsList = document.querySelector("#jobsList");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";

let people = [];
let activeJobId = null;
let activeJobTimer = null;
let playedAudioChunks = new Set();
let audioQueue = [];
let audioPlaying = false;

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

function restoreSettings() {
  try {
    poeApiKeyInput.value = localStorage.getItem(POE_API_KEY_STORAGE_KEY) || "";
    poeModelInput.value = localStorage.getItem(POE_MODEL_STORAGE_KEY) || poeModelInput.value;
  } catch {
    // Ignore disabled browser storage.
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
      const normalized = line.replace(/^我[:：]/, "self:").replace(/^对方[:：]/, "contact:");
      if (normalized.startsWith("self:")) return { role: "self", content: normalized.slice(5).trim() };
      if (normalized.startsWith("contact:")) return { role: "contact", content: normalized.slice(8).trim() };
      return { role: "contact", content: line };
    });
}

function renderPeopleOptions() {
  personSelect.innerHTML = "";
  if (!people.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No contacts";
    personSelect.appendChild(option);
    return;
  }
  for (const person of people) {
    const option = document.createElement("option");
    option.value = person.id;
    option.textContent = `${person.display_name || person.query} / ${person.category || "uncategorized"}`;
    personSelect.appendChild(option);
  }
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
  const ttsReady = Boolean(status.tts?.configured);
  const rendererReady = Boolean(baseReady || status.renderer?.configured);
  const lipsyncReady = Boolean(status.lipsync?.configured);
  const allReady = sourceReady && ttsReady && rendererReady && lipsyncReady;
  providerBadge.textContent = allReady ? "ready" : "missing";
  providerBadge.className = `mode-badge ${allReady ? "mode-ok" : "mode-warn"}`;
  providerSummary.textContent = allReady
    ? "Avatar layer is ready. Streaming audio chunks are enabled."
    : "Avatar layer needs portrait, TTS, base video or renderer, and lip-sync.";
  providerGrid.innerHTML = "";
  providerGrid.append(
    providerItem("Portrait", sourceReady, sourceReady ? status.source_image.path : "set DIGITAL_TWIN_AVATAR_IMAGE"),
    providerItem("Base video", baseReady, baseReady ? "cached base video enabled" : "will render with LivePortrait"),
    providerItem("TTS", ttsReady, status.tts?.worker_url ? workerText(status.tts.worker) : "command mode"),
    providerItem("LipSync", lipsyncReady, status.lipsync?.worker_url ? workerText(status.lipsync.worker) : "command mode"),
  );
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
    const chunks = job.files?.audio_chunks?.length ? `<span>${job.files.audio_chunks.length} chunks</span>` : "";
    item.innerHTML = `
      <div>
        <strong>${job.created_at || job.id} / ${job.status}</strong>
        <p>${job.person_query || "unknown"}: ${(job.draft_text || "").slice(0, 90)}</p>
      </div>
      <div>${videoLink || audioLink || chunks || ""}</div>
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

function enqueueAudioChunks(job) {
  const chunks = job.files?.audio_chunks || [];
  for (const url of chunks) {
    if (!playedAudioChunks.has(url) && !audioQueue.includes(url)) audioQueue.push(url);
  }
  playNextAudioChunk();
}

async function playNextAudioChunk() {
  if (audioPlaying || !audioQueue.length) return;
  const url = audioQueue.shift();
  if (!url) return;
  playedAudioChunks.add(url);
  audioPlaying = true;
  avatarAudio.hidden = false;
  avatarAudio.src = `${url}?t=${Date.now()}`;
  avatarAudio.onended = () => {
    audioPlaying = false;
    playNextAudioChunk();
  };
  avatarAudio.onerror = () => {
    audioPlaying = false;
    playNextAudioChunk();
  };
  try {
    await avatarAudio.play();
  } catch {
    audioPlaying = false;
    setHealth(false, "Audio is ready. Press play in the audio control if autoplay is blocked.");
  }
}

function renderJob(job) {
  jobSummary.textContent = job.message || `job ${job.id}`;
  setBadge(jobBadge, job.status);
  replyText.textContent = [
    job.draft_text || "",
    "",
    `status: ${job.status}`,
    job.message ? `message: ${job.message}` : "",
    job.audio_chunks?.length ? `audio chunks: ${job.audio_chunks.filter((chunk) => chunk.status === "ready").length}/${job.audio_chunks.length}` : "",
    ...(job.steps || []).map((step) => `${step.name}: ${step.mode || "command"}, code=${step.returncode}, ${step.duration_seconds}s`),
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
  enqueueAudioChunks(job);
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
    renderButton.textContent = "Generate avatar reply";
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
  playedAudioChunks = new Set();
  audioQueue = [];
  audioPlaying = false;
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
  replyText.textContent = "Starting streaming avatar job. Audio chunks will play before the final video is ready.";
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
        streaming: true,
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "avatar generation failed");
    renderJob(data.result);
    startAvatarJobPolling(data.result.id);
    setHealth(true, "streaming avatar job started");
  } catch (error) {
    replyText.textContent = `generation failed: ${error.message}`;
    jobSummary.textContent = "job failed";
    setBadge(jobBadge, "render_failed");
    setHealth(false, error.message);
    renderButton.disabled = false;
    renderButton.textContent = "Generate avatar reply";
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

restoreSettings();
Promise.all([loadPeople(), refreshAll()]).catch((error) => setHealth(false, error.message));
