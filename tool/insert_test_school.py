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

def get_mongo_connection():
    """使用 config.py 獲取 MongoDB 連接"""
    try:
        from config import DevelopmentConfig
        
        config = DevelopmentConfig()
        mongo_uri = config.MONGO_URI
        db_name = config.MONGO_DB_NAME
        
        print(f"🔗 連接 MongoDB: {mongo_uri}")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # 測試連接
        client.admin.command('ping')
        print("✅ MongoDB 連接成功")
        
        return db
        
    except Exception as e:
        print(f"❌ MongoDB 連接失敗: {str(e)}")
        return None

def insert_test_school_data(auto_mode=False):
    """從資料庫選擇各題型題目插入測試學校"""
    try:
        # 獲取資料庫連接
        db = get_mongo_connection()
        if db is None:
            return False
        
        if auto_mode:
            print("🚀 自動模式：從資料庫選擇題目插入測試學校...")
        else:
            print("🚀 開始從資料庫選擇題目插入測試學校...")
        
        # 檢查是否已存在測試學校資料
        existing_count = db.exam.count_documents({
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114'
        })
        
        if existing_count > 0:
            if auto_mode:
                print(f"✅ 測試學校資料已存在 ({existing_count} 題)，跳過插入")
                return True
            else:
                print(f"⚠️  已存在 {existing_count} 筆測試學校資料")
                choice = input("是否要重新插入？(y/N): ").strip().lower()
                if choice != 'y':
                    print("取消插入操作")
                    return True
        
        # 獲取所有不同的 answer_type
        answer_types = db.exam.distinct('answer_type')
        print(f"🔍 找到的 answer_type: {answer_types}")
        
        # 為每個 answer_type 從資料庫選擇 2 題
        selected_questions = []
        for answer_type in answer_types:
            if answer_type:  # 確保 answer_type 不為空
                # 從該 answer_type 中隨機選擇 2 題
                questions = list(db.exam.find({'answer_type': answer_type}).limit(20))
                if len(questions) >= 2:
                    selected = random.sample(questions, 2)
                elif len(questions) == 1:
                    selected = questions
                else:
                    continue  # 如果沒有題目，跳過這個 answer_type
                
                print(f"✅ {answer_type}: 選擇了 {len(selected)} 題")
                selected_questions.extend(selected)
        
        if not selected_questions:
            print("❌ 沒有找到任何題目")
            return False
        
        print(f"📊 總共選擇了 {len(selected_questions)} 題")
        
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
                print(f"✅ 插入題目 {question['question_number']}: {question['question_text'][:30]}...")
                inserted_count += 1
            except Exception as e:
                print(f"❌ 插入題目 {question['question_number']} 失敗: {str(e)}")
        
        print(f"\n🎉 成功插入 {inserted_count} 筆測試學校資料！")
        print("📊 包含的題型: single-choice, multiple-choice, short-answer, true-false, fill-in-the-blank")
        
        return True
        
    except Exception as e:
        print(f"❌ 插入資料失敗: {str(e)}")
        return False

def show_database_stats():
    """顯示資料庫統計資訊"""
    try:
        db = get_mongo_connection()
        if db is None:
            return
        
        print("\n📊 資料庫統計資訊:")
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
        print(f"❌ 獲取統計資訊失敗: {str(e)}")

def check_and_insert_test_school():
    """自動檢查並插入測試學校資料（用於 app.py 啟動時調用）"""
    try:
        # 獲取資料庫連接
        db = get_mongo_connection()
        if db is None:
            print("❌ MongoDB 連接失敗，跳過測試學校資料檢查")
            return False
        
        # 檢查是否已存在測試學校資料
        existing_count = db.exam.count_documents({
            'school': '測試學校(全題型)',
            'department': '資訊管理學系',
            'year': '114'
        })
        
        if existing_count > 0:
            print(f"✅ 測試學校資料已存在 ({existing_count} 題)，跳過插入")
            return True
        
        print("🔍 測試學校資料不存在，開始自動插入...")
        
        # 自動插入測試學校資料
        success = insert_test_school_data(auto_mode=True)
        
        if success:
            print("✅ 測試學校資料自動插入完成！")
        else:
            print("❌ 測試學校資料自動插入失敗！")
        
        return success
        
    except Exception as e:
        print(f"❌ 檢查測試學校資料時發生錯誤: {str(e)}")
        return False

def main():
    """主函數"""
    print("=" * 60)
    print("🎯 測試學校資料插入工具")
    print("=" * 60)
    
    # 顯示資料庫統計
    show_database_stats()
    
    # 插入測試學校資料
    success = insert_test_school_data()
    
    if success:
        print("\n✅ 測試學校資料插入完成！")
        print("現在可以在測驗中心選擇「測試學校(全題型)」進行全題型測驗測試")
        print("後端會自動從真實資料庫中選擇各題型的題目")
    else:
        print("\n❌ 測試學校資料插入失敗！")

if __name__ == "__main__":
    main()
