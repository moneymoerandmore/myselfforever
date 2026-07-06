const poeApiKeyInput = document.querySelector("#poeApiKey");
const poeModelInput = document.querySelector("#poeModel");
const newsTextInput = document.querySelector("#newsText");
const userAlignmentInput = document.querySelector("#userAlignment");
const clearButton = document.querySelector("#clearButton");
const fetchNewsButton = document.querySelector("#fetchNewsButton");
const analyzeButton = document.querySelector("#analyzeButton");
const mergeCandidateButton = document.querySelector("#mergeCandidateButton");
const confirmButton = document.querySelector("#confirmButton");
const resultMeta = document.querySelector("#resultMeta");
const analysisText = document.querySelector("#analysisText");
const confirmMeta = document.querySelector("#confirmMeta");
const candidateList = document.querySelector("#candidateList");
const newsList = document.querySelector("#newsList");
const newsDetail = document.querySelector("#newsDetail");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";

let lastAnalysis = null;
let fetchedNewsItems = [];
let selectedNewsIndex = 0;
let alignmentNotesByNewsId = {};

function restoreSettings() {
  try {
    poeApiKeyInput.value = localStorage.getItem(POE_API_KEY_STORAGE_KEY) || "";
    poeModelInput.value = localStorage.getItem(POE_MODEL_STORAGE_KEY) || "GPT-4o";
  } catch {
    // Local storage can be unavailable.
  }
}

function cacheSettings() {
  try {
    const key = poeApiKeyInput.value.trim();
    const model = poeModelInput.value.trim();
    if (key) localStorage.setItem(POE_API_KEY_STORAGE_KEY, key);
    else localStorage.removeItem(POE_API_KEY_STORAGE_KEY);
    if (model) localStorage.setItem(POE_MODEL_STORAGE_KEY, model);
  } catch {
    // Keep page state only.
  }
}

function emptyNode(text) {
  const node = document.createElement("div");
  node.className = "empty";
  node.textContent = text;
  return node;
}

function currentNewsItem() {
  return fetchedNewsItems[selectedNewsIndex] || null;
}

function currentNewsId() {
  return currentNewsItem()?.news_id || "";
}

function saveCurrentAlignmentNote() {
  const id = currentNewsId();
  if (!id) return;
  alignmentNotesByNewsId[id] = userAlignmentInput.value.trim();
}

function loadCurrentAlignmentNote() {
  const id = currentNewsId();
  userAlignmentInput.value = id ? alignmentNotesByNewsId[id] || "" : "";
}

function buildUserAlignmentText() {
  saveCurrentAlignmentNote();
  return fetchedNewsItems
    .map((item, index) => {
      const note = alignmentNotesByNewsId[item.news_id]?.trim();
      return note ? `${index + 1}. ${item.title || item.news_id}\n${note}` : "";
    })
    .filter(Boolean)
    .join("\n\n");
}

function buildUserAlignmentByNewsId() {
  saveCurrentAlignmentNote();
  return Object.fromEntries(
    Object.entries(alignmentNotesByNewsId).filter(([, note]) => note?.trim())
  );
}

function candidateSourceIds(item) {
  return Array.isArray(item.source_news_ids) ? item.source_news_ids : [];
}

function renderNewsBrowser() {
  newsList.innerHTML = "";
  if (!fetchedNewsItems.length) {
    newsDetail.className = "news-detail empty";
    newsDetail.textContent = "自动拉取后，详情会显示在这里。";
    userAlignmentInput.value = "";
    return;
  }

  selectedNewsIndex = Math.min(Math.max(selectedNewsIndex, 0), fetchedNewsItems.length - 1);
  fetchedNewsItems.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `news-tab${index === selectedNewsIndex ? " active" : ""}`;
    button.innerHTML = `<span>${index + 1}</span><strong></strong>`;
    button.querySelector("strong").textContent = item.title || item.news_id || "未命名新闻";
    button.addEventListener("click", () => {
      saveCurrentAlignmentNote();
      selectedNewsIndex = index;
      renderNewsBrowser();
      renderAnalysisForSelected();
      renderCandidates(lastAnalysis || {});
    });
    newsList.appendChild(button);
  });

  const item = currentNewsItem();
  const hasFallbackDetail = item.detail && item.detail_status && item.detail_status !== "ok";
  const rows = hasFallbackDetail
    ? [item.detail]
    : [
        item.title ? `标题：${item.title}` : "",
        item.tags ? `标签：${item.tags}` : "",
        item.interest_category_label ? `兴趣类别：${item.interest_category_label}` : "",
        item.published_at ? `时间：${item.published_at}` : "",
        item.source ? `来源：${item.source}` : "",
        item.source_url ? `来源站点：${item.source_url}` : "",
        item.detail_status ? `正文状态：${item.detail_status}` : "",
        item.summary ? `摘要：${item.summary}` : "",
        item.detail
          ? `详情：\n${item.detail}`
          : `详情：暂未抽取到正文详情（${item.detail_status || "unknown"}）。可以点来源链接查看原文。`,
        item.url ? `聚合链接：${item.url}` : "",
      ].filter(Boolean);
  const modelRows = [
    item.conflict_axis ? `模型冲突轴：${item.conflict_axis}` : "",
    item.alignment_value_reason ? `模型选题理由：${item.alignment_value_reason}` : "",
    item.diversity_reason ? `多样性理由：${item.diversity_reason}` : "",
    item.model_discussion_score ? `模型可讨论分：${item.model_discussion_score}` : "",
  ].filter(Boolean);
  if (modelRows.length) rows.splice(Math.min(rows.length, 5), 0, ...modelRows);
  newsDetail.className = "news-detail";
  newsDetail.textContent = rows.join("\n\n");
  loadCurrentAlignmentNote();
}

function analysisForCurrentNews() {
  const id = currentNewsId();
  const rows = Array.isArray(lastAnalysis?.selected_news) ? lastAnalysis.selected_news : [];
  return rows.find((item) => item.news_id === id) || null;
}

function renderAnalysisForSelected() {
  if (!lastAnalysis) {
    analysisText.textContent = fetchedNewsItems.length
      ? "已拉取新闻。下一步点击“生成对齐分析”，让数字“我”逐条输出观点。"
      : "分析结果会显示在这里。";
    return;
  }

  const item = analysisForCurrentNews();
  if (!item) {
    analysisText.textContent = [
      `今日摘要：${lastAnalysis.daily_summary || "--"}`,
      "",
      "当前新闻还没有对应初判。可以补充校对意见后重新生成。",
    ].join("\n");
    return;
  }

  analysisText.textContent = [
    `事实：${item.fact_summary || "--"}`,
    `为什么关心：${item.why_user_may_care || "--"}`,
    `第一反应：${item.first_reaction || "--"}`,
    `我的观点：${item.my_viewpoint || item.first_reaction || "--"}`,
    item.deep_viewpoint ? `深度初判：${item.deep_viewpoint}` : "",
    item.selfcore_basis?.length ? `SelfCore 依据：${item.selfcore_basis.join("；")}` : "",
    `判断框架：${item.judgment_frame || "--"}`,
    item.possible_user_disagreement ? `可能需要你校对的分歧：${item.possible_user_disagreement}` : "",
    item.boundary_conditions?.length ? `判断边界：${item.boundary_conditions.join("；")}` : "",
    item.attitude_markers?.length ? `态度标记：${item.attitude_markers.join("；")}` : "",
    `不确定性：${(item.uncertainties || []).join("；") || "--"}`,
    `想问你：${(item.questions_for_user || []).join("；") || "--"}`,
    `可以和谁聊：${(item.can_discuss_with || []).join("；") || "--"}`,
    `不适合聊给谁：${(item.not_for || []).join("；") || "--"}`,
    `长期更新：${item.long_term_update || "none"}`,
  ].join("\n\n");
}

function renderCandidates(result) {
  candidateList.innerHTML = "";
  const allCandidates = Array.isArray(result.calibration_candidates) ? result.calibration_candidates : [];
  const id = currentNewsId();
  const candidates = id ? allCandidates.filter((item) => candidateSourceIds(item).includes(id)) : allCandidates;
  if (!candidates.length) {
    candidateList.appendChild(emptyNode("当前新闻没有可确认的 SelfCore 候选。"));
    confirmMeta.textContent = "可以在校对说明里补充你的真实观点后重新生成。";
    return;
  }

  confirmMeta.textContent = `当前新闻 ${candidates.length} 条候选，默认只勾选模型认为需要确认的项。`;
  for (const item of candidates) {
    const card = document.createElement("article");
    card.className = "candidate-card";
    card.dataset.index = String(allCandidates.indexOf(item));

    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "candidate-check";
    checkbox.checked = item.needs_user_confirmation !== false;
    const title = document.createElement("strong");
    title.textContent = `${item.target || "self_understanding"} / ${item.confidence || "medium"}`;
    label.append(checkbox, title);

    const textarea = document.createElement("textarea");
    textarea.className = "candidate-text";
    textarea.value = item.candidate || "";

    const meta = document.createElement("div");
    meta.className = "meta";
    const extraMeta = [
      item.model_called ? `模型：Poe 已调用（${item.model_name || item.poe_model || "未记录模型名"}）` : "",
      item.merge_engine ? `生成来源：${item.merge_engine}` : "",
      item.model_call_at ? `调用时间：${item.model_call_at}` : "",
      item.evidence ? `证据：${item.evidence}` : "",
      item.delta_from_digital_self ? `校正：${item.delta_from_digital_self}` : "",
      item.why_selfcore_relevant ? `入池理由：${item.why_selfcore_relevant}` : "",
    ].filter(Boolean);
    meta.textContent = `新闻来源：${candidateSourceIds(item).join(", ") || "--"} · ${extraMeta.join(" · ") || "暂无证据"}`;

    card.append(label, textarea, meta);
    candidateList.appendChild(card);
  }
}

function ensureAnalysisCandidateStore() {
  if (!lastAnalysis) {
    lastAnalysis = {
      id: `local-news-align-${Date.now()}`,
      news_count: fetchedNewsItems.length,
      daily_summary: "",
      selected_news: [],
      calibration_candidates: [],
    };
  }
  if (!Array.isArray(lastAnalysis.calibration_candidates)) {
    lastAnalysis.calibration_candidates = [];
  }
}

async function mergeCurrentAlignmentToCandidate() {
  saveCurrentAlignmentNote();
  cacheSettings();
  const newsItem = currentNewsItem();
  const note = userAlignmentInput.value.trim();
  if (!newsItem) {
    confirmMeta.textContent = "先选择一条新闻";
    return;
  }
  if (!note) {
    confirmMeta.textContent = "先在“我的校对”里写下你的真实判断";
    userAlignmentInput.focus();
    return;
  }
  if (!lastAnalysis || !analysisForCurrentNews()) {
    confirmMeta.textContent = "先生成数字“我”的初判，再合并成候选";
    return;
  }
  if (!poeApiKeyInput.value.trim()) {
    confirmMeta.textContent = "需要 Poe API Key 才能融合生成候选";
    poeApiKeyInput.focus();
    return;
  }

  ensureAnalysisCandidateStore();
  const newsId = currentNewsId();
  const analysisItem = analysisForCurrentNews();
  mergeCandidateButton.disabled = true;
  confirmMeta.textContent = "正在融合你的校对和数字“我”的初判，生成 SelfCore 候选...";
  try {
    const response = await fetch("/api/news-alignment/merge-candidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        news_item: newsItem,
        analysis_item: analysisItem,
        user_alignment: note,
        poe_api_key: poeApiKeyInput.value.trim(),
        poe_model: poeModelInput.value.trim(),
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "候选融合失败");
    const candidate = data.result;
    const existingIndex = lastAnalysis.calibration_candidates.findIndex(
      (item) => item.created_by === "model_alignment_merge" && candidateSourceIds(item).includes(newsId)
    );
    if (existingIndex >= 0) {
      lastAnalysis.calibration_candidates[existingIndex] = candidate;
    } else {
      lastAnalysis.calibration_candidates.push(candidate);
    }
    renderCandidates(lastAnalysis);
    const modelStatus = candidate.model_called
      ? `Poe 已调用（${candidate.model_name || "未记录模型名"}）`
      : "未记录到 Poe 调用";
    confirmMeta.textContent = `已融合生成候选：${modelStatus}；可继续编辑右侧候选文本后写入候选池。`;
  } catch (error) {
    confirmMeta.textContent = `候选融合失败：${error.message}`;
  } finally {
    mergeCandidateButton.disabled = false;
  }
}

function selectedConfirmations() {
  const source = Array.isArray(lastAnalysis?.calibration_candidates) ? lastAnalysis.calibration_candidates : [];
  return Array.from(candidateList.querySelectorAll(".candidate-card"))
    .filter((card) => card.querySelector(".candidate-check")?.checked)
    .map((card) => {
      const index = Number(card.dataset.index || 0);
      const original = source[index] || {};
      return {
        ...original,
        candidate: card.querySelector(".candidate-text")?.value.trim() || "",
      };
    })
    .filter((item) => item.candidate);
}

async function analyzeNews() {
  cacheSettings();
  const newsText = newsTextInput.value.trim();
  if (!newsText && !fetchedNewsItems.length) {
    resultMeta.textContent = "先粘贴或自动拉取今天的 10 条新闻";
    return;
  }
  if (!poeApiKeyInput.value.trim()) {
    resultMeta.textContent = "需要 Poe API Key 才能生成对齐分析";
    poeApiKeyInput.focus();
    return;
  }

  analyzeButton.disabled = true;
  resultMeta.textContent = "正在生成新闻对齐分析...";
  analysisText.textContent = "模型正在根据 SelfCore、新闻事实和你的补充生成逐条初判。";
  candidateList.innerHTML = "";
  try {
    const response = await fetch("/api/news-alignment/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        news_items: fetchedNewsItems,
        news_text: newsText,
        user_alignment: buildUserAlignmentText(),
        user_alignment_by_news_id: buildUserAlignmentByNewsId(),
        poe_api_key: poeApiKeyInput.value.trim(),
        poe_model: poeModelInput.value.trim(),
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "生成失败");
    lastAnalysis = data.result;
    resultMeta.textContent = `${data.result.news_count || 0} 条新闻 · 记录 ${data.result.id || "--"}`;
    renderAnalysisForSelected();
    renderCandidates(data.result);
  } catch (error) {
    lastAnalysis = null;
    resultMeta.textContent = `生成失败：${error.message}`;
    analysisText.textContent = [
      `具体错误：${error.message}`,
      "",
      "这通常表示 Poe API Key 无效/过期、模型名不可用、新闻输入为空，或模型返回内容不是合法 JSON。",
    ].join("\n");
    candidateList.innerHTML = "";
    candidateList.appendChild(emptyNode("没有可确认候选。"));
  } finally {
    analyzeButton.disabled = false;
  }
}

function renderFetchedNews(items) {
  fetchedNewsItems = items;
  selectedNewsIndex = 0;
  lastAnalysis = null;
  alignmentNotesByNewsId = {};
  newsTextInput.value = items
    .map((item, index) => {
      return [
        `${index + 1}. ${item.title || ""}`,
        item.summary ? `摘要：${item.summary}` : "",
        item.detail ? `详情：${item.detail}` : "",
        item.source ? `来源：${item.source}` : "",
        item.source_url ? `来源站点：${item.source_url}` : "",
        item.published_at ? `时间：${item.published_at}` : "",
        item.tags ? `标签：${item.tags}` : "",
        item.url ? `链接：${item.url}` : "",
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n\n");
  renderNewsBrowser();
  renderAnalysisForSelected();
  renderCandidates({});
}

async function fetchNews() {
  cacheSettings();
  fetchNewsButton.disabled = true;
  resultMeta.textContent = "正在拉取可讨论新闻...";
  try {
    const key = poeApiKeyInput.value.trim();
    const response = await fetch("/api/news-alignment/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 10,
        poe_api_key: key,
        poe_model: poeModelInput.value.trim(),
        use_model_screening: Boolean(key),
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "拉取失败");
    const items = data.result?.news_items || [];
    renderFetchedNews(items);
    const screeningText = data.result?.model_screening
      ? `；模型精筛，候选池 ${data.result.candidate_pool_count || items.length} 条`
      : "；代码粗筛（未提供 Poe Key）";
    const diversityText = data.result?.diversity_rerank ? "；已做兴趣类别多样性重排" : "";
    const sourceErrorText = data.result?.errors?.length ? `；部分源失败：${data.result.errors.join("；")}` : "";
    resultMeta.textContent = `已拉取 ${items.length} 条可讨论新闻${screeningText}${diversityText}${sourceErrorText}`;
  } catch (error) {
    resultMeta.textContent = `拉取失败：${error.message}`;
    analysisText.textContent = "可以手动粘贴 10 条新闻继续对齐。";
  } finally {
    fetchNewsButton.disabled = false;
  }
}

async function confirmCandidates() {
  const confirmations = selectedConfirmations();
  if (!lastAnalysis || !confirmations.length) {
    confirmMeta.textContent = "先生成分析，并勾选要写入候选池的项";
    return;
  }

  confirmButton.disabled = true;
  confirmMeta.textContent = "正在写入 SelfCore 候选池...";
  try {
    const response = await fetch("/api/news-alignment/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirmations,
        source_saved_path: lastAnalysis.saved_path,
        analysis_summary: lastAnalysis.daily_summary || "",
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "写入失败");
    confirmMeta.textContent = `已写入 ${data.result?.injected_count || confirmations.length} 条候选；可去新闻候选池合并。`;
  } catch (error) {
    confirmMeta.textContent = `写入失败：${error.message}`;
  } finally {
    confirmButton.disabled = false;
  }
}

clearButton.addEventListener("click", () => {
  newsTextInput.value = "";
  userAlignmentInput.value = "";
  fetchedNewsItems = [];
  selectedNewsIndex = 0;
  alignmentNotesByNewsId = {};
  lastAnalysis = null;
  resultMeta.textContent = "等待输入";
  confirmMeta.textContent = "只写入你勾选确认的候选。";
  candidateList.innerHTML = "";
  candidateList.appendChild(emptyNode("生成分析后会出现候选。"));
  renderNewsBrowser();
  renderAnalysisForSelected();
});

newsTextInput.addEventListener("input", () => {
  fetchedNewsItems = [];
  selectedNewsIndex = 0;
  alignmentNotesByNewsId = {};
  lastAnalysis = null;
  renderNewsBrowser();
  renderAnalysisForSelected();
  renderCandidates({});
});
userAlignmentInput.addEventListener("input", saveCurrentAlignmentNote);

analyzeButton.addEventListener("click", analyzeNews);
fetchNewsButton.addEventListener("click", fetchNews);
mergeCandidateButton.addEventListener("click", mergeCurrentAlignmentToCandidate);
confirmButton.addEventListener("click", confirmCandidates);
poeApiKeyInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);

restoreSettings();
renderNewsBrowser();
renderAnalysisForSelected();
candidateList.appendChild(emptyNode("生成分析后会出现候选。"));
