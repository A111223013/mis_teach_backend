#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網站AI助手 - 主代理人系統
只負責：1.接收聊天訊息 2.主代理人判斷調用工具 3.回傳訊息
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from typing import Dict, Any

# LangChain 導入
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor

# 創建藍圖
web_ai_bp = Blueprint('web-ai', __name__, url_prefix='/web-ai')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 配置讀取函數 ====================

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tool.api_keys import get_api_key

def get_google_api_key():
    """獲取 Google API key"""
    try:
        return get_api_key()
    except Exception as e:
        logger.error(f"❌ 獲取 API Key 失敗: {e}")
        return None

# ==================== 主代理人類別 ====================

class WebAIAssistant:
    """主代理人 - 只負責判斷調用哪個工具"""
    
    def __init__(self):
        self.llm = None
        self.tools = []
        self.agent_executor = None
        self._init_llm()
        self._init_tools()
        self._init_agent_executor()
    
    def _init_llm(self):
        """初始化LLM"""
        try:
            api_key = get_google_api_key()
            if not api_key:
                raise RuntimeError("無法獲取 Google API Key")
            
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.7,
                max_tokens=2000
            )
            logger.info("✅ LLM 初始化成功")
        except Exception as e:
            logger.error(f"❌ LLM 初始化失敗: {e}")
            raise
    
    def _init_tools(self):
        """初始化工具列表 - 只包含工具引用，不包含實現"""
        try:
            # 工具列表 - 實際實現在其他.py文件中
            self.tools = [
                self._create_website_guide_tool(),
                self._create_learning_progress_tool(),
                self._create_ai_tutor_tool(),
                self._create_memory_tool()
            ]
            logger.info("✅ 工具列表初始化成功")
        except Exception as e:
            logger.error(f"❌ 工具列表初始化失敗: {e}")
            raise
    
    def _create_website_guide_tool(self):
        """創建網站導覽工具引用"""
        from langchain_core.tools import tool
        
        @tool
        def website_guide_tool(query: str) -> str:
            """網站導覽工具，介紹網站功能"""
            try:
                # 調用其他.py文件中的實現
                from .website_guide import get_website_guide
                return get_website_guide(query)
            except ImportError:
                return "❌ 網站導覽系統暫時不可用，請稍後再試。"
            except Exception as e:
                logger.error(f"網站導覽工具執行失敗: {e}")
                return f"網站導覽功能執行失敗：{str(e)}"
        
        return website_guide_tool
    
    def _create_learning_progress_tool(self):
        """創建學習進度工具引用"""
        from langchain_core.tools import tool
        
        @tool
        def learning_progress_tool(query: str) -> str:
            """學習進度工具，查詢用戶學習統計"""
            try:
                # 調用其他.py文件中的實現
                from .dashboard import get_user_progress_data, get_user_quiz_history
                progress_data = get_user_progress_data()
                quiz_history = get_user_quiz_history()
                
                if progress_data and quiz_history:
                    content = f"""📊 **您的學習進度概覽**

**整體表現：**
• 已完成測驗：{progress_data.get('total_quizzes', 0)} 次
• 平均分數：{progress_data.get('average_score', 0)} 分
• 累計學習時間：{progress_data.get('total_study_time', 0)} 小時

**最近測驗記錄：**"""
                    
                    for quiz in quiz_history[:5]:
                        content += f"\n• {quiz.get('date', '')}: {quiz.get('quiz_name', '')} (分數: {quiz.get('score', 0)})"
                    
                    content += "\n\n💡 **建議：** 根據您的表現，建議多練習相關題目來提升成績！"
                    return content
                else:
                    return "❌ 無法獲取學習進度數據，請稍後再試。"
                    
            except ImportError:
                return "❌ 學習進度系統暫時不可用，請稍後再試。"
            except Exception as e:
                logger.error(f"學習進度工具執行失敗: {e}")
                return f"獲取學習進度時發生錯誤：{str(e)}"
        
        return learning_progress_tool
    
    def _create_ai_tutor_tool(self):
        """創建AI導師工具引用"""
        from langchain_core.tools import tool
        
        @tool
        def ai_tutor_tool(question: str, mode: str = "general") -> str:
            """AI導師工具，支援蘇格拉底式教學和一般回答"""
            try:
                # 調用其他.py文件中的實現
                from .rag_sys.rag_ai_role import MultiAITutor, AIResponder
                
                if mode == "socratic":
                    tutor = MultiAITutor()
                    result = tutor.socratic_teaching(question)
                    return result
                else:
                    responder = AIResponder()
                    result = responder.answer_question(question)
                    return result
                    
            except ImportError:
                return "❌ AI導師系統暫時不可用，請稍後再試。"
            except Exception as e:
                logger.error(f"AI導師工具執行失敗: {e}")
                return f"AI導師回應時發生錯誤：{str(e)}"
        
        return ai_tutor_tool
    
    def _create_memory_tool(self):
        """創建記憶管理工具引用"""
        from langchain_core.tools import tool
        
        @tool
        def memory_tool(action: str, user_id: str = "default") -> str:
            """記憶管理工具，用於查看、清除對話記憶"""
            try:
                # 調用其他.py文件中的實現
                from .memory_manager import manage_user_memory
                return manage_user_memory(action, user_id)
            except ImportError:
                return "❌ 記憶管理系統暫時不可用，請稍後再試。"
            except Exception as e:
                logger.error(f"記憶工具執行失敗: {e}")
                return f"記憶工具執行失敗：{str(e)}"
        
        return memory_tool
    
    def _init_agent_executor(self):
        """初始化代理執行器"""
        try:
            system_prompt = """你是MIS教學系統的主代理人，負責理解學生需求並調用最適合的工具。

## 可用的工具
- website_guide_tool: 網站導覽和功能介紹
- learning_progress_tool: 查詢學習進度和成績
- ai_tutor_tool: AI導師，支援蘇格拉底式教學和一般回答
- memory_tool: 記憶管理，查看或清除對話記憶

## 工具選擇邏輯
- 網站導覽/功能介紹 → 使用 website_guide_tool
- 學習進度/成績查詢 → 使用 learning_progress_tool
- 一般學習問題 → 使用 ai_tutor_tool
- 記憶管理 → 使用 memory_tool

根據學生需求自動選擇最適合的工具，回應要親切、專業、有幫助。"""
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad")
            ])
            
            agent = create_tool_calling_agent(self.llm, self.tools, prompt)
            self.agent_executor = AgentExecutor(
                agent=agent, 
                tools=self.tools, 
                verbose=True,
                max_iterations=3
            )
            
            logger.info("✅ 代理執行器初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 代理執行器初始化失敗: {e}")
            raise
    
    def process_message(self, message: str, user_id: str = "default") -> Dict[str, Any]:
        """處理用戶訊息 - 主代理人模式"""
        try:
            # 添加用戶訊息到記憶
            from .memory_manager import add_user_message, add_ai_message
            add_user_message(user_id, message)
            
            # 使用主代理人處理請求
            result = self.agent_executor.invoke({
                "input": message,
                "context": {"user_id": user_id}
            })
            
            # 格式化回應
            response = result.get("output", "抱歉，我無法理解您的請求。")
            
            # 添加AI回應到記憶
            add_ai_message(user_id, response)
            
            return {
                'success': True,
                'content': response,
                'category': 'main_agent',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"主代理人處理失敗: {e}")
            return {
                'success': False,
                'content': '抱歉，處理您的請求時發生錯誤。請稍後再試。',
                'category': 'error',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_assistant_status(self) -> Dict[str, Any]:
        """獲取助手狀態"""
        return {
            'status': 'running',
            'tools_count': len(self.tools),
            'llm_ready': self.llm is not None,
            'agent_ready': self.agent_executor is not None
        }

# ==================== 服務管理 ====================

web_ai_service = None

def get_web_ai_service():
    """獲取網站AI助手服務實例 - 延遲初始化"""
    global web_ai_service
    if web_ai_service is None:
        try:
            web_ai_service = WebAIAssistant()
            logger.info("✅ 網站AI助手服務延遲初始化完成")
        except Exception as e:
            logger.error(f"❌ 網站AI助手服務初始化失敗: {e}")
            raise RuntimeError(f"無法初始化主代理人服務: {e}")
    return web_ai_service

# ==================== API 端點 ====================

@web_ai_bp.route('/chat', methods=['POST'])
def chat():
    """主代理人聊天端點"""
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        user_id = data.get('user_id', 'default')
        
        if not message:
            return jsonify({
                'success': False,
                'error': '訊息不能為空'
            }), 400
        
        # 獲取服務實例並處理訊息
        service = get_web_ai_service()
        result = service.process_message(message, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"聊天處理失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@web_ai_bp.route('/quick-action', methods=['POST'])
def quick_action():
    """快速操作端點"""
    try:
        data = request.get_json() or {}
        action = data.get('action', '')
        
        if not action:
            return jsonify({
                'success': False,
                'error': '操作類型不能為空'
            }), 400
        
        # 根據操作類型創建對應訊息
        action_messages = {
            'guide': '請為我介紹網站的主要功能',
            'progress': '我想查看我的學習進度',
            'tutor': '我有學習問題需要幫助',
            'memory': '請查看我的對話記憶'
        }
        
        message = action_messages.get(action, '您好，我需要幫助')
        
        # 獲取服務實例並處理訊息
        service = get_web_ai_service()
        result = service.process_message(message)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"快速操作處理失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@web_ai_bp.route('/status', methods=['GET'])
def get_status():
    """獲取助手狀態"""
    try:
        service = get_web_ai_service()
        status = service.get_assistant_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"獲取狀態失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@web_ai_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'success': True,
        'service': 'Web AI Assistant - Main Agent',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })
