#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini API 診斷工具
用於診斷 API 金鑰和模型配額問題
"""

import os
import sys
import google.generativeai as genai
from pathlib import Path

# 添加 backend 目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tool.api_keys import get_api_key

def test_model_availability(api_key: str, model_name: str) -> dict:
    """測試特定模型是否可用"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 嘗試簡單請求
        response = model.generate_content("Hi")
        
        return {
            'status': 'success',
            'model': model_name,
            'available': True,
            'message': '模型可用'
        }
    except Exception as e:
        error_msg = str(e)
        
        # 分析錯誤類型
        if 'quota' in error_msg.lower() or '429' in error_msg:
            if 'limit: 0' in error_msg:
                return {
                    'status': 'quota_zero',
                    'model': model_name,
                    'available': False,
                    'message': '免費配額為 0（此模型可能不支援免費層或需要啟用計費）'
                }
            else:
                return {
                    'status': 'quota_exceeded',
                    'model': model_name,
                    'available': False,
                    'message': '配額已用完'
                }
        elif 'invalid' in error_msg.lower() or '401' in error_msg:
            return {
                'status': 'invalid_key',
                'model': model_name,
                'available': False,
                'message': 'API 金鑰無效'
            }
        else:
            return {
                'status': 'error',
                'model': model_name,
                'available': False,
                'message': f'其他錯誤: {error_msg[:200]}'
            }

def main():
    """主診斷函數"""
    print("=" * 80)
    print("🔍 Gemini API 診斷工具")
    print("=" * 80)
    print()
    
    # 獲取 API 金鑰
    api_key = get_api_key()
    if not api_key:
        print("❌ 無法獲取 API 金鑰")
        return
    
    masked_key = f"{api_key[:8]}...{api_key[-4:]}"
    print(f"🔑 使用 API 金鑰: {masked_key}")
    print()
    
    # 測試的模型列表（按優先順序）
    models_to_test = [
        "gemini-2.5-flash",      # 通常可用（根據診斷結果）
        "gemini-1.5-flash",      # 通常有免費配額
        "gemini-1.5-pro",        # 可能有免費配額
        "gemini-2.0-flash",      # 免費配額可能為 0
    ]
    
    print("🧪 測試各模型的可用性...")
    print("-" * 80)
    
    results = []
    for model_name in models_to_test:
        print(f"\n📋 測試模型: {model_name}")
        result = test_model_availability(api_key, model_name)
        results.append(result)
        
        if result['status'] == 'success':
            print(f"   ✅ {result['message']}")
        elif result['status'] == 'quota_zero':
            print(f"   ⚠️  {result['message']}")
        else:
            print(f"   ❌ {result['message']}")
    
    print()
    print("=" * 80)
    print("📊 診斷結果總結")
    print("=" * 80)
    
    # 找出可用的模型
    available_models = [r for r in results if r['available']]
    
    if available_models:
        print(f"\n✅ 找到 {len(available_models)} 個可用的模型:")
        for result in available_models:
            print(f"   • {result['model']}")
        print("\n💡 建議: 在程式碼中使用這些可用的模型")
    else:
        print("\n❌ 沒有找到任何可用的模型")
        print("\n🔧 可能的解決方案:")
        print("   1. 檢查 Google Cloud Console 是否已啟用 Generative AI API")
        print("   2. 確認 API 金鑰有正確的權限")
        print("   3. 檢查是否需要啟用計費帳戶（即使使用免費層）")
        print("   4. 確認您的地區支援 Gemini API 免費層")
        print("   5. 等待配額重置（如果是暫時性配額用完）")
        print("\n📚 參考資源:")
        print("   • https://ai.google.dev/gemini-api/docs/troubleshooting")
        print("   • https://ai.google.dev/gemini-api/docs/rate-limits")
    
    print()
    print("=" * 80)
    print("💡 關於免費層配額限制")
    print("=" * 80)
    print("""
根據 Google 在 2025 年 12 月的政策調整：

1. gemini-2.5-flash: 通常可用（建議優先使用）
2. gemini-1.5-flash: 通常有免費配額（但可能在某些 API 版本中不可用）
3. gemini-1.5-pro: 可能有免費配額（但可能在某些 API 版本中不可用）
4. gemini-2.0-flash: 免費配額可能為 0

如果看到 "limit: 0" 錯誤，表示：
- 該模型的免費層配額已被限制為 0
- 可能需要啟用計費帳戶（即使使用免費層）
- 或該模型不再支援免費層

如果看到 "404 models/xxx is not found" 錯誤，表示：
- 該模型名稱在當前 API 版本中不存在
- 可能需要使用不同的模型名稱或 API 版本

建議：
- 優先使用 gemini-2.5-flash（根據診斷結果通常可用）
- 如需使用其他模型，請先執行診斷工具確認可用性
    """)

if __name__ == "__main__":
    main()

