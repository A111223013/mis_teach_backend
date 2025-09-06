#!/usr/bin/env python3
"""
工具：測試每個 API key 的狀態
找出哪個 API key 沒有額度
"""

import os
import sys
import time
import google.generativeai as genai
from pathlib import Path

# 添加 backend 目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tool.api_keys import APIKeyManager

def test_single_api_key(api_key, test_prompt="Hello, this is a test."):
    """測試單個 API key"""
    try:
        # 配置 API key
        genai.configure(api_key=api_key)
        
        # 創建模型
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 發送測試請求
        start_time = time.time()
        response = model.generate_content(test_prompt)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        return {
            'status': 'success',
            'response_time': response_time,
            'response_text': response.text[:100] if hasattr(response, 'text') else str(response)[:100],
            'error': None
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # 檢查是否是額度問題
        if 'quota' in error_msg.lower() or '429' in error_msg:
            return {
                'status': 'quota_exceeded',
                'response_time': None,
                'response_text': None,
                'error': error_msg
            }
        elif 'invalid' in error_msg.lower() or '401' in error_msg:
            return {
                'status': 'invalid_key',
                'response_time': None,
                'response_text': None,
                'error': error_msg
            }
        else:
            return {
                'status': 'error',
                'response_time': None,
                'response_text': None,
                'error': error_msg
            }

def test_all_api_keys():
    """測試所有 API keys"""
    print("🔍 開始測試所有 API keys...")
    print("=" * 80)
    
    # 載入 API key 管理器
    api_manager = APIKeyManager()
    api_keys = api_manager.api_keys
    
    if not api_keys:
        print("❌ 沒有找到任何 API keys")
        return
    
    print(f"📊 找到 {len(api_keys)} 個 API keys")
    print()
    
    results = []
    
    for i, api_key in enumerate(api_keys, 1):
        masked_key = f"{api_key[:8]}...{api_key[-4:]}"
        print(f"🧪 測試 API key {i}/{len(api_keys)}: {masked_key}")
        
        result = test_single_api_key(api_key)
        result['key_index'] = i
        result['masked_key'] = masked_key
        result['full_key'] = api_key
        results.append(result)
        
        # 顯示結果
        if result['status'] == 'success':
            print(f"   ✅ 成功 - 回應時間: {result['response_time']:.2f}s")
            print(f"   📝 回應: {result['response_text']}")
        elif result['status'] == 'quota_exceeded':
            print(f"   ❌ 額度超限 - {result['error']}")
        elif result['status'] == 'invalid_key':
            print(f"   ⚠️  無效密鑰 - {result['error']}")
        else:
            print(f"   ❌ 其他錯誤 - {result['error']}")
        
        print()
        
        # 避免請求過於頻繁
        time.sleep(1)
    
    # 生成總結報告
    print("📊 測試結果總結:")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    quota_exceeded_count = sum(1 for r in results if r['status'] == 'quota_exceeded')
    invalid_count = sum(1 for r in results if r['status'] == 'invalid_key')
    error_count = sum(1 for r in results if r['status'] == 'error')
    
    print(f"✅ 正常可用: {success_count} 個")
    print(f"❌ 額度超限: {quota_exceeded_count} 個")
    print(f"⚠️  無效密鑰: {invalid_count} 個")
    print(f"❌ 其他錯誤: {error_count} 個")
    print()
    
    # 顯示有問題的 keys
    if quota_exceeded_count > 0:
        print("🚫 額度超限的 API keys:")
        for result in results:
            if result['status'] == 'quota_exceeded':
                print(f"   - {result['masked_key']} (第 {result['key_index']} 個)")
        print()
    
    if invalid_count > 0:
        print("⚠️  無效的 API keys:")
        for result in results:
            if result['status'] == 'invalid_key':
                print(f"   - {result['masked_key']} (第 {result['key_index']} 個)")
        print()
    
    # 顯示可用的 keys
    if success_count > 0:
        print("✅ 可用的 API keys:")
        for result in results:
            if result['status'] == 'success':
                print(f"   - {result['masked_key']} (第 {result['key_index']} 個) - {result['response_time']:.2f}s")
        print()
    
    # 建議
    if quota_exceeded_count > 0:
        print("💡 建議:")
        print("   1. 移除額度超限的 API keys")
        print("   2. 添加新的 API keys")
        print("   3. 等待額度重置（通常是每分鐘或每天）")
        print()
    
    return results

def create_clean_api_env(results):
    """創建清理後的 api.env 文件"""
    valid_keys = []
    
    for result in results:
        if result['status'] == 'success':
            valid_keys.append(result['full_key'])
    
    if valid_keys:
        env_content = f"AI_API_KEYS={','.join(valid_keys)}\n"
        
        with open('backend/api.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"✅ 已更新 api.env，保留 {len(valid_keys)} 個有效的 API keys")
    else:
        print("❌ 沒有找到任何有效的 API keys！")

if __name__ == "__main__":
    results = test_all_api_keys()
    
    # 詢問是否要清理 api.env
    print("🛠️  是否要清理 api.env 文件，只保留有效的 API keys？")
    print("   這將移除所有額度超限和無效的 keys")
    
    # 自動清理（可以改為手動確認）
    create_clean_api_env(results)
