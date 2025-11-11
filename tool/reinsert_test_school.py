#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新插入測試學校資料，確保包含所有題型
"""

import sys
import os

# 添加父目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool.insert_test_school import delete_test_school_data, insert_test_school_data

def main():
    """主函數"""
    print("=" * 60)
    print("重新插入測試學校資料")
    print("=" * 60)
    
    # 1. 刪除現有資料
    print("\n步驟 1: 刪除現有測試學校資料...")
    delete_test_school_data(auto_confirm=True)
    
    # 2. 重新插入
    print("\n步驟 2: 重新插入測試學校資料（包含所有題型）...")
    success = insert_test_school_data(auto_mode=True)
    
    if success:
        print("\n[OK] 測試學校資料重新插入完成！")
        print("現在包含所有題型，包括畫圖題（draw-answer）")
    else:
        print("\n[!] 測試學校資料重新插入失敗！")

if __name__ == "__main__":
    main()

