#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import random
from typing import List, Dict, Any

# ========== 讀取 API KEY ==========
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

# ========== 載入分類數據 ==========
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

# ========== 載入題目 ==========
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

# ========== 比對大知識點 ==========
def match_domain(text: str, domains: List[str]) -> str:
    if not text or not domains:
        return random.choice(domains) if domains else ""
    text_lower = str(text).lower()
    for d in domains:
        if d.lower() in text_lower:
            return d
    return random.choice(domains)

# ========== 比對微概念 ==========
def match_micro_concepts(text: str, micro_list: List[str]) -> List[str]:
    if not text or not micro_list:
        return [random.choice(micro_list)] if micro_list else []
    text_lower = str(text).lower()
    matched = [m for m in micro_list if m.lower() in text_lower]
    if not matched:
        matched = [random.choice(micro_list)]
    return matched

# ========== 分類題目 ==========
def classify_questions(questions: List[Dict[str, Any]], domains: List[str], micro_concepts: List[str]) -> List[Dict[str, Any]]:
    classified = []
    for q in questions:
        text = q.get("question_text", "")

        # 判斷 key-points (大知識點)
        key_point = match_domain(text, domains)

        # 判斷 micro_concepts (微概念)
        micro_matched = match_micro_concepts(text, micro_concepts)

        # 更新題目
        q["key-points"] = key_point
        q["micro_concepts"] = micro_matched
        classified.append(q)
    return classified

# ========== 儲存 JSON ==========
def save_to_json(data: Any, filename: str):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 已輸出到 {filename}")
    except Exception as e:
        print(f"❌ 儲存 JSON 錯誤: {e}")

# ========== 主程式 ==========
if __name__ == "__main__":
    api_keys = load_api_keys("api.env")
    domains, micro_concepts = load_classification_data("domains_batch_20250903.json", "micro_concepts_batch_20250903.json")
    questions = load_questions("check_exam_output2.json")

    if questions:
        classified = classify_questions(questions, domains, micro_concepts)
        save_to_json(classified, "fainaldata_updated.json")
