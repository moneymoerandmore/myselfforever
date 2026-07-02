const poeApiKeyInput = document.querySelector("#poeApiKey");
const poeModelInput = document.querySelector("#poeModel");
const newsTextInput = document.querySelector("#newsText");
const userAlignmentInput = document.querySelector("#userAlignment");
const clearButton = document.querySelector("#clearButton");
const analyzeButton = document.querySelector("#analyzeButton");
const confirmButton = document.querySelector("#confirmButton");
const resultMeta = document.querySelector("#resultMeta");
const analysisText = document.querySelector("#analysisText");
const confirmMeta = document.querySelector("#confirmMeta");
const candidateList = document.querySelector("#candidateList");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";

let lastAnalysis = null;

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

function stringifyAnalysis(result) {
  const sections = [];
  sections.push(`今日摘要：\n${result.daily_summary || "--"}`);
  const selected = Array.isArray(result.selected_news) ? result.selected_news : [];
  if (selected.length) {
    sections.push(
      selected
        .map((item, index) => {
          return [
            `${index + 1}. ${item.title || item.news_id || "新闻"}`,
            `事实：${item.fact_summary || "--"}`,
            `为什么关心：${item.why_user_may_care || "--"}`,
            `第一反应：${item.first_reaction || "--"}`,
            `判断框架：${item.judgment_frame || "--"}`,
            `不确定性：${(item.uncertainties || []).join("；") || "--"}`,
            `追问：${(item.questions_for_user || []).join("；") || "--"}`,
            `长期更新：${item.long_term_update || "none"}`,
          ].join("\n");
        })
        .join("\n\n")
    );
  }
  const questions = Array.isArray(result.questions_for_user) ? result.questions_for_user : [];
  if (questions.length) sections.push(`跨新闻校对问题：\n${questions.map((item) => `- ${item}`).join("\n")}`);
  const outbound = Array.isArray(result.outbound_topic_signals) ? result.outbound_topic_signals : [];
  if (outbound.length) sections.push(`可交给对外主动沟通重新评估的话题：\n${outbound.map((item) => `- ${item}`).join("\n")}`);
  const risky = Array.isArray(result.rejected_or_risky) ? result.rejected_or_risky : [];
  if (risky.length) sections.push(`不沉淀/有风险：\n${risky.map((item) => `- ${item}`).join("\n")}`);
  return sections.join("\n\n");
}

function renderCandidates(result) {
  candidateList.innerHTML = "";
  const candidates = Array.isArray(result.calibration_candidates) ? result.calibration_candidates : [];
  if (!candidates.length) {
    candidateList.appendChild(emptyNode("本次没有可确认的 SelfCore 候选。"));
    confirmMeta.textContent = "可以补充你的校对意见后重新生成";
    return;
  }
  confirmMeta.textContent = `${candidates.length} 条候选，默认只勾选模型认为需要确认的项`;
  for (const [index, item] of candidates.entries()) {
    const card = document.createElement("article");
    card.className = "candidate-card";
    card.dataset.index = String(index);

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
    meta.textContent = `新闻来源：${(item.source_news_ids || []).join(", ") || "--"} · 证据：${item.evidence || "--"}`;

    card.append(label, textarea, meta);
    candidateList.appendChild(card);
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
  if (!newsText) {
    resultMeta.textContent = "先粘贴今天的 10 条新闻";
    return;
  }
  if (!poeApiKeyInput.value.trim()) {
    resultMeta.textContent = "需要 Poe API Key 才能生成对齐分析";
    poeApiKeyInput.focus();
    return;
  }
  analyzeButton.disabled = true;
  resultMeta.textContent = "正在生成新闻对齐分析...";
  analysisText.textContent = "模型正在根据 SelfCore、新闻事实和你的补充生成初判。";
  candidateList.innerHTML = "";
  try {
    const response = await fetch("/api/news-alignment/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        news_text: newsText,
        user_alignment: userAlignmentInput.value.trim(),
        poe_api_key: poeApiKeyInput.value.trim(),
        poe_model: poeModelInput.value.trim(),
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "生成失败");
    lastAnalysis = data.result;
    resultMeta.textContent = `${data.result.news_count || 0} 条新闻 · 记录 ${data.result.id || "--"}`;
    analysisText.textContent = stringifyAnalysis(data.result);
    renderCandidates(data.result);
  } catch (error) {
    lastAnalysis = null;
    resultMeta.textContent = `生成失败：${error.message}`;
    analysisText.textContent = "检查 Poe API Key、模型名和新闻输入后重试。";
    candidateList.innerHTML = "";
    candidateList.appendChild(emptyNode("没有可确认候选。"));
  } finally {
    analyzeButton.disabled = false;
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
    confirmMeta.textContent = `已写入 ${data.result?.injected_count || confirmations.length} 条候选；可去 SelfCore 候选页合并。`;
  } catch (error) {
    confirmMeta.textContent = `写入失败：${error.message}`;
  } finally {
    confirmButton.disabled = false;
  }
}

clearButton.addEventListener("click", () => {
  newsTextInput.value = "";
  userAlignmentInput.value = "";
  analysisText.textContent = "分析结果会显示在这里。";
  resultMeta.textContent = "等待输入";
  confirmMeta.textContent = "只写入你勾选确认的候选。";
  candidateList.innerHTML = "";
  lastAnalysis = null;
});
analyzeButton.addEventListener("click", analyzeNews);
confirmButton.addEventListener("click", confirmCandidates);
poeApiKeyInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);

restoreSettings();
candidateList.appendChild(emptyNode("生成分析后会出现候选。"));
