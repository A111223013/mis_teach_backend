"""
用戶導覽系統 API
"""

from flask import Blueprint, request, jsonify, session
import logging
from datetime import datetime
from typing import Dict, Any
import requests

# 創建藍圖
user_guide_bp = Blueprint('user_guide', __name__, url_prefix='/user-guide')

# 設置日誌
logger = logging.getLogger(__name__)

# 模擬用戶數據庫（實際應用中應該使用 MongoDB）
USER_DATABASE = {}

class UserGuideService:
    """用戶導覽服務"""
    
    def __init__(self):
        self.n8n_webhook_url = "http://localhost:5678/webhook-test/detailed-guide"
    
    def get_user_id(self) -> str:
        """獲取用戶 ID"""
        return session.get('user_id', f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    def is_new_user(self, user_id: str) -> bool:
        """檢查是否為新用戶"""
        user_data = USER_DATABASE.get(user_id, {})
        return user_data.get('new_user', True)
    
    def mark_user_as_guided(self, user_id: str) -> None:
        """標記用戶已完成導覽"""
        if user_id not in USER_DATABASE:
            USER_DATABASE[user_id] = {}
        USER_DATABASE[user_id]['new_user'] = False
        USER_DATABASE[user_id]['guide_completed_at'] = datetime.now().isoformat()
        logger.info(f"用戶 {user_id} 已完成導覽")
    
    def trigger_n8n_workflow(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """觸發 n8n 工作流"""
        try:
            response = requests.post(
                self.n8n_webhook_url,
                json=user_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"n8n webhook 調用失敗: {response.status_code}")
                return self._get_fallback_guide_steps()
                
        except Exception as e:
            logger.error(f"調用 n8n webhook 時發生錯誤: {e}")
            return self._get_fallback_guide_steps()
    
    def _get_fallback_guide_steps(self) -> Dict[str, Any]:
        """備用導覽步驟（當 n8n 不可用時）"""
        return {
            "success": True,
            "steps": [
                {
                    "id": "welcome",
                    "target": "body",
                    "title": "歡迎來到 MIS 教學系統！",
                    "content": "讓我為您介紹這個智能教學平台的主要功能。",
                    "position": "bottom",
                    "action": "none",
                    "nextDelay": 3000
                },
                {
                    "id": "dashboard",
                    "target": "[routerLink='/dashboard']",
                    "title": "儀表板",
                    "content": "這裡是您的學習中心，可以查看學習進度和統計資料。",
                    "position": "bottom",
                    "action": "click",
                    "nextDelay": 2000
                },
                {
                    "id": "quiz-demo",
                    "target": "[routerLink='/dashboard/quiz-demo']",
                    "title": "測驗練習",
                    "content": "點擊這裡開始練習測驗，測試您的學習成果。",
                    "position": "right",
                    "action": "hover",
                    "nextDelay": 3000
                },
                {
                    "id": "ai-chat",
                    "target": "[routerLink='/dashboard/ai-chat']",
                    "title": "AI 智能助理",
                    "content": "與 AI 助理對話，獲得學習指導和問題解答。",
                    "position": "right",
                    "action": "hover",
                    "nextDelay": 3000
                },
                {
                    "id": "profile",
                    "target": ".avatar, .user-avatar",
                    "title": "個人資料",
                    "content": "點擊頭像可以查看和編輯您的個人資料。",
                    "position": "left",
                    "action": "hover",
                    "nextDelay": 2000
                },
                {
                    "id": "complete",
                    "target": "body",
                    "title": "導覽完成！",
                    "content": "您已經了解了系統的主要功能。現在可以開始您的學習之旅了！",
                    "position": "bottom",
                    "action": "none",
                    "nextDelay": 3000
                }
            ],
            "message": "導覽步驟已生成"
        }

# 創建服務實例
user_guide_service = UserGuideService()

@user_guide_bp.route('/check-new-user', methods=['GET'])
def check_new_user():
    """檢查用戶是否為新用戶"""
    try:
        user_id = user_guide_service.get_user_id()
        is_new = user_guide_service.is_new_user(user_id)
        
        return jsonify({
            'success': True,
            'is_new_user': is_new,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"檢查新用戶狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_guide_bp.route('/trigger-guide', methods=['POST'])
def trigger_guide():
    """觸發導覽工作流"""
    try:
        data = request.get_json() or {}
        user_id = user_guide_service.get_user_id()
        
        # 準備發送給 n8n 的數據
        user_data = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'page': data.get('page', '/dashboard'),
            'user_agent': request.headers.get('User-Agent', ''),
            'ip_address': request.remote_addr,
            'screen_size': data.get('screen_size', {}),
            'language': data.get('language', 'zh-TW')
        }
        
        # 調用 n8n 工作流
        result = user_guide_service.trigger_n8n_workflow(user_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"觸發導覽時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_guide_bp.route('/mark-guided', methods=['POST'])
def mark_guided():
    """標記用戶已完成導覽"""
    try:
        user_id = user_guide_service.get_user_id()
        user_guide_service.mark_user_as_guided(user_id)
        
        return jsonify({
            'success': True,
            'message': '用戶導覽狀態已更新'
        })
        
    except Exception as e:
        logger.error(f"更新用戶導覽狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_guide_bp.route('/reset-user', methods=['POST'])
def reset_user():
    """重置用戶狀態（用於測試）"""
    try:
        user_id = user_guide_service.get_user_id()
        if user_id in USER_DATABASE:
            USER_DATABASE[user_id]['new_user'] = True
            
        return jsonify({
            'success': True,
            'message': '用戶狀態已重置為新用戶'
        })
        
    except Exception as e:
        logger.error(f"重置用戶狀態時發生錯誤: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_guide_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'success': True,
        'service': 'User Guide API',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })
