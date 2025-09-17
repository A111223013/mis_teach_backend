#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import time
from typing import List, Dict, Any
import google.generativeai as genai

# 延遲時間（秒）
delay_between_requests = 1.0

# ========== 載入分類數據 ==========
def load_classification_data(domains_file: str, micro_concepts_file: str):
    """從 JSON 檔案載入 key-points 和 micro_concepts 清單。"""
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

        print(f"📊 載入了 {len(domains_list)} 個 key-points 和 {len(micro_list)} 個 micro_concepts")
        return domains_list, micro_list

    except Exception as e:
        print(f"❌ 載入分類數據錯誤: {e}")
        return [], []

# ========== 載入題目 ==========
def load_questions(file_path: str) -> List[Dict[str, Any]]:
    """從 JSON 檔案載入題目清單。"""
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

# ========== 使用 Gemini AI 批量判斷（含重試機制） ==========
def classify_with_gemini_batch(model_name: str, questions: List[Dict[str, Any]], domains: List[str], micro_concepts: List[str], max_retries=3):
    """
    批量處理題目，將多個問題打包成一個 API 請求。
    
    根據 key-points 欄位是否為 "基本計概" 來決定判斷範圍。
    """
    
    # 根據 key-points 區分需要重新判斷的題目和只需判斷 micro_concepts 的題目
    reclassify_questions = [q for q in questions if q.get('key-points') == '基本計概']
    micro_only_questions = [q for q in questions if q.get('key-points') != '基本計概']

    classified_results = []
    
    # --- 處理 key-points 為 "基本計概" 的題目 ---
    if reclassify_questions:
        print(f"🔄 正在重新判斷 {len(reclassify_questions)} 題 '基本計概' 類別的題目...")
        prompt_reclassify = f"""
請協助判斷以下題目的 key-points 和 micro_concepts，並以 JSON 陣列格式回覆。

候選 key-points: {domains}
候選 micro_concepts: {micro_concepts}

要求：
1. 針對每個題目，從候選列表中選出最符合的 key-points 和 micro_concepts。
2. key_points 必須為單一字串，如果沒有明確匹配，選最接近的一個。
3. micro_concepts 必須為字串陣列 (array of strings)，允許多個，若完全沒有匹配，選最接近的一個。
4. 以 JSON 陣列格式回覆，每個物件代表一題，其結構應為：
   {{"question_number": "題號", "key_points": "選出的 key-points", "micro_concepts": ["選出的微概念列表"]}}

待分類的題目列表：
{json.dumps(reclassify_questions, ensure_ascii=False, indent=2)}
"""
        attempt = 0
        while attempt < max_retries:
            try:
                gemini_model = genai.GenerativeModel(model_name=model_name)
                response = gemini_model.generate_content(
                    prompt_reclassify,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=4096  # 增加 token 限制以處理多個題目
                    )
                )
                if not response.text:
                    raise ValueError("API 回應為空")

                output_text = response.text
                json_match = re.search(r'\[\s*\{.*\}\s*\]', output_text, re.S)
                if json_match:
                    classified_results.extend(json.loads(json_match.group()))
                    break
                else:
                    raise ValueError("API 回應中找不到有效的 JSON 陣列")

            except Exception as e:
                attempt += 1
                wait_time = 2 ** attempt
                print(f"❌ Gemini 批量判斷 (基本計概) 失敗 (第 {attempt} 次): {e}, {wait_time}s 後重試...")
                time.sleep(wait_time)
        else:
            print("❌ Gemini 判斷重試失敗，跳過所有 '基本計概' 題目。")

    # --- 處理只需判斷 micro_concepts 的題目 ---
    if micro_only_questions:
        print(f"🔍 正在判斷 {len(micro_only_questions)} 題 '非基本計概' 類別的 micro_concepts...")
        prompt_micro_only = f"""
請協助判斷以下題目的 micro_concepts，並以 JSON 陣列格式回覆。
這些題目的 key-points 已確定，請忽略。

候選 micro_concepts: {micro_concepts}

要求：
1. 針對每個題目，從候選列表中選出題目中出現的或最相關的微概念。
2. micro_concepts 必須為字串陣列 (array of strings)，允許多個，若完全沒有匹配，選最接近的一個。
3. 以 JSON 陣列格式回覆，每個物件代表一題，其結構應為：
   {{"question_number": "題號", "micro_concepts": ["選出的微概念列表"]}}

待分類的題目列表：
{json.dumps(micro_only_questions, ensure_ascii=False, indent=2)}
"""
        attempt = 0
        while attempt < max_retries:
            try:
                gemini_model = genai.GenerativeModel(model_name=model_name)
                response = gemini_model.generate_content(
                    prompt_micro_only,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=4096
                    )
                )
                if not response.text:
                    raise ValueError("API 回應為空")

                output_text = response.text
                json_match = re.search(r'\[\s*\{.*\}\s*\]', output_text, re.S)
                if json_match:
                    classified_results.extend(json.loads(json_match.group()))
                    break
                else:
                    raise ValueError("API 回應中找不到有效的 JSON 陣列")
            except Exception as e:
                attempt += 1
                wait_time = 2 ** attempt
                print(f"❌ Gemini 批量判斷 (micro_concepts) 失敗 (第 {attempt} 次): {e}, {wait_time}s 後重試...")
                time.sleep(wait_time)
        else:
            print("❌ Gemini 判斷重試失敗，跳過所有 '非基本計概' 題目。")

    return classified_results

# ========== 儲存 JSON ==========
def save_to_json(data: Any, filename: str):
    """將資料儲存為 JSON 檔案。"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 已輸出到 {filename}")
    except Exception as e:
        print(f"❌ 儲存 JSON 錯誤: {e}")

# ========== 主程式 ==========
if __name__ == "__main__":
    # 這裡只需要設定模型名稱，不需要初始化完整的模型物件
    genai.configure(api_key="AIzaSyC8y6nInv339tG3j2jwFfd2W3lU1A6aoBg") # 請確保您已設定您的 API 金鑰
    model_name = 'gemini-1.5-flash'
    
    # 載入所有數據
    domains, micro_concepts = load_classification_data("domains_batch_20250903.json", "micro_concepts_batch_20250903.json")
    questions = load_questions("check_exam_output2.json")

    if questions and domains and micro_concepts:
        # 批量呼叫 Gemini API 進行分類
        classified_results = classify_with_gemini_batch(model_name, questions, domains, micro_concepts)

        # 將分類結果與原始題目數據合併
        final_questions = []
        result_map = {q.get('question_number'): q for q in classified_results}
        for q in questions:
            q_num = q.get('question_number')
            if q_num in result_map:
                classified_info = result_map[q_num]
                # 只更新有判斷結果的欄位
                q['key-points'] = classified_info.get('key_points', q.get('key-points'))
                q['micro_concepts'] = classified_info.get('micro_concepts', q.get('micro_concepts', []))
            final_questions.append(q)

        # 儲存最終結果
        save_to_json(final_questions, "classified_questions_batch.json")