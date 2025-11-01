#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網站導覽工具實現
包含 AI 操作配置、導覽文本生成、導覽步驟 API 和用戶導覽狀態管理
"""

from flask import Blueprint, request, jsonify, session, current_app
from flask_cors import cross_origin
from accessories import refresh_token, mongo
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import jwt

logger = logging.getLogger(__name__)

# ==================== AI 操作配置系統 ====================

class ActionType(str, Enum):
    """操作類型枚舉"""
    NAVIGATE = "navigate"                    # 導航到頁面
    NAVIGATE_WITH_PARAMS = "navigate_with_params"  # 帶參數的導航
    API_CALL = "api_call"                    # API 調用
    CREATE_QUIZ = "create_quiz"              # 創建測驗（特殊處理）

@dataclass
class UIAction:
    """UI 操作配置"""
    id: str                                  # 操作 ID
    name: str                                # 操作名稱
    description: str                         # 操作描述
    action_type: ActionType                 # 操作類型
    route: Optional[str] = None             # 目標路由
    api_endpoint: Optional[str] = None      # API 端點
    api_method: Optional[str] = None         # API 方法
    required_params: Optional[List[str]] = None  # 必需參數
    guide_step: Optional[Dict[str, Any]] = None  # 導覽步驟配置

# ==================== AI 操作配置定義 ====================

AI_ACTIONS: Dict[str, UIAction] = {
    # ============ 測驗相關操作 ============
    "create_university_quiz": UIAction(
        id="create_university_quiz",
        name="創建大學考古題測驗",
        description="根據學校、系所、年度創建考古題測驗",
        action_type=ActionType.CREATE_QUIZ,
        api_endpoint="/quiz/create-quiz",
        api_method="POST",
        required_params=["university", "department", "year"],
        guide_step={
            "title": "創建考古題測驗",
            "content": "系統將根據您選擇的學校、系所和年度創建考古題測驗",
            "position": "bottom",
            "avatar_position": "top-right"
        }
    ),
    
    "create_knowledge_quiz": UIAction(
        id="create_knowledge_quiz",
        name="創建知識點測驗",
        description="根據知識點、難度、題數創建測驗",
        action_type=ActionType.CREATE_QUIZ,
        api_endpoint="/quiz/create-quiz",
        api_method="POST",
        required_params=["knowledge_point", "difficulty", "question_count"],
        guide_step={
            "title": "創建知識點測驗",
            "content": "系統將根據您選擇的知識點、難度和題數創建測驗",
            "position": "bottom",
            "avatar_position": "top-right"
        }
    ),
    
    "navigate_to_quiz_taking": UIAction(
        id="navigate_to_quiz_taking",
        name="導航到測驗頁面",
        description="導航到測驗作答頁面",
        action_type=ActionType.NAVIGATE_WITH_PARAMS,
        route="/dashboard/quiz-taking/:quiz_id",
        required_params=["quiz_id"]
    ),
    
    "navigate_to_quiz_center": UIAction(
        id="navigate_to_quiz_center",
        name="導航到測驗中心",
        description="導航到測驗中心頁面",
        action_type=ActionType.NAVIGATE,
        route="/dashboard/quiz-center",
        guide_step={
            "title": "測驗中心",
            "content": "這裡可以選擇不同類型的測驗進行練習",
            "position": "bottom",
            "avatar_position": "top-right",
            "wait_for_element": True,
            "delay": 1000
        }
    ),
    
    # ============ 課程相關操作 ============
    "navigate_to_courses": UIAction(
        id="navigate_to_courses",
        name="導航到課程頁面",
        description="導航到課程列表頁面",
        action_type=ActionType.NAVIGATE,
        route="/dashboard/courses",
        guide_step={
            "title": "課程中心",
            "content": "這裡可以瀏覽所有可用的課程和教材",
            "position": "bottom",
            "avatar_position": "top-right",
            "wait_for_element": True,
            "delay": 1000
        }
    ),
    
    "view_course_material": UIAction(
        id="view_course_material",
        name="查看課程教材",
        description="查看特定知識點的課程教材",
        action_type=ActionType.NAVIGATE_WITH_PARAMS,
        route="/dashboard/material/:keypoint",
        required_params=["keypoint"],
        guide_step={
            "title": "課程教材",
            "content": "這裡顯示該知識點的詳細教材內容",
            "position": "top",
            "avatar_position": "bottom-right",
            "wait_for_element": True,
            "delay": 1500
        }
    ),
    
    # ============ 學習分析相關操作 ============
    "navigate_to_learning_analytics": UIAction(
        id="navigate_to_learning_analytics",
        name="導航到學習分析頁面",
        description="導航到學習成效分析頁面",
        action_type=ActionType.NAVIGATE,
        route="/dashboard/learning-analytics",
        guide_step={
            "title": "學習成效分析",
            "content": "這裡可以查看您的學習進度、掌握度和學習建議",
            "position": "bottom",
            "avatar_position": "top-right",
            "wait_for_element": True,
            "delay": 1500
        }
    ),
    
    # ============ 新聞相關操作 ============
    "navigate_to_news": UIAction(
        id="navigate_to_news",
        name="導航到科技趨勢頁面",
        description="導航到科技新聞頁面",
        action_type=ActionType.NAVIGATE,
        route="/dashboard/news",
        guide_step={
            "title": "科技趨勢",
            "content": "這裡可以瀏覽最新的科技新聞和趨勢",
            "position": "bottom",
            "avatar_position": "top-right",
            "wait_for_element": True,
            "delay": 1000
        }
    ),
    
    # ============ 錯題相關操作 ============
    "navigate_to_mistake_analysis": UIAction(
        id="navigate_to_mistake_analysis",
        name="導航到錯題統整頁面",
        description="導航到錯題分析頁面",
        action_type=ActionType.NAVIGATE,
        route="/dashboard/mistake-analysis",
        guide_step={
            "title": "錯題統整",
            "content": "這裡可以查看和複習您曾經答錯的題目",
            "position": "bottom",
            "avatar_position": "top-right",
            "wait_for_element": True,
            "delay": 1000
        }
    ),
    
    # ============ AI 導師相關操作 ============
    "navigate_to_ai_tutoring": UIAction(
        id="navigate_to_ai_tutoring",
        name="導航到 AI 導師頁面",
        description="導航到 AI 引導教學頁面",
        action_type=ActionType.NAVIGATE_WITH_PARAMS,
        route="/dashboard/ai-tutoring",
        guide_step={
            "title": "AI 引導教學",
            "content": "這裡可以接受 AI 的引導式教學，幫助理解概念",
            "position": "bottom",
            "avatar_position": "bottom-right",
            "wait_for_element": True,
            "delay": 1200
        }
    ),
    
    # ============ 概覽頁面 ============
    "navigate_to_overview": UIAction(
        id="navigate_to_overview",
        name="導航到概覽頁面",
        description="導航到首頁概覽",
        action_type=ActionType.NAVIGATE,
        route="/dashboard/overview",
        guide_step={
            "title": "系統概覽",
            "content": "這是系統的主頁面，顯示學習統計和快速功能入口",
            "position": "bottom",
            "avatar_position": "top-right",
            "wait_for_element": True,
            "delay": 1000
        }
    )
}

def get_action(action_id: str) -> Optional[UIAction]:
    """根據 ID 獲取操作配置"""
    return AI_ACTIONS.get(action_id)

def get_all_actions() -> Dict[str, UIAction]:
    """獲取所有操作配置"""
    return AI_ACTIONS.copy()

def validate_action_params(action_id: str, params: Dict[str, Any]) -> tuple[bool, Optional[List[str]]]:
    """驗證操作參數是否完整"""
    action = get_action(action_id)
    if not action:
        return False, None
    
    if not action.required_params:
        return True, None
    
    missing = [p for p in action.required_params if p not in params]
    return len(missing) == 0, missing if missing else None

def export_actions_config() -> Dict[str, Any]:
    """導出操作配置"""
    return {
        "version": "1.0.0",
        "actions": [
            {
                "id": action.id,
                "name": action.name,
                "description": action.description,
                "action_type": action.action_type.value,
                "route": action.route,
                "api_endpoint": action.api_endpoint,
                "api_method": action.api_method,
                "required_params": action.required_params,
                "guide_step": action.guide_step
            }
            for action in AI_ACTIONS.values()
        ]
    }

# ==================== 網站導覽功能 ====================

# 創建 Blueprint
guide_bp = Blueprint('guide', __name__)

# ==================== 用戶導覽狀態管理 ====================

def get_user_email_from_token():
    """從 JWT token 獲取用戶 email"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return None
        
        decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return decoded.get('user')
    except:
        return None

class UserGuideService:
    """用戶導覽服務（使用 MongoDB）"""
    
    def get_user_id(self) -> str:
        """獲取用戶 ID"""
        return session.get('user_id', f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    def get_user_guide_status(self) -> Dict[str, Any]:
        """獲取用戶導覽狀態（從 MongoDB）"""
        try:
            user_email = get_user_email_from_token()
            
            if not user_email:
                user_id = session.get('user_id', 'anonymous_user')
                user_record = mongo.db.user.find_one({'user_id': user_id})
            else:
                user_record = mongo.db.user.find_one({'email': user_email})
            
            if user_record:
                return {
                    'user_id': str(user_record.get('_id', 'unknown')),
                    'email': user_record.get('email', ''),
                    'new_user': user_record.get('new_user', True),
                    'guide_completed': user_record.get('guide_completed', False),
                    'last_login': user_record.get('last_login', datetime.now().isoformat()),
                    'guide_completion_date': user_record.get('guide_completion_date')
                }
            else:
                return {
                    'user_id': 'anonymous',
                    'email': user_email or '',
                    'new_user': True,
                    'guide_completed': False,
                    'last_login': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"獲取用戶導覽狀態失敗: {e}")
            return {
                'user_id': 'anonymous',
                'new_user': True,
                'guide_completed': False
            }
    
    def mark_user_as_guided(self) -> Dict[str, Any]:
        """標記用戶已完成導覽（更新 MongoDB）"""
        try:
            user_email = get_user_email_from_token()
            
            if not user_email:
                user_id = session.get('user_id', 'anonymous_user')
                query = {'user_id': user_id}
                identifier = user_id
            else:
                query = {'email': user_email}
                identifier = user_email
            
            update_result = mongo.db.user.update_one(
                query,
                {
                    '$set': {
                        'new_user': False,
                        'guide_completed': True,
                        'guide_completion_date': datetime.now().isoformat(),
                        'last_updated': datetime.now().isoformat()
                    }
                }
            )
            
            if update_result.modified_count > 0:
                logger.info(f"用戶 {identifier} 已完成導覽")
                return {
                    'success': True,
                    'message': '導覽狀態已更新',
                    'user_identifier': identifier,
                    'completion_date': datetime.now().isoformat()
                }
            else:
                logger.warning(f"用戶 {identifier} 導覽狀態更新失敗")
                return {
                    'success': False,
                    'message': '導覽狀態更新失敗 - 用戶不存在或狀態未變更'
                }
        except Exception as e:
            logger.error(f"標記用戶導覽完成失敗: {e}")
            return {
                'success': False,
                'error': f'標記導覽完成失敗: {str(e)}'
            }

# 創建服務實例
user_guide_service = UserGuideService()

def get_website_guide(query: str) -> str:
    """獲取網站導覽信息（供 AI 工具調用）"""
    try:
        # 直接從配置生成導覽信息
        try:
            
            # 收集有導覽步驟的操作
            guide_items = []
            for action in AI_ACTIONS.values():
                if action.guide_step:
                    guide_items.append({
                        'name': action.name,
                        'description': action.guide_step.get('content', action.description)
                    })
            
            if guide_items:
                content = "🗺️ **網站功能導覽**\n\n"
                content += "我來為您介紹主要功能：\n\n"
                
                for i, item in enumerate(guide_items[:6], 1):  # 顯示前 6 個
                    content += f"{i}. **{item['name']}**\n   {item['description']}\n\n"
                
                content += "💡 您想深入了解哪個功能呢？或者可以點擊「網站導覽」按鈕開始互動式導覽！"
                return content
        except Exception as e:
            logger.warning(f"從配置生成導覽失敗，使用備用回應: {e}")
        
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

# generate_guide_steps 函數已移除，導覽步驟配置已移到前端 service

def get_actions_config() -> Dict[str, Any]:
    """獲取所有操作配置"""
    try:
        return {
            "success": True,
            "data": export_actions_config()
        }
    except Exception as e:
        logger.error(f"獲取操作配置失敗: {e}")
        return {
            "success": False,
            "data": {},
            "message": f"獲取配置失敗：{str(e)}"
        }

# ==================== API 路由 ====================

# /guide/steps API 已移除，導覽步驟配置已移到前端 service

@guide_bp.route('/actions-config', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_actions_config_api():
    """獲取 AI 操作配置 API"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 204
        
        result = get_actions_config()
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ 獲取操作配置失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取配置失敗：{str(e)}',
            'data': {}
        }), 500

# ==================== 用戶導覽狀態管理 API ====================

@guide_bp.route('/api/user-guide/status', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_user_guide_status():
    """獲取用戶導覽狀態（對應前端 user-guide-status.service）"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 204
        
        status = user_guide_service.get_user_guide_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"獲取用戶導覽狀態失敗: {e}")
        return jsonify({
            'token': None,
            'error': '獲取用戶狀態失敗',
            'message': str(e)
        }), 500

@guide_bp.route('/api/user-guide/mark-guided', methods=['POST', 'OPTIONS'])
@cross_origin()
def mark_user_as_guided():
    """標記用戶已完成導覽（對應前端 user-guide-status.service）"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 204
        
        result = user_guide_service.mark_user_as_guided()
        
        # 處理 token
        token = None
        auth_header = request.headers.get('Authorization', '').replace('Bearer ', '')
        if auth_header:
            token = auth_header
        
        response_data = result.copy()
        if token:
            response_data['token'] = refresh_token(token)
        
        status_code = 200 if result.get('success') else 400
        return jsonify(response_data), status_code
    except Exception as e:
        logger.error(f"標記用戶導覽完成失敗: {e}")
        return jsonify({
            'token': None,
            'error': '標記導覽完成失敗',
            'message': str(e)
        }), 500
