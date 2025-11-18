#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜尋測試學校中包含特定文字的題目
"""

import sys
import os
from pymongo import MongoClient

# 添加父目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool.insert_test_school import get_mongo_connection

def find_question_by_text(search_text):
    """搜尋包含特定文字的題目"""
    db = get_mongo_connection()
    if db is None:
        return
    
    print("=" * 60)
    print(f"搜尋包含 '{search_text}' 的題目")
    print("=" * 60)
    
    # 查詢測試學校的所有題目
    questions = list(db.exam.find({
        'school': '測試學校(全題型)',
        'department': '資訊管理學系',
        'year': '114',
        'question_text': {'$regex': search_text, '$options': 'i'}
    }).sort('_id', 1))
    
    if not questions:
        print(f"沒有找到包含 '{search_text}' 的題目")
        return
    
    print(f"\n找到 {len(questions)} 題\n")
    
    for i, question in enumerate(questions, 1):
        question_number = question.get('question_number', '?')
        answer_type = question.get('answer_type', '?')
        question_text = question.get('question_text', '')
        
        print(f"第 {question_number} 題:")
        print(f"  answer_type: {answer_type}")
        print(f"  question_text: {question_text[:200]}...")
        print()

def list_all_questions():
    """列出所有測試學校的題目"""
    db = get_mongo_connection()
    if db is None:
        return
    
    print("=" * 60)
    print("所有測試學校題目")
    print("=" * 60)
    
    questions = list(db.exam.find({
        'school': '測試學校(全題型)',
        'department': '資訊管理學系',
        'year': '114'
    }).sort('_id', 1))
    
    for i, question in enumerate(questions, 1):
        question_number = question.get('question_number', '?')
        answer_type = question.get('answer_type', '?')
        question_text = question.get('question_text', '')
        
        print(f"\n第 {question_number} 題 ({answer_type}):")
        print(f"  {question_text[:150]}...")

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
    
    parser = argparse.ArgumentParser(description='搜尋和修復測試學校的題目')
    parser.add_argument('--search', type=str, help='搜尋包含特定文字的題目')
    parser.add_argument('--list', action='store_true', help='列出所有題目')
    parser.add_argument('--fix', type=int, help='修復指定題號的 answer_type')
    parser.add_argument('--type', type=str, help='新的 answer_type（與 --fix 一起使用）')
    args = parser.parse_args()
    
    if args.search:
        find_question_by_text(args.search)
    elif args.list:
        list_all_questions()
    elif args.fix:
        if not args.type:
            print("請使用 --type 指定新的 answer_type")
            return
        fix_question_type(args.fix, args.type)
    else:
        # 預設搜尋「題目檔」
        find_question_by_text('題目檔')

if __name__ == "__main__":
    main()

