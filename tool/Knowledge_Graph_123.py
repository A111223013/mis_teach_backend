#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import random
import difflib
from typing import List, Dict, Any

# ====== 讀取 API KEY ======
def load_api_keys(env_file: str = "api.env") -> List[str]:
    api_keys = []
    if os.path.exists(env_file):
        print(f"✅ 成功載入 {env_file}")
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key = line.strip()
                    if key.startswith("AIza"):
                        api_keys.append(key)
    else:
        print(f"⚠️ 找不到 {env_file}")
    print(f"🔑 載入API密鑰: {len(api_keys)} 個")
    return api_keys

# ====== 載入分類數據 ======
def load_classification_data(domains_file: str, micro_concepts_file: str):
    try:
        with open(domains_file, "r", encoding="utf-8") as f:
            domains_data = json.load(f)
        if isinstance(domains_data, dict) and "domains" in domains_data:
            domains_data = domains_data["domains"]

        with open(micro_concepts_file, "r", encoding="utf-8") as f:
            micro_data = json.load(f)
        if isinstance(micro_data, dict) and "micro_concepts" in micro_data:
            micro_data = micro_data["micro_concepts"]

        domains_list = [d.get("name", "") for d in domains_data if isinstance(d, dict) and d.get("name")]
        micro_list = [m.get("name", "") for m in micro_data if isinstance(m, dict) and m.get("name")]

        print(f"📊 載入了 {len(domains_list)} 個大知識點 和 {len(micro_list)} 個小知識點")
        return domains_list, micro_list

    except Exception as e:
        print(f"❌ 載入分類數據錯誤: {e}")
        return [], []

# ====== 載入題目 ======
def load_questions(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]
        print(f"📘 載入了 {len(data)} 題")
        return data
    except Exception as e:
        print(f"❌ 載入題目錯誤: {e}")
        return []

# ====== 文字標準化 ======
def normalize_text(text: str) -> str:
    return text.lower().replace(" ", "").replace("\n", "")

# ====== 大知識點匹配 ======
def match_domains(text: str, domains: List[str], key_points: str) -> str:
    text_norm = normalize_text(text)
    key_norm = normalize_text(key_points)
    # 先找文字中或 key_points 出現的 domain
    for d in domains:
        d_norm = normalize_text(d)
        if d_norm in text_norm or d_norm in key_norm:
            return d
    # 找不到就選最接近的一個
    if domains:
        best_match = max(domains, key=lambda d: difflib.SequenceMatcher(None, text_norm, normalize_text(d)).ratio())
        return best_match
    return ""

# ====== 微概念匹配 ======
def match_micro_concepts(text: str, micro_list: List[str], key_points: str) -> List[str]:
    text_norm = normalize_text(text)
    key_norm = normalize_text(key_points)
    matched = []

    # 找文字中或 key_points 出現的微概念
    for m in micro_list:
        m_norm = normalize_text(m)
        if m_norm in text_norm or m_norm in key_norm:
            matched.append(m)

    # 找不到就選最接近的一個
    if not matched and micro_list:
        best_match = max(micro_list, key=lambda m: difflib.SequenceMatcher(None, text_norm, normalize_text(m)).ratio())
        matched = [best_match]

    return matched

# ====== 分類題目 ======
def classify_questions(questions: List[Dict[str, Any]], domains: List[str], micro_concepts: List[str]) -> List[Dict[str, Any]]:
    classified = []
    for q in questions:
        text = q.get("question_text", "")
        # 如果 options 有內容，也納入判斷
        options_text = " ".join(q.get("options", [])) if q.get("options") else ""
        full_text = text + " " + options_text
        key_points = q.get("key-points", "")

        domain = match_domains(full_text, domains, key_points)
        micro_matched = match_micro_concepts(full_text, micro_concepts, key_points)

        q["key-points"] = domain
        q["micro_concepts"] = micro_matched
        classified.append(q)
    return classified

# ====== 儲存 JSON ======
def save_to_json(data: Any, filename: str):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 已輸出到 {filename}")
    except Exception as e:
        print(f"❌ 儲存 JSON 錯誤: {e}")

# ====== 主程式 ======
if __name__ == "__main__":
    api_keys = load_api_keys("api.env")
    domains, micro_concepts = load_classification_data("domains_batch_20250903.json", "micro_concepts_batch_20250903.json")
    questions = load_questions("fainaldata_no_del.json")

    if questions:
        classified = classify_questions(questions, domains, micro_concepts)
        save_to_json(classified, "classified_questions.json")
