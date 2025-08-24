#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web AI 助理模組 - 整合多種AI工具
"""

from flask import Blueprint, request, jsonify
import logging
import json
from typing import Dict, Any, List
from datetime import datetime
import time
import sys
import os

# LangChain 導入
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from src.memory_manager import add_user_message, add_ai_message

# 本地模組導入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tool.api_keys import get_api_key

# LINE Bot 工具導入
from src.linebot import (
    generate_quiz_question,
    generate_knowledge_point,
    grade_answer,
    provide_tutoring,
    learning_analysis_placeholder,
    goal_setting_placeholder,
    news_exam_info_placeholder,
    calendar_placeholder
)

# 創建藍圖
web_ai_bp = Blueprint('web-ai', __name__, url_prefix='/web-ai')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 全局變數 ====================

# 延遲初始化的組件
llm = None

# ==================== 初始化代理人相關函數 ====================

def get_google_api_key():
    """獲取 Google API key"""
    try:
        return get_api_key()
    except Exception as e:
        logger.error(f"❌ 獲取 API Key 失敗: {e}")
        return None

def init_llm():
    """初始化LLM模型"""
    try:
        api_key = get_google_api_key()
        if not api_key:
            raise ValueError("未設置Gemini API Key")
        
        # 直接使用 API 密鑰初始化
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
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


def create_platform_specific_agent(platform: str = "web"):
    """根據平台創建對應的主代理人"""
    global llm  # 移到函數開頭
    
    try:
        # 根據平台獲取對應工具集
        platform_tools = get_platform_specific_tools(platform)
        
        # 根據平台獲取對應的系統提示詞
        platform_system_prompt = get_platform_specific_system_prompt(platform)
        
        # 獲取 LLM 模型
        if llm is None:
            llm = init_llm()
        
        # 創建平台特定的提示詞模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", platform_system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        
        # 創建平台特定的主代理人
        platform_agent = create_tool_calling_agent(llm, platform_tools, prompt)
        
        # 創建平台特定的執行器
        platform_executor = AgentExecutor(
            agent=platform_agent,
            tools=platform_tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=False,
            max_iterations=3 if platform == "linebot" else 1  # LINE Bot 需要更多迭代
        )
        
        logger.info(f"✅ {platform} 平台主代理人創建成功")
        return platform_executor
        
    except Exception as e:
        logger.error(f"❌ 創建 {platform} 平台主代理人失敗: {e}")
        raise

# ==================== 共通主要函數 ====================

def get_platform_specific_tools(platform: str = "web"):
    """根據平台獲取對應的工具集"""
    if platform == "linebot":
        # LINE Bot 專用工具 - 從 linebot.py 導入邏輯，在這裡包裝成 tool
        return [
            create_linebot_quiz_generator_tool(),
            create_linebot_knowledge_tool(),
            create_linebot_grade_tool(),
            create_linebot_tutor_tool(),
            create_linebot_learning_analysis_tool(),
            create_linebot_goal_setting_tool(),
            create_linebot_news_exam_tool(),
            create_linebot_calendar_tool(),
            create_memory_tool()
        ]
    else:
        # 網站完整工具集
        return [
            create_website_guide_tool(),
            create_learning_progress_tool(),
            create_ai_tutor_tool(),
            create_memory_tool(),
            create_quiz_generator_tool()
        ]

def create_quiz_generator_tool():
    """創建考卷生成工具引用 - 邏輯實現在 quiz_generator.py"""
    from langchain_core.tools import tool
    
    @tool
    def quiz_generator_tool(requirements: str) -> str:
        """考卷生成工具，根據用戶需求自動創建考卷並保存到數據庫"""
        try:
            # 調用 quiz_generator.py 中的實現
            from src.quiz_generator import create_quiz_generator_tool as create_quiz_tool
            quiz_tool = create_quiz_tool()
            return quiz_tool.invoke(requirements)
        except ImportError:
            return "❌ 考卷生成系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"考卷生成工具執行失敗: {e}")
            return f"❌ 考卷生成失敗，請稍後再試。錯誤: {str(e)}"
    
    return quiz_generator_tool

def get_platform_specific_system_prompt(platform: str = "web") -> str:
    """根據平台獲取對應的系統提示詞"""
    if platform == "linebot":
        return """你是一個智能 LINE Bot 助手，專門為 LINE 用戶提供輕量化的學習服務。

你有以下工具可以使用：
1. linebot_quiz_generator_tool - AI測驗生成（選擇題/知識問答題）
2. linebot_knowledge_tool - 隨機知識點
3. linebot_grade_tool - 答案批改和解釋
4. linebot_tutor_tool - AI導師教學指導
5. linebot_learning_analysis_tool - 學習分析（開發中）
6. linebot_goal_setting_tool - 目標設定（開發中）
7. linebot_news_exam_tool - 最新消息/考試資訊（開發中）
8. linebot_calendar_tool - 行事曆（開發中）
9. memory_tool - 記憶管理

重要：記憶管理是核心功能！
- 使用 memory_tool('view', user_id) 查看對話歷史
- 每次對話都會自動記錄到記憶中
- 測驗流程中必須維護上下文連貫性

測驗流程和記憶管理：
1. 用戶選擇測驗類型（選擇題/知識問答題）
2. 選擇知識點或隨機
3. 系統生成題目（不顯示答案）
4. 用戶答題（A、B、C、D 或文字答案）
5. 系統使用 linebot_grade_tool 進行批改
6. 如用戶有疑問，使用 linebot_tutor_tool 請求導師指導

測驗上下文維護：
- LINE Bot 會自動提供對話上下文，你不需要主動尋找記憶
- 當收到包含上下文的測驗批改請求時，直接進行智能批改
- 如果沒有上下文，正常回應

工具使用說明：
- linebot_grade_tool(answer, correct_answer="", question="") - 可以只提供答案，系統會自動處理
- 當用戶輸入 A、B、C、D 時，LINE Bot 會自動提供上下文

開發中功能：
- 學習分析、目標設定、最新消息/考試資訊、行事曆等功能目前顯示「開發中」訊息
- 這些功能會提供功能預覽和說明

請根據用戶的問題，選擇最適合的工具來幫助他們。這些工具會提供簡潔、實用的回應，適合在 LINE 聊天中顯示簡單明瞭不要長篇大論。

重要：當使用工具時，請直接返回工具的完整回應，不要重新格式化或摘要。

記住：你是一個助手，不是工具本身。請使用工具來幫助用戶，而不是直接回答問題。"""
    else:
        return """你是一個智能網站助手，能夠幫助用戶了解網站功能、查詢學習進度、提供AI教學指導，以及創建考卷。

你有以下工具可以使用：
1. website_guide_tool - 網站導覽和功能介紹
2. learning_progress_tool - 查詢學習進度和統計
3. ai_tutor_tool - AI智能教學指導
4. quiz_generator_tool - 考卷生成和測驗

請根據用戶的問題，選擇最適合的工具來幫助他們。如果用戶的問題不屬於以上任何類別，請禮貌地引導他們使用適當的功能。

關於考卷生成功能：
- 當用戶要求創建考卷、測驗或題目時，使用 quiz_generator_tool
- 支持知識點測驗和考古題兩種類型
- 可以指定知識點、題型、難度、題目數量等參數
- 支持自然語言描述需求，如"幫我創建20題計算機概論的單選題"

重要：當使用工具時，請直接返回工具的完整回應，不要重新格式化或摘要。特別是考卷生成工具的回應包含重要的JSON數據，必須完整保留。

記住：你是一個助手，不是工具本身。請使用工具來幫助用戶，而不是直接回答問題。"""

def process_message(message: str, user_id: str = "default", platform: str = "web") -> Dict[str, Any]:
    """處理用戶訊息 - 主代理人模式，支援平台區分"""
    try:
        # 添加用戶訊息到記憶
        add_user_message(user_id, message)
        
        # 根據平台創建對應的主代理人
        platform_executor = create_platform_specific_agent(platform)
        
        # 使用平台特定的主代理人處理
        result = platform_executor.invoke({
            "input": message,
            "context": {"user_id": user_id, "platform": platform}
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
            'error': f'處理訊息失敗：{str(e)}',
            'timestamp': datetime.now().isoformat()
        }

# ==================== 網站相關工具函數 ====================

def create_website_guide_tool():
    """創建網站導覽工具引用"""
    from langchain_core.tools import tool
    
    @tool
    def website_guide_tool(query: str) -> str:
        """網站導覽工具，介紹網站功能"""
        try:
            # 調用其他.py文件中的實現
            from src.website_guide import get_website_guide
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
            from src.dashboard import get_user_progress
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
            from src.rag_sys.rag_ai_role import handle_tutoring_conversation
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
            from src.memory_manager import manage_user_memory
            return manage_user_memory(action, user_id)
        except ImportError:
            return "❌ 記憶管理系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"記憶管理工具執行失敗: {e}")
            return "❌ 記憶管理失敗，請稍後再試。"
    
    return memory_tool

# ==================== LINE Bot 相關工具函數 ====================

def create_linebot_quiz_generator_tool():
    """創建 LINE Bot 測驗生成工具 - 調用 linebot.py 的邏輯"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_quiz_generator_tool(requirements: str) -> str:
        """LINE Bot 測驗生成工具"""
        return generate_quiz_question(requirements)
    
    return linebot_quiz_generator_tool

def create_linebot_knowledge_tool():
    """創建 LINE Bot 知識點工具 - 調用 linebot.py 的邏輯"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_knowledge_tool(query: str) -> str:
        """LINE Bot 知識點工具"""
        return generate_knowledge_point(query)
    
    return linebot_knowledge_tool

def create_linebot_grade_tool():
    """創建 LINE Bot 批改工具 - 調用 linebot.py 的邏輯"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_grade_tool(answer: str, correct_answer: str = "", question: str = "") -> str:
        """LINE Bot 批改工具 - 可以只提供答案，系統會自動從記憶中獲取題目信息"""
        # 如果只提供了答案，嘗試從記憶中獲取題目信息
        if answer and not question:
            try:
                from src.memory_manager import _user_memories
                # 這裡需要根據實際情況調整，暫時返回提示信息
                return f"正在批改答案：{answer}。請確保題目信息完整。"
            except:
                return f"正在批改答案：{answer}。請確保題目信息完整。"
        
        return grade_answer(answer, correct_answer, question)
    
    return linebot_grade_tool

def create_linebot_tutor_tool():
    """創建 LINE Bot 導師工具 - 調用 linebot.py 的邏輯"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_tutor_tool(question: str, user_answer: str, correct_answer: str) -> str:
        """LINE Bot 導師工具"""
        return provide_tutoring(question, user_answer, correct_answer)
    
    return linebot_tutor_tool

def create_linebot_learning_analysis_tool():
    """創建 LINE Bot 學習分析工具 - 開發中"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_learning_analysis_tool(query: str = "") -> str:
        """LINE Bot 學習分析工具 - 開發中"""
        return learning_analysis_placeholder()
    
    return linebot_learning_analysis_tool

def create_linebot_goal_setting_tool():
    """創建 LINE Bot 目標設定工具 - 開發中"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_goal_setting_tool(query: str = "") -> str:
        """LINE Bot 目標設定工具 - 開發中"""
        return goal_setting_placeholder()
    
    return linebot_goal_setting_tool

def create_linebot_news_exam_tool():
    """創建 LINE Bot 最新消息/考試資訊工具 - 開發中"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_news_exam_tool(query: str = "") -> str:
        """LINE Bot 最新消息/考試資訊工具 - 開發中"""
        return news_exam_info_placeholder()
    
    return linebot_news_exam_tool

def create_linebot_calendar_tool():
    """創建 LINE Bot 行事曆工具 - 開發中"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_calendar_tool(query: str = "") -> str:
        """LINE Bot 行事曆工具 - 開發中"""
        return calendar_placeholder()
    
    return linebot_calendar_tool

def _clean_json_string(json_str: str) -> str:
    """清理JSON字符串，處理轉義字符問題"""
    try:
        import re
        # 基本清理
        cleaned = json_str.replace('\\n', '\n').replace('\\"', '"')
        
        # 處理其他轉義字符 - 修復正則表達式
        try:
            cleaned = re.sub(r'\\([^"\\/bfnrt])', r'\1', cleaned)
        except re.error:
            # 如果正則表達式失敗，使用簡單替換
            cleaned = cleaned.replace('\\\\', '\\')
        
        # 處理多餘的反斜線
        try:
            cleaned = re.sub(r'\\{2,}', '\\', cleaned)
        except re.error:
            # 如果正則表達式失敗，使用簡單替換
            while '\\\\' in cleaned:
                cleaned = cleaned.replace('\\\\', '\\')
        
        # 處理不完整的轉義序列
        try:
            cleaned = re.sub(r'\\$', '', cleaned)
        except re.error:
            # 如果正則表達式失敗，使用簡單替換
            if cleaned.endswith('\\'):
                cleaned = cleaned[:-1]
        
        return cleaned
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"JSON清理失敗: {e}")
        return json_str

def _fix_incomplete_json(json_str: str) -> str:
    """嘗試修復不完整的JSON字符串"""
    try:
        # 基本清理
        cleaned = json_str.strip()
        
        # 嘗試找到最後一個完整的對象
        brace_count = 0
        end_pos = -1
        
        for i, char in enumerate(cleaned):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > 0:
            # 提取完整的JSON部分
            complete_json = cleaned[:end_pos]
            logger.info(f"修復JSON，提取完整部分: {complete_json[:100]}...")
            return complete_json
        else:
            # 如果無法修復，返回原始字符串
            return json_str
            
    except Exception as e:
        logger.warning(f"JSON修復失敗: {e}")
        return json_str

# ==================== API路由 ====================

@web_ai_bp.route('/chat', methods=['POST'])
def chat():
    """聊天API - 接收用戶訊息並返回AI回應，支援平台區分"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': '缺少必要參數'}), 400
        
        message = data['message']
        user_id = data.get('user_id', 'default')
        platform = data.get('platform', 'web')  # 新增平台參數
        
        # 處理訊息
        result = process_message(message, user_id, platform)
        
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

