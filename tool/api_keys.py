#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密鑰配置文件 - 從api.env讀取
"""

import os
import random
from typing import List

def load_env_file(file_path: str) -> dict:
    """載入.env文件"""
    env_vars = {}
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            print(f"✅ 成功載入 {file_path}")
        else:
            print(f"⚠️ 文件不存在: {file_path}")
    except Exception as e:
        print(f"❌ 載入 {file_path} 失敗: {e}")
    
    return env_vars

class APIKeyManager:
    """API密鑰管理器"""
    
    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.current_index = 0
        print(f"🔑 載入API密鑰: {len(self.api_keys)} 個")
    
    def _load_api_keys(self) -> List[str]:
        """載入API密鑰"""
        # 從api.env讀取AI_API_KEYS
        # 確保從正確的路徑讀取 api.env
        api_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api.env')
        env_vars = load_env_file(api_env_path)
        env_keys = env_vars.get('AI_API_KEYS')
        
        if env_keys:
            # 清理和解析API金鑰
            env_keys = env_keys.strip()
            
            # 移除可能的方括號和換行符
            env_keys = env_keys.replace('[', '').replace(']', '').replace('\n', '').replace('\r', '')
            
            # 分割並清理密鑰
            keys = []
            for key in env_keys.split(','):
                key = key.strip()
                if key and len(key) > 10:  # 確保是有效的API金鑰
                    keys.append(key)
            
            if keys:
                print(f"✅ 從api.env載入 {len(keys)} 個API密鑰")
                return keys
            else:
                print("⚠️ 從api.env解析的API密鑰無效")
        
        # 如果環境變數沒有或解析失敗，使用默認密鑰
        print("⚠️ api.env中 AI_API_KEYS 未設置或解析失敗，使用默認密鑰")
        return DEFAULT_API_KEYS.copy()
    
    def get_random_key(self) -> str:
        """隨機獲取一個API密鑰"""
        if not self.api_keys:
            raise ValueError("沒有可用的API密鑰")
        return random.choice(self.api_keys)
    
    def get_next_key(self) -> str:
        """輪流獲取API密鑰（輪詢方式）"""
        if not self.api_keys:
            raise ValueError("沒有可用的API密鑰")
        
        key = self.api_keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return key
    
    def get_keys_count(self) -> int:
        """獲取可用API密鑰數量"""
        return len(self.api_keys)
    
    def add_key(self, key: str):
        """添加新的API密鑰"""
        if key not in self.api_keys:
            self.api_keys.append(key)
            print(f"✅ 添加新API密鑰: {key[:20]}...")
    
    def remove_key(self, key: str):
        """移除API密鑰"""
        if key in self.api_keys:
            self.api_keys.remove(key)
            print(f"❌ 移除API密鑰: {key[:20]}...")
    
    def reload_keys(self):
        """重新載入API密鑰"""
        self.api_keys = self._load_api_keys()
        self.current_index = 0
        print(f"🔄 重新載入API密鑰: {len(self.api_keys)} 個")

# 創建全局實例
api_key_manager = APIKeyManager()

def get_api_key() -> str:
    """獲取API密鑰的便捷函數"""
    return api_key_manager.get_random_key()

def get_api_keys_count() -> int:
    """獲取API密鑰數量的便捷函數"""
    return api_key_manager.get_keys_count()

def reload_api_keys():
    """重新載入API密鑰的便捷函數"""
    api_key_manager.reload_keys()

# 測試函數
def test_api_keys():
    """測試API密鑰載入"""
    print("🧪 測試API密鑰載入...")
    print(f"📊 可用密鑰數量: {get_api_keys_count()}")
    
    # 顯示所有密鑰（隱藏部分內容）
    all_keys = api_key_manager.api_keys
    for i, key in enumerate(all_keys):
        masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else key
        print(f"🔑 密鑰 {i+1}: {masked_key}")
    
    # 測試隨機選擇
    random_key = get_api_key()
    masked_random = f"{random_key[:8]}...{random_key[-4:]}" if len(random_key) > 12 else random_key
    print(f"🎲 隨機選擇密鑰: {masked_random}")
    
    # 測試輪詢
    next_key = api_key_manager.get_next_key()
    masked_next = f"{next_key[:8]}...{next_key[-4:]}" if len(next_key) > 12 else next_key
    print(f"🔄 下一個密鑰: {masked_next}")

def test_parallel_processing():
    """測試並行處理功能"""
    print("\n🚀 測試並行處理功能...")
    
    # 模擬題目數據
    test_questions = [
        {'question_id': f'q{i}', 'user_answer': f'answer_{i}', 'question_type': 'single-choice'}
        for i in range(1, 11)  # 10個測試題目
    ]
    
    print(f"📝 測試題目數量: {len(test_questions)}")
    print(f"🔑 可用API金鑰: {get_api_keys_count()}")
    
    # 計算分配
    api_keys_count = get_api_keys_count()
    questions_per_key = len(test_questions) // api_keys_count
    remainder = len(test_questions) % api_keys_count
    
    print(f"📊 分配結果:")
    start_idx = 0
    for i in range(api_keys_count):
        batch_size = questions_per_key + (1 if i < remainder else 0)
        end_idx = start_idx + batch_size
        print(f"  API金鑰 {i+1}: 題目 {start_idx+1}-{end_idx} (共 {batch_size} 題)")
        start_idx = end_idx

if __name__ == "__main__":
    test_api_keys()
    test_parallel_processing()
