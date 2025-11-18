#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入 Demo 題目到 MongoDB
將 7 題 demo 題目插入到 exam collection 中
"""

import sys
import os
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_mongo_connection():
    """直接連接 MongoDB"""
    try:
        from config import DevelopmentConfig
        
        config = DevelopmentConfig()
        mongo_uri = config.MONGO_URI
        db_name = config.MONGO_DB_NAME
        
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # 測試連接
        client.admin.command('ping')
        print("MongoDB 連接成功")
        
        return db
        
    except Exception as e:
        print(f"MongoDB 連接失敗: {str(e)}")
        return None

def insert_demo_questions():
    """插入 7 題 demo 題目到資料庫"""
    
    # Demo 題目數據
    demo_questions = [
        {
            "_id": ObjectId("6905deac7292fdbd94102c01"),
            "type": "single",
            "school": "demo",
            "department": "demo",
            "year": "114",
            "question_number": "1",
            "question_text": "(申論題) 請簡述何謂變數(Variable)，並舉例說明其在程式設計中的用途。",
            "options": [],
            "answer": "變數是用來儲存資料的命名空間，讓程式能夠動態地讀取或修改資料。例如：x = 5 表示將數字 5 儲存在變數 x 中。",
            "answer_type": "long-answer",
            "image_file": [],
            "detail-answer": "變數是一種具名稱的儲存空間，用於保存程式運行過程中的資料。變數名稱通常代表記憶體中的一個位置，方便取用與更新。例如：在 Python 中，`x = 5` 表示建立變數 x 並指定其值為 5。",
            "key-points": "程式設計概念",
            "micro_concepts": ["資料表示", "記憶體與變數"],
            "difficulty level": "基礎",
            "error reason": ""
        },
        {
            "_id": ObjectId("6905deac7292fdbd94102c02"),
            "type": "single",
            "school": "demo",
            "department": "demo",
            "year": "114",
            "question_number": "2",
            "question_text": "(繪圖題) 請將數字序列 [25, 10, 30, 5, 15, 20, 35] 依序插入，畫出對應的二元搜尋樹（BST）結構。",
            "options": [],
            "answer": "根節點為 25，左子樹包含 [10, 5, 15, 20]，右子樹包含 [30, 35]。",
            "answer_type": "draw-answer",
            "image_file": [],
            "detail-answer": "依序插入：25 為根節點 → 10 < 25，插入左子樹 → 30 > 25，插入右子樹 → 5 < 25 且 5 < 10，插入 10 的左子樹 → 15 < 25 且 15 > 10，插入 10 的右子樹 → 20 < 25 且 20 > 10，插入 15 的右子樹 → 35 > 25 且 35 > 30，插入 30 的右子樹。",
            "key-points": "演算法設計",
            "micro_concepts": ["流程控制", "輸入輸出"],
            "difficulty level": "基礎",
            "error reason": ""
        },
        {
            "_id": ObjectId("6905deac7292fdbd94102c03"),
            "type": "single",
            "school": "demo",
            "department": "demo",
            "year": "114",
            "question_number": "3",
            "question_text": "請計算下列定積分，並寫出完整的計算過程：\n\n$$\\int_0^1 x^2 \\, dx$$\n\n請依照步驟填寫：\n1. 找出被積函數的不定積分\n2. 應用微積分基本定理\n3. 代入上下限並計算",
            "options": [],
            "answer": "計算過程：\n\n步驟 1：找出不定積分\n$$\\int x^2 \\, dx = \\frac{x^3}{3} + C$$\n\n步驟 2：應用微積分基本定理\n$$\\int_0^1 x^2 \\, dx = \\left[\\frac{x^3}{3}\\right]_0^1$$\n\n步驟 3：代入上下限\n$$= \\frac{1^3}{3} - \\frac{0^3}{3} = \\frac{1}{3} - 0 = \\frac{1}{3}$$\n\n最終答案：$\\frac{1}{3}$",
            "answer_type": "short-answer",
            "image_file": [],
            "detail-answer": "**解題過程詳解：**\n\n**步驟 1：找出不定積分**\n根據冪函數積分公式：\n$$\\int x^n \\, dx = \\frac{x^{n+1}}{n+1} + C \\quad (n \\neq -1)$$\n\n因此：\n$$\\int x^2 \\, dx = \\frac{x^{2+1}}{2+1} + C = \\frac{x^3}{3} + C$$\n\n**步驟 2：應用微積分基本定理**\n微積分基本定理指出：\n$$\\int_a^b f(x) \\, dx = F(b) - F(a)$$\n其中 $F(x)$ 是 $f(x)$ 的任意反導函數。\n\n因此：\n$$\\int_0^1 x^2 \\, dx = \\left[\\frac{x^3}{3}\\right]_0^1$$\n\n**步驟 3：代入上下限**\n$$= \\frac{1^3}{3} - \\frac{0^3}{3} = \\frac{1}{3} - 0 = \\frac{1}{3}$$\n\n**驗證：**\n我們可以驗證這個結果是否合理。函數 $f(x) = x^2$ 在區間 $[0,1]$ 上的圖形是一個拋物線，從 $(0,0)$ 到 $(1,1)$。定積分代表這個區域的面積，應該是一個正數且小於 $1$（因為是 $1 \\times 1$ 正方形的一部分），所以 $\\frac{1}{3}$ 是一個合理的答案。",
            "key-points": "微積分",
            "micro_concepts": ["定積分", "微積分基本定理"],
            "difficulty level": "基礎",
            "error reason": ""
            },

        {
            "_id": ObjectId("6905deac7292fdbd94102c04"),
            "type": "single",
            "school": "demo",
            "department": "demo",
            "year": "114",
            "question_number": "4",
            "question_text": "(程式題) 請撰寫一段 Python 程式，輸入兩個整數並輸出其乘積。",
            "options": [],
            "answer": "a = int(input())\nb = int(input())\nprint(a * b)",
            "answer_type": "coding-answer",
            "image_file": [],
            "detail-answer": "此題考察 Python 基礎輸入輸出與運算。正確程式範例：\n```python\na = int(input('輸入第一個數:'))\nb = int(input('輸入第二個數:'))\nprint('乘積:', a * b)\n```",
            "key-points": "程式設計基礎",
            "micro_concepts": ["輸入輸出", "基本運算"],
            "difficulty level": "基礎",
            "error reason": ""
        },
        {
            "_id": ObjectId("6905deac7292fdbd94102c05"),
            "type": "single",
            "school": "demo",
            "department": "demo",
            "year": "114",
            "question_number": "5",
            "question_text": "(選擇題) 下列哪一項是電腦的主要輸入裝置？",
            "options": ["(A) 印表機", "(B) 螢幕", "(C) 滑鼠", "(D) 喇叭"],
            "answer": "(C) 滑鼠",
            "answer_type": "single-choice",
            "image_file": [],
            "detail-answer": "輸入裝置是用於將資料送入電腦的設備，如滑鼠、鍵盤、掃描器。選項中只有滑鼠屬於輸入裝置。",
            "key-points": "計算機概論",
            "micro_concepts": ["硬體結構", "輸入裝置"],
            "difficulty level": "基礎",
            "error reason": ""
        },
        {
            "_id": ObjectId("6905deac7292fdbd94102c06"),
            "type": "single",
            "school": "demo",
            "department": "demo",
            "year": "114",
            "question_number": "6",
            "question_text": "(多選題) 下列哪些屬於作業系統的功能？",
            "options": ["(A) 記憶體管理", "(B) 處理程序管理", "(C) 網路架設", "(D) 檔案系統管理"],
            "answer": ["(A)", "(B)", "(D)"],
            "answer_type": "multiple-choice",
            "image_file": [],
            "detail-answer": "作業系統主要負責：記憶體管理、程序管理、檔案系統與裝置管理。網路架設屬於應用層級的任務。",
            "key-points": "作業系統",
            "micro_concepts": ["資源管理", "系統功能"],
            "difficulty level": "基礎",
            "error reason": ""
        },
        {
            "_id": ObjectId("6905deac7292fdbd94102c07"),
            "type": "single",
            "school": "demo",
            "department": "demo",
            "year": "114",
            "question_number": "7",
            "question_text": "(填空題) 在 Python 中，用來表示註解的符號是 ________ 。",
            "options": [],
            "answer": "#",
            "answer_type": "fill-in-the-blank",
            "image_file": [],
            "detail-answer": "在 Python 中，井字號 `#` 用於撰寫單行註解，例如：`# 這是一行註解`。",
            "key-points": "程式語法基礎",
            "micro_concepts": ["程式可讀性", "註解使用"],
            "difficulty level": "基礎",
            "error reason": ""
        }
    ]
    
    try:
        db = get_mongo_connection()
        if db is None:
            print("MongoDB 連接失敗")
            return False
        
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        
        for question in demo_questions:
            question_id = question['_id']
            
            # 檢查題目是否已存在
            existing = db.exam.find_one({"_id": question_id})
            
            if existing:
                # 如果已存在，更新題目
                result = db.exam.update_one(
                    {"_id": question_id},
                    {"$set": question}
                )
                if result.modified_count > 0:
                    updated_count += 1
                    print(f"[更新] 題目 {question['question_number']}: {question['question_text'][:30]}...")
                else:
                    skipped_count += 1
                    print(f"[跳過] 題目 {question['question_number']} 已存在且無需更新")
            else:
                # 如果不存在，插入新題目
                result = db.exam.insert_one(question)
                if result.inserted_id:
                    inserted_count += 1
                    print(f"[插入] 題目 {question['question_number']}: {question['question_text'][:30]}...")
                else:
                    print(f"[失敗] 插入題目 {question['question_number']} 失敗")
        
        print(f"\n統計:")
        print(f"  - 新增題目: {inserted_count}")
        print(f"  - 更新題目: {updated_count}")
        print(f"  - 跳過題目: {skipped_count}")
        print(f"  - 總計: {len(demo_questions)} 題")
        
        return True
        
    except Exception as e:
        print(f"插入題目時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("開始插入 Demo 題目...")
    print("=" * 50)
    
    success = insert_demo_questions()
    
    print("=" * 50)
    if success:
        print("Demo 題目插入完成！")
    else:
        print("Demo 題目插入失敗！")
        sys.exit(1)

    