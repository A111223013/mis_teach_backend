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
        env_vars = load_env_file('api.env')
        env_keys = env_vars.get('AI_API_KEYS')
        
        if env_keys:
            # 處理可能的陣列格式 [key1,key2] 或字串格式 key1,key2
            env_keys = env_keys.strip()
            if env_keys.startswith('[') and env_keys.endswith(']'):
                # 陣列格式: [key1,key2]
                env_keys = env_keys[1:-1]  # 移除方括號
            
            # 分割並清理密鑰
            keys = [key.strip() for key in env_keys.split(',') if key.strip()]
            print(f"✅ 從api.env載入 {len(keys)} 個API密鑰")
            return keys
        
        # 如果環境變數沒有，使用默認密鑰
        print("⚠️ api.env中 AI_API_KEYS 未設置，使用默認密鑰")
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
    print(f"🔑 隨機密鑰: {get_api_key()[:20]}...")
    print(f"🔑 下一個密鑰: {api_key_manager.get_next_key()[:20]}...")

if __name__ == "__main__":
    test_api_keys()
