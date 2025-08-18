#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網站導覽工具實現
"""

import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

def get_website_guide(query: str) -> str:
    """獲取網站導覽信息"""
    try:
        # 嘗試調用 n8n 工作流
        try:
            response = requests.post(
                "http://localhost:5678/webhook/game-guide",
                json={
                    'user_id': 'web_assistant',
                    'message': query,
                    'type': 'guide',
                    'timestamp': datetime.now().isoformat()
                },
                timeout=5
            )
            
            if response.status_code == 200:
                n8n_data = response.json()
                if n8n_data.get('success'):
                    # 格式化 n8n 回應
                    steps = n8n_data.get('steps', [])
                    if steps:
                        content = "🗺️ **網站功能導覽**\n\n"
                        content += "我來為您介紹主要功能：\n\n"
                        
                        for i, step in enumerate(steps[:4], 1):
                            title = step.get('title', f'功能 {i}')
                            description = step.get('content', '功能說明')
                            content += f"{i}. **{title}**\n   {description}\n\n"
                        
                        content += "💡 您想深入了解哪個功能呢？"
                        return content
        except:
            pass
        
        # 備用回應 - 原本網站助手的預設回應
        return """🗺️ **網站功能介紹**

歡迎使用 MIS 教學系統！讓我為您介紹主要功能：

📝 **測驗系統**
• 提供多種題型練習
• 即時評分和詳細解析
• 錯題重點複習

🤖 **AI 導師**
• 專業學習指導
• 個人化問題解答
• 智能教學對話

📊 **學習分析**
• 詳細進度追蹤
• 成績統計分析
• 學習建議推薦

⚙️ **個人設定**
• 自定義學習偏好
• 個人資料管理
• 系統設定調整

您想了解哪個功能的詳細使用方法呢？"""
        
    except Exception as e:
        logger.error(f"網站導覽工具執行失敗: {e}")
        return "抱歉，網站導覽功能暫時不可用。"
