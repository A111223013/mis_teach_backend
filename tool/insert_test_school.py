#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入測試學校資料到 MongoDB
用於測試全題型測驗功能
"""

import sys
import os
import random
from datetime import datetime
from pymongo import MongoClient

# 添加父目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 定義要使用的題型對應關係
TARGET_ANSWER_TYPES = {
    'Long-answer': 'short-answer',
    'Coding': 'coding-answer',
    'Diagram Drawing': 'draw-answer',
    'Multiple-select': 'true-false',
    'Fill-in-the-Blank': ' single-choice',
    'Math': 'choice-answer',
    'Multiple-choice': 'multiple-choice'
}

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

def insert_test_school_data(auto_mode=False):
    """從資料庫選擇各題型題目插入測試學校"""
    try:
        # 獲取資料庫連接
        db = get_mongo_connection()
        if db is None:
            return False
        
        if auto_mode:
            print("自動模式：從資料庫選擇題目插入測試學校...")
        else:
            print("開始從資料庫選擇題目插入測試學校...")
        
        # 檢查是否已存在測試學校資料
        existing_count = db.exam.count_documents({
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114'
        })
        
        if existing_count > 0:
            if auto_mode:
                print(f"測試學校資料已存在 ({existing_count} 題)，跳過插入")
                return True
            else:
                print(f"已存在 {existing_count} 筆測試學校資料")
                choice = input("是否要重新插入？(y/N): ").strip().lower()
                if choice != 'y':
                    print("取消插入操作")
                    return True
        
        # 只使用指定的題型
        target_types = list(TARGET_ANSWER_TYPES.values())
        print(f"目標題型: {list(TARGET_ANSWER_TYPES.keys())}")
        print(f"對應的 answer_type: {target_types}\n")
        
        # 檢查哪些題型在資料庫中存在
        available_types = []
        for display_name, answer_type in TARGET_ANSWER_TYPES.items():
            count = db.exam.count_documents({
                'answer_type': answer_type,
                'school': {'$ne': '測試學校(全題型)'}
            })
            if count > 0:
                available_types.append(answer_type)
                print(f"  {display_name} ({answer_type}): {count} 題可用")
            else:
                print(f"  {display_name} ({answer_type}): 0 題可用（跳過）")
        
        if not available_types:
            print("沒有找到任何可用的題型")
            return False
        
        print(f"\n將使用 {len(available_types)} 種題型\n")
        
        selected_questions = []
        used_answer_types = set()  # 記錄已使用的題型
        
        # 第一階段：前7題，選擇7種不同題型各1題
        print("第一階段：選擇前7種不同題型各1題")
        print("-" * 60)
        first_seven_types = available_types[:7]  # 取前7種題型
        
        for answer_type in first_seven_types:
            # 從該 answer_type 中隨機選擇 1 題（排除測試學校）
            questions = list(db.exam.find({
                'answer_type': answer_type,
                'school': {'$ne': '測試學校(全題型)'}
            }).limit(50))
            
            if questions:
                selected = random.choice(questions)
                selected_questions.append(selected)
                used_answer_types.add(answer_type)
                print(f"題目 {len(selected_questions)}: {answer_type}")
        
        # 第二階段：第8題之後，從指定題型中隨機選擇
        print(f"\n第二階段：第8題之後，從指定題型中隨機選擇")
        print("-" * 60)
        remaining_questions = []
        for answer_type in available_types:
            questions = list(db.exam.find({
                'answer_type': answer_type,
                'school': {'$ne': '測試學校(全題型)'}
            }).limit(100))
            remaining_questions.extend(questions)
        
        # 隨機選擇題目（第8題之後），只從指定題型中選擇
        # 目標總數約15題，所以再選8題
        target_count = 15
        remaining_count = target_count - len(selected_questions)
        
        if remaining_count > 0 and len(remaining_questions) >= remaining_count:
            random_selected = random.sample(remaining_questions, remaining_count)
        elif remaining_count > 0:
            random_selected = remaining_questions
        else:
            random_selected = []
        
        for question in random_selected:
            if len(selected_questions) >= target_count:
                break
            # 確保只選擇指定題型
            q_type = question.get('answer_type', '')
            if q_type in available_types:
                selected_questions.append(question)
                used_answer_types.add(q_type)
                print(f"題目 {len(selected_questions)}: {q_type}")
        
        if not selected_questions:
            print("沒有找到任何題目")
            return False
        
        print(f"\n總共選擇了 {len(selected_questions)} 題")
        print(f"涵蓋了 {len(used_answer_types)} 種不同題型: {sorted(used_answer_types)}")
        
        # 轉換為測試學校格式
        test_questions = []
        for i, question in enumerate(selected_questions):
            # 創建測試學校格式的題目
            test_question = {
                'type': question.get('type', 'single'),
                'school': '測試學校(全題型)',
                'department': '資訊管理學系',
                'year': '114',
                'question_number': str(i + 1),
                'question_text': question.get('question_text', ''),
                'options': question.get('options', []),
                'answer': question.get('answer', ''),
                'answer_type': question.get('answer_type', ''),
                'image_file': question.get('image_file', ''),
                'detail-answer': question.get('detail-answer', ''),
                'key-points': question.get('key-points', ''),
                'difficulty level': question.get('difficulty level', 'medium'),
                'created_at': datetime.now()
            }
            test_questions.append(test_question)
        
        # 所有測試資料都從資料庫選擇，不包含硬編碼資料
        
        # 插入資料
        inserted_count = 0
        for question in test_questions:
            try:
                result = db.exam.insert_one(question)
                print(f"插入題目 {question['question_number']}: {question['question_text'][:30]}...")
                inserted_count += 1
            except Exception as e:
                print(f"插入題目 {question['question_number']} 失敗: {str(e)}")
        
        print(f"\n成功插入 {inserted_count} 筆測試學校資料！")
        print(f"涵蓋了 {len(used_answer_types)} 種不同題型")
        
        return True
        
    except Exception as e:
        print(f"插入資料失敗: {str(e)}")
        return False

def list_all_answer_types():
    """列出所有 answer_type 及其數量"""
    try:
        db = get_mongo_connection()
        if db is None:
            return None
        
        # 獲取所有不同的 answer_type
        answer_types = db.exam.distinct('answer_type')
        
        # 過濾掉 None 和空字串
        answer_types = [at for at in answer_types if at]
        
        print("\n" + "=" * 60)
        print("資料庫中所有的 answer_type:")
        print("=" * 60)
        
        if not answer_types:
            print("沒有找到任何 answer_type")
            return None
        
        # 列出每個 answer_type 及其數量
        for i, answer_type in enumerate(answer_types, 1):
            count = db.exam.count_documents({'answer_type': answer_type})
            print(f"{i:2d}. {answer_type:30s} - {count:4d} 題")
        
        print("=" * 60)
        print(f"總共找到 {len(answer_types)} 種不同的題型")
        print("=" * 60 + "\n")
        
        return answer_types
        
    except Exception as e:
        print(f"查詢失敗: {str(e)}")
        return None

def show_database_stats():
    """顯示資料庫統計資訊"""
    try:
        db = get_mongo_connection()
        if db is None:
            return
        
        print("\n資料庫統計資訊:")
        print("=" * 50)
        
        # 總題目數
        total_count = db.exam.count_documents({})
        print(f"總題目數: {total_count}")
        
        # 測試學校題目數
        test_count = db.exam.count_documents({
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114'
        })
        print(f"測試學校題目數: {test_count}")
        
        # 各 answer_type 題目數
        answer_types = db.exam.distinct('answer_type')
        print(f"\n各題型題目數:")
        for answer_type in answer_types:
            count = db.exam.count_documents({'answer_type': answer_type})
            print(f"  {answer_type}: {count} 題")
        
    except Exception as e:
        print(f"獲取統計資訊失敗: {str(e)}")

def delete_test_school_data(auto_confirm=False):
    """刪除測試學校資料"""
    try:
        db = get_mongo_connection()
        if db is None:
            return False
        
        # 檢查是否已存在測試學校資料
        existing_count = db.exam.count_documents({
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114'
        })
        
        if existing_count == 0:
            print("沒有找到測試學校資料，無需刪除")
            return True
        
        print(f"找到 {existing_count} 筆測試學校資料")
        
        if not auto_confirm:
            choice = input("確定要刪除嗎？(y/N): ").strip().lower()
            if choice != 'y':
                print("取消刪除操作")
                return False
        else:
            print("自動確認刪除...")
        
        # 刪除測試學校資料
        result = db.exam.delete_many({
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114'
        })
        
        print(f"成功刪除 {result.deleted_count} 筆測試學校資料！")
        return True
        
    except Exception as e:
        print(f"刪除資料失敗: {str(e)}")
        return False

def check_and_insert_test_school():
    """自動檢查並插入測試學校資料（用於 app.py 啟動時調用）"""
    try:
        # 獲取資料庫連接
        db = get_mongo_connection()
        if db is None:
            print("MongoDB 連接失敗，跳過測試學校資料檢查")
            return False
        
        # 檢查是否已存在測試學校資料
        existing_count = db.exam.count_documents({
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114'
        })
        
        if existing_count > 0:
            print(f"測試學校資料已存在 ({existing_count} 題)，跳過插入")
            return True
        
        print("測試學校資料不存在，開始自動插入...")
        
        # 自動插入測試學校資料
        success = insert_test_school_data(auto_mode=True)
        
        if success:
            print("測試學校資料自動插入完成！")
        else:
            print("測試學校資料自動插入失敗！")
        
        return success
        
    except Exception as e:
        print(f"檢查測試學校資料時發生錯誤: {str(e)}")
        return False

def main():
    """主函數"""
    print("=" * 60)
    print("測試學校資料插入工具")
    print("=" * 60)
    
    # 顯示選單
    print("\n請選擇操作：")
    print("1. 列出所有題型")
    print("2. 插入測試學校資料（使用指定7種題型）")
    print("3. 刪除測試學校資料")
    print("4. 顯示資料庫統計")
    print("0. 退出")
    
    choice = input("\n請輸入選項 (0-4): ").strip()
    
    if choice == '1':
        list_all_answer_types()
    elif choice == '2':
        # 先列出所有題型
        answer_types = list_all_answer_types()
        if answer_types is None:
            print("無法獲取題型列表，程式結束")
            return
        
        # 插入測試學校資料
        success = insert_test_school_data()
        
        if success:
            print("\n測試學校資料插入完成！")
            print("現在可以在測驗中心選擇「測試學校(全題型)」進行全題型測驗測試")
            print("使用的題型: " + ", ".join(TARGET_ANSWER_TYPES.keys()))
        else:
            print("\n測試學校資料插入失敗！")
    elif choice == '3':
        delete_test_school_data()
    elif choice == '4':
        show_database_stats()
    elif choice == '0':
        print("退出程式")
    else:
        print("無效的選項")

if __name__ == "__main__":
    main()
