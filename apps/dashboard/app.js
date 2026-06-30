const form = document.querySelector("#draftForm");
const personFilterInput = document.querySelector("#personFilter");
const categoryFilterInput = document.querySelector("#categoryFilter");
const peopleList = document.querySelector("#peopleList");
const peopleMeta = document.querySelector("#peopleMeta");
const peopleBreakdown = document.querySelector("#peopleBreakdown");
const segmentButtons = [...document.querySelectorAll(".segment")];
const scenarioInput = document.querySelector("#scenario");
const conversationThread = document.querySelector("#conversationThread");
const conversationMeta = document.querySelector("#conversationMeta");
const speakerSwitch = document.querySelector("#speakerSwitch");
const speakerButtons = [...document.querySelectorAll(".speaker")];
const addMessageButton = document.querySelector("#addMessageButton");
const scenarioLabel = document.querySelector("#scenarioLabel");
const poeApiKeyInput = document.querySelector("#poeApiKey");
const poeModelInput = document.querySelector("#poeModel");
const clearPoeApiKeyButton = document.querySelector("#clearPoeApiKey");
const intentInput = document.querySelector("#intent");
const modeInput = document.querySelector("#mode");
const submitButton = document.querySelector("#submitButton");
const clearButton = document.querySelector("#clearButton");
const healthStatus = document.querySelector("#healthStatus");
const groupMonitorButton = document.querySelector("#groupMonitorButton");
const groupMonitorStatus = document.querySelector("#groupMonitorStatus");
const groupReplyModeInput = document.querySelector("#groupReplyMode");
const monitorGroupNameInput = document.querySelector("#monitorGroupName");
const monitorSelfNameInput = document.querySelector("#monitorSelfName");
const replySettleSecondsInput = document.querySelector("#replySettleSeconds");
const replyCooldownSecondsInput = document.querySelector("#replyCooldownSeconds");

const profileName = document.querySelector("#profileName");
const profileSubtitle = document.querySelector("#profileSubtitle");
const permissionBadge = document.querySelector("#permissionBadge");
const relationshipPositioning = document.querySelector("#relationshipPositioning");
const callEvidence = document.querySelector("#callEvidence");
const frequentTopics = document.querySelector("#frequentTopics");
const mainScenes = document.querySelector("#mainScenes");
const permissionText = document.querySelector("#permissionText");
const dyadicProfileText = document.querySelector("#dyadicProfileText");
const composerHint = document.querySelector("#composerHint");
const contactModeBadge = document.querySelector("#contactModeBadge");

const draftText = document.querySelector("#draftText");
const toneBasis = document.querySelector("#toneBasis");
const riskBadge = document.querySelector("#riskBadge");
const relationshipBasis = document.querySelector("#relationshipBasis");
const topicBasis = document.querySelector("#topicBasis");
const questionsList = document.querySelector("#questionsList");
const candidatesList = document.querySelector("#candidatesList");

let people = [];
let selectedPerson = null;
let activeScope = "all";
let activeCategory = "all";
let activeSpeaker = "contact";
let activeConversationMode = "person";
let activeBasisMessageId = "";
let userSelectedPerson = false;
const conversationHistories = new Map();

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";
const MONITOR_CONFIG_STORAGE_KEY = "digitalTwin.monitorConfig";
const GROUP_CONVERSATION_KEY = "__group_monitor__";

const riskClassMap = {
  R0_safe: "risk-r0",
  R1_low: "risk-r1",
  R2_medium: "risk-r2",
  R3_high: "risk-r3",
  R4_forbidden: "risk-r4",
};

function setHealth(ok, text) {
  healthStatus.textContent = text;
  healthStatus.classList.toggle("ok", ok);
  healthStatus.classList.toggle("error", !ok);
}

function restorePoeSettings() {
  try {
    poeApiKeyInput.value = localStorage.getItem(POE_API_KEY_STORAGE_KEY) || "";
    poeModelInput.value = localStorage.getItem(POE_MODEL_STORAGE_KEY) || poeModelInput.value;
    const monitorConfigValue = JSON.parse(localStorage.getItem(MONITOR_CONFIG_STORAGE_KEY) || "{}");
    monitorGroupNameInput.value = monitorConfigValue.groupName || monitorGroupNameInput.value;
    monitorSelfNameInput.value = monitorConfigValue.selfName || monitorSelfNameInput.value;
    groupReplyModeInput.value = monitorConfigValue.replyMode || groupReplyModeInput.value;
    replySettleSecondsInput.value = monitorConfigValue.settleSeconds || replySettleSecondsInput.value;
    replyCooldownSecondsInput.value = monitorConfigValue.cooldownSeconds || replyCooldownSecondsInput.value;
  } catch {
    // Browser storage may be disabled; generation still works for this page session.
  }
}

function cachePoeSettings() {
  try {
    const apiKey = poeApiKeyInput.value.trim();
    const model = poeModelInput.value.trim();
    if (apiKey) {
      localStorage.setItem(POE_API_KEY_STORAGE_KEY, apiKey);
    } else {
      localStorage.removeItem(POE_API_KEY_STORAGE_KEY);
    }
    if (model) {
      localStorage.setItem(POE_MODEL_STORAGE_KEY, model);
    }
  } catch {
    // Keep the current in-memory values when browser storage is unavailable.
  }
}

let groupMonitorRunning = false;

function isGroupConversationMode() {
  return activeConversationMode === "group";
}

function groupHistory() {
  if (!conversationHistories.has(GROUP_CONVERSATION_KEY)) {
    conversationHistories.set(GROUP_CONVERSATION_KEY, []);
  }
  return conversationHistories.get(GROUP_CONVERSATION_KEY);
}

function readMonitorConfig() {
  return {
    groupName: monitorGroupNameInput.value.trim(),
    selfName: monitorSelfNameInput.value.trim(),
    replyMode: groupReplyModeInput.value,
    settleSeconds: Number(replySettleSecondsInput.value || 10),
    cooldownSeconds: Number(replyCooldownSecondsInput.value || 90),
  };
}

function cacheMonitorConfig() {
  try {
    localStorage.setItem(MONITOR_CONFIG_STORAGE_KEY, JSON.stringify(readMonitorConfig()));
  } catch {
    // Keep current visible values when storage is unavailable.
  }
}

function clearPoeSettings() {
  poeApiKeyInput.value = "";
  try {
    localStorage.removeItem(POE_API_KEY_STORAGE_KEY);
  } catch {
    // The visible value is still cleared even if storage is unavailable.
  }
  poeApiKeyInput.focus();
}

function setGroupMonitorUi(status, text) {
  groupMonitorRunning = status === "running";
  groupMonitorStatus.textContent = text;
  groupMonitorStatus.className = "monitor-status";
  groupMonitorStatus.classList.add(`monitor-${status}`);
  groupMonitorButton.textContent = groupMonitorRunning ? "停止监控" : "启动监控";
  groupMonitorButton.classList.toggle("monitor-active", groupMonitorRunning);
  groupMonitorButton.disabled = false;
}

function activateGroupConversationMode() {
  activeConversationMode = "group";
  selectedPerson = null;
  activeBasisMessageId = "";
  userSelectedPerson = false;
  renderPeopleList();
  renderProfile();
  renderConversation();
  resetDraftArea();
}

function updateComposerMode() {
  const groupMode = isGroupConversationMode();
  speakerSwitch.hidden = groupMode;
  addMessageButton.hidden = groupMode;
  scenarioLabel.textContent = groupMode ? "我的候选回复" : "补充一条消息";
  scenarioInput.placeholder = groupMode
    ? "点击下方按钮，模型会根据当前群聊上下文生成；你可以在这里继续修改"
    : activeSpeaker === "self"
      ? "补录你已经发过的话"
      : "输入对方刚说的话";
}

async function refreshGroupMonitorStatus() {
  try {
    const response = await fetch("http://127.0.0.1:8790/api/status");
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "状态读取失败");
    const status = data.status || {};
    if (status.running) {
      const monitor = status.monitor || {};
      const modeText = status.auto_send ? "自动发送" : status.auto_reply ? "自动草稿" : "只读";
      const suffix = monitor.last_error ? ` · OCR: ${monitor.last_error}` : "";
      setGroupMonitorUi("running", `${modeText}中${suffix}`);
      if (!isGroupConversationMode() && !userSelectedPerson) {
        activateGroupConversationMode();
      }
      await syncGroupMonitorConversation();
    } else {
      setGroupMonitorUi("idle", "未启动");
    }
  } catch {
    setGroupMonitorUi("error", "Bridge 未运行");
  }
}

async function stopGroupMonitor() {
  groupMonitorButton.disabled = true;
  groupMonitorButton.textContent = "停止中";
  try {
    const response = await fetch("http://127.0.0.1:8790/api/watch/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "停止失败");
    setGroupMonitorUi("idle", "已停止");
    setHealth(true, "群监控已停止");
  } catch (error) {
    setGroupMonitorUi("error", `停止失败：${error.message}`);
  }
}

async function startGroupMonitor() {
  const config = readMonitorConfig();
  const replyMode = config.replyMode;
  const apiKey = poeApiKeyInput.value.trim();
  if (!config.groupName || !config.selfName) {
    setHealth(false, "先填写群名和我的群昵称");
    return;
  }
  if (replyMode !== "observe" && !apiKey) {
    setHealth(false, "自动草稿/发送需要 Poe API Key");
    poeApiKeyInput.focus();
    return;
  }
  if (replyMode === "send") {
    const confirmed = window.confirm(
      "开启自动发送后，系统不会再切换窗口或点击输入框。你需要手动保持 PC 微信目标群输入框为当前焦点；新回复会直接粘贴并回车。确认开启？",
    );
    if (!confirmed) return;
  }
  cacheMonitorConfig();
  groupMonitorButton.disabled = true;
  groupMonitorButton.textContent = "启动中";
  try {
    const response = await fetch("http://127.0.0.1:8790/api/watch/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        groups: [config.groupName],
        self_names: [config.selfName],
        adapter: "window_capture_ocr",
        trigger_all: true,
        auto_reply: replyMode !== "observe",
        auto_send: replyMode === "send",
        poe_api_key: apiKey,
        poe_model: poeModelInput.value.trim(),
        reply_settle_seconds: config.settleSeconds,
        reply_cooldown_seconds: config.cooldownSeconds,
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "启动失败");
    const modeText =
      replyMode === "send"
        ? "自动发送中：请保持微信输入框焦点"
        : replyMode === "draft"
          ? "自动草稿中"
          : "只读监控中";
    setGroupMonitorUi("running", modeText);
    setHealth(true, "群监控已启动");
    activateGroupConversationMode();
    await syncGroupMonitorConversation();
  } catch (error) {
    setGroupMonitorUi("error", `启动失败：${error.message}`);
    setHealth(false, `群监控失败：${error.message}`);
  }
}

async function toggleGroupMonitor() {
  if (groupMonitorRunning) {
    await stopGroupMonitor();
  } else {
    await startGroupMonitor();
  }
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    setHealth(Boolean(data.ok), data.ok ? "本地服务已连接" : "服务异常");
  } catch {
    setHealth(false, "服务未连接");
  }
}

function setRisk(element, level) {
  element.textContent = level || "--";
  element.className = "risk";
  element.classList.add(riskClassMap[level] || "risk-idle");
}

function compactText(value, fallback = "--") {
  const text = (value || "").trim();
  return text || fallback;
}

function personSearchText(person) {
  return [
    person.display_name,
    person.call_name,
    person.wechat_name,
    person.objective_relationship,
    person.relationship_positioning,
    person.category,
    person.communication_density_label,
    String(person.communication_daily_average || ""),
    String(person.communication_total || ""),
    person.node_type,
    person.frequent_topics,
    person.interest_circles,
    person.main_scenes,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function filteredPeople() {
  const needle = personFilterInput.value.trim().toLowerCase();
  return people.filter((person) => {
    const scopeOk = activeScope === "all" || person.group === activeScope;
    const categoryOk = activeCategory === "all" || person.category === activeCategory;
    const textOk = !needle || personSearchText(person).includes(needle);
    return scopeOk && categoryOk && textOk;
  });
}

function renderCategoryOptions() {
  const stats = new Map();
  for (const person of people) {
    const category = person.category || "未分类";
    const current = stats.get(category) || { count: 0, maxTotal: 0 };
    current.count += 1;
    current.maxTotal = Math.max(current.maxTotal, person.communication_total || 0);
    stats.set(category, current);
  }

  const categories = [...stats.entries()].sort((left, right) => {
    const scoreDiff = right[1].maxTotal - left[1].maxTotal;
    if (scoreDiff !== 0) return scoreDiff;
    return left[0].localeCompare(right[0], "zh-CN");
  });

  categoryFilterInput.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = "全部分类";
  categoryFilterInput.appendChild(allOption);

  for (const [category, stat] of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = `${category} (${stat.count})`;
    categoryFilterInput.appendChild(option);
  }

  categoryFilterInput.value = activeCategory;
}

function renderPeopleList() {
  const filtered = filteredPeople();
  const directCount = people.filter((person) => person.group === "direct").length;
  const mentionedCount = people.filter((person) => person.group === "mentioned").length;
  peopleMeta.textContent = `${filtered.length} / ${people.length}`;
  peopleBreakdown.textContent = `直接 ${directCount} · 提及 ${mentionedCount}`;
  peopleList.innerHTML = "";

  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-list";
    empty.textContent = "没有匹配联系人";
    peopleList.appendChild(empty);
    return;
  }

  for (const person of filtered) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "person-row";
    if (selectedPerson && selectedPerson.id === person.id) {
      button.classList.add("active");
    }
    button.dataset.personId = person.id;

    const name = document.createElement("span");
    name.className = "person-name";
    name.textContent = person.display_name || person.query;

    const volume = document.createElement("span");
    volume.className = "person-volume";
    volume.textContent = `总量 ${person.communication_total || 0}`;

    const nameLine = document.createElement("span");
    nameLine.className = "person-name-line";
    nameLine.append(name, volume);

    const meta = document.createElement("span");
    meta.className = "person-meta";
    meta.textContent = `${person.objective_relationship || "未知"} · ${person.node_type || "未知"}`;

    const topics = document.createElement("span");
    topics.className = "person-topics";
    topics.textContent = [
      person.communication_density_label || "低密度",
      `日均 ${Number(person.communication_daily_average || 0).toFixed(1)}`,
      person.frequent_topics || person.interest_circles || "暂无主题",
    ].join(" · ");

    button.append(nameLine, meta, topics);
    button.addEventListener("click", () => selectPerson(person.id));
    peopleList.appendChild(button);
  }
}

function selectPerson(id) {
  activeConversationMode = "person";
  activeBasisMessageId = "";
  userSelectedPerson = true;
  selectedPerson = people.find((person) => person.id === id) || null;
  renderPeopleList();
  renderProfile();
  renderConversation();
  resetDraftArea();
}

function currentHistory() {
  if (isGroupConversationMode()) return groupHistory();
  if (!selectedPerson) return [];
  if (!conversationHistories.has(selectedPerson.id)) {
    conversationHistories.set(selectedPerson.id, []);
  }
  return conversationHistories.get(selectedPerson.id);
}

function renderConversation() {
  conversationThread.innerHTML = "";
  const history = currentHistory();
  conversationMeta.textContent = isGroupConversationMode()
    ? history.length
      ? `群监控已沉淀 ${history.length} 条文字消息/回复`
      : "群监控已启动，等待采集文字消息"
    : selectedPerson
      ? history.length
        ? `${history.length} 条消息会作为本次模型上下文`
        : "当前联系人还没有消息"
      : "先从左侧选择联系人";

  if ((!selectedPerson && !isGroupConversationMode()) || history.length === 0) {
    const empty = document.createElement("div");
    empty.className = "conversation-empty";
    empty.textContent = isGroupConversationMode()
      ? "监控启动后，识别到的群文字消息和模型替你说的话会出现在这里。"
      : selectedPerson
      ? "先录入对方说的话；已有的双方消息也可以逐条补进来。"
      : "选择联系人后开始模拟。";
    conversationThread.appendChild(empty);
    return;
  }

  history.forEach((message, index) => {
    const row = document.createElement("div");
    row.className = `message-row ${message.role === "self" ? "message-self" : "message-contact"}`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    if (message.basis) {
      bubble.classList.add("message-clickable");
      if (message.id === activeBasisMessageId) bubble.classList.add("message-selected");
      bubble.tabIndex = 0;
      bubble.title = "点击查看这句回复的生成依据";
      bubble.addEventListener("click", () => renderMessageBasis(message));
      bubble.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          renderMessageBasis(message);
        }
      });
    }
    const label = document.createElement("span");
    label.className = "message-label";
    label.textContent =
      message.label ||
      (message.role === "self" ? (message.source === "model" ? "我 · 模型草稿" : "我") : message.sender || "对方");
    const content = document.createElement("p");
    content.textContent = message.content;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "message-remove";
    remove.title = "从上下文删除";
    remove.setAttribute("aria-label", "从上下文删除");
    remove.textContent = "×";
    remove.addEventListener("click", (event) => {
      event.stopPropagation();
      history.splice(index, 1);
      renderConversation();
    });
    bubble.append(label, content, remove);
    row.appendChild(bubble);
    conversationThread.appendChild(row);
  });
  conversationThread.scrollTop = conversationThread.scrollHeight;
}

function setActiveSpeaker(role) {
  activeSpeaker = role;
  speakerButtons.forEach((button) => button.classList.toggle("active", button.dataset.speaker === role));
  scenarioInput.placeholder = role === "self" ? "补录你已经发过的话" : "输入对方刚说的话";
}

function addMessage(content = scenarioInput.value.trim(), role = activeSpeaker, source = "manual") {
  if ((!selectedPerson && !isGroupConversationMode()) || !content) return false;
  currentHistory().push({ role, content, source });
  scenarioInput.value = "";
  renderConversation();
  scenarioInput.focus();
  return true;
}

function parseBridgeTime(value) {
  const timestamp = Date.parse(value || "");
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function reviewLabel(review) {
  if (review.status === "sent_by_group_monitor") return "我 · 已自动发送";
  if (review.status === "drafted_by_group_monitor") return "我 · 自动草稿";
  if (review.status === "drafted") return "我 · 模型草稿";
  return "我 · 待确认草稿";
}

function draftSegments(source) {
  const direct = source && Array.isArray(source.draft_segments) ? source.draft_segments : null;
  const metadata = source && source.draft_metadata && Array.isArray(source.draft_metadata.draft_segments)
    ? source.draft_metadata.draft_segments
    : null;
  const segments = (direct || metadata || [])
    .map((item) => String(item || "").trim())
    .filter(Boolean);
  if (segments.length) return segments;
  return String((source && (source.draft || source.draft_text)) || "")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildGroupConversation(events, reviews) {
  const config = readMonitorConfig();
  const selfNames = new Set([config.selfName, ...(config.selfName ? [config.selfName.trim()] : [])].filter(Boolean));
  const groupName = config.groupName;
  const rows = [];

  for (const event of events || []) {
    if (groupName && event.group !== groupName) continue;
    const isSelf = selfNames.has(event.sender);
    rows.push({
      id: event.event_id || `event-${rows.length}`,
      role: isSelf ? "self" : "contact",
      sender: event.sender,
      label: isSelf ? `我 · ${event.sender}` : event.sender,
      content: event.content,
      source: event.source || "group_monitor",
      occurredAt: event.occurred_at,
      sortTime: parseBridgeTime(event.occurred_at),
      sortBias: 0,
    });
  }

  for (const review of reviews || []) {
    if (groupName && review.group !== groupName) continue;
    if (!review.draft) continue;
    const segments = draftSegments(review);
    segments.forEach((segment, index) => {
      rows.push({
        id: `review-${review.review_id}-${index}`,
        role: "self",
        sender: "我",
        label: segments.length > 1 ? `${reviewLabel(review)} ${index + 1}/${segments.length}` : reviewLabel(review),
        content: segment,
        source: "group_monitor_model",
        occurredAt: review.created_at,
        sortTime: parseBridgeTime(review.created_at),
        sortBias: 1 + index / 10,
        basis: {
          ...(review.draft_metadata || {}),
          review_id: review.review_id,
          segment_index: index + 1,
          segment_count: segments.length,
          full_reply: review.draft,
          status: review.status,
          trigger_reasons: review.trigger_reasons || [],
          trigger_event_id: review.trigger_event_id,
          context: review.context || [],
          sender: review.sender,
        },
      });
    });
  }

  rows.sort((left, right) => left.sortTime - right.sortTime || left.sortBias - right.sortBias);
  return rows.slice(-200);
}

async function syncGroupMonitorConversation() {
  if (!isGroupConversationMode()) return;
  const groupName = readMonitorConfig().groupName;
  if (!groupName) return;
  try {
    const [eventsResponse, reviewsResponse] = await Promise.all([
      fetch(`http://127.0.0.1:8790/api/events?group=${encodeURIComponent(groupName)}`),
      fetch("http://127.0.0.1:8790/api/reviews"),
    ]);
    const eventsData = await eventsResponse.json();
    const reviewsData = await reviewsResponse.json();
    if (!eventsData.ok || !reviewsData.ok) return;
    conversationHistories.set(
      GROUP_CONVERSATION_KEY,
      buildGroupConversation(eventsData.events || [], reviewsData.reviews || []),
    );
    if (!currentHistory().some((message) => message.id === activeBasisMessageId)) {
      activeBasisMessageId = "";
    }
    renderConversation();
  } catch {
    // Bridge status refresh already shows connectivity errors.
  }
}

function renderMessageBasis(message) {
  if (!message || !message.basis) return;
  activeBasisMessageId = message.id || "";
  const basis = message.basis || {};
  draftText.textContent = buildReplyRationale(message);
  toneBasis.textContent = "为什么像我会这么说";
  relationshipBasis.textContent = basis.relationship_basis || "--";
  topicBasis.textContent = basis.topic_basis || "--";
  setRisk(riskBadge, basis.risk_level);
  renderList(
    questionsList,
    [
      basis.status ? `监控状态：${basis.status}` : "",
      basis.review_id ? `review_id：${basis.review_id}` : "",
      basis.trigger_reasons && basis.trigger_reasons.length
        ? `触发原因：${basis.trigger_reasons.join(" / ")}`
        : "",
      basis.tone_basis ? `模型依据：${basis.tone_basis}` : "",
    ].filter(Boolean),
    "暂无",
  );
  renderCandidates([]);
  renderConversation();
}

function compactOneLine(value, maxLength = 60) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

function translateTriggerReason(reason) {
  const map = {
    active_group_mode: "当前是主动群监控模式，不需要等 @ 才可以判断是否接话",
    mentioned_self: "对方提到了我的群昵称",
    keyword: "命中了监控关键词",
    question: "触发消息是疑问句，天然适合回应",
  };
  return map[reason] || reason;
}

function inferReplyMove(replyText) {
  const text = String(replyText || "").trim();
  const moves = [];
  if (text.length <= 24) moves.push("回复很短，像群聊里顺手接一句，不把场面变成正式发言");
  if (/[？?]$/.test(text)) moves.push("末尾用问题把话题递回去，适合继续听别人补充");
  if (/(可以|行|那就|先|别急|我觉得|有点|不一定|看看|盯|确认)/.test(text)) {
    moves.push("措辞偏判断和推进，不是模板式安慰，也不是大段说教");
  }
  if (!/(保证|必须|一定|买入|卖出|加仓|减仓|内幕)/.test(text)) {
    moves.push("没有做强承诺或高风险建议，符合群里自动回复的边界");
  }
  return moves.length ? moves : ["这句主要是在承接上一轮语境，保持轻量回应。"];
}

function buildReplyRationale(message) {
  const basis = message.basis || {};
  const context = Array.isArray(basis.context) ? basis.context : [];
  const trigger =
    context.find((item) => item.event_id && item.event_id === basis.trigger_event_id) ||
    context[context.length - 1] ||
    {};
  const recent = context.slice(-4);
  const recentLines = recent
    .map((item) => `${item.sender || "群友"}：${compactOneLine(item.content, 44)}`)
    .join("\n");
  const triggerText = trigger.content
    ? `${trigger.sender || basis.sender || "群友"}：${compactOneLine(trigger.content, 80)}`
    : "未找到触发消息";
  const triggerReasons = (basis.trigger_reasons || []).map(translateTriggerReason);
  const replyMoves = inferReplyMove(message.content);
  const relationship = compactOneLine(basis.relationship_basis || "没有明确关系依据", 90);
  const topic = compactOneLine(basis.topic_basis || "没有明确话题依据", 90);
  const hasRelationshipBasis = !/(未识别|没有明确|未检索|暂无)/.test(`${relationship} ${topic}`);
  const risk = basis.risk_level || "--";

  return [
    `这句话：${message.content || "--"}`,
    "",
    "为什么我觉得你会这么说：",
    `1. 触发点是「${triggerText}」。这不是凭空插话，而是在接最后一个可回应的文字语境。`,
    recentLines ? `2. 最近上下文是：\n${recentLines}` : "2. 最近上下文不足，所以只能轻量接话，不展开长判断。",
    `3. 这句话的互动功能是：${replyMoves.join("；")}。`,
    hasRelationshipBasis
      ? `4. 关系/话题底座：${relationship}；${topic}。所以它更像基于已有画像的熟人接话，而不是客服式回答。`
      : `4. 关系/话题底座不足：${relationship}；${topic}。所以这次不能声称“因为熟悉这个人”，只能说明它依赖群聊上下文、短句形态和低风险边界。`,
    `5. 风险边界：${risk}。这里没有扩大承诺、没有连续抢话，也没有把话题硬转成结论。`,
    triggerReasons.length ? `6. 触发逻辑：${triggerReasons.join("；")}。` : "6. 触发逻辑：没有额外关键词，只按群监控语境判断。",
  ].join("\n");
}

function renderProfile() {
  updateComposerMode();
  if (isGroupConversationMode()) {
    profileName.textContent = "群监控模式";
    profileSubtitle.textContent = `正在沉淀「${readMonitorConfig().groupName || "未命名群"}」的文字上下文。`;
    setRisk(permissionBadge, "");
    permissionBadge.textContent = "--";
    relationshipPositioning.textContent = "--";
    callEvidence.textContent = "--";
    frequentTopics.textContent = "--";
    mainScenes.textContent = "--";
    permissionText.textContent = "--";
    dyadicProfileText.textContent = "--";
    composerHint.textContent = "点击生成后，模型读取当前群聊上下文，候选回复只写入输入框，不会自动发送。";
    contactModeBadge.textContent = "群监控";
    contactModeBadge.className = "mode-badge mode-ok";
    modeInput.disabled = false;
    return;
  }

  if (!selectedPerson) {
    profileName.textContent = "选择联系人";
    profileSubtitle.textContent = "从左侧关系链选择一个人。";
    setRisk(permissionBadge, "");
    relationshipPositioning.textContent = "--";
    callEvidence.textContent = "--";
    frequentTopics.textContent = "--";
    mainScenes.textContent = "--";
    permissionText.textContent = "--";
    dyadicProfileText.textContent = "--";
    composerHint.textContent = "选择联系人后输入场景。";
    contactModeBadge.textContent = "未选择";
    contactModeBadge.className = "mode-badge";
    modeInput.disabled = false;
    return;
  }

  const permission = selectedPerson.permission || {};
  const isDirect = selectedPerson.group === "direct";
  profileName.textContent = selectedPerson.display_name || selectedPerson.query;
  profileSubtitle.textContent = `${selectedPerson.objective_relationship || "未知"} · ${
    selectedPerson.node_type || "未知"
  } · 总量 ${selectedPerson.communication_total || 0} 条 · 日均 ${Number(
    selectedPerson.communication_daily_average || 0,
  ).toFixed(2)} 条 · ${
    selectedPerson.call_name || "称呼待审计"
  }`;
  setRisk(permissionBadge, permission.can_proactively_suggest ? "R1_low" : "R3_high");
  permissionBadge.textContent = permission.can_proactively_suggest ? "可建议主动" : "仅确认后";
  relationshipPositioning.textContent = compactText(selectedPerson.relationship_positioning);
  callEvidence.textContent = compactText(
    selectedPerson.call_evidence,
    selectedPerson.has_call_evidence ? "有称呼证据" : "暂无称呼证据，建议审计",
  );
  frequentTopics.textContent = compactText(selectedPerson.frequent_topics || selectedPerson.interest_circles);
  mainScenes.textContent = compactText(selectedPerson.main_scenes);
  permissionText.textContent = [
    permission.note || "--",
    `学习样本：${selectedPerson.communication_total || 0} 条`,
    `样本跨度：${selectedPerson.communication_date_span || "暂无"}`,
    `检索上下文：${permission.can_retrieve_context ? "是" : "否"}`,
    `生成草稿：${permission.can_generate_draft ? "是" : "否"}`,
    `主动建议：${permission.can_proactively_suggest ? "是" : "否"}`,
    `自动发送：${permission.can_auto_send ? "是" : "否"}`,
  ].join("；");
  const dyadic = selectedPerson.dyadic_profile || {};
  dyadicProfileText.textContent = dyadic.available
    ? [
        `置信度：${dyadic.confidence_level}`,
        `私聊样本：${dyadic.private_outgoing_count}/${dyadic.private_incoming_count}`,
        `群聊定向：${dyadic.group_directed_outgoing_count}/${dyadic.group_directed_incoming_count}`,
        `平均/中位字数：${dyadic.average_chars}/${dyadic.median_chars}`,
        `连续发送：${dyadic.average_burst_size}`,
        `主动开启：${dyadic.initiation_ratio}`,
        `主要话题：${(dyadic.top_topics || []).join("、") || "不足"}`,
        ...(dyadic.limitations || []),
      ].join("；")
    : "暂无可用的双人定向画像，模型必须保守生成，不使用关系大类模板补齐。";

  if (isDirect) {
    composerHint.textContent = "可基于关系链生成草稿；发送前仍需你确认。";
    contactModeBadge.textContent = "可草稿";
    contactModeBadge.className = "mode-badge mode-ok";
    modeInput.disabled = false;
  } else {
    composerHint.textContent = "该人物只是被提及节点，只能用于观察和身份校对。";
    contactModeBadge.textContent = "观察";
    contactModeBadge.className = "mode-badge mode-warn";
    modeInput.value = "observe";
    modeInput.disabled = true;
  }
}

async function loadPeople() {
  try {
    const response = await fetch("/api/people");
    const data = await response.json();
    if (!data.ok) {
      throw new Error("people api failed");
    }
    people = data.people || [];
    selectedPerson = people[0] || null;
    renderCategoryOptions();
    renderPeopleList();
    renderProfile();
    renderConversation();
  } catch {
    peopleMeta.textContent = "加载失败";
    peopleBreakdown.textContent = "--";
    peopleList.innerHTML = '<div class="empty-list">关系链加载失败</div>';
  }
}

function renderList(element, items, emptyText = "暂无") {
  element.innerHTML = "";
  if (!items || items.length === 0) {
    const item = document.createElement("li");
    item.textContent = emptyText;
    element.appendChild(item);
    return;
  }
  for (const value of items) {
    const item = document.createElement("li");
    item.textContent = value;
    element.appendChild(item);
  }
}

function renderCandidates(candidates) {
  if (!candidates || candidates.length === 0) {
    renderList(candidatesList, [], "暂无");
    return;
  }
  renderList(
    candidatesList,
    candidates.map(
      (candidate) =>
        `${candidate.display_name} · ${candidate.objective_relationship} · score ${candidate.match_score}`,
    ),
  );
}

function resetDraftArea() {
  draftText.textContent = isGroupConversationMode()
    ? "点击“生成我的下一条回复”，模型会读取当前群聊上下文并把候选写入上方输入框。"
    : selectedPerson
      ? "生成的回复会直接加入上方对话。"
      : "先从左侧选择联系人。";
  toneBasis.textContent = "等待输入";
  relationshipBasis.textContent = "--";
  topicBasis.textContent = "--";
  setRisk(riskBadge, "");
  renderList(questionsList, []);
  renderCandidates([]);
}

function renderResult(result) {
  draftText.textContent = result.draft_text || "";
  toneBasis.textContent = result.tone_basis || "无";
  relationshipBasis.textContent = result.relationship_basis || "--";
  topicBasis.textContent = result.topic_basis || "--";
  setRisk(riskBadge, result.risk_level);
  renderList(questionsList, result.questions_for_user || []);
  renderCandidates(result.candidates || []);
}

function groupGenerationHistory() {
  const filtered = currentHistory().filter(
    (message) =>
      message.source !== "group_monitor_model" || message.basis?.status === "sent_by_group_monitor",
  );
  const deduped = [];
  for (const message of filtered) {
    const previous = deduped[deduped.length - 1];
    const seconds = previous
      ? (parseBridgeTime(message.occurredAt) - parseBridgeTime(previous.occurredAt)) / 1000
      : Number.POSITIVE_INFINITY;
    if (
      previous &&
      previous.sender === message.sender &&
      previous.content === message.content &&
      seconds >= 0 &&
      seconds <= 60
    ) {
      continue;
    }
    deduped.push(message);
  }
  if (deduped.length === 0) return [];
  const latestTime = parseBridgeTime(deduped[deduped.length - 1].occurredAt);
  const recent = [];
  let newerTime = latestTime;
  for (let index = deduped.length - 1; index >= 0 && recent.length < 40; index -= 1) {
    const message = deduped[index];
    const messageTime = parseBridgeTime(message.occurredAt);
    if (latestTime && messageTime && latestTime - messageTime > 3600000) break;
    if (newerTime && messageTime && newerTime - messageTime > 900000) break;
    recent.push(message);
    newerTime = messageTime;
  }
  return recent.reverse();
}

function latestIncomingMessage(history) {
  return [...history].reverse().find((message) => message.role !== "self") || history[history.length - 1];
}

function modelConversationHistory(history) {
  return history.slice(-40).map(({ role, content, sender }) => ({
    role,
    content: role === "self" || !sender ? content : `[${sender}] ${content}`,
  }));
}

async function submitGroupDraft(apiKey) {
  await syncGroupMonitorConversation();
  const history = groupGenerationHistory();
  if (history.length === 0) {
    draftText.textContent = "还没有抓到可用的群聊文字上下文。先启动监控，等消息出现在上方后再生成。";
    toneBasis.textContent = "等待群聊上下文";
    relationshipBasis.textContent = "--";
    topicBasis.textContent = "--";
    setRisk(riskBadge, "");
    renderList(questionsList, ["图片、表情、文件和未实际发送的模型草稿不会作为本次上下文。"]);
    renderCandidates([]);
    return;
  }

  const latestIncoming = latestIncomingMessage(history);
  const groupName = readMonitorConfig().groupName;
  submitButton.disabled = true;
  submitButton.textContent = "正在读取上下文并生成";
  draftText.textContent = "模型正在根据当前群聊上下文生成候选回复。";
  toneBasis.textContent = "人工触发 · 不受自动回复阈值影响";

  const payload = {
    query: latestIncoming?.sender || groupName || "群聊联系人",
    scenario: latestIncoming?.content || history[history.length - 1].content,
    conversation_history: modelConversationHistory(history),
    poe_api_key: apiKey,
    poe_model: poeModelInput.value.trim(),
    intent: intentInput.value,
    mode: "draft",
    allow_no_reply: false,
    response_policy: "active_group",
    factuality_guard: true,
    trusted_group: true,
  };

  try {
    const response = await fetch("/api/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "生成失败");

    renderResult(data.result);
    const generated = data.result.draft_text || "";
    if (data.result.tone_basis === "poe_model_failed_no_fallback" || !generated) {
      scenarioInput.value = "";
      throw new Error(data.result.questions_for_user?.[0] || "模型没有返回候选回复");
    }

    scenarioInput.value = generated;
    toneBasis.textContent = "人工触发 · 强制给出最佳候选";
    draftText.textContent = [
      `已读取最近连续的 ${Math.min(history.length, 40)} 条有效文字上下文。`,
      `最后接话对象：${latestIncoming?.sender || "未识别"}。`,
      "本次绕过自动回复阈值，只评估模型能生成什么；候选已放入上方输入框，不会自动发送。",
    ].join("\n");
    renderList(questionsList, [
      ...(data.result.questions_for_user || []),
      "未实际发送的历史模型草稿已从上下文排除。",
    ]);
    scenarioInput.focus();
  } catch (error) {
    draftText.textContent = `生成失败：${error.message}`;
    toneBasis.textContent = "error";
    relationshipBasis.textContent = "--";
    topicBasis.textContent = "--";
    setRisk(riskBadge, "R3_high");
    renderList(questionsList, ["检查 Poe API Key、模型名称和本地服务状态。"]);
    renderCandidates([]);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "生成我的下一条回复";
  }
}

async function submitDraft(event) {
  event.preventDefault();
  const apiKey = poeApiKeyInput.value.trim();
  if (!apiKey) {
    draftText.textContent = "先在页面顶部输入 Poe API Key。\n没有 Key 不生成正文，避免再回到模板假输出。";
    toneBasis.textContent = "poe_api_key_required";
    relationshipBasis.textContent = "--";
    topicBasis.textContent = "--";
    setRisk(riskBadge, "R3_high");
    renderList(questionsList, ["请输入 Poe API Key 后再生成。"]);
    renderCandidates([]);
    poeApiKeyInput.focus();
    return;
  }
  if (isGroupConversationMode()) {
    await submitGroupDraft(apiKey);
    return;
  }
  if (!selectedPerson) {
    resetDraftArea();
    renderList(questionsList, ["先从左侧选择联系人"]);
    return;
  }

  const pendingText = scenarioInput.value.trim();
  if (pendingText) addMessage(pendingText, activeSpeaker);
  const history = currentHistory();
  if (history.length === 0) {
    draftText.textContent = "先加入至少一条对话消息，模型才有上下文。";
    scenarioInput.focus();
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "生成中";

  const payload = {
    query: selectedPerson.query,
    scenario: history[history.length - 1].content,
    conversation_history: history.map(({ role, content }) => ({ role, content })),
    poe_api_key: apiKey,
    poe_model: poeModelInput.value.trim(),
    intent: intentInput.value,
    mode: selectedPerson.group === "direct" ? modeInput.value : "observe",
  };

  try {
    const response = await fetch("/api/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!data.ok) {
      throw new Error(data.error || "生成失败");
    }
    renderResult(data.result);
    if (data.result.tone_basis !== "poe_model_failed_no_fallback") {
      for (const segment of draftSegments(data.result)) {
        addMessage(segment, "self", "model");
      }
      setActiveSpeaker("contact");
    }
  } catch (error) {
    draftText.textContent = `生成失败：${error.message}`;
    toneBasis.textContent = "error";
    relationshipBasis.textContent = "--";
    topicBasis.textContent = "--";
    setRisk(riskBadge, "R3_high");
    renderList(questionsList, ["检查输入和本地服务状态"]);
    renderCandidates([]);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "生成我的下一条回复";
  }
}

function clearForm() {
  if (isGroupConversationMode()) {
    conversationHistories.set(GROUP_CONVERSATION_KEY, []);
    activeBasisMessageId = "";
  } else if (selectedPerson) {
    conversationHistories.set(selectedPerson.id, []);
  }
  scenarioInput.value = "";
  intentInput.value = "work_discussion";
  modeInput.value = "draft";
  resetDraftArea();
  renderConversation();
  scenarioInput.focus();
}

form.addEventListener("submit", submitDraft);
clearButton.addEventListener("click", clearForm);
addMessageButton.addEventListener("click", () => addMessage());
speakerButtons.forEach((button) => button.addEventListener("click", () => setActiveSpeaker(button.dataset.speaker)));
poeApiKeyInput.addEventListener("change", cachePoeSettings);
poeApiKeyInput.addEventListener("blur", cachePoeSettings);
poeModelInput.addEventListener("change", cachePoeSettings);
poeModelInput.addEventListener("blur", cachePoeSettings);
clearPoeApiKeyButton.addEventListener("click", clearPoeSettings);
groupMonitorButton.addEventListener("click", toggleGroupMonitor);
groupReplyModeInput.addEventListener("change", () => {
  cacheMonitorConfig();
  if (!groupMonitorRunning) {
    const labels = { observe: "只读", draft: "自动草稿", send: "自动发送" };
    setGroupMonitorUi("idle", `待启动：${labels[groupReplyModeInput.value]}`);
  }
});
[monitorGroupNameInput, monitorSelfNameInput, replySettleSecondsInput, replyCooldownSecondsInput].forEach((input) => {
  input.addEventListener("change", cacheMonitorConfig);
  input.addEventListener("blur", cacheMonitorConfig);
});
personFilterInput.addEventListener("input", renderPeopleList);
categoryFilterInput.addEventListener("change", () => {
  activeCategory = categoryFilterInput.value;
  renderPeopleList();
});
for (const button of segmentButtons) {
  button.addEventListener("click", () => {
    activeScope = button.dataset.filter;
    segmentButtons.forEach((item) => item.classList.toggle("active", item === button));
    renderPeopleList();
  });
}
scenarioInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    form.requestSubmit();
  }
});

restorePoeSettings();
checkHealth();
refreshGroupMonitorStatus();
setInterval(refreshGroupMonitorStatus, 5000);
loadPeople();
