#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用戶角色系統遷移腳本
將students collection改為user，新增role字段
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrate_user_roles():
    """遷移用戶角色系統"""
    try:
        # 連接MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['MIS_Teach']
        
        print("🔄 開始用戶角色系統遷移...")
        
        # 檢查是否存在students collection
        if 'students' in db.list_collection_names():
            print("📊 發現students collection，開始遷移...")
            
            # 獲取所有學生資料
            students = list(db.students.find())
            print(f"📝 找到 {len(students)} 筆學生資料")
            
            # 為每個學生添加role字段
            for student in students:
                student['role'] = 'student'
            
            # 創建user collection並插入資料
            if 'user' in db.list_collection_names():
                print("⚠️ user collection已存在，先清空...")
                db.user.drop()
            
            result = db.user.insert_many(students)
            print(f"✅ 成功遷移 {len(result.inserted_ids)} 筆學生資料到user collection")
            
            
        else:
            print("ℹ️ 未發現students collection，跳過遷移")
        
        # 檢查user collection結構
        user_count = db.user.count_documents({})
        print(f"📊 user collection目前有 {user_count} 筆資料")
        
        # 顯示角色分布
        role_stats = db.user.aggregate([
            {"$group": {"_id": "$role", "count": {"$sum": 1}}}
        ])
        
        print("📈 角色分布統計:")
        for stat in role_stats:
            print(f"   {stat['_id']}: {stat['count']} 筆")
        
        print("🎉 用戶角色系統遷移完成！")
        return True
        
    except Exception as e:
        print(f"❌ 遷移失敗: {e}")
        return False


if __name__ == "__main__":
    print("🔧 用戶角色系統遷移工具")
    print("=" * 50)
    
    # 執行遷移
    if migrate_user_roles():
        print("\n✅ 所有操作完成！")
    else:
        print("\n❌ 遷移失敗！")
