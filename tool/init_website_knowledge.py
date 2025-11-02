#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化網站知識庫腳本
運行此腳本以初始化網站知識庫，將預設的網站功能資訊儲存到 ChromaDB
"""

import sys
import os
import json
import logging

# 添加項目根目錄到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.website_knowledge_db import (
    init_chromadb_knowledge_collection,
    save_knowledge_to_chromadb
)

logger = logging.getLogger(__name__)

# ==================== 載入知識項目 ====================

def load_knowledge_from_json() -> list:
    """從 JSON 文件載入知識項目"""
    try:
        # 獲取當前文件的絕對路徑
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 構建 JSON 文件的路徑
        json_path = os.path.join(current_dir, '..', 'src', 'rag_sys', 'data', 'website_knowledge.json')
        
        with open(json_path, 'r', encoding='utf-8') as f:
            knowledge_items = json.load(f)
        
        logger.info(f"✅ 從 JSON 載入 {len(knowledge_items)} 筆知識項目")
        return knowledge_items
    except FileNotFoundError:
        logger.error(f"❌ 找不到知識庫 JSON 文件: {json_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 解析錯誤: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ 載入知識項目失敗: {e}")
        return []

# ==================== 初始化函數 ====================

def initialize_website_knowledge_base() -> bool:
    """
    初始化網站知識庫，插入預設的網站功能資訊到 ChromaDB
    
    Returns:
        是否成功
    """
    try:
        client, collection = init_chromadb_knowledge_collection()
        
        # 檢查是否已經初始化（檢查集合中是否有資料）
        try:
            existing_count = collection.count()
            if existing_count > 0:
                logger.info(f"⚠️ 網站知識庫已存在 {existing_count} 筆資料，是否要重新初始化？")
                # 可選：如果需要重新初始化，可以刪除現有資料
                # collection.delete()
        except Exception:
            pass  # 如果 count 失敗，繼續初始化
        
        # 從 JSON 文件載入知識項目
        knowledge_items = load_knowledge_from_json()
        
        if not knowledge_items:
            logger.error("❌ 沒有載入到任何知識項目")
            return False
        
        # 儲存到 ChromaDB
        saved_count = 0
        for knowledge in knowledge_items:
            try:
                doc_id = save_knowledge_to_chromadb(knowledge)
                knowledge["doc_id"] = doc_id
                saved_count += 1
            except Exception as e:
                logger.error(f"❌ 儲存知識項目失敗: {knowledge.get('title', 'Unknown')}, 錯誤: {e}")
        
        logger.info(f"✅ 網站知識庫初始化完成: 已插入 {saved_count}/{len(knowledge_items)} 筆知識項目")
        return saved_count > 0
    except Exception as e:
        logger.error(f"❌ 初始化網站知識庫失敗: {e}")
        return False

# ==================== 主函數 ====================

def main():
    """主函數"""
    print("🚀 開始初始化網站知識庫（使用 ChromaDB）...")
    
    success = initialize_website_knowledge_base()
    
    if success:
        print("✅ 網站知識庫初始化成功！")
        print("\n已儲存的知識項目包括：")
        print("- 系統概覽頁面")
        print("- 測驗中心（知識點測驗、學校考古題測驗）")
        print("- 測驗作答頁面")
        print("- 學習成效分析頁面")
        print("- 科技趨勢頁面")
        print("- 系統設定功能")
        print("- 各種操作說明")
        print("\n現在 AI 可以準確回答網站相關問題了！")
    else:
        print("❌ 網站知識庫初始化失敗，請檢查錯誤訊息")

if __name__ == "__main__":
    main()
