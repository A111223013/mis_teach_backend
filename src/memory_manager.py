#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記憶管理工具實現
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 簡單的記憶存儲（實際應用中可以使用數據庫）
_user_memories = {}

def manage_user_memory(action: str, user_id: str = "default") -> str:
    """管理用戶記憶"""
    if action == 'view':
        return _get_memory_summary(user_id)
    elif action == 'clear':
        return _clear_user_memory(user_id)
    elif action == 'stats':
        return _get_memory_stats()
    else:
        return f"❓ **未知操作**\n\n支持的操作: view(查看), clear(清除), stats(統計)"

def _get_memory_summary(user_id: str) -> str:
    """獲取用戶記憶摘要"""
    if user_id not in _user_memories or not _user_memories[user_id]:
        return "📚 **對話記憶摘要**\n\n無對話記憶\n\n💡 我們可以開始新的對話！"
    
    memory = _user_memories[user_id]
    
    # 返回最近的幾條記憶
    recent_messages = memory[-min(3, len(memory)):]
    summary = "📚 **對話記憶摘要**\n\n"
    
    for i, msg in enumerate(recent_messages, 1):
        summary += f"{i}. {msg}\n"
    
    summary += "\n💡 這是您最近的對話內容，我會根據這些信息為您提供更貼心的服務！"
    return summary

def _clear_user_memory(user_id: str) -> str:
    """清除用戶記憶"""
    if user_id in _user_memories:
        del _user_memories[user_id]
    
    return f"🧹 **記憶已清除**\n\n您的對話記憶已經清除，我們可以開始新的對話！"

def _get_memory_stats() -> str:
    """獲取記憶統計信息"""
    total_users = len(_user_memories)
    user_memories = {}
    
    for uid, memory in _user_memories.items():
        user_memories[uid] = len(memory) if memory else 0
    
    stats_text = f"📊 **記憶統計**\n\n總用戶數: {total_users}\n\n各用戶記憶條數:\n"
    
    if user_memories:
        for uid, count in user_memories.items():
            stats_text += f"• {uid}: {count} 條\n"
    else:
        stats_text += "• 暫無用戶記憶\n"
    
    return stats_text

def add_user_message(user_id: str, message: str):
    """添加用戶訊息到記憶"""
    if user_id not in _user_memories:
        _user_memories[user_id] = []
    
    _user_memories[user_id].append(f"用戶: {message}")
    
    # 限制記憶條數
    if len(_user_memories[user_id]) > 10:
        _user_memories[user_id] = _user_memories[user_id][-10:]

def add_ai_message(user_id: str, message: str):
    """添加AI回應到記憶"""
    if user_id not in _user_memories:
        _user_memories[user_id] = []
    
    _user_memories[user_id].append(f"助手: {message}")
    
    # 限制記憶條數
    if len(_user_memories[user_id]) > 10:
        _user_memories[user_id] = _user_memories[user_id][-10:]
