#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from sqlalchemy import create_engine, text
from pymongo import MongoClient
import json

# 添加 src 目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

try:
    from accessories import sqldb, mongo
    print("✅ 成功導入資料庫模組")
except ImportError as e:
    print(f"❌ 導入資料庫模組失敗: {e}")
    print(f"當前目錄: {current_dir}")
    print(f"Python 路徑: {sys.path}")
    sys.exit(1)

def test_database():
    """測試資料庫連接和資料"""
    print("🔍 開始檢查資料庫...")
    
    try:
        # 檢查 SQL 資料庫
        print("\n📊 檢查 SQL 資料庫...")
        with sqldb.engine.connect() as conn:
            # 檢查 quiz_templates 表
            print("\n1. 檢查 quiz_templates 表:")
            templates = conn.execute(text("SELECT * FROM quiz_templates")).fetchall()
            print(f"   - 總共 {len(templates)} 個模板")
            
            for i, template in enumerate(templates):
                print(f"   - 模板 {i+1}:")
                print(f"     ID: {template[0]}")
                print(f"     用戶: {template[1]}")
                print(f"     類型: {template[2]}")
                print(f"     question_ids: {template[3]}")
                print(f"     question_ids 類型: {type(template[3])}")
                if template[3]:
                    try:
                        parsed = json.loads(template[3])
                        print(f"     解析後: {parsed}")
                        print(f"     長度: {len(parsed) if isinstance(parsed, list) else 'N/A'}")
                    except:
                        print(f"     JSON 解析失敗")
                print(f"     學校: {template[4]}")
                print(f"     系所: {template[5]}")
                print(f"     年份: {template[6]}")
                print()
            
            # 檢查 quiz_history 表
            print("\n2. 檢查 quiz_history 表:")
            histories = conn.execute(text("SELECT * FROM quiz_history")).fetchall()
            print(f"   - 總共 {len(histories)} 個測驗記錄")
            
            for i, history in enumerate(histories):
                print(f"   - 記錄 {i+1}:")
                print(f"     ID: {history[0]}")
                print(f"     模板ID: {history[1]}")
                print(f"     用戶: {history[2]}")
                print(f"     類型: {history[3]}")
                print(f"     總題數: {history[4]}")
                print(f"     已答題數: {history[5]}")
                print(f"     正確數: {history[6]}")
                print(f"     錯誤數: {history[7]}")
                print()
            
            # 檢查 quiz_errors 表
            print("\n3. 檢查 quiz_errors 表:")
            errors = conn.execute(text("SELECT * FROM quiz_errors")).fetchall()
            print(f"   - 總共 {len(errors)} 個錯題記錄")
            
            for i, error in enumerate(errors):
                print(f"   - 錯題 {i+1}:")
                print(f"     測驗ID: {error[1]}")
                print(f"     用戶: {error[2]}")
                print(f"     題目ID: {error[3]}")
                print(f"     用戶答案: {error[4]}")
                print()
        
        # 檢查 MongoDB
        print("\n📊 檢查 MongoDB...")
        try:
            # 檢查 exam 集合
            exam_count = mongo.db.exam.count_documents({})
            print(f"   - exam 集合總共 {exam_count} 個文檔")
            
            # 檢查前幾個文檔
            if exam_count > 0:
                sample_exam = mongo.db.exam.find_one()
                print(f"   - 樣本文檔結構:")
                for key, value in sample_exam.items():
                    if key == '_id':
                        print(f"     {key}: {type(value)}")
                    else:
                        print(f"     {key}: {value}")
        except Exception as e:
            print(f"   - MongoDB 檢查失敗: {e}")
            
    except Exception as e:
        print(f"❌ 資料庫檢查失敗: {e}")

if __name__ == "__main__":
    test_database()
