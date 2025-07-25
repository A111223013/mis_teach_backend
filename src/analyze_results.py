#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析 results.json 中有錯誤訊息的題目資料
"""

import json
import os
from typing import List, Dict, Any

def load_results_json(file_path: str = "data/results.json") -> List[Dict[str, Any]]:
    """載入 results.json 檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 成功載入 {file_path}")
        print(f"📊 總題目數: {len(data)}")
        return data
    except FileNotFoundError:
        print(f"❌ 找不到檔案: {file_path}")
        # 嘗試其他可能的路徑
        alternative_paths = [
            "backend/data/results.json",
            "../data/results.json",
            "results.json"
        ]
        for alt_path in alternative_paths:
            try:
                with open(alt_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ 成功載入 {alt_path}")
                print(f"📊 總題目數: {len(data)}")
                return data
            except FileNotFoundError:
                continue
        print("❌ 嘗試了所有可能的路徑都找不到檔案")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析錯誤: {e}")
        return []

def find_questions_with_errors(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """找出有錯誤訊息的題目"""
    error_questions = []
    
    for question in questions:
        # 檢查是否有 error reason 欄位且不為空
        error_reason = question.get("error reason", "")
        if error_reason and error_reason.strip():
            error_questions.append(question)
    
    return error_questions

def analyze_error_types(error_questions: List[Dict[str, Any]]) -> Dict[str, int]:
    """分析錯誤類型統計"""
    error_types = {}
    
    for question in error_questions:
        error_reason = question.get("error reason", "")
        error_types[error_reason] = error_types.get(error_reason, 0) + 1
    
    return error_types

def save_error_questions_to_json(error_questions: List[Dict[str, Any]], output_file: str = "error_questions.json"):
    """將有錯誤的題目儲存為 JSON 檔案"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(error_questions, f, ensure_ascii=False, indent=2)
        print(f"✅ 成功儲存 {len(error_questions)} 道錯誤題目到 {output_file}")
    except Exception as e:
        print(f"❌ 儲存檔案時發生錯誤: {e}")

def print_error_questions(error_questions: List[Dict[str, Any]], max_display: int = 10):
    """輸出有錯誤的題目詳細資料（限制顯示數量）"""
    print(f"\n🔍 找到 {len(error_questions)} 道有錯誤訊息的題目:")
    print("=" * 80)
    
    # 只顯示前 max_display 個題目
    display_count = min(len(error_questions), max_display)
    
    for i, question in enumerate(error_questions[:display_count], 1):
        print(f"\n📝 題目 {i}:")
        print(f"   題目編號: {question.get('question_number', 'N/A')}")
        print(f"   題目類型: {question.get('type', 'N/A')}")
        print(f"   學校: {question.get('school', 'N/A')}")
        print(f"   科系: {question.get('department', 'N/A')}")
        print(f"   年度: {question.get('year', 'N/A')}")
        print(f"   題目內容: {question.get('question_text', 'N/A')[:100]}...")
        print(f"   答案: {question.get('answer', 'N/A')}")
        print(f"   詳細解答: {question.get('detail-answer', 'N/A')[:100]}...")
        print(f"   知識點: {question.get('key-points', 'N/A')}")
        print(f"   難度等級: {question.get('difficulty level', 'N/A')}")
        print(f"   ❌ 錯誤原因: {question.get('error reason', 'N/A')}")
        print("-" * 60)
    
    if len(error_questions) > max_display:
        print(f"\n... 還有 {len(error_questions) - max_display} 道題目未顯示")
        print(f"完整資料已儲存到 error_questions.json")

def main():
    """主函數"""
    print("🚀 開始分析 results.json 中的錯誤題目...")
    
    # 載入資料
    questions = load_results_json()
    if not questions:
        return
    
    # 找出有錯誤的題目
    error_questions = find_questions_with_errors(questions)
    
    if not error_questions:
        print("✅ 沒有發現有錯誤訊息的題目")
        return
    
    # 分析錯誤類型
    error_types = analyze_error_types(error_questions)
    
    print(f"\n📈 錯誤類型統計:")
    for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {error_type}: {count} 題")
    
    # 儲存到 JSON 檔案
    save_error_questions_to_json(error_questions)
    
    # 輸出詳細資料（限制顯示數量）
    print_error_questions(error_questions, max_display=10)
    
    # 統計資訊
    print(f"\n📊 統計摘要:")
    print(f"   總題目數: {len(questions)}")
    print(f"   有錯誤題目數: {len(error_questions)}")
    print(f"   錯誤率: {len(error_questions)/len(questions)*100:.2f}%")
    print(f"   錯誤類型數: {len(error_types)}")

if __name__ == "__main__":
    main() 