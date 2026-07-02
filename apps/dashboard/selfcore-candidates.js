const poeApiKeyInput = document.querySelector("#poeApiKey");
const poeModelInput = document.querySelector("#poeModel");
const useModelInput = document.querySelector("#useModel");
const refreshButton = document.querySelector("#refreshButton");
const mergeButton = document.querySelector("#mergeButton");
const selectAllButton = document.querySelector("#selectAllButton");
const injectButton = document.querySelector("#injectButton");
const pendingCount = document.querySelector("#pendingCount");
const totalCount = document.querySelector("#totalCount");
const proposalCount = document.querySelector("#proposalCount");
const candidateMeta = document.querySelector("#candidateMeta");
const proposalMeta = document.querySelector("#proposalMeta");
const injectMeta = document.querySelector("#injectMeta");
const candidateList = document.querySelector("#candidateList");
const proposalList = document.querySelector("#proposalList");
const injectPreview = document.querySelector("#injectPreview");

const POE_API_KEY_STORAGE_KEY = "digitalTwin.poeApiKey";
const POE_MODEL_STORAGE_KEY = "digitalTwin.poeModel";
const CANDIDATE_POOL = new URLSearchParams(window.location.search).get("pool") === "news_alignment"
  ? "news_alignment"
  : "multimodal";
const POOL_LABELS = {
  multimodal: "多模态画像候选池",
  news_alignment: "每日新闻对齐候选池",
};

let currentCandidates = [];
let currentProposals = [];

function applyPoolLabels() {
  const heading = document.querySelector(".topbar h1");
  const subtitle = document.querySelector(".topbar p");
  if (CANDIDATE_POOL === "news_alignment") {
    document.title = "新闻 SelfCore 候选池";
    if (heading) heading.textContent = "新闻 SelfCore 候选池";
    if (subtitle) subtitle.textContent = "汇总每日新闻对齐候选，合并特征，最终注入 SelfCore。";
  }
}

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

function renderCandidates() {
  candidateList.innerHTML = "";
  const pending = currentCandidates.filter((item) => !item.injected);
  pendingCount.textContent = String(pending.length);
  totalCount.textContent = String(currentCandidates.length);
  candidateMeta.textContent = `${POOL_LABELS[CANDIDATE_POOL]} · ${pending.length} 条待处理，${currentCandidates.length} 条总候选`;
  if (!currentCandidates.length) {
    const hint =
      CANDIDATE_POOL === "news_alignment"
        ? "暂无新闻对齐候选。先在每日新闻对齐页确认一些候选。"
        : "暂无 SelfCore 候选。先在多模态页确认一些候选。";
    candidateList.appendChild(emptyNode(hint));
    return;
  }
  for (const item of currentCandidates) {
    const card = document.createElement("article");
    card.className = `candidate-card${item.injected ? " injected" : ""}`;
    card.dataset.id = item.id;

    const head = document.createElement("div");
    head.className = "card-head";
    const label = document.createElement("label");
    label.className = "check-line";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "candidate-check";
    checkbox.disabled = item.injected;
    const labelText = document.createElement("span");
    labelText.textContent = item.injected ? "已注入" : "纳入合并";
    label.append(checkbox, labelText);
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = `${item.target || "self"} / ${item.confidence || "medium"}`;
    head.append(label, pill);

    const text = document.createElement("p");
    text.className = "candidate-text";
    text.textContent = item.candidate || "";
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `${item.created_at || "--"} · ${item.source_type || "candidate"} · ${item.id}`;
    card.append(head, text, meta);
    candidateList.appendChild(card);
  }
}

function selectedCandidateIds() {
  return Array.from(candidateList.querySelectorAll(".candidate-card"))
    .filter((card) => card.querySelector(".candidate-check")?.checked)
    .map((card) => card.dataset.id)
    .filter(Boolean);
}

function renderProposals() {
  proposalList.innerHTML = "";
  proposalCount.textContent = String(currentProposals.length);
  if (!currentProposals.length) {
    proposalList.appendChild(emptyNode("还没有合并提案。"));
    injectPreview.textContent = "等待合并提案。";
    return;
  }
  for (const proposal of currentProposals) {
    const card = document.createElement("article");
    card.className = "proposal-card";
    card.dataset.id = proposal.id;

    const head = document.createElement("div");
    head.className = "card-head";
    const label = document.createElement("label");
    label.className = "check-line";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "proposal-check";
    checkbox.checked = true;
    checkbox.addEventListener("change", updateInjectPreview);
    const labelText = document.createElement("span");
    labelText.textContent = proposal.title || "合并提案";
    label.append(checkbox, labelText);
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = `${proposal.section || "SelfCore"} / ${proposal.confidence || "medium"}`;
    head.append(label, pill);

    const textarea = document.createElement("textarea");
    textarea.className = "proposal-textarea";
    textarea.value = proposal.patch_text || proposal.merged_feature || "";
    textarea.addEventListener("input", updateInjectPreview);

    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `候选来源：${(proposal.candidate_ids || []).join(", ") || "--"}`;
    card.append(head, textarea, meta);
    proposalList.appendChild(card);
  }
  updateInjectPreview();
}

function collectSelectedProposals() {
  return Array.from(proposalList.querySelectorAll(".proposal-card"))
    .filter((card) => card.querySelector(".proposal-check")?.checked)
    .map((card) => {
      const source = currentProposals.find((item) => item.id === card.dataset.id) || {};
      return {
        ...source,
        patch_text: card.querySelector(".proposal-textarea")?.value.trim() || "",
      };
    })
    .filter((item) => item.patch_text);
}

function updateInjectPreview() {
  const selected = collectSelectedProposals();
  if (!selected.length) {
    injectPreview.textContent = "没有选中的提案。";
    injectMeta.textContent = "只会注入你勾选的提案";
    return;
  }
  injectMeta.textContent = `准备注入 ${selected.length} 条提案`;
  injectPreview.textContent = selected
    .map((item, index) => {
      return [`${index + 1}. ${item.title || item.section || "候选提案"}`, item.patch_text].join("\n");
    })
    .join("\n\n");
}

async function refreshCandidates() {
  refreshButton.disabled = true;
  candidateMeta.textContent = "正在读取候选池...";
  try {
    const response = await fetch(`/api/selfcore-candidates?pool=${encodeURIComponent(CANDIDATE_POOL)}`);
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "读取失败");
    currentCandidates = data.result?.candidates || [];
    renderCandidates();
  } catch (error) {
    candidateList.innerHTML = "";
    candidateList.appendChild(emptyNode(`读取失败：${error.message}`));
  } finally {
    refreshButton.disabled = false;
  }
}

async function mergeSelected() {
  cacheSettings();
  const ids = selectedCandidateIds();
  if (!ids.length) {
    proposalMeta.textContent = "先选择候选，或点击全选待处理";
    return;
  }
  mergeButton.disabled = true;
  proposalMeta.textContent = "正在合并候选...";
  try {
    const response = await fetch("/api/selfcore-candidates/merge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate_ids: ids,
        pool: CANDIDATE_POOL,
        use_model: useModelInput.checked,
        poe_api_key: poeApiKeyInput.value.trim(),
        poe_model: poeModelInput.value.trim(),
      }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "合并失败");
    currentProposals = data.result?.proposals || [];
    const candidateCount = data.result?.candidate_count || ids.length;
    const clusterCount = data.result?.cluster_count ?? currentProposals.length;
    const dedupedCount = data.result?.deduped_count ?? Math.max(0, candidateCount - clusterCount);
    proposalMeta.textContent = `${data.result?.engine || "local"} · ${candidateCount} 条候选 → ${clusterCount} 条提案，压缩 ${dedupedCount} 条相近候选`;
    renderProposals();
  } catch (error) {
    proposalMeta.textContent = `合并失败：${error.message}`;
  } finally {
    mergeButton.disabled = false;
  }
}

async function injectSelected() {
  const proposals = collectSelectedProposals();
  if (!proposals.length) {
    injectMeta.textContent = "先勾选要注入的提案";
    return;
  }
  injectButton.disabled = true;
  injectMeta.textContent = "正在写入 SelfCore...";
  try {
    const response = await fetch("/api/selfcore-candidates/inject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proposals }),
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "注入失败");
    injectMeta.textContent = `已注入 ${data.result?.injected_count || proposals.length} 条提案`;
    currentProposals = [];
    await refreshCandidates();
    renderProposals();
    injectPreview.textContent = [
      "注入完成。",
      `SelfCore：${data.result?.selfcore_path || "--"}`,
      `备份：${data.result?.backup_path || "--"}`,
      `记录：${data.result?.record_path || "--"}`,
    ].join("\n");
  } catch (error) {
    injectMeta.textContent = `注入失败：${error.message}`;
  } finally {
    injectButton.disabled = false;
  }
}

selectAllButton.addEventListener("click", () => {
  for (const checkbox of candidateList.querySelectorAll(".candidate-check:not(:disabled)")) {
    checkbox.checked = true;
  }
});
refreshButton.addEventListener("click", refreshCandidates);
mergeButton.addEventListener("click", mergeSelected);
injectButton.addEventListener("click", injectSelected);
poeApiKeyInput.addEventListener("change", cacheSettings);
poeModelInput.addEventListener("change", cacheSettings);

restoreSettings();
applyPoolLabels();
refreshCandidates();
