#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多組API密鑰管理系統
支援多個不同的API密鑰組，可以指定使用特定組或隨機選擇
"""

import os
import random
from typing import List, Dict, Optional

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

class MultiGroupAPIKeyManager:
    """多組API密鑰管理器"""
    
    def __init__(self, api_group: Optional[str] = None):
        """
        初始化API密鑰管理器
        api_group: 指定要使用的API密鑰組，如果為None則隨機選擇
        """
        self.api_groups = self._load_all_api_groups()
        self.current_group = api_group or self._get_default_group()
        self.api_keys = self._get_group_keys(self.current_group)
        self.current_index = 0
        
        print(f"🔑 載入API密鑰組: {self.current_group}")
        print(f"📊 可用密鑰數量: {len(self.api_keys)} 個")
    
    def _load_all_api_groups(self) -> Dict[str, List[str]]:
        """載入所有API密鑰組"""
        # 從api.env讀取所有API密鑰組
        api_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api.env')
        env_vars = load_env_file(api_env_path)
        
        api_groups = {}
        
        # 載入各個API密鑰組
        for key, value in env_vars.items():
            if key.endswith('_API_KEYS'):
                group_name = key.replace('_API_KEYS', '').lower() + '_api'
                keys = self._parse_api_keys(value)
                if keys:
                    api_groups[group_name] = keys
                    print(f"✅ 載入 {group_name}: {len(keys)} 個密鑰")
        
        return api_groups
    
    def _parse_api_keys(self, keys_string: str) -> List[str]:
        """解析API密鑰字符串"""
        if not keys_string:
            return []
        
        # 清理和解析API金鑰
        keys_string = keys_string.strip()
        keys_string = keys_string.replace('[', '').replace(']', '').replace('\n', '').replace('\r', '')
        
        # 分割並清理密鑰
        keys = []
        for key in keys_string.split(','):
            key = key.strip()
            if key and len(key) > 10:  # 確保是有效的API金鑰
                keys.append(key)
        
        return keys
    
    def _get_default_group(self) -> str:
        """隨機選擇一個可用的API密鑰組"""
        available_groups = list(self.api_groups.keys())
        if not available_groups:
            raise ValueError("沒有可用的API密鑰組")
        
        return random.choice(available_groups)
    
    def _get_group_keys(self, group_name: str) -> List[str]:
        """獲取指定組的API密鑰"""
        if group_name not in self.api_groups:
            raise ValueError(f"API密鑰組 '{group_name}' 不存在")
        
        return self.api_groups[group_name].copy()
    
    def get_random_key(self) -> str:
        """隨機獲取一個API密鑰"""
        if not self.api_keys:
            raise ValueError(f"API密鑰組 '{self.current_group}' 沒有可用的密鑰")
        return random.choice(self.api_keys)
    
    def get_next_key(self) -> str:
        """輪流獲取API密鑰（輪詢方式）"""
        if not self.api_keys:
            raise ValueError(f"API密鑰組 '{self.current_group}' 沒有可用的密鑰")
        
        key = self.api_keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return key
    
    def get_keys_count(self) -> int:
        """獲取當前組的API密鑰數量"""
        return len(self.api_keys)
    
    def get_all_groups(self) -> List[str]:
        """獲取所有可用的API密鑰組"""
        return list(self.api_groups.keys())
    
    def get_group_info(self, group_name: str) -> Dict[str, any]:
        """獲取指定組的詳細信息"""
        if group_name not in self.api_groups:
            return {'exists': False}
        
        return {
            'exists': True,
            'key_count': len(self.api_groups[group_name]),
            'keys': self.api_groups[group_name]
        }
    
    def switch_group(self, group_name: str):
        """切換到指定的API密鑰組"""
        if group_name not in self.api_groups:
            raise ValueError(f"API密鑰組 '{group_name}' 不存在")
        
        self.current_group = group_name
        self.api_keys = self._get_group_keys(group_name)
        self.current_index = 0
        print(f"🔄 切換到API密鑰組: {group_name}")
        print(f"📊 可用密鑰數量: {len(self.api_keys)} 個")
    
    def reload_groups(self):
        """重新載入所有API密鑰組"""
        self.api_groups = self._load_all_api_groups()
        self.api_keys = self._get_group_keys(self.current_group)
        self.current_index = 0
        print(f"🔄 重新載入API密鑰組: {self.current_group}")
        print(f"📊 可用密鑰數量: {len(self.api_keys)} 個")

# 創建全局實例（預設隨機選擇組）
api_key_manager = MultiGroupAPIKeyManager()

def get_api_key(api_group: Optional[str] = None) -> str:
    """
    獲取API密鑰的便捷函數
    api_group: 指定API密鑰組，如果為None則使用當前組
    """
    if api_group and api_group != api_key_manager.current_group:
        api_key_manager.switch_group(api_group)
    
    return api_key_manager.get_random_key()

def get_api_keys_count(api_group: Optional[str] = None) -> int:
    """
    獲取API密鑰數量的便捷函數
    api_group: 指定API密鑰組，如果為None則使用當前組
    """
    if api_group and api_group != api_key_manager.current_group:
        api_key_manager.switch_group(api_group)
    
    return api_key_manager.get_keys_count()

def get_available_groups() -> List[str]:
    """獲取所有可用的API密鑰組"""
    return api_key_manager.get_all_groups()

def switch_api_group(api_group: str):
    """切換到指定的API密鑰組"""
    api_key_manager.switch_group(api_group)

def reload_api_keys():
    """重新載入API密鑰的便捷函數"""
    api_key_manager.reload_groups()

# 測試函數
def test_api_groups():
    """測試所有API密鑰組"""
    print("🧪 測試所有API密鑰組...")
    print("=" * 80)
    
    groups = get_available_groups()
    print(f"📊 找到 {len(groups)} 個API密鑰組")
    print()
    
    for group in groups:
        info = api_key_manager.get_group_info(group)
        print(f"🔑 {group}:")
        print(f"   📊 密鑰數量: {info['key_count']}")
        
        # 顯示前3個密鑰（隱藏部分內容）
        for i, key in enumerate(info['keys'][:3]):
            masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else key
            print(f"   🔐 密鑰 {i+1}: {masked_key}")
        
        if info['key_count'] > 3:
            print(f"   ... 還有 {info['key_count'] - 3} 個密鑰")
        print()

def test_group_switching():
    """測試組切換功能"""
    print("🔄 測試組切換功能...")
    print("=" * 80)
    
    groups = get_available_groups()
    if len(groups) < 2:
        print("⚠️ 需要至少2個API密鑰組才能測試切換功能")
        return
    
    # 測試切換到每個組
    for group in groups:
        print(f"🧪 切換到 {group}...")
        switch_api_group(group)
        
        # 獲取一個密鑰
        key = get_api_key()
        masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else key
        print(f"   ✅ 獲取密鑰: {masked_key}")
        print(f"   📊 密鑰數量: {get_api_keys_count()}")
        print()

if __name__ == "__main__":
    test_api_groups()
    test_group_switching()