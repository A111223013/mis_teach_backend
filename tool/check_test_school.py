#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
檢查和修復測試學校的題目
"""

import sys
import os
from pymongo import MongoClient

# 添加父目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入標準化函數
from tool.insert_test_school import normalize_answer_type, get_mongo_connection

def check_test_school_questions():
    """檢查測試學校的所有題目"""
    db = get_mongo_connection()
    if db is None:
        return
    
    print("=" * 60)
    print("檢查測試學校題目")
    print("=" * 60)
    
    # 查詢測試學校的所有題目（按照插入順序排序）
    questions = list(db.exam.find({
        'school': '測試學校(全題型)',
        'department': '資訊管理學系',
        'year': '114'
    }).sort('_id', 1))
    
    if not questions:
        print("沒有找到測試學校的題目")
        return
    
    print(f"\n找到 {len(questions)} 題\n")
    
    # 檢查每一題
    issues = []
    for i, question in enumerate(questions, 1):
        question_number = question.get('question_number', str(i))
        answer_type = question.get('answer_type', '')
        normalized_type = normalize_answer_type(answer_type)
        
        # 檢查問題
        problems = []
        question_text = question.get('question_text', '')
        options = question.get('options', [])
        
        # 檢查題目文字是否包含「題目檔」，如果是單選題應該改為簡答題
        if '題目檔' in question_text and normalized_type == 'single-choice':
            problems.append(f"題目包含「題目檔」但 answer_type 是 single-choice，應該改為 short-answer")
        
        # 檢查多選題是否有選項
        if normalized_type == 'multiple-choice':
            if not options or (isinstance(options, list) and len(options) == 0):
                problems.append(f"answer_type 是 multiple-choice 但沒有選項，應該改為 short-answer")
            elif isinstance(options, str) and not options.strip():
                problems.append(f"answer_type 是 multiple-choice 但選項為空字串，應該改為 short-answer")
        
        # 檢查 answer_type
        if answer_type != normalized_type:
            problems.append(f"answer_type 不標準: '{answer_type}' -> '{normalized_type}'")
        
        # 檢查 question_number
        if question_number != str(i):
            problems.append(f"question_number 不正確: '{question_number}' (應該是 '{i}')")
        
        # 檢查必要欄位
        if not question_text:
            problems.append("缺少 question_text")
        
        if not answer_type:
            problems.append("缺少 answer_type")
        
        # 檢查 answer_type 是否有效
        valid_types = {
            'single-choice', 'multiple-choice', 'fill-in-the-blank',
            'true-false', 'short-answer', 'long-answer',
            'choice-answer', 'draw-answer', 'coding-answer', 'group'
        }
        if normalized_type not in valid_types:
            problems.append(f"無效的 answer_type: '{normalized_type}'")
        
        if problems:
            issues.append({
                'number': i,
                'question_number': question_number,
                'answer_type': answer_type,
                'normalized_type': normalized_type,
                'problems': problems,
                'question_text': question_text
            })
            print(f"[!] 第 {i} 題 (question_number: {question_number}):")
            print(f"   answer_type: '{answer_type}' -> '{normalized_type}'")
            for problem in problems:
                print(f"   - {problem}")
            print()
        else:
            print(f"[OK] 第 {i} 題: {normalized_type}")
    
    if issues:
        print(f"\n發現 {len(issues)} 題有問題")
        return issues
    else:
        print("\n[OK] 所有題目都正常")
        return []

def fix_test_school_questions(dry_run=True, target_count=20):
    """修復測試學校的題目，只保留指定數量的題目"""
    db = get_mongo_connection()
    if db is None:
        return False
    
    # 先檢查現有題目（按照插入順序排序）
    all_questions = list(db.exam.find({
        'school': '測試學校(全題型)',
        'department': '資訊管理學系',
        'year': '114'
    }).sort('_id', 1))
    
    current_count = len(all_questions)
    
    if dry_run:
        print(f"\n[!] 預覽模式：")
        print(f"  目前有 {current_count} 題")
        print(f"  目標保留 {target_count} 題")
        if current_count > target_count:
            print(f"  將刪除 {current_count - target_count} 題")
        print("執行時請使用 --execute 參數")
        issues = check_test_school_questions()
        return False
    
    print("\n" + "=" * 60)
    print("開始修復")
    print("=" * 60)
    
    # 1. 刪除多餘的題目（保留前 target_count 題）
    if current_count > target_count:
        # 獲取要刪除的題目（從第 target_count + 1 題開始）
        questions_to_delete = all_questions[target_count:]
        delete_count = len(questions_to_delete)
        
        print(f"\n刪除多餘的 {delete_count} 題...")
        for q in questions_to_delete:
            result = db.exam.delete_one({'_id': q['_id']})
            if result.deleted_count > 0:
                print(f"  刪除題目 {q.get('question_number', '?')}")
    
    # 2. 重新獲取所有題目（刪除後）
    remaining_questions = list(db.exam.find({
        'school': '測試學校(全題型)',
        'department': '資訊管理學系',
        'year': '114'
    }).sort('_id', 1))  # 使用 _id 排序以保持插入順序
    
    # 3. 修復所有題目的 question_number 和 answer_type
    fixed_count = 0
    
    for i, question in enumerate(remaining_questions, 1):
        question_id = question['_id']
        old_question_number = question.get('question_number', '')
        old_answer_type = question.get('answer_type', '')
        question_text = question.get('question_text', '')
        options = question.get('options', [])
        normalized_type = normalize_answer_type(old_answer_type)
        
        update_data = {}
        
        # 修復 question_number
        new_question_number = str(i)
        if old_question_number != new_question_number:
            update_data['question_number'] = new_question_number
        
        # 檢查題目文字是否包含「題目檔」，如果是單選題應該改為簡答題
        if '題目檔' in question_text and normalized_type == 'single-choice':
            normalized_type = 'short-answer'
        
        # 檢查多選題是否有選項，如果沒有選項應該改為簡答題
        if normalized_type == 'multiple-choice':
            has_options = False
            if isinstance(options, list) and len(options) > 0:
                has_options = True
            elif isinstance(options, str) and options.strip():
                has_options = True
            
            if not has_options:
                normalized_type = 'short-answer'
        
        # 修復 answer_type
        if old_answer_type != normalized_type:
            update_data['answer_type'] = normalized_type
        
        if update_data:
            result = db.exam.update_one(
                {'_id': question_id},
                {'$set': update_data}
            )
            if result.modified_count > 0:
                changes = []
                if 'question_number' in update_data:
                    changes.append(f"question_number: '{old_question_number}' -> '{new_question_number}'")
                if 'answer_type' in update_data:
                    changes.append(f"answer_type: '{old_answer_type}' -> '{normalized_type}'")
                print(f"[OK] 修復第 {i} 題: {', '.join(changes)}")
                fixed_count += 1
    
    print(f"\n[OK] 修復完成！")
    print(f"  保留 {len(remaining_questions)} 題")
    print(f"  修復 {fixed_count} 個問題")
    return True

def find_question_by_text(search_text):
    """搜尋包含特定文字的題目"""
    db = get_mongo_connection()
    if db is None:
        return []
    
    print("=" * 60)
    print(f"搜尋包含 '{search_text}' 的題目")
    print("=" * 60)
    
    questions = list(db.exam.find({
        'school': '測試學校(全題型)',
        'department': '資訊管理學系',
        'year': '114',
        'question_text': {'$regex': search_text, '$options': 'i'}
    }).sort('_id', 1))
    
    if not questions:
        print(f"沒有找到包含 '{search_text}' 的題目")
        return []
    
    print(f"\n找到 {len(questions)} 題\n")
    
    for i, question in enumerate(questions, 1):
        question_number = question.get('question_number', '?')
        answer_type = question.get('answer_type', '?')
        question_text = question.get('question_text', '')
        
        print(f"第 {question_number} 題:")
        print(f"  answer_type: {answer_type}")
        print(f"  question_text: {question_text[:200]}...")
        print()
    
    return questions

def show_question_detail(question_number: int):
    """顯示特定題目的詳細資訊"""
    db = get_mongo_connection()
    if db is None:
        return
    
    question = db.exam.find_one({
        'school': '測試學校(全題型)',
        'department': '資訊管理學系',
        'year': '114',
        'question_number': str(question_number)
    })
    
    if not question:
        print(f"找不到第 {question_number} 題")
        return
    
    print("=" * 60)
    print(f"第 {question_number} 題詳細資訊")
    print("=" * 60)
    print(f"question_number: {question.get('question_number')}")
    print(f"answer_type: {question.get('answer_type')}")
    print(f"normalized_type: {normalize_answer_type(question.get('answer_type', ''))}")
    print(f"type: {question.get('type')}")
    print(f"question_text: {question.get('question_text', '')[:100]}...")
    print(f"options: {question.get('options', [])}")
    print(f"answer: {question.get('answer', '')}")
    print("=" * 60)

def fix_question_type(question_number, new_answer_type):
    """修復題目的 answer_type"""
    db = get_mongo_connection()
    if db is None:
        return False
    
    result = db.exam.update_one(
        {
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114',
            'question_number': str(question_number)
        },
        {'$set': {'answer_type': new_answer_type}}
    )
    
    if result.modified_count > 0:
        print(f"[OK] 修復第 {question_number} 題: answer_type -> '{new_answer_type}'")
        return True
    else:
        print(f"[!] 找不到第 {question_number} 題或無需修復")
        return False

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='檢查和修復測試學校的題目')
    parser.add_argument('--execute', action='store_true', help='實際執行修復（預設為預覽模式）')
    parser.add_argument('--question', type=int, help='顯示特定題目的詳細資訊')
    parser.add_argument('--count', type=int, default=20, help='目標題目數量（預設20題）')
    parser.add_argument('--search', type=str, help='搜尋包含特定文字的題目')
    parser.add_argument('--fix-type', type=int, help='修復指定題號的 answer_type')
    parser.add_argument('--new-type', type=str, help='新的 answer_type（與 --fix-type 一起使用）')
    args = parser.parse_args()
    
    if args.search:
        find_question_by_text(args.search)
    elif args.fix_type:
        if not args.new_type:
            print("請使用 --new-type 指定新的 answer_type")
            return
        fix_question_type(args.fix_type, args.new_type)
    elif args.question:
        show_question_detail(args.question)
    else:
        dry_run = not args.execute
        fix_test_school_questions(dry_run=dry_run, target_count=args.count)
        
        if not dry_run:
            print("\n重新檢查修復後的題目...")
            check_test_school_questions()

if __name__ == "__main__":
    main()

