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

# ==================== 全局變數 ====================

# 延遲初始化的組件
llm = None
tools = []
agent_executor = None

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

# ==================== 初始化函數 ====================

def init_llm():
    """初始化LLM模型"""
    try:
        api_key = config.GEMINI_CONFIG.get('api_key')
        if not api_key:
            raise ValueError("未設置Gemini API Key")
        
        genai.configure(api_key=api_key)
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048,
            convert_system_message_to_human=True
        )
        return llm
    except Exception as e:
        logging.error(f"❌ LLM初始化失敗: {e}")
        raise RuntimeError(f"LLM初始化失敗: {e}")

def init_tools():
    """初始化工具列表 - 只包含工具引用，不包含實現"""
    global tools
    try:
        # 工具列表 - 實際實現在其他.py文件中
        tools = [
            create_website_guide_tool(),
            create_learning_progress_tool(),
            create_ai_tutor_tool(),
            create_memory_tool()
        ]
        logger.info("✅ 工具列表初始化成功")
        return tools
    except Exception as e:
        logger.error(f"❌ 工具列表初始化失敗: {e}")
        raise

def create_website_guide_tool():
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
            return "❌ 網站導覽執行失敗，請稍後再試。"
    
    return website_guide_tool

def create_learning_progress_tool():
    """創建學習進度工具引用"""
    from langchain_core.tools import tool
    
    @tool
    def learning_progress_tool(query: str) -> str:
        """學習進度工具，查詢用戶學習進度"""
        try:
            # 調用其他.py文件中的實現
            from .dashboard import get_user_progress
            return get_user_progress(query)
        except ImportError:
            return "❌ 學習進度系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"學習進度工具執行失敗: {e}")
            return "❌ 學習進度查詢失敗，請稍後再試。"
    
    return learning_progress_tool

def create_ai_tutor_tool():
    """創建AI導師工具引用"""
    from langchain_core.tools import tool
    
    @tool
    def ai_tutor_tool(query: str) -> str:
        """AI導師工具，提供智能教學指導"""
        try:
            # 調用其他.py文件中的實現
            from .rag_sys.rag_ai_role import handle_tutoring_conversation
            return handle_tutoring_conversation("default_session", query, "default_user")
        except ImportError:
            return "❌ AI導師系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"AI導師工具執行失敗: {e}")
            return "❌ AI導師回應失敗，請稍後再試。"
    
    return ai_tutor_tool

def create_memory_tool():
    """創建記憶管理工具引用"""
    from langchain_core.tools import tool
    
    @tool
    def memory_tool(action: str, user_id: str = "default") -> str:
        """記憶管理工具，管理用戶對話記憶"""
        try:
            # 調用其他.py文件中的實現
            from .memory_manager import manage_user_memory
            return manage_user_memory(action, user_id)
        except ImportError:
            return "❌ 記憶管理系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"記憶管理工具執行失敗: {e}")
            return "❌ 記憶管理失敗，請稍後再試。"
    
    return memory_tool

def init_agent_executor():
    """初始化主代理人執行器"""
    global agent_executor
    try:
        # 系統提示詞
        system_prompt = """你是一個智能網站助手，能夠幫助用戶了解網站功能、查詢學習進度、提供AI教學指導，以及管理對話記憶。

你有以下工具可以使用：
1. website_guide_tool - 網站導覽和功能介紹
2. learning_progress_tool - 查詢學習進度和統計
3. ai_tutor_tool - AI智能教學指導
4. memory_tool - 管理對話記憶

請根據用戶的問題，選擇最適合的工具來幫助他們。如果用戶的問題不屬於以上任何類別，請禮貌地引導他們使用適當的功能。

記住：你是一個助手，不是工具本身。請使用工具來幫助用戶，而不是直接回答問題。"""

        # 創建提示詞模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])

        # 創建主代理人
        agent = create_tool_calling_agent(llm, tools, prompt)
        
        # 創建執行器
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True
        )
        
        logger.info("✅ 主代理人執行器初始化成功")
        return agent_executor
        
    except Exception as e:
        logger.error(f"❌ 主代理人執行器初始化失敗: {e}")
        raise

# ==================== 核心處理函數 ====================

def get_web_ai_service():
    """獲取Web AI服務 - 延遲初始化"""
    global llm, tools, agent_executor
    
    if llm is None:
        llm = init_llm()
    if not tools:
        tools = init_tools()
    if agent_executor is None:
        agent_executor = init_agent_executor()
    
    return {
        'llm': llm,
        'tools': tools,
        'agent_executor': agent_executor
    }

def process_message(message: str, user_id: str = "default") -> Dict[str, Any]:
    """處理用戶訊息 - 主代理人模式"""
    try:
        # 添加用戶訊息到記憶
        from .memory_manager import add_user_message, add_ai_message
        add_user_message(user_id, message)
        
        # 獲取服務
        service = get_web_ai_service()
        
        # 使用主代理人處理請求
        result = service['agent_executor'].invoke({
            "input": message,
            "context": {"user_id": user_id}
        })
        
        # 格式化回應
        response = result.get("output", "抱歉，我無法理解您的請求。")
        
        # 添加AI回應到記憶
        add_ai_message(user_id, response)
        
        return {
            'success': True,
            'message': response,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 處理訊息失敗: {e}")
        return {
            'success': False,
            'message': f"抱歉，處理您的訊息時發生錯誤：{str(e)}",
            'timestamp': datetime.now().isoformat()
        }

# ==================== API路由 ====================

@web_ai_bp.route('/chat', methods=['POST'])
def chat():
    """聊天API - 接收用戶訊息並返回AI回應"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': '缺少必要參數'}), 400
        
        message = data['message']
        user_id = data.get('user_id', 'default')
        
        # 處理訊息
        result = process_message(message, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 聊天API錯誤: {e}")
        return jsonify({
            'success': False,
            'error': f'聊天API錯誤：{str(e)}'
        }), 500

@web_ai_bp.route('/quick-action', methods=['POST'])
def quick_action():
    """快速動作API - 處理預定義的快速動作"""
    try:
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'success': False, 'error': '缺少必要參數'}), 400
        
        action = data['action']
        user_id = data.get('user_id', 'default')
        
        # 根據動作類型處理
        if action == 'website_guide':
            from .website_guide import get_website_guide
            response = get_website_guide("網站導覽")
        elif action == 'learning_progress':
            from .dashboard import get_user_progress
            response = get_user_progress("查詢進度")
        else:
            response = "抱歉，我不認識這個動作。"
        
        return jsonify({
            'success': True,
            'message': response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 快速動作API錯誤: {e}")
        return jsonify({
            'success': False,
            'error': f'快速動作API錯誤：{str(e)}'
        }), 500

@web_ai_bp.route('/status', methods=['GET'])
def get_status():
    """狀態檢查API"""
    try:
        service = get_web_ai_service()
        return jsonify({
            'success': True,
            'status': 'ready',
            'llm_ready': service['llm'] is not None,
            'tools_ready': len(service['tools']) > 0,
            'agent_ready': service['agent_executor'] is not None,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ 狀態檢查失敗: {e}")
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@web_ai_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查API"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# ==================== 初始化檢查 ====================

def check_system_ready():
    """檢查系統是否準備就緒"""
    try:
        service = get_web_ai_service()
        logger.info("✅ Web AI 系統初始化完成")
        return True
    except Exception as e:
        logger.error(f"❌ Web AI 系統初始化失敗: {e}")
        return False

# 系統啟動時檢查
if __name__ == "__main__":
    check_system_ready()
