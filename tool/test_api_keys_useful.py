#!/usr/bin/env python3
"""
工具：測試每個 API key 組的狀態
支援多組API密鑰測試，找出哪個組的API key沒有額度
"""

import os
import sys
import time
import google.generativeai as genai
from pathlib import Path
from typing import Dict, List, Any

# 添加 backend 目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tool.api_keys import MultiGroupAPIKeyManager, get_available_groups

def test_single_api_key(api_key: str, model_name: str = "gemini-2.5-flash", test_prompt: str = "Hello, this is a test.") -> Dict[str, Any]:
    """測試單個 API key，支援指定模型"""
    try:
        # 配置 API key
        genai.configure(api_key=api_key)
        
        # 創建模型
        model = genai.GenerativeModel(model_name)
        
        # 發送測試請求
        start_time = time.time()
        response = model.generate_content(test_prompt)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        return {
            'status': 'success',
            'model': model_name,
            'response_time': response_time,
            'response_text': response.text[:100] if hasattr(response, 'text') else str(response)[:100],
            'error': None
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # 檢查是否是額度問題
        if 'quota' in error_msg.lower() or '429' in error_msg:
            # 檢查是否是 limit: 0 的情況
            if 'limit: 0' in error_msg:
                return {
                    'status': 'quota_zero',
                    'model': model_name,
                    'response_time': None,
                    'response_text': None,
                    'error': error_msg
                }
            else:
                return {
                    'status': 'quota_exceeded',
                    'model': model_name,
                    'response_time': None,
                    'response_text': None,
                    'error': error_msg
                }
        elif 'invalid' in error_msg.lower() or '401' in error_msg:
            return {
                'status': 'invalid_key',
                'model': model_name,
                'response_time': None,
                'response_text': None,
                'error': error_msg
            }
        elif '404' in error_msg or 'not found' in error_msg.lower():
            return {
                'status': 'model_not_found',
                'model': model_name,
                'response_time': None,
                'response_text': None,
                'error': error_msg
            }
        else:
            return {
                'status': 'error',
                'model': model_name,
                'response_time': None,
                'response_text': None,
                'error': error_msg
            }

def test_api_group(group_name: str, model_names: List[str] = None, test_prompt: str = "Hello, this is a test.") -> Dict[str, Any]:
    """測試指定API密鑰組的所有密鑰，支援測試多個模型"""
    if model_names is None:
        # 預設測試多個模型，優先使用有免費配額的模型
        # 根據診斷結果，gemini-2.5-flash 通常可用
        model_names = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]
    
    print(f"🔍 測試API密鑰組: {group_name}")
    print("-" * 60)
    
    # 創建API密鑰管理器
    api_manager = MultiGroupAPIKeyManager(group_name)
    api_keys = api_manager.api_keys
    
    if not api_keys:
        print(f"❌ {group_name} 沒有找到任何 API keys")
        return {
            'group_name': group_name,
            'total_keys': 0,
            'success_count': 0,
            'quota_exceeded_count': 0,
            'invalid_count': 0,
            'error_count': 0,
            'results': []
        }
    
    print(f"📊 找到 {len(api_keys)} 個 API keys")
    print(f"🤖 將測試以下模型: {', '.join(model_names)}")
    print()
    
    results = []
    
    for i, api_key in enumerate(api_keys, 1):
        masked_key = f"{api_key[:8]}...{api_key[-4:]}"
        print(f"🧪 測試 API key {i}/{len(api_keys)}: {masked_key}")
        
        # 嘗試每個模型，找到第一個可用的
        key_success = False
        for model_name in model_names:
            print(f"   🔄 嘗試模型: {model_name}")
            result = test_single_api_key(api_key, model_name, test_prompt)
            result['key_index'] = i
            result['masked_key'] = masked_key
            result['full_key'] = api_key
            results.append(result)
            
            # 顯示結果
            if result['status'] == 'success':
                print(f"   ✅ 成功 (模型: {model_name}) - 回應時間: {result['response_time']:.2f}s")
                print(f"   📝 回應: {result['response_text']}")
                key_success = True
                break  # 找到可用模型就停止測試其他模型
            elif result['status'] == 'quota_zero':
                print(f"   ⚠️  模型 {model_name} 免費配額為 0（可能需要啟用計費或使用其他模型）")
            elif result['status'] == 'quota_exceeded':
                print(f"   ❌ 額度超限 (模型: {model_name})")
            elif result['status'] == 'model_not_found':
                print(f"   ⚠️  模型 {model_name} 不存在或在此 API 版本中不可用")
            elif result['status'] == 'invalid_key':
                print(f"   ⚠️  無效密鑰 (模型: {model_name})")
                break  # 無效密鑰不需要測試其他模型
            else:
                print(f"   ❌ 其他錯誤 (模型: {model_name}): {result['error'][:100]}")
        
        if not key_success:
            print(f"   ⚠️  此 API key 在所有測試的模型中均無法使用")
        
        print()
        
        # 避免請求過於頻繁
        time.sleep(1)
    
    # 統計結果
    success_count = sum(1 for r in results if r['status'] == 'success')
    quota_exceeded_count = sum(1 for r in results if r['status'] in ['quota_exceeded', 'quota_zero'])
    invalid_count = sum(1 for r in results if r['status'] == 'invalid_key')
    model_not_found_count = sum(1 for r in results if r['status'] == 'model_not_found')
    error_count = sum(1 for r in results if r['status'] == 'error' and r['status'] != 'model_not_found')
    
    group_result = {
        'group_name': group_name,
        'total_keys': len(api_keys),
        'success_count': success_count,
        'quota_exceeded_count': quota_exceeded_count,
        'invalid_count': invalid_count,
        'model_not_found_count': model_not_found_count,
        'error_count': error_count,
        'results': results
    }
    
    # 顯示組總結
    print(f"📊 {group_name} 測試結果總結:")
    print(f"   ✅ 正常可用: {success_count} 個")
    print(f"   ❌ 額度超限: {quota_exceeded_count} 個")
    print(f"   ⚠️  模型不存在: {model_not_found_count} 個")
    print(f"   ⚠️  無效密鑰: {invalid_count} 個")
    print(f"   ❌ 其他錯誤: {error_count} 個")
    print()
    
    return group_result

def test_all_api_groups(model_names: List[str] = None, test_prompt: str = "Hello, this is a test.") -> List[Dict[str, Any]]:
    """測試所有API密鑰組，支援指定模型列表"""
    print("🔍 開始測試所有API密鑰組...")
    print("=" * 80)
    
    # 獲取所有可用的API密鑰組
    groups = get_available_groups()
    
    if not groups:
        print("❌ 沒有找到任何API密鑰組")
        return []
    
    print(f"📊 找到 {len(groups)} 個API密鑰組: {', '.join(groups)}")
    print()
    
    all_results = []
    
    for group in groups:
        group_result = test_api_group(group, model_names, test_prompt)
        all_results.append(group_result)
        print("=" * 80)
    
    # 生成總體總結報告
    print("📊 所有API密鑰組測試結果總結:")
    print("=" * 80)
    
    total_groups = len(all_results)
    total_keys = sum(r['total_keys'] for r in all_results)
    total_success = sum(r['success_count'] for r in all_results)
    total_quota_exceeded = sum(r['quota_exceeded_count'] for r in all_results)
    total_invalid = sum(r['invalid_count'] for r in all_results)
    total_model_not_found = sum(r.get('model_not_found_count', 0) for r in all_results)
    total_error = sum(r['error_count'] for r in all_results)
    
    print(f"📊 總體統計:")
    print(f"   🔑 API密鑰組數量: {total_groups}")
    print(f"   🔐 總密鑰數量: {total_keys}")
    print(f"   ✅ 正常可用: {total_success} 個")
    print(f"   ❌ 額度超限: {total_quota_exceeded} 個")
    print(f"   ⚠️  模型不存在: {total_model_not_found} 個")
    print(f"   ⚠️  無效密鑰: {total_invalid} 個")
    print(f"   ❌ 其他錯誤: {total_error} 個")
    print()
    
    # 顯示各組詳細情況
    print("📋 各組詳細情況:")
    for result in all_results:
        group_name = result['group_name']
        success_rate = (result['success_count'] / result['total_keys'] * 100) if result['total_keys'] > 0 else 0
        print(f"   🔑 {group_name}: {result['success_count']}/{result['total_keys']} ({success_rate:.1f}%)")
    print()
    
    # 推薦最佳組
    best_group = max(all_results, key=lambda x: x['success_count'])
    if best_group['success_count'] > 0:
        print(f"🏆 推薦使用API密鑰組: {best_group['group_name']}")
        print(f"   ✅ 可用密鑰: {best_group['success_count']} 個")
        print(f"   📊 成功率: {best_group['success_count']/best_group['total_keys']*100:.1f}%")
    else:
        print("⚠️  所有API密鑰組都有問題，建議檢查密鑰或等待額度重置")
    
    print()
    
    return all_results

def create_clean_api_env(results: List[Dict[str, Any]]):
    """創建清理後的 api.env 文件"""
    print("🛠️  創建清理後的 api.env 文件...")
    
    # 收集所有有效的密鑰
    valid_keys_by_group = {}
    
    for result in results:
        group_name = result['group_name']
        valid_keys = []
        
        for key_result in result['results']:
            if key_result['status'] == 'success':
                valid_keys.append(key_result['full_key'])
        
        if valid_keys:
            valid_keys_by_group[group_name] = valid_keys
    
    if not valid_keys_by_group:
        print("❌ 沒有找到任何有效的API密鑰！")
        return
    
    # 生成新的api.env內容
    env_content = "# API密鑰配置文件\n"
    env_content += "# 支援多個不同的API密鑰組\n\n"
    
    for group_name, keys in valid_keys_by_group.items():
        # 將組名轉換為環境變數格式
        env_var_name = group_name.upper().replace('_API', '_API_KEYS')
        env_content += f"# {group_name}的API密鑰組\n"
        env_content += f"{env_var_name}={','.join(keys)}\n\n"
    
    # 設定預設組
    best_group = max(valid_keys_by_group.keys(), key=lambda x: len(valid_keys_by_group[x]))
    env_content += f"# 預設API密鑰組（如果沒有指定，會隨機選擇一組）\n"
    env_content += f"DEFAULT_API_GROUP={best_group}\n"
    
    # 寫入文件
    api_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api.env')
    with open(api_env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ 已更新 api.env")
    print(f"   📊 保留 {len(valid_keys_by_group)} 個API密鑰組")
    for group_name, keys in valid_keys_by_group.items():
        print(f"   🔑 {group_name}: {len(keys)} 個有效密鑰")

def main():
    """主函數"""
    print("🔧 多組API密鑰測試工具")
    print("=" * 80)
    
    # 測試所有API密鑰組
    results = test_all_api_groups()
    
    if results:
        # 詢問是否要清理 api.env
        print("🛠️  是否要清理 api.env 文件，只保留有效的API密鑰？")
        print("   這將移除所有額度超限和無效的密鑰")
        
        # 自動清理（可以改為手動確認）
        create_clean_api_env(results)
    
    print("\n🎉 測試完成！")

if __name__ == "__main__":
    main()