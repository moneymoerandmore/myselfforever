#!/usr/bin/env python
"""Local dashboard server for the digital twin project."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import csv
from datetime import date
import importlib.util
import json
import math
import mimetypes
import os
import re
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, request
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = Path(__file__).resolve().parent
DRAFT_GENERATOR_PATH = ROOT / "tools" / "draft-generator" / "draft_generator.py"
SELF_CORE_PATH = ROOT / "runtime" / "self-core" / "SelfCore.v0.1.md"
DYADIC_PROFILES_PATH = ROOT / "runtime" / "dyadic-profiles" / "profiles.json"
MULTIMODAL_INTAKE_DIR = ROOT / "data" / "generated" / "multimodal-intake"
MULTIMODAL_ASR_DIR = ROOT / "data" / "generated" / "multimodal-asr"
MULTIMODAL_DIARIZED_ASR_DIR = ROOT / "data" / "generated" / "multimodal-diarized-asr"
MULTIMODAL_CONFIRM_DIR = ROOT / "data" / "generated" / "multimodal-confirmations"
MULTIMODAL_MEMORY_DIR = ROOT / "runtime" / "multimodal-memory"
MULTIMODAL_MEMORY_PATH = MULTIMODAL_MEMORY_DIR / "confirmed-features.jsonl"
SPEAKER_PROFILE_DIR = ROOT / "runtime" / "speaker-profiles"
SPEAKER_PROFILE_PATH = SPEAKER_PROFILE_DIR / "profiles.json"
SELFCORE_MERGE_DIR = ROOT / "data" / "generated" / "selfcore-candidate-merges"
SELFCORE_INJECTION_DIR = ROOT / "data" / "generated" / "selfcore-injections"
SELFCORE_INJECTION_LOG_PATH = ROOT / "runtime" / "self-core" / "candidate-injections.jsonl"
MAX_MULTIMODAL_FILES = 36
MAX_IMAGE_DATA_URL_CHARS = 900_000
MAX_TOTAL_DATA_URL_CHARS = 8_000_000
local_whisper_models: dict[tuple[str, str, str], Any] = {}
funasr_models: dict[tuple[str, str, str, str], Any] = {}
pyannote_pipelines: dict[str, Any] = {}
pyannote_embedding_inferences: dict[str, Any] = {}
asr_jobs: dict[str, dict[str, Any]] = {}
asr_jobs_lock = threading.Lock()
asr_job_executor = ThreadPoolExecutor(max_workers=1)
TOPIC_LABELS = {
    "ai_technology": "AI与技术",
    "work_organization": "工作与组织",
    "investment_market": "投资与市场",
    "family_parenting": "家庭与育儿",
    "housing_city": "住房与城市",
    "food_social": "吃饭与社交",
    "games_entertainment": "游戏与娱乐",
    "health_medical": "健康与医疗",
    "travel_life": "旅行与生活",
    "relationship_emotion": "关系与情绪",
}


def load_draft_generator():
    spec = importlib.util.spec_from_file_location("draft_generator", DRAFT_GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load draft generator: {DRAFT_GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


draft_generator = load_draft_generator()
RELATIONSHIP_DATA_DIR = Path(draft_generator.DEFAULT_RELATIONSHIP_CSV).parent
IDENTITY_ALIAS_MAP_PATH = RELATIONSHIP_DATA_DIR / "identity_alias_map.json"
SESSION_SUMMARY_PATH = Path(draft_generator.DEFAULT_RELATIONSHIP_CSV).parent / "wechat_sessions_summary.csv"
people_cache: list[dict[str, str]] | None = None
session_cache: dict[str, dict[str, Any]] | None = None
dyadic_cache: dict[str, dict[str, Any]] | None = None
alias_cache: dict[str, str] | None = None


def get_people() -> list[dict[str, str]]:
    global people_cache
    if people_cache is None:
        people_cache = draft_generator.read_people(Path(draft_generator.DEFAULT_RELATIONSHIP_CSV))
    return people_cache


def get_sessions() -> dict[str, dict[str, Any]]:
    global session_cache
    if session_cache is not None:
        return session_cache

    sessions: dict[str, dict[str, Any]] = {}
    if not SESSION_SUMMARY_PATH.exists():
        session_cache = sessions
        return sessions

    with SESSION_SUMMARY_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = field(row, "会话名")
            if not name:
                continue
            try:
                start = date.fromisoformat(field(row, "起始日期"))
                end = date.fromisoformat(field(row, "结束日期"))
            except ValueError:
                continue
            sessions[name] = {
                "message_count": int(field(row, "消息数") or "0"),
                "start": start,
                "end": end,
            }

    session_cache = sessions
    return sessions


def normalize_person_key(value: str) -> str:
    return "".join(
        char.lower()
        for char in (value or "").strip().lstrip("@").strip()
        if char.isalnum() or "\u4e00" <= char <= "\u9fff"
    )


def get_identity_aliases() -> dict[str, str]:
    global alias_cache
    if alias_cache is not None:
        return alias_cache
    aliases: dict[str, str] = {}
    if IDENTITY_ALIAS_MAP_PATH.exists():
        payload = json.loads(IDENTITY_ALIAS_MAP_PATH.read_text(encoding="utf-8"))
        for alias, canonical in (payload.get("aliases") or {}).items():
            key = normalize_person_key(str(alias))
            if key and canonical:
                aliases[key] = str(canonical).strip()
    alias_cache = aliases
    return aliases


def canonicalize_person_name(value: str) -> str:
    cleaned = (value or "").strip().lstrip("@").strip()
    key = normalize_person_key(cleaned)
    canonical = get_identity_aliases().get(key)
    if canonical:
        return canonical
    profile = get_dyadic_profiles().get(key)
    if profile and profile.get("canonical_name"):
        return str(profile["canonical_name"]).strip()
    return cleaned


def get_dyadic_profiles() -> dict[str, dict[str, Any]]:
    global dyadic_cache
    if dyadic_cache is not None:
        return dyadic_cache
    index: dict[str, dict[str, Any]] = {}
    if DYADIC_PROFILES_PATH.exists():
        payload = json.loads(DYADIC_PROFILES_PATH.read_text(encoding="utf-8"))
        for profile in payload.get("profiles") or []:
            names = [profile.get("canonical_name") or ""] + list(profile.get("aliases") or [])
            for name in names:
                key = normalize_person_key(str(name))
                if key:
                    index.setdefault(key, profile)
    dyadic_cache = index
    return index


def resolve_dyadic_profile(*names: str) -> dict[str, Any] | None:
    profiles = get_dyadic_profiles()
    for name in names:
        profile = profiles.get(normalize_person_key(name))
        if profile:
            return profile
    return None


def generate_draft(payload: dict[str, Any]) -> dict[str, Any]:
    requested_query = str(payload.get("query") or "").strip()
    query = canonicalize_person_name(requested_query)
    scenario = str(payload.get("scenario") or "").strip()
    poe_api_key = str(payload.get("poe_api_key") or "").strip()
    poe_model = str(payload.get("poe_model") or "").strip()
    intent = str(payload.get("intent") or "unknown").strip()
    mode = str(payload.get("mode") or "draft").strip()
    allow_no_reply = bool(payload.get("allow_no_reply", False))
    response_policy = str(payload.get("response_policy") or "balanced").strip()
    factuality_guard = bool(payload.get("factuality_guard", False))
    trusted_group = bool(payload.get("trusted_group", False))
    conversation_history = normalize_conversation_history(payload.get("conversation_history"))

    if not query:
        raise ValueError("query is required")
    if not scenario and conversation_history:
        scenario = conversation_history[-1]["content"]
    if not scenario:
        raise ValueError("scenario is required")
    if intent not in draft_generator.INTENTS:
        raise ValueError(f"invalid intent: {intent}")
    if mode not in {"observe", "draft", "assist_send"}:
        raise ValueError(f"invalid mode: {mode}")
    if response_policy not in {"balanced", "active_group"}:
        raise ValueError(f"invalid response_policy: {response_policy}")

    matches = draft_generator.resolve_people(get_people(), query)
    if not matches and query != requested_query:
        matches = draft_generator.resolve_people(get_people(), requested_query)
    output = draft_generator.build_output(query, scenario, intent, mode, matches)
    result = draft_generator.asdict(output)
    result["requested_query"] = requested_query
    result["resolved_query"] = query
    result["allow_no_reply"] = allow_no_reply
    result["response_policy"] = response_policy
    result["factuality_guard"] = factuality_guard
    result["trusted_group"] = trusted_group
    person = result.get("person") or {}
    if trusted_group:
        prepare_trusted_group_context(result)
    dyadic_profile = resolve_dyadic_profile(
        requested_query,
        query,
        str(person.get("display_name") or ""),
        str(person.get("call_name") or ""),
        str(person.get("wechat_name") or ""),
        str(person.get("person_name") or ""),
    )
    result["dyadic_profile"] = dyadic_profile
    prompt = build_model_prompt(result, dyadic_profile, conversation_history)
    model_text, model_error = call_poe_model(prompt, poe_api_key, poe_model)
    result["generation_engine"] = "poe_model"
    result["model_prompt"] = prompt
    if model_text:
        if factuality_guard:
            audit = audit_group_draft_factuality(
                model_text,
                conversation_history,
                poe_api_key,
                poe_model,
            )
            result["factuality_status"] = audit["status"]
            result["factuality_reason"] = audit["reason"]
            model_text = audit["draft"]
            if audit["reason"]:
                result["questions_for_user"].append(f"事实审计：{audit['reason']}")
        else:
            result["factuality_status"] = "not_requested"
            result["factuality_reason"] = ""
        if allow_no_reply and is_no_reply_output(model_text):
            result["draft_segments"] = []
            result["draft_text"] = ""
            result["no_reply"] = True
            result["tone_basis"] = "poe_model_chose_no_reply"
            return result
        segments = normalize_chat_style(model_text)
        result["draft_segments"] = segments
        result["draft_text"] = "\n".join(segments)
        result["no_reply"] = len(segments) == 0
        result["tone_basis"] = "poe_model_with_relationship_context"
        if trusted_group:
            apply_trusted_group_risk(result)
    else:
        result["draft_text"] = (
            "Poe 模型生成失败，没有生成正文。\n"
            f"原因：{model_error}\n\n"
            "下面是本次准备送入模型的提示词：\n\n"
            + prompt
        )
        result["tone_basis"] = "poe_model_failed_no_fallback"
        if model_error not in result["questions_for_user"]:
            result["questions_for_user"].insert(0, model_error)
    return result


GROUP_R2_TERMS = {
    "买入", "卖出", "加仓", "减仓", "仓位", "止损", "目标价", "收益率", "内幕",
    "转账", "借钱", "金额", "密码", "验证码", "保证", "承诺", "一定能", "必须赚",
    "诊断", "处方", "用药", "律师", "起诉", "合同", "离职", "开除", "内部消息",
}
GROUP_R3_TERMS = {
    "身份证", "银行卡", "家庭住址", "手机号", "隐私", "威胁", "报复", "人身攻击",
}


def prepare_trusted_group_context(result: dict[str, Any]) -> None:
    result["identity_confidence"] = "known" if result.get("person") else "group_member_unmapped"
    if result.get("person"):
        return
    result["risk_level"] = "R1_low"
    result["approval_required"] = False
    result["relationship_basis"] = "已授权群聊成员；个人身份尚未映射，不使用熟人称呼或私人关系推断。"
    result["questions_for_user"] = [
        item
        for item in result.get("questions_for_user") or []
        if "联系人是谁" not in item and "未识别联系人" not in item
    ]


def apply_trusted_group_risk(result: dict[str, Any]) -> None:
    draft = str(result.get("draft_text") or "").strip()
    factuality_status = str(result.get("factuality_status") or "not_requested")
    if not draft or result.get("no_reply"):
        return

    reasons: list[str] = []
    if factuality_status in {"audit_failed"}:
        level = "R3_high"
        reasons.append("事实审计失败，不能自动发送。")
    elif any(term in draft for term in GROUP_R3_TERMS):
        level = "R3_high"
        reasons.append("草稿涉及高敏感个人信息或冲突风险。")
    elif any(term in draft for term in GROUP_R2_TERMS):
        level = "R2_medium"
        reasons.append("草稿包含操作建议、承诺、金额或专业高风险内容。")
    elif len(draft) > 120:
        level = "R2_medium"
        reasons.append("群聊草稿过长，不适合自动发送。")
    else:
        level = "R1_low"
        reasons.append("已授权群聊中的低风险日常接话，事实审计已通过。")

    prepare_trusted_group_context(result)
    result["risk_level"] = level
    result["approval_required"] = level not in {"R0_safe", "R1_low"}
    result["questions_for_user"].extend(reasons)


def parse_json_object(value: str) -> dict[str, Any] | None:
    text = str(value or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def audit_group_draft_factuality(
    draft: str,
    conversation_history: list[dict[str, str]],
    api_key: str,
    model: str,
) -> dict[str, str]:
    history = "\n".join(
        f"{'我' if item['role'] == 'self' else '群友'}：{item['content']}"
        for item in conversation_history[-40:]
    )
    prompt = f"""当前日期是 {date.today().isoformat()}。你是群聊草稿的事实审计器。

最近连续群聊：
{history or '（无）'}

待发送草稿：
{draft}

只检查“草稿是否引入了上下文没有提供的具体事实前提”，不评价文风。

硬规则：
- 当前赛事参赛资格、晋级、比分、阵容、伤病、球员状态、赛程等都属于时效事实。
- 当前新闻、政策、价格、产品状态、公司人物、日期和数字也属于时效事实。
- 如果草稿新增具体国家、球队、球员、公司、人物或数字，并据此作判断，而最近群聊没有给出依据，必须判为不安全。
- “意大利这次有机会”隐含意大利参加本届赛事；若上下文没确认参赛，就不安全。
- 不允许用模型记忆补齐最新事实，也不要尝试判断事实真伪。只判断它是否得到当前上下文支持。
- 不安全时，把草稿改成只承接最后 1-3 条消息、且不包含无依据具体事实的自然短回复。
- 如果无法安全改写，draft 输出 `__NO_REPLY__`。

只输出 JSON：
{{"safe":true或false,"draft":"审计后的草稿","reason":"一句中文原因"}}"""
    audit_text, audit_error = call_poe_model(
        prompt,
        api_key,
        model,
        system_prompt="你是严格的事实审计器，只输出合法 JSON，不使用外部记忆补事实。",
        temperature=0.0,
    )
    if not audit_text:
        return {
            "status": "audit_failed",
            "draft": "__NO_REPLY__",
            "reason": audit_error or "事实审计没有返回结果，已阻止发送。",
        }
    payload = parse_json_object(audit_text)
    if payload is None:
        return {
            "status": "audit_failed",
            "draft": "__NO_REPLY__",
            "reason": "事实审计返回格式无法解析，已阻止发送。",
        }
    audited_draft = str(payload.get("draft") or "").strip() or "__NO_REPLY__"
    safe = bool(payload.get("safe", False))
    return {
        "status": "passed" if safe and audited_draft == draft.strip() else "rewritten",
        "draft": audited_draft,
        "reason": str(payload.get("reason") or "").strip(),
    }


def build_multimodal_intake_prompt(payload: dict[str, Any], files: list[dict[str, Any]]) -> str:
    note = str(payload.get("note") or "").strip()
    context = str(payload.get("context") or "").strip()
    target = str(payload.get("target") or "self_understanding").strip()
    media_kind = str(payload.get("media_kind") or "mixed").strip()
    source_name = str(payload.get("source_name") or "").strip()
    video_metadata = payload.get("video_metadata") if isinstance(payload.get("video_metadata"), dict) else {}
    timeline_text = str(payload.get("timeline_text") or "").strip()
    file_lines = []
    for index, item in enumerate(files, start=1):
        timestamp = item.get("timestamp_seconds")
        timestamp_text = f", t={timestamp}s" if timestamp is not None else ""
        file_lines.append(
            f"{index}. {item.get('name') or '未命名'} "
            f"({item.get('type') or 'unknown'}, {item.get('size') or 0} bytes{timestamp_text})"
        )
    return f"""当前日期是 {date.today().isoformat()}。你是数字分身的多模态材料摄入器。

目标不是直接改写人格，而是把用户提供的图片、视频抽帧、录屏关键帧、字幕/ASR 转写和材料说明，转成可校对的记忆候选。

视频理解必须分层：
- 视觉帧只能说明画面、界面、场景和少量动作。
- 字幕/ASR/人工转写用于理解说了什么、怎么接话、气氛、态度、停顿、打断、玩笑和压力。
- 用户补充说明用于解释为什么这段材料代表用户，以及哪些地方不能过度推断。
- 如果缺少音频转写，不得声称理解了完整交流内容、语气或气氛。

材料用途：{target}
媒体类型：{media_kind}
来源文件：{source_name or '（未提供）'}
视频/录屏元数据：
{json.dumps(video_metadata, ensure_ascii=False, indent=2) if video_metadata else '（无）'}

用户补充说明：
{note or '（无）'}

场景/来源上下文：
{context or '（无）'}

人工时间线/转写/操作说明：
{timeline_text or '（无）'}

文件清单：
{chr(10).join(file_lines) or '（无文件，仅文字）'}

已知的 SelfCore 表达摘要：
{self_core_excerpt()}

已确认的多模态记忆：
{confirmed_multimodal_memory_excerpt()}

请只输出 JSON，不要 Markdown，不要解释。结构如下：
{{
  "summary": "一句话概括这批材料说明了什么",
  "observations": ["从材料中能直接观察到的事实或时间线事件，最多8条"],
  "timeline_events": ["按时间顺序列出关键事件，格式如 00:12 用户停在某页/说了某句，最多12条"],
  "conversation_summary": "如果有转写，概括交流双方/多方主要谈了什么；没有转写则说明无法判断",
  "communication_atmosphere": ["交流气氛、张力、松弛度、玩笑感、压迫感或协作感，必须来自转写/说明，最多6条"],
  "attitude_signals": ["用户在交流中的态度、立场、情绪强度、边界感、确定/不确定表达，最多6条"],
  "interaction_style": ["接话方式、主导/跟随、追问、打断、解释、反驳、缓和、收束等互动模式，最多6条"],
  "self_signals": ["可能增进对用户真实偏好/表达/生活状态理解的信号，最多8条"],
  "expression_signals": ["能帮助生成更像用户的表达线索，最多5条"],
  "relationship_signals": ["涉及关系、场景或共同话题的信号，最多5条"],
  "memory_candidates": [
    {{"candidate": "可进入长期/短期记忆的候选", "scope": "short_term|relationship|self_core_candidate", "confidence": "low|medium|high", "needs_user_confirmation": true}}
  ],
  "risk_flags": ["隐私、跨关系泄露、时效事实、过度推断等风险，没有则空数组"],
  "questions_for_user": ["为了避免误解，最值得问用户确认的问题，最多4条"],
  "recommended_next_action": "ignore|ask_user|save_short_term|propose_profile_update"
}}

硬规则：
- 图片或视频帧里看不清、时间线上没提供、音频没有转写的内容，不要猜。
- 视频帧是抽样，不代表完整视频；必须保留抽样盲区。
- 对录屏，重点关注用户如何选择、停留、删改、切换、暂停和反应，不只是屏幕上有什么。
- 对沟通视频，必须优先从转写中抽取“说了什么”和“怎么说”；只看画面时只能给出低置信度的场景推断。
- 区分内容层、态度层、关系层、表达层：不要把一次情绪反应直接写成稳定人格。
- 对气氛的判断要给出证据来源，如“连续短句追问”“对方打断后用户收束”“多次玩笑缓和”等。
- 不要从单次状态直接推出稳定人格。
- 涉及他人身份、亲密关系、公司、投资、医疗、法律、地址、账号等信息，默认需要用户确认。
- 如果只有视频元数据但没有抽帧/转写，只能输出摄入计划和需要用户补充的问题，不要假装看过视频。"""


def normalize_intake_files(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("files must be a list")
    normalized = []
    total_data_url_chars = 0
    for item in value[:MAX_MULTIMODAL_FILES]:
        if not isinstance(item, dict):
            raise ValueError("file item must be an object")
        name = str(item.get("name") or "未命名").strip()[:160]
        mime_type = str(item.get("type") or "").strip()[:120]
        data_url = str(item.get("data_url") or "").strip()
        size = int(item.get("size") or 0)
        timestamp = item.get("timestamp_seconds")
        try:
            timestamp_seconds = round(float(timestamp), 2) if timestamp is not None else None
        except (TypeError, ValueError):
            timestamp_seconds = None
        if data_url and not data_url.startswith("data:"):
            raise ValueError(f"invalid data URL for {name}")
        if data_url and len(data_url) > MAX_IMAGE_DATA_URL_CHARS:
            raise ValueError(f"file is too large for model input: {name}")
        total_data_url_chars += len(data_url)
        if total_data_url_chars > MAX_TOTAL_DATA_URL_CHARS:
            raise ValueError("multimodal payload is too large; reduce frame count or image quality")
        normalized.append(
            {
                "name": name,
                "type": mime_type,
                "size": size,
                "data_url": data_url,
                "timestamp_seconds": timestamp_seconds,
            }
        )
    return normalized


def build_multimodal_user_content(prompt: str, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for item in files:
        mime_type = str(item.get("type") or "")
        data_url = str(item.get("data_url") or "")
        if mime_type.startswith("image/") and data_url:
            content.append({"type": "image_url", "image_url": {"url": data_url, "detail": "low"}})
    return content


def select_evenly_spaced_files(files: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or len(files) <= limit:
        return list(files)
    if limit == 1:
        return [files[len(files) // 2]]
    indexes = {
        round(index * (len(files) - 1) / (limit - 1))
        for index in range(limit)
    }
    return [files[index] for index in sorted(indexes)]


def multimodal_retry_variants(files: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    variants = [("full", list(files))]
    if len(files) > 4:
        variants.append(("reduced_4_frames", select_evenly_spaced_files(files, 4)))
    if len(files) > 1:
        variants.append(("single_middle_frame", select_evenly_spaced_files(files, 1)))

    deduped: list[tuple[str, list[dict[str, Any]]]] = []
    seen: set[tuple[tuple[str, Any], ...]] = set()
    for label, variant_files in variants:
        signature = tuple(
            (
                str(item.get("name") or ""),
                item.get("timestamp_seconds"),
                len(str(item.get("data_url") or "")),
            )
            for item in variant_files
        )
        if signature not in seen:
            seen.add(signature)
            deduped.append((label, variant_files))
    return deduped


def should_retry_multimodal_error(message: str) -> bool:
    return (
        "HTTP 500" in message
        or "HTTP 502" in message
        or "HTTP 503" in message
        or "HTTP 504" in message
        or "过大的请求" in message
        or "too large" in message.lower()
    )


def format_timestamp(seconds: float) -> str:
    value = max(0, float(seconds or 0))
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    rest = int(value % 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:02d}:{rest:02d}"


def resolve_local_media_path(value: str) -> Path:
    raw = str(value or "").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("local_path is required")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("本地路径不是文件。")

    allowed_roots = [ROOT.resolve(), Path("C:/tmp").resolve()]
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise ValueError("出于安全边界，本地 ASR 只读取项目目录或 C:\\tmp 下的文件。请把视频复制到这些目录后重试。")
    return resolved


def get_local_whisper_model(model_size: str, device: str, compute_type: str) -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ValueError("本地 Whisper 依赖未安装：请安装 faster-whisper。") from exc

    key = (model_size, device, compute_type)
    model = local_whisper_models.get(key)
    if model is None:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        local_whisper_models[key] = model
    return model


def call_local_whisper_asr(payload: dict[str, Any]) -> dict[str, Any]:
    source_path = resolve_local_media_path(str(payload.get("local_path") or ""))
    model_size = str(payload.get("local_model") or os.environ.get("DIGITAL_TWIN_LOCAL_WHISPER_MODEL", "tiny")).strip()
    device = str(payload.get("device") or os.environ.get("DIGITAL_TWIN_LOCAL_WHISPER_DEVICE", "cpu")).strip()
    compute_type = str(payload.get("compute_type") or os.environ.get("DIGITAL_TWIN_LOCAL_WHISPER_COMPUTE", "int8")).strip()
    language = str(payload.get("language") or "zh").strip() or None
    beam_size = int(payload.get("beam_size") or 5)

    if model_size not in {"tiny", "base", "small", "medium", "large-v3"}:
        raise ValueError(f"invalid local_model: {model_size}")
    if device not in {"cpu", "cuda"}:
        raise ValueError(f"invalid device: {device}")
    if compute_type not in {"int8", "int8_float16", "float16", "float32"}:
        raise ValueError(f"invalid compute_type: {compute_type}")

    model = get_local_whisper_model(model_size, device, compute_type)
    segments_iter, info = model.transcribe(
        str(source_path),
        language=language,
        beam_size=beam_size,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=False,
    )
    segments: list[dict[str, Any]] = []
    lines: list[str] = []
    for segment in segments_iter:
        text = str(segment.text or "").strip()
        item = {
            "start": round(float(segment.start or 0), 2),
            "end": round(float(segment.end or 0), 2),
            "text": text,
        }
        segments.append(item)
        if text:
            lines.append(f"[{format_timestamp(item['start'])}-{format_timestamp(item['end'])}] {text}")

    transcript = "\n".join(lines).strip()
    MULTIMODAL_ASR_DIR.mkdir(parents=True, exist_ok=True)
    record_id = f"asr-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    txt_path = MULTIMODAL_ASR_DIR / f"{record_id}.txt"
    json_path = MULTIMODAL_ASR_DIR / f"{record_id}.json"
    txt_path.write_text(transcript, encoding="utf-8")
    record = {
        "id": record_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_path": str(source_path),
        "source_size": source_path.stat().st_size,
        "model": model_size,
        "device": device,
        "compute_type": compute_type,
        "language": getattr(info, "language", language),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
        "segments": segments,
        "transcript_path": str(txt_path),
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "text": transcript,
        "segments": segments,
        "saved_path": str(txt_path),
        "record_path": str(json_path),
        "model": model_size,
        "device": device,
        "compute_type": compute_type,
        "language": record["language"],
        "duration": record["duration"],
    }


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def configure_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
    except ImportError:
        return None

    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
    ffmpeg_path = Path(ffmpeg)
    if not ffmpeg_path.exists():
        return None
    shim_dir = ROOT / "data" / "generated" / "runtime-bin"
    shim_path = shim_dir / "ffmpeg.exe"
    try:
        shim_dir.mkdir(parents=True, exist_ok=True)
        if not shim_path.exists() or shim_path.stat().st_size != ffmpeg_path.stat().st_size:
            shutil.copy2(ffmpeg_path, shim_path)
        ffmpeg_path = shim_path
    except OSError:
        pass
    os.environ["IMAGEIO_FFMPEG_EXE"] = str(ffmpeg_path)
    os.environ["FFMPEG_BINARY"] = str(ffmpeg_path)
    path_value = os.environ.get("PATH", "")
    ffmpeg_dir = str(ffmpeg_path.parent)
    if ffmpeg_dir not in path_value.split(os.pathsep):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + path_value
    return str(ffmpeg_path)


def pyannote_dependency_status() -> dict[str, Any]:
    ffmpeg_path = configure_ffmpeg()
    dependencies = {
        "pyannote.audio": module_available("pyannote") and module_available("pyannote.audio"),
        "faster_whisper": module_available("faster_whisper"),
        "torch": module_available("torch"),
        "hf_xet": module_available("hf_xet"),
        "soundfile": module_available("soundfile"),
        "omegaconf": module_available("omegaconf"),
        "funasr": module_available("funasr"),
        "modelscope": module_available("modelscope"),
        "imageio_ffmpeg": module_available("imageio_ffmpeg"),
        "ffmpeg": bool(ffmpeg_path),
    }
    local_pyannote_available = all(
        dependencies[name]
        for name in ["pyannote.audio", "faster_whisper", "torch", "hf_xet", "soundfile", "omegaconf"]
    )
    funasr_available = dependencies["funasr"] and dependencies["modelscope"] and dependencies["ffmpeg"]
    return {
        "available": local_pyannote_available,
        "funasr_available": funasr_available,
        "dependencies": dependencies,
        "ffmpeg_path": ffmpeg_path,
        "package": "pyannote.audio + faster-whisper; FunASR optional",
        "install_hint": "pip install pyannote.audio faster-whisper soundfile hf_xet omegaconf hydra-core funasr modelscope imageio-ffmpeg",
    }


def speaker_profiles_payload() -> dict[str, Any]:
    if not SPEAKER_PROFILE_PATH.exists():
        return {"version": 1, "profiles": []}
    try:
        payload = json.loads(SPEAKER_PROFILE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "profiles": []}
    if not isinstance(payload, dict):
        return {"version": 1, "profiles": []}
    profiles = payload.get("profiles")
    if not isinstance(profiles, list):
        payload["profiles"] = []
    payload.setdefault("version", 1)
    return payload


def save_speaker_profiles_payload(payload: dict[str, Any]) -> None:
    SPEAKER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    SPEAKER_PROFILE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def public_speaker_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": profile.get("id"),
        "display_name": profile.get("display_name"),
        "role": profile.get("role"),
        "source_path": profile.get("source_path"),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
        "embedding_dimensions": len(profile.get("embedding") or []),
    }


def list_speaker_profiles() -> dict[str, Any]:
    payload = speaker_profiles_payload()
    return {
        "dependency": pyannote_dependency_status(),
        "profiles": [public_speaker_profile(profile) for profile in payload.get("profiles", [])],
        "path": str(SPEAKER_PROFILE_PATH),
    }


def hf_token_from_payload(payload: dict[str, Any]) -> str:
    return (
        str(payload.get("hf_token") or "").strip()
        or os.environ.get("HUGGINGFACE_TOKEN", "").strip()
        or os.environ.get("HF_TOKEN", "").strip()
    )


def require_pyannote(token: str) -> None:
    status = pyannote_dependency_status()
    if not status["available"]:
        raise ValueError("长期说话人分离需要安装 pyannote.audio；请先运行 pip install pyannote.audio soundfile。")
    if not token:
        raise ValueError("长期说话人分离需要 HuggingFace token，并且要在 HuggingFace 接受 pyannote 模型授权。")


def get_pyannote_pipeline(token: str) -> Any:
    key = token[-12:] if token else "env"
    pipeline = pyannote_pipelines.get(key)
    if pipeline is not None:
        return pipeline
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise ValueError("pyannote.audio 未安装，无法做长期说话人分离。") from exc

    pipeline_id = os.environ.get("DIGITAL_TWIN_PYANNOTE_PIPELINE", "pyannote/speaker-diarization-community-1")
    pipeline = Pipeline.from_pretrained(pipeline_id, token=token)
    pyannote_pipelines[key] = pipeline
    return pipeline


def get_pyannote_embedding_inference(token: str) -> Any:
    key = token[-12:] if token else "env"
    inference = pyannote_embedding_inferences.get(key)
    if inference is not None:
        return inference
    try:
        from pyannote.audio import Inference, Model
    except ImportError as exc:
        raise ValueError("pyannote.audio 未安装，无法建立声纹身份库。") from exc

    embedding_model_id = os.environ.get("DIGITAL_TWIN_PYANNOTE_EMBEDDING", "pyannote/embedding")
    model = Model.from_pretrained(embedding_model_id, token=token)
    inference = Inference(model, window="whole")
    pyannote_embedding_inferences[key] = inference
    return inference


def pyannote_audio_source(source_path: Path) -> dict[str, Any]:
    try:
        import torch
        from faster_whisper.audio import decode_audio
    except ImportError as exc:
        raise ValueError("说话人分离需要 faster-whisper 和 torch 来解码本地音频。") from exc

    try:
        samples = decode_audio(str(source_path), sampling_rate=16000)
    except Exception as exc:
        raise ValueError(f"无法把本地视频/音频解码为 pyannote 可用的音频流：{exc}") from exc
    waveform = torch.from_numpy(samples).float()
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    elif waveform.ndim == 2 and waveform.shape[0] > waveform.shape[1]:
        waveform = waveform.transpose(0, 1)
    return {"waveform": waveform, "sample_rate": 16000}


def normalize_embedding(value: Any) -> list[float]:
    try:
        import numpy as np

        array = np.asarray(value, dtype=float)
        if array.ndim > 1:
            array = array.mean(axis=0)
        vector = [float(item) for item in array.reshape(-1)]
    except Exception:
        vector = [float(item) for item in (value or [])]
    norm = math.sqrt(sum(item * item for item in vector))
    if norm <= 0:
        return vector
    return [item / norm for item in vector]


def audio_embedding(audio_source: dict[str, Any], token: str, start: float | None = None, end: float | None = None) -> list[float]:
    inference = get_pyannote_embedding_inference(token)
    if start is None or end is None:
        return normalize_embedding(inference(audio_source))
    try:
        from pyannote.core import Segment

        segment = Segment(float(start), float(end))
        return normalize_embedding(inference.crop(audio_source, segment))
    except Exception:
        return normalize_embedding(inference(audio_source))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    return sum(left[index] * right[index] for index in range(size))


def best_speaker_identity(embedding: list[float], profiles: list[dict[str, Any]], threshold: float = 0.72) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for profile in profiles:
        score = cosine_similarity(embedding, [float(item) for item in profile.get("embedding") or []])
        if score > best_score:
            best = profile
            best_score = score
    if best is None or best_score < threshold:
        return None
    return {
        "id": best.get("id"),
        "display_name": best.get("display_name"),
        "role": best.get("role"),
        "score": round(best_score, 4),
    }


def speaker_slug(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-").lower()
    return slug or f"speaker-{uuid4().hex[:8]}"


def enroll_speaker_profile(payload: dict[str, Any]) -> dict[str, Any]:
    source_path = resolve_local_media_path(str(payload.get("local_path") or ""))
    token = hf_token_from_payload(payload)
    require_pyannote(token)
    display_name = str(payload.get("display_name") or "我").strip() or "我"
    role = str(payload.get("role") or ("self" if display_name == "我" else "contact")).strip() or "contact"
    profile_id = speaker_slug(str(payload.get("id") or display_name))
    audio_source = pyannote_audio_source(source_path)
    embedding = audio_embedding(audio_source, token)
    now = datetime.now().isoformat(timespec="seconds")

    payload_data = speaker_profiles_payload()
    profiles = [profile for profile in payload_data.get("profiles", []) if profile.get("id") != profile_id]
    existing = next((profile for profile in payload_data.get("profiles", []) if profile.get("id") == profile_id), {})
    profile = {
        "id": profile_id,
        "display_name": display_name,
        "role": role,
        "embedding": embedding,
        "source_path": str(source_path),
        "created_at": existing.get("created_at") or now,
        "updated_at": now,
    }
    profiles.append(profile)
    payload_data["profiles"] = sorted(profiles, key=lambda item: str(item.get("display_name") or item.get("id") or ""))
    save_speaker_profiles_payload(payload_data)
    return {
        "profile": public_speaker_profile(profile),
        "profile_count": len(payload_data["profiles"]),
        "path": str(SPEAKER_PROFILE_PATH),
    }


def diarization_turns(audio_source: dict[str, Any], token: str) -> list[dict[str, Any]]:
    pipeline = get_pyannote_pipeline(token)
    output = pipeline(audio_source)
    diarization = (
        getattr(output, "exclusive_speaker_diarization", None)
        or getattr(output, "speaker_diarization", None)
        or output
    )
    if not hasattr(diarization, "itertracks"):
        raise ValueError(f"pyannote returned unsupported diarization output: {type(output).__name__}")
    turns: list[dict[str, Any]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append(
            {
                "start": round(float(turn.start), 2),
                "end": round(float(turn.end), 2),
                "speaker": str(speaker),
            }
        )
    return turns


def interval_overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    return max(0.0, min(left_end, right_end) - max(left_start, right_start))


def speaker_for_interval(start: float, end: float, turns: list[dict[str, Any]]) -> str:
    best_speaker = "UNKNOWN"
    best_overlap = 0.0
    midpoint = (start + end) / 2
    for turn in turns:
        overlap = interval_overlap(start, end, float(turn["start"]), float(turn["end"]))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = str(turn["speaker"])
    if best_overlap > 0:
        return best_speaker
    for turn in turns:
        if float(turn["start"]) <= midpoint <= float(turn["end"]):
            return str(turn["speaker"])
    return best_speaker


def summarize_diarized_speakers(audio_source: dict[str, Any], token: str, turns: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    profile_payload = speaker_profiles_payload()
    profiles = profile_payload.get("profiles", [])
    speakers = sorted({str(turn["speaker"]) for turn in turns})
    summary: list[dict[str, Any]] = []
    speaker_name_map: dict[str, str] = {}
    for speaker in speakers:
        speaker_turns = [turn for turn in turns if turn["speaker"] == speaker]
        duration = sum(max(0.0, float(turn["end"]) - float(turn["start"])) for turn in speaker_turns)
        longest = max(speaker_turns, key=lambda turn: float(turn["end"]) - float(turn["start"]))
        embedding = audio_embedding(audio_source, token, float(longest["start"]), float(longest["end"]))
        identity = best_speaker_identity(embedding, profiles)
        display_name = identity["display_name"] if identity else speaker
        speaker_name_map[speaker] = str(display_name)
        summary.append(
            {
                "speaker": speaker,
                "display_name": display_name,
                "duration": round(duration, 2),
                "turn_count": len(speaker_turns),
                "identity": identity,
            }
        )
    return summary, speaker_name_map


def call_diarized_whisper_asr(payload: dict[str, Any]) -> dict[str, Any]:
    source_path = resolve_local_media_path(str(payload.get("local_path") or ""))
    token = hf_token_from_payload(payload)
    require_pyannote(token)
    audio_source = pyannote_audio_source(source_path)
    turns = diarization_turns(audio_source, token)
    speaker_summary, speaker_name_map = summarize_diarized_speakers(audio_source, token, turns)

    asr_result = call_local_whisper_asr(payload)
    segments: list[dict[str, Any]] = []
    lines: list[str] = []
    for segment in asr_result.get("segments", []):
        start = float(segment.get("start") or 0)
        end = float(segment.get("end") or start)
        raw_speaker = speaker_for_interval(start, end, turns)
        display_name = speaker_name_map.get(raw_speaker, raw_speaker)
        text = str(segment.get("text") or "").strip()
        item = {
            **segment,
            "speaker": display_name,
            "raw_speaker": raw_speaker,
        }
        segments.append(item)
        if text:
            lines.append(f"[{format_timestamp(start)}-{format_timestamp(end)}] {display_name}({raw_speaker}): {text}")

    transcript = "\n".join(lines).strip()
    MULTIMODAL_DIARIZED_ASR_DIR.mkdir(parents=True, exist_ok=True)
    record_id = f"diarized-asr-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    txt_path = MULTIMODAL_DIARIZED_ASR_DIR / f"{record_id}.txt"
    json_path = MULTIMODAL_DIARIZED_ASR_DIR / f"{record_id}.json"
    txt_path.write_text(transcript, encoding="utf-8")
    record = {
        "id": record_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_path": str(source_path),
        "source_size": source_path.stat().st_size,
        "model": asr_result.get("model"),
        "device": asr_result.get("device"),
        "compute_type": asr_result.get("compute_type"),
        "language": asr_result.get("language"),
        "duration": asr_result.get("duration"),
        "diarization_turns": turns,
        "speakers": speaker_summary,
        "segments": segments,
        "transcript_path": str(txt_path),
        "plain_asr_record_path": asr_result.get("record_path"),
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "text": transcript,
        "segments": segments,
        "speakers": speaker_summary,
        "diarization_turns": turns,
        "saved_path": str(txt_path),
        "record_path": str(json_path),
        "plain_asr_record_path": asr_result.get("record_path"),
        "model": asr_result.get("model"),
        "device": asr_result.get("device"),
        "compute_type": asr_result.get("compute_type"),
        "language": asr_result.get("language"),
        "duration": asr_result.get("duration"),
    }


def volcengine_credentials(payload: dict[str, Any]) -> dict[str, str]:
    app_id = str(payload.get("volcengine_app_id") or os.environ.get("VOLCENGINE_ASR_APP_ID", "")).strip()
    token = str(payload.get("volcengine_token") or os.environ.get("VOLCENGINE_ASR_TOKEN", "")).strip()
    cluster = str(
        payload.get("volcengine_cluster")
        or os.environ.get("VOLCENGINE_ASR_CLUSTER", "volcengine_input_common")
    ).strip()
    audio_url = str(payload.get("volcengine_audio_url") or "").strip()
    if not app_id:
        raise ValueError("火山引擎 ASR 需要 AppID。")
    if not token:
        raise ValueError("火山引擎 ASR 需要 Access Token。")
    if not cluster:
        raise ValueError("火山引擎 ASR 需要 Cluster。")
    if not audio_url:
        raise ValueError("火山引擎 ASR 需要可访问的音视频 URL；本地 C:\\tmp 路径不能直接提交给云端服务。")
    return {
        "app_id": app_id,
        "token": token,
        "cluster": cluster,
        "audio_url": audio_url,
    }


def volcengine_post_json(url: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"火山引擎 ASR HTTP {exc.code}: {raw[:1000]}") from exc
    except error.URLError as exc:
        raise ValueError(f"火山引擎 ASR 请求失败：{exc.reason}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"火山引擎 ASR 返回了非 JSON：{raw[:1000]}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("火山引擎 ASR 返回结构不是对象。")
    return parsed


def first_nested_value(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                return item
        for item in value.values():
            found = first_nested_value(item, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = first_nested_value(item, keys)
            if found is not None:
                return found
    return None


def numeric_time_seconds(value: Any) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if number > 10_000:
        return number / 1000.0
    return number


def normalize_volcengine_segment(raw: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    text = str(
        raw.get("text")
        or raw.get("utterance")
        or raw.get("sentence")
        or raw.get("result")
        or ""
    ).strip()
    start = numeric_time_seconds(
        raw.get("start")
        or raw.get("start_time")
        or raw.get("startTime")
        or raw.get("begin_time")
        or raw.get("beginTime")
    )
    end = numeric_time_seconds(
        raw.get("end")
        or raw.get("end_time")
        or raw.get("endTime")
        or raw.get("stop_time")
        or raw.get("stopTime")
    )
    speaker = str(
        raw.get("speaker")
        or raw.get("speaker_id")
        or raw.get("speakerId")
        or raw.get("speaker_label")
        or raw.get("channel")
        or f"SPEAKER_{fallback_index:02d}"
    )
    return {
        "start": round(start, 2),
        "end": round(end, 2),
        "text": text,
        "speaker": speaker,
        "raw_speaker": speaker,
    }


def normalize_volcengine_result(raw: dict[str, Any], source_url: str, reqid: str) -> dict[str, Any]:
    segment_candidates = first_nested_value(raw, {"utterances", "segments", "sentences"})
    segments: list[dict[str, Any]] = []
    if isinstance(segment_candidates, list):
        for index, item in enumerate(segment_candidates):
            if isinstance(item, dict):
                segment = normalize_volcengine_segment(item, index)
                if segment["text"]:
                    segments.append(segment)
    if not segments:
        text_value = first_nested_value(raw, {"text", "transcript", "result_text"})
        text = str(text_value or "").strip()
        if text:
            segments.append({"start": 0.0, "end": 0.0, "text": text, "speaker": "SPEAKER_00", "raw_speaker": "SPEAKER_00"})

    speakers: list[dict[str, Any]] = []
    for speaker in sorted({segment["speaker"] for segment in segments}):
        speaker_segments = [segment for segment in segments if segment["speaker"] == speaker]
        duration = sum(max(0.0, float(segment.get("end") or 0) - float(segment.get("start") or 0)) for segment in speaker_segments)
        speakers.append(
            {
                "speaker": speaker,
                "display_name": speaker,
                "duration": round(duration, 2),
                "turn_count": len(speaker_segments),
                "identity": None,
            }
        )

    lines = []
    for segment in segments:
        lines.append(
            f"[{format_timestamp(float(segment['start']))}-{format_timestamp(float(segment['end']))}] "
            f"{segment['speaker']}({segment['raw_speaker']}): {segment['text']}"
        )
    transcript = "\n".join(lines).strip()

    MULTIMODAL_DIARIZED_ASR_DIR.mkdir(parents=True, exist_ok=True)
    record_id = f"volcengine-asr-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    txt_path = MULTIMODAL_DIARIZED_ASR_DIR / f"{record_id}.txt"
    json_path = MULTIMODAL_DIARIZED_ASR_DIR / f"{record_id}.json"
    txt_path.write_text(transcript, encoding="utf-8")
    record = {
        "id": record_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "provider": "volcengine",
        "source_url": source_url,
        "reqid": reqid,
        "speakers": speakers,
        "segments": segments,
        "transcript_path": str(txt_path),
        "raw_result": raw,
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "text": transcript,
        "segments": segments,
        "speakers": speakers,
        "diarization_turns": [
            {"start": segment["start"], "end": segment["end"], "speaker": segment["raw_speaker"]}
            for segment in segments
        ],
        "saved_path": str(txt_path),
        "record_path": str(json_path),
        "provider": "volcengine",
        "reqid": reqid,
    }


def volcengine_status(raw: dict[str, Any]) -> str:
    status_value = str(first_nested_value(raw, {"status", "status_text", "state"}) or "").lower()
    code_value = first_nested_value(raw, {"code", "err_code", "error_code"})
    if status_value in {"success", "succeeded", "done", "completed", "finished"}:
        return "completed"
    if status_value in {"failed", "error", "failure"}:
        return "failed"
    if isinstance(code_value, int) and code_value not in {0, 1000, 20000000}:
        return "failed"
    if first_nested_value(raw, {"utterances", "segments", "sentences", "text", "transcript", "result_text"}) is not None:
        return "completed"
    return "running"


def call_volcengine_diarized_asr(payload: dict[str, Any]) -> dict[str, Any]:
    credentials = volcengine_credentials(payload)
    submit_url = str(
        payload.get("volcengine_submit_url")
        or os.environ.get("VOLCENGINE_ASR_SUBMIT_URL", "https://openspeech.bytedance.com/api/v1/auc/submit")
    ).strip()
    query_url = str(
        payload.get("volcengine_query_url")
        or os.environ.get("VOLCENGINE_ASR_QUERY_URL", "https://openspeech.bytedance.com/api/v1/auc/query")
    ).strip()
    reqid = f"dtwin-{uuid4().hex}"
    common_payload = {
        "app": {
            "appid": credentials["app_id"],
            "token": credentials["token"],
            "cluster": credentials["cluster"],
        },
        "user": {"uid": "digital-twin-local"},
        "audio": {"url": credentials["audio_url"]},
        "request": {
            "reqid": reqid,
            "nbest": 1,
            "show_utterances": True,
            "enable_speaker_info": True,
            "show_speaker_info": True,
            "diarization": True,
        },
    }
    submit_result = volcengine_post_json(submit_url, common_payload, credentials["token"])
    submit_status = volcengine_status(submit_result)
    if submit_status == "failed":
        raise ValueError(f"火山引擎 ASR 提交失败：{json.dumps(submit_result, ensure_ascii=False)[:1000]}")
    if submit_status == "completed":
        return normalize_volcengine_result(submit_result, credentials["audio_url"], reqid)

    deadline = time.time() + int(payload.get("volcengine_timeout_seconds") or 6 * 60 * 60)
    query_payload = {
        "app": common_payload["app"],
        "user": common_payload["user"],
        "request": {"reqid": reqid},
    }
    last_result = submit_result
    while time.time() < deadline:
        time.sleep(int(payload.get("volcengine_poll_interval_seconds") or 5))
        query_result = volcengine_post_json(query_url, query_payload, credentials["token"])
        last_result = query_result
        status = volcengine_status(query_result)
        if status == "completed":
            return normalize_volcengine_result(query_result, credentials["audio_url"], reqid)
        if status == "failed":
            raise ValueError(f"火山引擎 ASR 任务失败：{json.dumps(query_result, ensure_ascii=False)[:1000]}")
    raise ValueError(f"火山引擎 ASR 超时，最后返回：{json.dumps(last_result, ensure_ascii=False)[:1000]}")


def funasr_config(payload: dict[str, Any]) -> dict[str, Any]:
    model = str(payload.get("funasr_model") or os.environ.get("FUNASR_MODEL", "paraformer-zh")).strip()
    vad_model = str(payload.get("funasr_vad_model") or os.environ.get("FUNASR_VAD_MODEL", "fsmn-vad")).strip()
    punc_model = str(payload.get("funasr_punc_model") or os.environ.get("FUNASR_PUNC_MODEL", "ct-punc")).strip()
    spk_model = str(payload.get("funasr_spk_model") or os.environ.get("FUNASR_SPK_MODEL", "cam++")).strip()
    batch_size_s = int(payload.get("funasr_batch_size_s") or os.environ.get("FUNASR_BATCH_SIZE_S", "300"))
    return {
        "model": model,
        "vad_model": vad_model,
        "punc_model": punc_model,
        "spk_model": spk_model,
        "batch_size_s": max(1, batch_size_s),
        "hotword": str(payload.get("funasr_hotword") or "").strip(),
    }


def get_funasr_model(config: dict[str, Any]) -> Any:
    try:
        from funasr import AutoModel
    except ImportError as exc:
        raise ValueError("FunASR 未安装；请先运行 pip install funasr modelscope。") from exc

    key = (
        str(config["model"]),
        str(config["vad_model"]),
        str(config["punc_model"]),
        str(config["spk_model"]),
    )
    model = funasr_models.get(key)
    if model is not None:
        return model

    kwargs: dict[str, Any] = {"model": config["model"]}
    if config["vad_model"]:
        kwargs["vad_model"] = config["vad_model"]
    if config["punc_model"]:
        kwargs["punc_model"] = config["punc_model"]
    if config["spk_model"]:
        kwargs["spk_model"] = config["spk_model"]
    model = AutoModel(**kwargs)
    funasr_models[key] = model
    return model


def normalize_funasr_speaker(value: Any, fallback_index: int) -> str:
    if value is None or value == "":
        return f"SPEAKER_{fallback_index:02d}"
    if isinstance(value, int):
        return f"SPEAKER_{value:02d}"
    text = str(value).strip()
    if text.isdigit():
        return f"SPEAKER_{int(text):02d}"
    return text


def normalize_funasr_segment(raw: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    text = str(raw.get("text") or raw.get("sentence") or raw.get("onebest") or "").strip()
    timestamp = raw.get("timestamp") or raw.get("time_stamp")
    start = numeric_time_seconds(raw.get("start") or raw.get("begin") or raw.get("start_time"))
    end = numeric_time_seconds(raw.get("end") or raw.get("stop") or raw.get("end_time"))
    if isinstance(timestamp, list) and timestamp:
        first = timestamp[0]
        last = timestamp[-1]
        if isinstance(first, list) and first:
            start = numeric_time_seconds(first[0])
        if isinstance(last, list) and len(last) > 1:
            end = numeric_time_seconds(last[1])
    speaker = normalize_funasr_speaker(
        raw.get("spk") or raw.get("speaker") or raw.get("speaker_id"),
        fallback_index,
    )
    return {
        "start": round(start, 2),
        "end": round(end, 2),
        "text": text,
        "speaker": speaker,
        "raw_speaker": speaker,
    }


def funasr_result_items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def normalize_funasr_result(raw: Any, source_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for item in funasr_result_items(raw):
        sentence_info = item.get("sentence_info") or item.get("sentences") or item.get("segments")
        if isinstance(sentence_info, list):
            for sentence in sentence_info:
                if isinstance(sentence, dict):
                    segment = normalize_funasr_segment(sentence, len(segments))
                    if segment["text"]:
                        segments.append(segment)
        text = str(item.get("text") or "").strip()
        if text:
            text_parts.append(text)

    if not segments and text_parts:
        segments.append(
            {
                "start": 0.0,
                "end": 0.0,
                "text": "\n".join(text_parts),
                "speaker": "SPEAKER_00",
                "raw_speaker": "SPEAKER_00",
            }
        )

    speakers: list[dict[str, Any]] = []
    for speaker in sorted({segment["speaker"] for segment in segments}):
        speaker_segments = [segment for segment in segments if segment["speaker"] == speaker]
        duration = sum(max(0.0, float(segment.get("end") or 0) - float(segment.get("start") or 0)) for segment in speaker_segments)
        speakers.append(
            {
                "speaker": speaker,
                "display_name": speaker,
                "duration": round(duration, 2),
                "turn_count": len(speaker_segments),
                "identity": None,
            }
        )

    lines = [
        f"[{format_timestamp(float(segment['start']))}-{format_timestamp(float(segment['end']))}] "
        f"{segment['speaker']}({segment['raw_speaker']}): {segment['text']}"
        for segment in segments
        if segment.get("text")
    ]
    transcript = "\n".join(lines).strip()

    MULTIMODAL_DIARIZED_ASR_DIR.mkdir(parents=True, exist_ok=True)
    record_id = f"funasr-asr-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    txt_path = MULTIMODAL_DIARIZED_ASR_DIR / f"{record_id}.txt"
    json_path = MULTIMODAL_DIARIZED_ASR_DIR / f"{record_id}.json"
    txt_path.write_text(transcript, encoding="utf-8")
    record = {
        "id": record_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "provider": "funasr",
        "source_path": str(source_path),
        "source_size": source_path.stat().st_size,
        "model": config["model"],
        "vad_model": config["vad_model"],
        "punc_model": config["punc_model"],
        "spk_model": config["spk_model"],
        "speakers": speakers,
        "segments": segments,
        "transcript_path": str(txt_path),
        "raw_result": raw,
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "text": transcript,
        "segments": segments,
        "speakers": speakers,
        "diarization_turns": [
            {"start": segment["start"], "end": segment["end"], "speaker": segment["raw_speaker"]}
            for segment in segments
        ],
        "saved_path": str(txt_path),
        "record_path": str(json_path),
        "provider": "funasr",
        "model": config["model"],
        "vad_model": config["vad_model"],
        "punc_model": config["punc_model"],
        "spk_model": config["spk_model"],
    }


def call_funasr_diarized_asr(payload: dict[str, Any]) -> dict[str, Any]:
    source_path = resolve_local_media_path(str(payload.get("local_path") or ""))
    if configure_ffmpeg() is None:
        raise ValueError("FunASR 处理视频/音频需要 ffmpeg；请安装 imageio-ffmpeg 或把 ffmpeg.exe 加入 PATH。")
    config = funasr_config(payload)
    model = get_funasr_model(config)
    generate_kwargs: dict[str, Any] = {
        "input": str(source_path),
        "batch_size_s": config["batch_size_s"],
        "merge_vad": True,
        "merge_length_s": int(payload.get("funasr_merge_length_s") or 15),
    }
    if config["hotword"]:
        generate_kwargs["hotword"] = config["hotword"]
    try:
        raw_result = model.generate(**generate_kwargs)
    except FileNotFoundError as exc:
        raise ValueError(f"FunASR 调用外部解码工具失败，通常是 ffmpeg 不可用；原始错误：{exc}") from exc
    return normalize_funasr_result(raw_result, source_path, config)


def call_diarized_asr(payload: dict[str, Any]) -> dict[str, Any]:
    provider = str(payload.get("asr_provider") or os.environ.get("DIGITAL_TWIN_ASR_PROVIDER", "local")).strip().lower()
    if provider in {"volcengine", "volcano", "bytedance"}:
        return call_volcengine_diarized_asr(payload)
    if provider in {"funasr", "local_funasr"}:
        return call_funasr_diarized_asr(payload)
    return call_diarized_whisper_asr(payload)


def public_asr_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job.get("id"),
        "status": job.get("status"),
        "stage": job.get("stage"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "source_path": job.get("source_path"),
        "result": job.get("result"),
        "error": job.get("error"),
    }


def update_asr_job(job_id: str, **updates: Any) -> None:
    with asr_jobs_lock:
        job = asr_jobs.get(job_id)
        if job is None:
            return
        job.update(updates)
        job["updated_at"] = datetime.now().isoformat(timespec="seconds")


def run_diarized_asr_job(job_id: str, payload: dict[str, Any]) -> None:
    try:
        update_asr_job(job_id, status="running", stage="说话人分离与 ASR 处理中")
        result = call_diarized_asr(payload)
    except Exception as exc:
        update_asr_job(job_id, status="failed", stage="失败", error=str(exc))
        return
    update_asr_job(job_id, status="completed", stage="完成", result=result, error=None)


def start_diarized_asr_job(payload: dict[str, Any]) -> dict[str, Any]:
    provider = str(payload.get("asr_provider") or os.environ.get("DIGITAL_TWIN_ASR_PROVIDER", "local")).strip().lower()
    source_label = str(payload.get("volcengine_audio_url") or "") if provider in {"volcengine", "volcano", "bytedance"} else ""
    if not source_label:
        source_label = str(resolve_local_media_path(str(payload.get("local_path") or "")))
    job_id = f"diarized-asr-job-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    now = datetime.now().isoformat(timespec="seconds")
    job = {
        "id": job_id,
        "status": "queued",
        "stage": "排队中",
        "created_at": now,
        "updated_at": now,
        "source_path": source_label,
        "result": None,
        "error": None,
    }
    with asr_jobs_lock:
        asr_jobs[job_id] = job
    asr_job_executor.submit(run_diarized_asr_job, job_id, dict(payload))
    return public_asr_job(job)


def get_asr_job(job_id: str) -> dict[str, Any]:
    with asr_jobs_lock:
        job = asr_jobs.get(job_id)
        if job is None:
            raise ValueError(f"ASR job not found: {job_id}")
        return public_asr_job(dict(job))


def generate_multimodal_intake(payload: dict[str, Any]) -> dict[str, Any]:
    poe_api_key = str(payload.get("poe_api_key") or "").strip()
    poe_model = (
        str(payload.get("poe_model") or "").strip()
        or os.environ.get("DIGITAL_TWIN_MULTIMODAL_MODEL", "GPT-4o").strip()
    )
    files = normalize_intake_files(payload.get("files"))
    original_files = list(files)
    note = str(payload.get("note") or "").strip()
    context = str(payload.get("context") or "").strip()
    if not note and not context and not files:
        raise ValueError("note, context, or files is required")

    attempts: list[dict[str, Any]] = []
    model_text = ""
    model_error = ""
    used_variant = "full"
    for variant_label, variant_files in multimodal_retry_variants(files):
        prompt = build_multimodal_intake_prompt(payload, variant_files)
        user_content = build_multimodal_user_content(prompt, variant_files)
        model_text, model_error = call_poe_model(
            user_content,
            poe_api_key,
            poe_model,
            system_prompt="你是数字分身的多模态材料摄入器，只输出合法 JSON。",
            temperature=0.2,
        )
        attempts.append(
            {
                "variant": variant_label,
                "file_count": len(variant_files),
                "total_bytes": sum(int(item.get("size") or 0) for item in variant_files),
                "error": "" if model_text else model_error,
            }
        )
        if model_text:
            files = variant_files
            used_variant = variant_label
            break
        if not should_retry_multimodal_error(model_error):
            break

    if not model_text:
        return {
            "generation_engine": "poe_model",
            "error": model_error,
            "analysis": None,
            "saved_path": "",
            "attempts": attempts,
            "files": [
                {key: item[key] for key in ("name", "type", "size", "timestamp_seconds")}
                for item in files
            ],
        }
    analysis = parse_json_object(model_text)
    if analysis is None:
        analysis = {
            "summary": "模型返回了非 JSON 结果，已保存原文供人工查看。",
            "observations": [model_text[:1200]],
            "self_signals": [],
            "expression_signals": [],
            "relationship_signals": [],
            "memory_candidates": [],
            "risk_flags": ["模型输出格式不可解析，不能自动进入记忆。"],
            "questions_for_user": ["是否把这段原文作为人工材料继续整理？"],
            "recommended_next_action": "ask_user",
        }
    if len(files) < len(original_files):
        analysis.setdefault("risk_flags", [])
        analysis["risk_flags"].append(
            f"为避免 Poe 多图请求失败，本次从 {len(original_files)} 帧自动降级为 {len(files)} 帧分析；结论只代表抽样帧。"
        )

    MULTIMODAL_INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "id": f"mmi-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "target": str(payload.get("target") or "self_understanding").strip(),
        "media_kind": str(payload.get("media_kind") or "mixed").strip(),
        "source_name": str(payload.get("source_name") or "").strip(),
        "video_metadata": payload.get("video_metadata") if isinstance(payload.get("video_metadata"), dict) else {},
        "timeline_text": str(payload.get("timeline_text") or "").strip(),
        "note": note,
        "context": context,
        "attempts": attempts,
        "used_variant": used_variant,
        "files": [
            {key: item[key] for key in ("name", "type", "size", "timestamp_seconds")}
            for item in files
        ],
        "analysis": analysis,
    }
    output_path = MULTIMODAL_INTAKE_DIR / f"{record['id']}.json"
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "generation_engine": "poe_model",
        "error": "",
        "analysis": analysis,
        "saved_path": str(output_path),
        "attempts": attempts,
        "used_variant": used_variant,
        "files": record["files"],
    }


def normalize_confirmed_scope(value: str) -> str:
    allowed = {
        "short_term",
        "self_core_candidate",
        "expression_style",
        "interaction_style",
        "relationship",
        "daily_topic",
    }
    scope = str(value or "short_term").strip()
    return scope if scope in allowed else "short_term"


def normalize_confirmed_confidence(value: str) -> str:
    confidence = str(value or "medium").strip()
    return confidence if confidence in {"low", "medium", "high"} else "medium"


def confirm_multimodal_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    confirmations = payload.get("confirmations")
    question_answers = payload.get("question_answers")
    if not isinstance(confirmations, list):
        confirmations = []
    if not isinstance(question_answers, list):
        question_answers = []

    record_id = f"mmc-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    created_at = datetime.now().isoformat(timespec="seconds")
    source_saved_path = str(payload.get("source_saved_path") or "").strip()
    target = str(payload.get("target") or "self_understanding").strip()
    analysis_summary = str(payload.get("analysis_summary") or "").strip()

    memory_rows: list[dict[str, Any]] = []
    normalized_confirmations: list[dict[str, Any]] = []
    for item in confirmations:
        if not isinstance(item, dict):
            continue
        candidate = str(item.get("candidate") or "").strip()
        if not candidate:
            continue
        row = {
            "id": f"{record_id}-f{len(memory_rows) + 1}",
            "created_at": created_at,
            "candidate": candidate[:2000],
            "scope": "self_core_candidate",
            "confidence": normalize_confirmed_confidence(str(item.get("confidence") or "")),
            "target": target,
            "source_type": str(item.get("source_type") or "memory_candidate").strip()[:80],
            "source_saved_path": source_saved_path,
            "analysis_summary": analysis_summary[:600],
            "confirmed_by_user": True,
        }
        memory_rows.append(row)
        normalized_confirmations.append(row)

    normalized_answers: list[dict[str, Any]] = []
    for item in question_answers:
        if not isinstance(item, dict):
            continue
        answer = str(item.get("answer") or "").strip()
        if not answer:
            continue
        question = str(item.get("question") or "").strip()
        row = {
            "id": f"{record_id}-q{len(normalized_answers) + 1}",
            "created_at": created_at,
            "candidate": f"用户对确认问题的补充：{answer[:1800]}",
            "scope": "self_core_candidate",
            "confidence": "high",
            "target": target,
            "source_type": "question_answer",
            "question": question[:600],
            "source_saved_path": source_saved_path,
            "analysis_summary": analysis_summary[:600],
            "confirmed_by_user": True,
        }
        memory_rows.append(row)
        normalized_answers.append(row)

    if not memory_rows:
        raise ValueError("no confirmed candidates selected")

    MULTIMODAL_CONFIRM_DIR.mkdir(parents=True, exist_ok=True)
    MULTIMODAL_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "id": record_id,
        "created_at": created_at,
        "target": target,
        "source_saved_path": source_saved_path,
        "analysis_summary": analysis_summary,
        "confirmations": normalized_confirmations,
        "question_answers": normalized_answers,
    }
    record_path = MULTIMODAL_CONFIRM_DIR / f"{record_id}.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    with MULTIMODAL_MEMORY_PATH.open("a", encoding="utf-8") as handle:
        for row in memory_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "record_path": str(record_path),
        "memory_path": str(MULTIMODAL_MEMORY_PATH),
        "injected_count": len(memory_rows),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def injected_selfcore_candidate_ids() -> set[str]:
    ids: set[str] = set()
    for item in read_jsonl(SELFCORE_INJECTION_LOG_PATH):
        for candidate_id in item.get("candidate_ids") or []:
            if candidate_id:
                ids.add(str(candidate_id))
    return ids


def load_selfcore_candidate_records() -> list[dict[str, Any]]:
    injected_ids = injected_selfcore_candidate_ids()
    records = []
    for item in read_jsonl(MULTIMODAL_MEMORY_PATH):
        if str(item.get("scope") or "") != "self_core_candidate":
            continue
        candidate_id = str(item.get("id") or "").strip()
        if not candidate_id:
            continue
        records.append(
            {
                "id": candidate_id,
                "created_at": str(item.get("created_at") or ""),
                "candidate": str(item.get("candidate") or "").strip(),
                "confidence": normalize_confirmed_confidence(str(item.get("confidence") or "")),
                "target": str(item.get("target") or "self_understanding"),
                "source_type": str(item.get("source_type") or ""),
                "source_saved_path": str(item.get("source_saved_path") or ""),
                "analysis_summary": str(item.get("analysis_summary") or ""),
                "injected": candidate_id in injected_ids,
            }
        )
    return [item for item in records if item["candidate"]]


def list_selfcore_candidates() -> dict[str, Any]:
    candidates = load_selfcore_candidate_records()
    pending = [item for item in candidates if not item["injected"]]
    counts: dict[str, int] = {}
    for item in pending:
        counts[item["target"]] = counts.get(item["target"], 0) + 1
    return {
        "candidates": candidates,
        "pending_count": len(pending),
        "total_count": len(candidates),
        "target_counts": counts,
        "selfcore_path": str(SELF_CORE_PATH),
        "injection_log_path": str(SELFCORE_INJECTION_LOG_PATH),
    }


def selected_selfcore_candidates(candidate_ids: list[Any]) -> list[dict[str, Any]]:
    requested = {str(item) for item in candidate_ids if item}
    candidates = [item for item in load_selfcore_candidate_records() if not item["injected"]]
    if not requested:
        return candidates
    return [item for item in candidates if item["id"] in requested]


def local_selfcore_merge(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        grouped.setdefault(str(item.get("target") or "self_understanding"), []).append(item)

    proposals = []
    for target, items in grouped.items():
        priority = {"high": 0, "medium": 1, "low": 2}
        chosen = sorted(items, key=lambda item: priority.get(str(item.get("confidence")), 3))[:8]
        candidate_ids = [str(item["id"]) for item in chosen]
        lines = [f"- {item['candidate']}" for item in chosen]
        proposal_text = "\n".join(lines)
        proposals.append(
            {
                "id": f"proposal-{len(proposals) + 1}",
                "section": target,
                "title": target.replace("_", " "),
                "merged_feature": proposal_text,
                "candidate_ids": candidate_ids,
                "confidence": "medium" if len(chosen) < 3 else "high",
                "patch_text": proposal_text,
            }
        )
    return {
        "engine": "local",
        "proposals": proposals,
        "questions": [],
    }


def model_selfcore_merge(
    candidates: list[dict[str, Any]],
    api_key: str,
    model: str,
) -> dict[str, Any] | None:
    candidate_lines = "\n".join(
        f"- id={item['id']} target={item['target']} confidence={item['confidence']} text={item['candidate']}"
        for item in candidates
    )
    prompt = f"""你是 SelfCore 候选合并器。请把用户已经确认的多模态候选，合并成可注入 SelfCore 的提案。

现有 SelfCore 摘要：
{self_core_excerpt()}

候选池：
{candidate_lines}

要求：
- 合并重复、相近、同义的候选，不要逐条堆砌。
- 区分稳定特征、表达风格、互动习惯、反模式/边界。
- 不要把单次状态写成稳定人格；置信度不足时写成候选或观察。
- 每个提案必须保留 candidate_ids。
- 只输出 JSON。

JSON 结构：
{{
  "proposals": [
    {{
      "id": "proposal-1",
      "section": "SelfCore 中建议注入的章节名",
      "title": "短标题",
      "merged_feature": "合并后的特征描述",
      "candidate_ids": ["候选 id"],
      "confidence": "low|medium|high",
      "patch_text": "建议追加到 SelfCore 的 Markdown 片段"
    }}
  ],
  "questions": ["仍需要用户确认的问题"]
}}"""
    text, error_message = call_poe_model(
        prompt,
        api_key,
        model or "GPT-4o",
        system_prompt="你是严格的 SelfCore 候选合并器，只输出合法 JSON。",
        temperature=0.2,
    )
    if not text:
        fallback = local_selfcore_merge(candidates)
        fallback["engine"] = "poe_model_failed_local_fallback"
        fallback["error"] = error_message
        return fallback
    parsed = parse_json_object(text)
    if not parsed or not isinstance(parsed.get("proposals"), list):
        fallback = local_selfcore_merge(candidates)
        fallback["engine"] = "poe_model_unparseable_local_fallback"
        fallback["error"] = "model output is not valid proposal JSON"
        return fallback
    return {
        "engine": "poe_model",
        "proposals": parsed.get("proposals") or [],
        "questions": parsed.get("questions") or [],
    }


def merge_selfcore_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    candidate_ids = payload.get("candidate_ids")
    if not isinstance(candidate_ids, list):
        candidate_ids = []
    candidates = selected_selfcore_candidates(candidate_ids)
    if not candidates:
        raise ValueError("no pending selfcore candidates selected")

    api_key = str(payload.get("poe_api_key") or "").strip()
    model = str(payload.get("poe_model") or "GPT-4o").strip()
    use_model = bool(payload.get("use_model", False)) and bool(api_key)
    merged = model_selfcore_merge(candidates, api_key, model) if use_model else None
    if merged is None:
        merged = local_selfcore_merge(candidates)

    record_id = f"scm-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    record = {
        "id": record_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "candidate_ids": [item["id"] for item in candidates],
        "candidate_count": len(candidates),
        **merged,
    }
    SELFCORE_MERGE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SELFCORE_MERGE_DIR / f"{record_id}.json"
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    record["saved_path"] = str(output_path)
    return record


def inject_selfcore_proposals(payload: dict[str, Any]) -> dict[str, Any]:
    proposals = payload.get("proposals")
    if not isinstance(proposals, list):
        proposals = []
    selected = []
    for item in proposals:
        if not isinstance(item, dict):
            continue
        patch_text = str(item.get("patch_text") or item.get("merged_feature") or "").strip()
        if not patch_text:
            continue
        candidate_ids = [str(value) for value in item.get("candidate_ids") or [] if value]
        selected.append(
            {
                "id": str(item.get("id") or f"proposal-{len(selected) + 1}"),
                "section": str(item.get("section") or "SelfCore 候选注入"),
                "title": str(item.get("title") or "候选合并特征"),
                "confidence": normalize_confirmed_confidence(str(item.get("confidence") or "medium")),
                "patch_text": patch_text,
                "candidate_ids": candidate_ids,
            }
        )
    if not selected:
        raise ValueError("no proposal selected for selfcore injection")
    if not SELF_CORE_PATH.exists():
        raise ValueError("SelfCore file does not exist")

    injection_id = f"sci-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    created_at = datetime.now().isoformat(timespec="seconds")
    SELFCORE_INJECTION_DIR.mkdir(parents=True, exist_ok=True)
    SELFCORE_INJECTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup_path = SELFCORE_INJECTION_DIR / f"{injection_id}.SelfCore.before.md"
    current_text = SELF_CORE_PATH.read_text(encoding="utf-8")
    backup_path.write_text(current_text, encoding="utf-8")

    block_lines = [
        "",
        f"## SelfCore 候选注入（{created_at}）",
        "",
        f"> 来源：多模态候选工作台；注入批次 `{injection_id}`。",
        "",
    ]
    all_candidate_ids: list[str] = []
    for item in selected:
        block_lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- 建议章节：{item['section']}",
                f"- 置信度：{item['confidence']}",
                f"- 候选来源：{', '.join(item['candidate_ids']) or 'manual-proposal'}",
                "",
                item["patch_text"],
                "",
            ]
        )
        all_candidate_ids.extend(item["candidate_ids"])
    SELF_CORE_PATH.write_text(current_text.rstrip() + "\n" + "\n".join(block_lines).rstrip() + "\n", encoding="utf-8")

    log_record = {
        "id": injection_id,
        "created_at": created_at,
        "proposal_count": len(selected),
        "candidate_ids": sorted(set(all_candidate_ids)),
        "selfcore_path": str(SELF_CORE_PATH),
        "backup_path": str(backup_path),
        "proposals": selected,
    }
    with SELFCORE_INJECTION_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(log_record, ensure_ascii=False) + "\n")
    record_path = SELFCORE_INJECTION_DIR / f"{injection_id}.json"
    record_path.write_text(json.dumps(log_record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "id": injection_id,
        "injected_count": len(selected),
        "candidate_count": len(set(all_candidate_ids)),
        "selfcore_path": str(SELF_CORE_PATH),
        "backup_path": str(backup_path),
        "record_path": str(record_path),
    }


NO_REPLY_SENTINELS = {"__NO_REPLY__", "NO_REPLY", "不回复", "不用回", "沉默"}
LOW_VALUE_REPLIES = {
    "哈哈",
    "哈哈哈",
    "确实",
    "有道理",
    "是的",
    "对",
    "可以",
    "行",
    "嗯",
    "好的",
}


def is_no_reply_output(value: str) -> bool:
    text = value.strip().strip("。.!！ \n\r\t")
    return text in NO_REPLY_SENTINELS


def normalize_chat_style(value: str, max_segments: int = 3, max_chars: int = 22) -> list[str]:
    text = re.sub(r"^\s*(我|用户|回复|草稿)\s*[：:]\s*", "", value.strip())
    text = text.strip("「」\"'“”")
    text = re.sub(r"\s+", " ", text)
    if not text:
        return []
    if is_no_reply_output(text):
        return []

    rough_parts = []
    for part in re.split(r"[\n\r]+", text):
        rough_parts.extend(re.split(r"(?<=[。！？!?；;，,、])\s*", part.strip()))

    segments: list[str] = []
    for part in rough_parts:
        part = part.strip()
        if not part:
            continue
        queue = [part]
        while queue:
            current = queue.pop(0).strip()
            if not current:
                continue
            if len(current) <= max_chars and not (len(current) > 14 and re.search(r"[，,、]", current)):
                segments.append(current)
                continue
            split_at = max(current.rfind(mark, 0, max_chars + 1) for mark in "，,、 ")
            if split_at < 4:
                split_at = max(current.find(mark, max_chars // 2) for mark in "，,、 ")
            if split_at >= 4:
                left = current[:split_at].strip(" ，,、")
                right = current[split_at + 1 :].strip()
                if left:
                    segments.append(left)
                if right:
                    queue.insert(0, right)
            else:
                segments.append(current)
        if len(segments) >= max_segments:
            break

    cleaned = []
    for segment in segments[:max_segments]:
        segment = segment.strip().strip("，,、")
        if segment in LOW_VALUE_REPLIES:
            continue
        if segment and segment not in cleaned:
            cleaned.append(segment)
    if cleaned:
        return cleaned
    fallback = text[:max_chars].strip().strip("，,、")
    if not fallback or fallback in LOW_VALUE_REPLIES or is_no_reply_output(fallback):
        return []
    return [fallback]


def normalize_conversation_history(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("conversation_history must be a list")
    normalized: list[dict[str, str]] = []
    for item in value[-40:]:
        if not isinstance(item, dict):
            raise ValueError("conversation history item must be an object")
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role not in {"contact", "self"}:
            raise ValueError(f"invalid conversation role: {role}")
        if content:
            normalized.append({"role": role, "content": content[:4000]})
    return normalized


def self_core_excerpt() -> str:
    if not SELF_CORE_PATH.exists():
        return ""
    text_value = SELF_CORE_PATH.read_text(encoding="utf-8")
    start = text_value.find("## 表达 DNA")
    end = text_value.find("## 反模式与边界")
    if start == -1:
        return text_value[:1800]
    if end == -1 or end <= start:
        end = min(len(text_value), start + 2200)
    return text_value[start:end].strip()


def confirmed_multimodal_memory_excerpt(limit: int = 30) -> str:
    if not MULTIMODAL_MEMORY_PATH.exists():
        return "（暂无已确认的多模态记忆）"
    lines = MULTIMODAL_MEMORY_PATH.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    output = []
    for item in records:
        scope = str(item.get("scope") or "short_term")
        confidence = str(item.get("confidence") or "medium")
        candidate = str(item.get("candidate") or "").strip()
        if candidate:
            output.append(f"- [{scope}/{confidence}] {candidate}")
    return "\n".join(output) or "（暂无已确认的多模态记忆）"


def format_dyadic_profile(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "未找到该联系人的双人沟通画像。禁止用关系大类模板补齐，只能保守生成。"
    evidence = profile.get("evidence") or {}
    confidence = profile.get("confidence") or {}
    topics = profile.get("topics") or {}
    interaction = profile.get("interaction_pattern") or {}
    expression = profile.get("expression_pattern") or {}
    temporal = profile.get("temporal_pattern") or {}
    relative = profile.get("relative_to_global") or {}
    topic_names = [
        item.get("label") or TOPIC_LABELS.get(item.get("topic"), item.get("topic"))
        for item in (topics.get("shared_topics") or [])[:8]
    ]
    mechanisms = [
        f"{item.get('mechanism')}:{item.get('ratio')}"
        for item in (expression.get("dominant_mechanisms") or [])[:6]
    ]
    differences = [
        f"{item.get('metric')}:{item.get('delta')}"
        for item in (relative.get("strongest_differences") or [])
    ]
    return f"""- 画像置信度：{confidence.get('level')} ({confidence.get('score')})
- 私聊样本（我/对方）：{evidence.get('private_outgoing_count', 0)}/{evidence.get('private_incoming_count', 0)}
- 群聊定向样本（我/对方）：{evidence.get('group_directed_outgoing_count', 0)}/{evidence.get('group_directed_incoming_count', 0)}
- 共同主题：{', '.join(str(item) for item in topic_names if item) or '不足'}
- 我主动开启比例：{interaction.get('initiation_ratio')}
- 中位回复秒数：{interaction.get('median_reply_seconds')}
- 连续发送平均条数：{interaction.get('average_burst_size')}
- 平均/中位字数：{expression.get('average_chars')}/{expression.get('median_chars')}
- 短消息比例：{expression.get('short_message_ratio')}
- 追问比例：{expression.get('question_marker_ratio')}
- 判断比例：{expression.get('judgment_marker_ratio')}
- 边界表达比例：{expression.get('boundary_marker_ratio')}
- 行动表达比例：{expression.get('action_marker_ratio')}
- 玩笑比例：{expression.get('laughter_ratio')}
- 强反应比例：{expression.get('strong_reaction_ratio')}
- 主要表达机制：{', '.join(mechanisms) or '不足'}
- 相对全局最明显差异：{', '.join(differences) or '不足'}
- 时间段分布：{json.dumps(temporal.get('daypart_distribution') or {}, ensure_ascii=False)}
- 数据限制：{'；'.join(confidence.get('limitations') or []) or '无'}"""


def build_model_prompt(
    draft_context: dict[str, Any],
    dyadic_profile: dict[str, Any] | None,
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    person = draft_context.get("person") or {}
    questions = "\n".join(f"- {item}" for item in draft_context.get("questions_for_user") or [])
    history = conversation_history or []
    background_history = history[:-3]
    reply_anchor_history = history[-3:]

    def render_history(items: list[dict[str, str]]) -> str:
        lines = []
        for item in items:
            speaker = "我" if item["role"] == "self" else "群友"
            lines.append(f"{speaker}：{item['content']}")
        return "\n".join(lines) or "（无）"

    background_text = render_history(background_history)
    reply_anchor_text = render_history(reply_anchor_history)
    response_policy = draft_context.get("response_policy") or "balanced"
    allow_no_reply = bool(draft_context.get("allow_no_reply", False))
    if response_policy == "active_group":
        participation_guidance = """当前是熟人群的积极参与模式：
- 不要把“不说废话”理解成“不说话”。你应保持自然存在感。
- 被直接提问、被点名、出现 AI/投资/游戏/日常等共同话题时，原则上回应。
- 有一句态度、一个反问、一个接梗、一个轻判断或一条补充信息，就足以回复；不要求形成完整论证。
- 只有重复消息、系统噪声、无法理解的残缺上下文，或确实完全没有可接内容时，才输出 `__NO_REPLY__`。
- 当“回复”和“沉默”都合理时，优先给出一句短而具体的回复。"""
    else:
        participation_guidance = """当前是平衡参与模式：
- 不逐条抢答，也不默认沉默。
- 被直接提问或有自然接话空间时应回复；确实没有内容时才输出 `__NO_REPLY__`。"""
    if not allow_no_reply:
        participation_guidance += """

本次是用户主动发起的诊断生成：
- 必须给出当前上下文下最合适的候选回复，不得输出 `__NO_REPLY__`、沉默或“不用回”。
- 即使自动监控可能选择沉默，也要给出一句最自然、最短且有具体作用的接话，供用户判断内容质量。"""
    if response_policy == "active_group":
        participation_guidance += """

群聊接话时序：
- 接话锚点只能来自最后 1-3 条消息，尤其以最后一条为准。
- 更早的长上下文用于理解整场话题、人物立场、指代、玩笑和话题转折，不能直接作为回复对象。
- 如果最后几条已经切换话题，必须跟随新话题；宁可轻接当前话题，也不要远距离回头接话。"""
    return f"""你是用户的数字分身草稿生成器。不要写咨询师腔、客服腔、公众号腔、AI 模板腔。

任务：生成一次“像用户本人会发”的中文聊天草稿。它可以是 1-5 条连续短消息，而不是一整段长回复。

核心要求：
- 只输出草稿正文，不解释。
- 用户表达简洁，但不是默认沉默。目标是少空话、自然参与。
- 不需要每次都有深刻观点；短态度、轻判断、反问、接梗和具体追问都是有效回复。
- 回复要有观点和态度，不能只是“哈哈哈”“确实”“有道理”“可以”“你说得对”。
- 不要打哈哈，不要没话找话，不要为了显得在线而接话。
- 你正在续写多轮真实聊天。必须理解前文中的指代、问题、情绪变化和双方已经表达过的立场。
- 不要重复前文已经说过的话，不要把对方的话误认为是用户的话。
- 输出的是“我”的下一条回复；不要加“我：”、引号或角色名。
- 用户很少发大段话。就算信息量多，也通常拆成连续短句发送。
- 每条短消息尽量 6-28 个字；不要写成回车换行的一大段解释。
- 如果需要表达多层意思，用多行短句表示“连续发了几条微信”，每行就是一条待发送消息。
- 不要用分号串成长句，不要写论文式因果链，不要一次性把所有判断都讲完。
- 群聊里优先短、准、接得上上下文；可追问，可轻判断，可半句话收住。
- 群聊涉及“这次、今年、现在、刚刚”等时效话题时，不得自行补充上下文未出现的球队、球员、人物、公司、比分、阵容、资格、价格、日期或数字。
- 不确定当前事实时，只对群友已经说出的内容作回应，或提出短问题；不要用旧知识猜当前状态。
- 不得向群友询问“你们在聊什么”“现在什么话题”“发生什么了”来弥补上下文不足，这不像用户本人。
- 自动模式下，如果长上下文仍不足以理解最后 1-3 条，就输出 `__NO_REPLY__`，不要暴露自己没看懂；人工强制生成时也只能基于接话窗口给出最小回应，不能反问聊天主题。
- 联系人的双人沟通画像优先于通用 SelfCore，必须按该对象的真实句长、节奏、主动性、话题和表达机制生成。
- 统计画像描述的是机制和分布，不是要求每条消息都塞入全部特征。
- 如果双人画像置信度不足，保守生成，不得用“家人/同事/朋友模板”脑补。
- 不要机械使用“先别急”“安顿情绪”“谁对谁错”“关键是边界和责任”“你已经做很多了”。
- 不要过度温柔，不要心理咨询式共情。
- 高风险内容只写草稿，不替用户承诺、道歉、投资建议或发送决定。

本轮参与策略：
{participation_guidance}

SelfCore 表达摘要：
{self_core_excerpt()}

已确认的多模态记忆：
{confirmed_multimodal_memory_excerpt()}

该联系人的双人沟通表现型（优先级高于 SelfCore）：
{format_dyadic_profile(dyadic_profile)}

联系人关系：
- 展示名：{person.get("display_name") or "未识别"}
- 称呼候选：{person.get("call_name") or "无"}
- 节点类型：{person.get("node_type") or "未知"}
- 客观关系：{person.get("objective_relationship") or "未知"}
- 关系定位：{person.get("relationship_positioning") or "暂无"}
- 高频主题：{person.get("frequent_topics") or person.get("interest_circles") or "暂无"}
- 称呼证据：{person.get("call_evidence") or "暂无，称呼要保守"}

本次场景：
- 意图：{draft_context.get("intent")}
- 模式：{draft_context.get("mode")}
- 场景：{draft_context.get("scenario")}
- 风险等级：{draft_context.get("risk_level")}
- 需要确认：{draft_context.get("approval_required")}

主题理解上下文（只用于理解整场对话，不直接回这里的旧消息）：
{background_text}

当前接话窗口（回复必须直接承接这里，不能回到更早话题）：
{reply_anchor_text}

需要用户确认的事项：
{questions or "- 暂无"}

请紧接上面的最后一条消息，生成“我”的下一次发言正文。
如果输出多行，每一行都必须是一条可以单独发送的短微信消息。"""


def call_poe_model(
    prompt: str | list[dict[str, Any]],
    api_key: str,
    model: str,
    system_prompt: str = "你只生成中文聊天草稿正文，不解释，不复述规则。",
    temperature: float = 0.75,
) -> tuple[str | None, str]:
    endpoint = os.environ.get(
        "DIGITAL_TWIN_LLM_ENDPOINT",
        "https://api.poe.com/v1/chat/completions",
    ).strip()
    resolved_model = model or os.environ.get("DIGITAL_TWIN_LLM_MODEL", "Claude-Sonnet-4").strip()
    resolved_api_key = api_key or os.environ.get("DIGITAL_TWIN_LLM_API_KEY", "").strip()
    if not resolved_api_key:
        return None, "Poe API Key 未输入。"
    if not resolved_model:
        return None, "Poe 模型名未填写。"

    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {resolved_api_key}",
    }
    req = request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            detail = ""

        if exc.code == 401:
            return (
                None,
                "Poe API Key 无效、过期，或没有权限访问当前 Poe API。请重新粘贴 Key，并确认没有混入空格或换行。",
            )
        if exc.code == 403:
            return None, "Poe API 权限不足：当前 Key 可能不能访问所选模型或接口。"
        if exc.code == 413:
            return None, "Poe API 拒绝了过大的请求。请减少抽帧数量、降低最长边或 JPEG 质量后重试。"
        if exc.code >= 500:
            suffix = f"；返回：{detail[:500]}" if detail else ""
            return None, f"Poe API 服务端错误 HTTP {exc.code}。多模态请求可先试 4 帧、480px、低质量；也可能是 Poe 临时异常{suffix}"

        suffix = f"；返回：{detail[:500]}" if detail else ""
        return None, f"Poe API 调用失败 HTTP {exc.code}{suffix}"
    except Exception as exc:
        return None, f"Poe API 调用失败：{exc}"

    try:
        text_value = str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError):
        return None, "Poe API 返回格式无法解析。"
    if not text_value:
        return None, "Poe API 返回为空。"
    return text_value, ""


def field(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def count_total(value: str) -> int:
    return sum(int(match) for match in re.findall(r":(\d+)", value or ""))


def parse_scene_counts(value: str) -> list[tuple[str, int]]:
    pairs: list[tuple[str, int]] = []
    for item in re.split(r"[；;]", value or ""):
        item = item.strip()
        if not item or ":" not in item:
            continue
        name, count = item.rsplit(":", 1)
        try:
            pairs.append((name.strip(), int(count.strip())))
        except ValueError:
            continue
    return pairs


def communication_stats(main_scenes: str) -> dict[str, Any]:
    scene_counts = parse_scene_counts(main_scenes)
    total = sum(count for _, count in scene_counts)
    sessions = get_sessions()

    starts: list[date] = []
    ends: list[date] = []
    matched_count = 0
    for scene_name, count in scene_counts:
        session = sessions.get(scene_name)
        if not session:
            continue
        matched_count += count
        starts.append(session["start"])
        ends.append(session["end"])

    if starts and ends:
        start = min(starts)
        end = max(ends)
        days = max(1, (end - start).days + 1)
        daily_average = matched_count / days
        date_span = f"{start.isoformat()} 至 {end.isoformat()}"
    else:
        days = None
        daily_average = float(total)
        date_span = "暂无会话日期"

    return {
        "communication_total": total,
        "communication_matched_total": matched_count,
        "communication_days": days,
        "communication_daily_average": round(daily_average, 2),
        "communication_date_span": date_span,
    }


def communication_label(daily_average: float) -> str:
    if daily_average >= 50:
        return "高密度"
    if daily_average >= 15:
        return "中高密度"
    if daily_average >= 5:
        return "中密度"
    return "低密度"


def list_people() -> list[dict[str, Any]]:
    people: list[dict[str, Any]] = []
    for index, row in enumerate(get_people()):
        display_name = field(row, "展示名称")
        call_name = field(row, "称呼名")
        wechat_name = field(row, "微信名")
        objective_relationship = field(row, "客观关系")
        relationship_positioning = field(row, "关系定位")
        node_type = field(row, "节点类型")
        main_scenes = field(row, "主要场景")
        frequent_topics = field(row, "高频主题")
        interest_circles = field(row, "兴趣/活动圈层")
        call_evidence = field(row, "称呼证据")
        primary_query = call_name or wechat_name or display_name
        if not primary_query:
            continue
        is_direct = node_type == "直接微信关系"
        stats = communication_stats(main_scenes)
        dyadic_profile = resolve_dyadic_profile(
            primary_query,
            display_name,
            call_name,
            wechat_name,
            field(row, "人物"),
        )
        dyadic_confidence = (dyadic_profile or {}).get("confidence") or {}
        dyadic_evidence = (dyadic_profile or {}).get("evidence") or {}
        dyadic_expression = (dyadic_profile or {}).get("expression_pattern") or {}
        dyadic_interaction = (dyadic_profile or {}).get("interaction_pattern") or {}
        dyadic_topics = (dyadic_profile or {}).get("topics") or {}
        can_generate_draft = is_direct
        can_proactively_suggest = is_direct and bool(frequent_topics or interest_circles)
        permission_note = (
            "可生成草稿；主动沟通仍需确认"
            if is_direct
            else "仅用于上下文；不可主动或假装熟悉"
        )
        people.append(
            {
                "id": f"p{index + 1}",
                "query": primary_query,
                "display_name": display_name,
                "call_name": call_name,
                "wechat_name": wechat_name,
                "objective_relationship": objective_relationship,
                "relationship_positioning": relationship_positioning,
                "node_type": node_type,
                "main_scenes": main_scenes,
                "frequent_topics": frequent_topics,
                "interest_circles": interest_circles,
                "call_evidence": call_evidence,
                "has_call_evidence": bool(call_evidence),
                "category": objective_relationship or "未分类",
                "communication_total": stats["communication_total"],
                "communication_matched_total": stats["communication_matched_total"],
                "communication_days": stats["communication_days"],
                "communication_daily_average": stats["communication_daily_average"],
                "communication_date_span": stats["communication_date_span"],
                "communication_density_label": communication_label(
                    stats["communication_daily_average"]
                ),
                "dyadic_profile": {
                    "available": bool(dyadic_profile),
                    "confidence_level": dyadic_confidence.get("level", "insufficient"),
                    "confidence_score": dyadic_confidence.get("score", 0),
                    "private_outgoing_count": dyadic_evidence.get("private_outgoing_count", 0),
                    "private_incoming_count": dyadic_evidence.get("private_incoming_count", 0),
                    "group_directed_outgoing_count": dyadic_evidence.get(
                        "group_directed_outgoing_count", 0
                    ),
                    "group_directed_incoming_count": dyadic_evidence.get(
                        "group_directed_incoming_count", 0
                    ),
                    "average_chars": dyadic_expression.get("average_chars", 0),
                    "median_chars": dyadic_expression.get("median_chars", 0),
                    "average_burst_size": dyadic_interaction.get("average_burst_size", 0),
                    "initiation_ratio": dyadic_interaction.get("initiation_ratio", 0),
                    "top_topics": [
                        item.get("label")
                        or TOPIC_LABELS.get(item.get("topic"), item.get("topic"))
                        for item in (dyadic_topics.get("shared_topics") or [])[:5]
                        if item.get("topic")
                    ],
                    "limitations": dyadic_confidence.get("limitations", []),
                },
                "group": "direct" if is_direct else "mentioned",
                "permission": {
                    "can_retrieve_context": True,
                    "can_generate_draft": can_generate_draft,
                    "can_proactively_suggest": can_proactively_suggest,
                    "can_auto_send": False,
                    "requires_user_approval": True,
                    "note": permission_note,
                },
            }
        )
    people.sort(
        key=lambda item: (
            -item["communication_total"],
            -item["communication_daily_average"],
            item["display_name"],
        )
    )
    return people


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "DigitalTwinDashboard/0.1"

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self.serve_file(DASHBOARD_DIR / "index.html")
            return
        if self.path == "/multimodal.html":
            self.serve_file(DASHBOARD_DIR / "multimodal.html")
            return
        if self.path == "/multimodal.js":
            self.serve_file(DASHBOARD_DIR / "multimodal.js")
            return
        if self.path == "/multimodal.css":
            self.serve_file(DASHBOARD_DIR / "multimodal.css")
            return
        if self.path == "/selfcore-candidates.html":
            self.serve_file(DASHBOARD_DIR / "selfcore-candidates.html")
            return
        if self.path == "/selfcore-candidates.js":
            self.serve_file(DASHBOARD_DIR / "selfcore-candidates.js")
            return
        if self.path == "/selfcore-candidates.css":
            self.serve_file(DASHBOARD_DIR / "selfcore-candidates.css")
            return
        if self.path == "/app.js":
            self.serve_file(DASHBOARD_DIR / "app.js")
            return
        if self.path == "/styles.css":
            self.serve_file(DASHBOARD_DIR / "styles.css")
            return
        if self.path == "/api/health":
            self.send_json({"ok": True})
            return
        if self.path == "/api/people":
            self.send_json({"ok": True, "people": list_people()})
            return
        if self.path == "/api/selfcore-candidates":
            self.send_json({"ok": True, "result": list_selfcore_candidates()})
            return
        if self.path == "/api/speaker-profiles":
            self.send_json({"ok": True, "result": list_speaker_profiles()})
            return
        if self.path.startswith("/api/multimodal/asr-jobs/"):
            job_id = self.path.rsplit("/", 1)[-1]
            try:
                self.send_json({"ok": True, "result": get_asr_job(job_id)})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=404)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path not in {
            "/api/draft",
            "/api/multimodal/intake",
            "/api/multimodal/local-asr",
            "/api/multimodal/diarized-asr",
            "/api/multimodal/diarized-asr-job",
            "/api/multimodal/confirm",
            "/api/speaker-profiles/enroll",
            "/api/selfcore-candidates/merge",
            "/api/selfcore-candidates/inject",
        }:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if self.path == "/api/draft":
                result = generate_draft(payload)
            elif self.path == "/api/multimodal/local-asr":
                result = call_local_whisper_asr(payload)
            elif self.path == "/api/multimodal/diarized-asr":
                result = call_diarized_asr(payload)
            elif self.path == "/api/multimodal/diarized-asr-job":
                result = start_diarized_asr_job(payload)
            elif self.path == "/api/multimodal/confirm":
                result = confirm_multimodal_candidates(payload)
            elif self.path == "/api/speaker-profiles/enroll":
                result = enroll_speaker_profile(payload)
            elif self.path == "/api/selfcore-candidates/merge":
                result = merge_selfcore_candidates(payload)
            elif self.path == "/api/selfcore-candidates/inject":
                result = inject_selfcore_proposals(payload)
            else:
                result = generate_multimodal_intake(payload)
        except Exception as exc:  # Keep local UI errors readable.
            self.send_json({"ok": False, "error": str(exc)}, status=400)
            return
        self.send_json({"ok": True, "result": result})

    def serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local digital twin dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping dashboard.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
