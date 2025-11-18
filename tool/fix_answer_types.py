#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修復資料庫中現有題目的 answer_type
將非標準格式的 answer_type 標準化為系統定義的格式
"""

import sys
import os
from pymongo import MongoClient
from pymongo.collection import Collection

# 添加父目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 定義有效的 answer_type 值
VALID_ANSWER_TYPES = {
    'single-choice',
    'multiple-choice',
    'fill-in-the-blank',
    'true-false',
    'short-answer',
    'long-answer',
    'choice-answer',
    'draw-answer',
    'coding-answer',
    'group'
}

def normalize_answer_type(answer_type: str, question_data: dict = None) -> str:
    """
    標準化 answer_type，確保符合系統定義的格式
    
    Args:
        answer_type: 原始 answer_type 值
        question_data: 可選的題目資料，用於檢查選項等
        
    Returns:
        標準化的 answer_type 值
    """
    if not answer_type:
        return 'single-choice'  # 預設值
    
    # 移除前後空格
    answer_type = answer_type.strip()
    
    # 保存原始值用於比較
    original = answer_type
    
    # 轉換為小寫
    answer_type = answer_type.lower()
    
    # 處理常見的變體
    type_mapping = {
        'single': 'single-choice',
        'single-choice': 'single-choice',
        'multiple': 'multiple-choice',
        'multiple-choice': 'multiple-choice',
        'fill': 'fill-in-the-blank',
        'fill_in_the_blank': 'fill-in-the-blank',
        'fill-in-blank': 'fill-in-the-blank',
        'fill-in-the-blank': 'fill-in-the-blank',
        'truefalse': 'true-false',
        'true_false': 'true-false',
        'true-false': 'true-false',
        'short': 'short-answer',
        'short-answer': 'short-answer',
        'long': 'long-answer',
        'long-answer': 'long-answer',
        'choice': 'choice-answer',
        'choice-answer': 'choice-answer',
        'draw': 'draw-answer',
        'drawing': 'draw-answer',
        'draw-answer': 'draw-answer',
        'code': 'coding-answer',
        'coding': 'coding-answer',
        'coding-answer': 'coding-answer',
        'programming': 'coding-answer',
        'group': 'group',
    }
    
    # 先檢查映射表
    if answer_type in type_mapping:
        answer_type = type_mapping[answer_type]
    
    # 驗證是否為有效的 answer_type
    if answer_type not in VALID_ANSWER_TYPES:
        print(f"⚠️ 警告：無效的 answer_type '{original}'，將使用預設值 'single-choice'")
        return 'single-choice'
    
    # 如果有提供題目資料，進行額外檢查
    if question_data:
        question_text = question_data.get('question_text', '')
        options = question_data.get('options', [])
        
        # 檢查題目文字是否包含「題目檔」，如果是單選題應該改為簡答題
        if '題目檔' in question_text and answer_type == 'single-choice':
            return 'short-answer'
        
        # 檢查多選題是否有選項，如果沒有選項應該改為簡答題
        if answer_type == 'multiple-choice':
            has_options = False
            if isinstance(options, list) and len(options) > 0:
                has_options = True
            elif isinstance(options, str) and options.strip():
                has_options = True
            
            if not has_options:
                return 'short-answer'
    
    return answer_type

def get_mongo_connection():
    """使用 config.py 獲取 MongoDB 連接"""
    try:
        from config import DevelopmentConfig
        
        config = DevelopmentConfig()
        mongo_uri = config.MONGO_URI
        db_name = config.MONGO_DB_NAME
        
        print(f"連接 MongoDB: {mongo_uri}")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # 測試連接
        client.admin.command('ping')
        print("MongoDB 連接成功")
        
        return db
        
    except Exception as e:
        print(f"MongoDB 連接失敗: {str(e)}")
        return None

def analyze_answer_types(db: Collection):
    """分析資料庫中所有的 answer_type"""
    print("\n" + "=" * 60)
    print("分析資料庫中的 answer_type")
    print("=" * 60)
    
    # 獲取所有不同的 answer_type
    answer_types = db.exam.distinct('answer_type')
    
    # 統計每個 answer_type 的數量
    type_stats = {}
    for at in answer_types:
        if at:
            count = db.exam.count_documents({'answer_type': at})
            normalized = normalize_answer_type(at)
            type_stats[at] = {
                'count': count,
                'normalized': normalized,
                'needs_fix': at != normalized
            }
    
    print(f"\n找到 {len(type_stats)} 種不同的 answer_type：\n")
    
    needs_fix_count = 0
    for original, stats in sorted(type_stats.items()):
        status = "✅" if not stats['needs_fix'] else "⚠️ 需要修復"
        print(f"{status} {original:30s} -> {stats['normalized']:20s} ({stats['count']:5d} 題)")
        if stats['needs_fix']:
            needs_fix_count += stats['count']
    
    print(f"\n總共需要修復 {needs_fix_count} 題")
    print("=" * 60 + "\n")
    
    return type_stats, needs_fix_count

def fix_answer_types(db: Collection, dry_run: bool = True):
    """修復資料庫中的 answer_type"""
    print("\n" + "=" * 60)
    print("開始修復 answer_type" + (" (預覽模式)" if dry_run else ""))
    print("=" * 60)
    
    # 分析現有資料
    type_stats, needs_fix_count = analyze_answer_types(db)
    
    if needs_fix_count == 0:
        print("✅ 所有 answer_type 都已經是標準格式，無需修復")
        return True
    
    if dry_run:
        print(f"\n⚠️ 預覽模式：將修復 {needs_fix_count} 題")
        print("執行時請使用 --execute 參數")
        return False
    
    # 實際修復（需要逐題檢查，因為可能需要根據選項等條件修改）
    fixed_count = 0
    error_count = 0
    
    # 獲取所有需要檢查的題目（包括可能需要根據選項修改的）
    print(f"\n開始逐題檢查和修復...")
    all_questions = list(db.exam.find({}))
    total = len(all_questions)
    
    for idx, question in enumerate(all_questions, 1):
        try:
            old_answer_type = question.get('answer_type', '')
            if not old_answer_type:
                continue
            
            normalized_type = normalize_answer_type(old_answer_type, question)
            
            if old_answer_type != normalized_type:
                result = db.exam.update_one(
                    {'_id': question['_id']},
                    {'$set': {'answer_type': normalized_type}}
                )
                if result.modified_count > 0:
                    fixed_count += 1
                    if fixed_count <= 20 or fixed_count % 100 == 0:
                        reason = []
                        if '題目檔' in question.get('question_text', '') and old_answer_type == 'single-choice':
                            reason.append("包含「題目檔」")
                        if old_answer_type == 'multiple-choice' and not (isinstance(question.get('options', []), list) and len(question.get('options', [])) > 0 or (isinstance(question.get('options', ''), str) and question.get('options', '').strip())):
                            reason.append("多選題沒有選項")
                        reason_str = f" ({', '.join(reason)})" if reason else ""
                        print(f"  [OK] 修復: '{old_answer_type}' -> '{normalized_type}'{reason_str}")
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # 只顯示前10個錯誤
                print(f"  [!] 修復失敗: {str(e)}")
        
        if idx % 1000 == 0:
            print(f"  已處理 {idx}/{total} 題，修復 {fixed_count} 題...")
    
    print("\n" + "=" * 60)
    print(f"修復完成！")
    print(f"  ✅ 成功修復: {fixed_count} 題")
    if error_count > 0:
        print(f"  ❌ 修復失敗: {error_count} 種類型")
    print("=" * 60 + "\n")
    
    return True

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='修復資料庫中現有題目的 answer_type')
    parser.add_argument('--execute', action='store_true', help='實際執行修復（預設為預覽模式）')
    args = parser.parse_args()
    
    print("=" * 60)
    print("answer_type 修復工具")
    print("=" * 60)
    
    # 獲取資料庫連接
    db = get_mongo_connection()
    if db is None:
        print("無法連接資料庫，程式結束")
        return
    
    # 執行修復
    dry_run = not args.execute
    success = fix_answer_types(db, dry_run=dry_run)
    
    if not success and dry_run:
        print("\n提示：使用 --execute 參數來實際執行修復")
    elif success:
        print("\n✅ 修復完成！")

if __name__ == "__main__":
    main()

