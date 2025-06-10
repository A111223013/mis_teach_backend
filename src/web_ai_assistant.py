"""
Web AI 助手 API
專門處理網站導覽、學習進度、學習計畫等功能
"""

from flask import Blueprint, request, jsonify, session
import logging
from datetime import datetime
from typing import Dict, Any, List
import requests
import json

# 創建藍圖
web_ai_bp = Blueprint('web_ai', __name__, url_prefix='/web-ai')

# 設置日誌
logger = logging.getLogger(__name__)

class WebAiAssistant:
    """Web AI 助手服務"""
    
    def __init__(self):
        self.n8n_webhook_url = "http://localhost:5678/webhook/game-guide"
        self.gemini_api_url = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"
        self.gemini_api_key = "YOUR_GEMINI_API_KEY"  # 應該從環境變量獲取
        
        # 模擬用戶數據
        self.user_progress_data = {
            "completed_quizzes": 5,
            "average_score": 85,
            "study_hours": 12,
            "strong_subjects": ["資料庫管理"],
            "weak_subjects": ["系統分析"],
            "recent_activities": [
                {"date": "2024-12-01", "activity": "完成測驗", "score": 90},
                {"date": "2024-11-30", "activity": "AI 導師對話", "duration": "30分鐘"},
                {"date": "2024-11-29", "activity": "完成測驗", "score": 80}
            ]
        }
    
    def get_user_id(self) -> str:
        """獲取用戶 ID"""
        return session.get('user_id', f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    def process_message(self, message: str, message_type: str = 'general') -> Dict[str, Any]:
        """處理用戶訊息"""
        try:
            user_id = self.get_user_id()
            
            # 根據訊息類型處理
            if message_type == 'guide' or self._is_guide_related(message):
                return self._handle_guide_request(message, user_id)
            elif message_type == 'progress' or self._is_progress_related(message):
                return self._handle_progress_request(message, user_id)
            elif message_type == 'plan' or self._is_plan_related(message):
                return self._handle_plan_request(message, user_id)
            else:
                return self._handle_general_request(message, user_id)
                
        except Exception as e:
            logger.error(f"處理訊息時發生錯誤: {e}")
            return {
                'success': False,
                'content': '抱歉，處理您的請求時發生錯誤。請稍後再試。',
                'category': 'error'
            }
    
    def _is_guide_related(self, message: str) -> bool:
        """判斷是否為導覽相關訊息"""
        guide_keywords = ['導覽', '介紹', '功能', '怎麼用', '如何', '教學', '說明']
        return any(keyword in message for keyword in guide_keywords)
    
    def _is_progress_related(self, message: str) -> bool:
        """判斷是否為進度相關訊息"""
        progress_keywords = ['進度', '成績', '分數', '統計', '表現', '結果']
        return any(keyword in message for keyword in progress_keywords)
    
    def _is_plan_related(self, message: str) -> bool:
        """判斷是否為計畫相關訊息"""
        plan_keywords = ['計畫', '規劃', '建議', '安排', '學習路徑', '目標']
        return any(keyword in message for keyword in plan_keywords)
    
    def _handle_guide_request(self, message: str, user_id: str) -> Dict[str, Any]:
        """處理導覽請求"""
        try:
            # 調用 n8n 工作流
            response = requests.post(
                self.n8n_webhook_url,
                json={
                    'user_id': user_id,
                    'message': message,
                    'type': 'guide',
                    'timestamp': datetime.now().isoformat()
                },
                timeout=10
            )
            
            if response.status_code == 200:
                n8n_data = response.json()
                if n8n_data.get('success'):
                    return {
                        'success': True,
                        'content': self._format_guide_response(n8n_data),
                        'category': 'guide'
                    }
        except Exception as e:
            logger.error(f"調用 n8n 導覽工作流失敗: {e}")
        
        # 備用回應
        return {
            'success': True,
            'content': self._get_default_guide_response(),
            'category': 'guide'
        }
    
    def _handle_progress_request(self, message: str, user_id: str) -> Dict[str, Any]:
        """處理進度請求"""
        progress = self.user_progress_data
        
        content = f"""📊 **您的學習進度概覽**

**整體表現：**
• 已完成測驗：{progress['completed_quizzes']} 次
• 平均分數：{progress['average_score']} 分
• 累計學習時間：{progress['study_hours']} 小時

**科目表現：**
• 💪 強項科目：{', '.join(progress['strong_subjects'])}
• 📈 需要加強：{', '.join(progress['weak_subjects'])}

**最近活動：**"""
        
        for activity in progress['recent_activities'][:3]:
            content += f"\n• {activity['date']}: {activity['activity']}"
            if 'score' in activity:
                content += f" (分數: {activity['score']})"
            elif 'duration' in activity:
                content += f" ({activity['duration']})"
        
        content += "\n\n💡 **建議：** 多練習系統分析相關題目，可以提升整體表現！"
        
        return {
            'success': True,
            'content': content,
            'category': 'progress'
        }
    
    def _handle_plan_request(self, message: str, user_id: str) -> Dict[str, Any]:
        """處理計畫請求"""
        content = """📅 **個人化學習計畫建議**

**本週學習目標：**
• 完成 3 次測驗練習
• 複習系統分析章節
• 與 AI 導師討論疑難問題
• 加強弱項科目練習

**詳細學習路徑：**
1. **基礎複習** (2天)
   - 重點複習系統分析概念
   - 完成相關練習題

2. **實作練習** (3天)
   - 進行模擬測驗
   - 分析錯誤題目

3. **綜合評估** (2天)
   - 完成綜合測驗
   - 檢視學習成果

**每日建議時間：** 1-2 小時
**推薦學習方式：** 理論學習 + 實作練習 + AI 導師指導

需要我為您制定更詳細的學習計畫嗎？"""
        
        return {
            'success': True,
            'content': content,
            'category': 'plan'
        }
    
    def _handle_general_request(self, message: str, user_id: str) -> Dict[str, Any]:
        """處理一般請求"""
        content = """我是您的網站助手，專門協助您使用本學習平台。我可以幫助您：

🗺️ **網站導覽**
• 介紹各項功能和使用方法
• 引導您快速上手

📊 **學習進度**
• 查看測驗成績和統計
• 分析學習表現

📅 **學習規劃**
• 制定個人學習計畫
• 提供學習建議

❓ **使用協助**
• 解答操作問題
• 提供技術支援

請告訴我您需要什麼具體幫助？"""
        
        return {
            'success': True,
            'content': content,
            'category': 'general'
        }
    
    def _format_guide_response(self, n8n_data: Dict[str, Any]) -> str:
        """格式化導覽回應"""
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
        
        return self._get_default_guide_response()
    
    def _get_default_guide_response(self) -> str:
        """獲取預設導覽回應"""
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

# 創建服務實例
web_ai_service = WebAiAssistant()

@web_ai_bp.route('/chat', methods=['POST'])
def chat():
    """Web AI 助手聊天端點"""
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        message_type = data.get('type', 'general')
        
        if not message:
            return jsonify({
                'success': False,
                'error': '訊息不能為空'
            }), 400
        
        # 處理訊息
        result = web_ai_service.process_message(message, message_type)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Web AI 聊天處理失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'content': '抱歉，處理您的請求時發生錯誤。'
        }), 500

@web_ai_bp.route('/quick-action', methods=['POST'])
def quick_action():
    """快速操作端點"""
    try:
        data = request.get_json() or {}
        action = data.get('action', '')
        
        action_messages = {
            'guide': '請為我介紹網站的主要功能',
            'progress': '我想查看我的學習進度',
            'plan': '請為我制定學習計畫',
            'faq': '有什麼常見問題嗎？'
        }
        
        message = action_messages.get(action, '您好，我需要幫助')
        result = web_ai_service.process_message(message, action)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"快速操作處理失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@web_ai_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'success': True,
        'service': 'Web AI Assistant',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })
