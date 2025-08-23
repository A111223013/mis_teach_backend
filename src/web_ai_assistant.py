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

def init_tools():
    """初始化工具列表 - 只包含工具引用，不包含實現"""
    global tools
    try:
        # 工具列表 - 實際實現在其他.py文件中
        tools = [
            create_website_guide_tool(),
            create_learning_progress_tool(),
            create_ai_tutor_tool(),
            create_memory_tool(),
            create_quiz_generator_tool()
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

def create_quiz_generator_tool():
    """創建考卷生成工具引用"""
    from langchain_core.tools import tool
    
    @tool
    def quiz_generator_tool(requirements: str) -> str:
        """考卷生成工具，根據用戶需求自動創建考卷並保存到數據庫"""
        try:
            # 調用其他.py文件中的實現
            from src.quiz_generator import generate_and_save_quiz_by_ai, get_available_topics, get_available_schools, get_available_years, get_available_departments
            
            # 解析用戶需求
            import json
            try:
                # 嘗試解析JSON格式的需求
                req_dict = json.loads(requirements)
            except:
                # 如果不是JSON，嘗試從文本中提取信息
                req_dict = _parse_quiz_requirements(requirements)
            
            # 生成考卷並保存到數據庫
            result = generate_and_save_quiz_by_ai(req_dict)
            
            if result['success']:
                quiz_info = result['quiz_info']
                questions = result['questions']
                database_ids = result.get('database_ids', [])
                
                # 返回可跳轉的考卷數據
                quiz_data = {
                    'quiz_id': f"ai_generated_{int(time.time())}",
                    'template_id': f"ai_template_{int(time.time())}",
                    'questions': questions,
                    'time_limit': quiz_info['time_limit'],
                    'quiz_info': quiz_info,
                    'database_ids': database_ids  # 添加數據庫ID
                }
                
                response = f"✅ 考卷生成成功！\n\n"
                response += f"📝 考卷標題: {quiz_info['title']}\n"
                response += f"📚 主題: {quiz_info['topic']}\n"
                response += f"📊 難度: {quiz_info['difficulty']}\n"
                response += f"🔢 題目數量: {quiz_info['question_count']}\n"
                response += f"⏱️ 時間限制: {quiz_info['time_limit']}分鐘\n"
                response += f"💯 總分: {quiz_info['total_score']}分\n\n"
                
                if database_ids:
                    response += f"💾 已保存到數據庫，題目ID: {', '.join(database_ids[:3])}{'...' if len(database_ids) > 3 else ''}\n\n"
                
                response += "📋 題目預覽:\n"
                for i, q in enumerate(questions[:3]):  # 只顯示前3題
                    response += f"{i+1}. {q['question_text'][:100]}...\n"
                
                if len(questions) > 3:
                    response += f"... 還有 {len(questions)-3} 題\n\n"
                
                response += "🚀 **點擊下方按鈕開始測驗！**\n\n"
                response += "```json\n"
                response += json.dumps(quiz_data, ensure_ascii=False, indent=2)
                response += "\n```\n\n"
                
                response += "💡 提示：點擊「開始測驗」按鈕即可開始答題！"
                
                return response
            else:
                return f"❌ 考卷生成失敗: {result.get('error', '未知錯誤')}"
                
        except ImportError:
            return "❌ 考卷生成系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"考卷生成工具執行失敗: {e}")
            return f"❌ 考卷生成失敗，請稍後再試。錯誤: {str(e)}"
    
    return quiz_generator_tool

def _parse_quiz_requirements(text: str) -> dict:
    """從文本中解析考卷需求"""
    requirements = {
        'topic': '計算機概論',
        'question_types': ['single-choice', 'multiple-choice'],
        'difficulty': 'medium',
        'question_count': 20,
        'exam_type': 'knowledge'
    }
    
    text_lower = text.lower()
    
    # 檢測知識點
    topics = ['計算機概論', '程式設計', '資料結構', '演算法', '作業系統', '資料庫', '網路', '軟體工程', '人工智慧', '機器學習']
    for topic in topics:
        if topic in text:
            requirements['topic'] = topic
            break
    
    # 檢測題型
    if '單選' in text or '選擇' in text:
        requirements['question_types'] = ['single-choice']
    elif '多選' in text:
        requirements['question_types'] = ['multiple-choice']
    elif '填空' in text:
        requirements['question_types'] = ['fill-in-the-blank']
    elif '是非' in text or '判斷' in text:
        requirements['question_types'] = ['true-false']
    elif '簡答' in text:
        requirements['question_types'] = ['short-answer']
    elif '申論' in text:
        requirements['question_types'] = ['long-answer']
    
    # 檢測難度
    if '簡單' in text or 'easy' in text_lower:
        requirements['difficulty'] = 'easy'
    elif '困難' in text or 'hard' in text_lower:
        requirements['difficulty'] = 'hard'
    
    # 檢測題目數量
    import re
    count_match = re.search(r'(\d+)題', text)
    if count_match:
        requirements['question_count'] = int(count_match.group(1))
    
    # 檢測考古題
    schools = ['台大', '清大', '交大', '成大', '政大', '中央', '中興', '中山', '中正', '台科大']
    for school in schools:
        if school in text:
            requirements['exam_type'] = 'pastexam'
            requirements['school'] = school
            break
    
    # 檢測年份
    year_match = re.search(r'(\d{4})年', text)
    if year_match:
        requirements['year'] = year_match.group(1)
    
    return requirements

def _is_quiz_generation_request(text: str) -> bool:
    """檢查是否為考卷生成請求"""
    quiz_keywords = [
        '創建', '生成', '建立', '製作', '產生',
        '考卷', '測驗', '題目', '考試', '練習',
        '單選題', '多選題', '填空題', '是非題', '簡答題', '申論題'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in quiz_keywords)

def init_agent_executor():
    """初始化主代理人執行器"""
    global agent_executor
    try:
        # 系統提示詞
        system_prompt = """你是一個智能網站助手，能夠幫助用戶了解網站功能、查詢學習進度、提供AI教學指導，管理對話記憶，以及創建考卷。

你有以下工具可以使用：
1. website_guide_tool - 網站導覽和功能介紹
2. learning_progress_tool - 查詢學習進度和統計
3. ai_tutor_tool - AI智能教學指導
4. memory_tool - 管理對話記憶
5. quiz_generator_tool - 考卷生成和測驗

請根據用戶的問題，選擇最適合的工具來幫助他們。如果用戶的問題不屬於以上任何類別，請禮貌地引導他們使用適當的功能。

關於考卷生成功能：
- 當用戶要求創建考卷、測驗或題目時，使用 quiz_generator_tool
- 支持知識點測驗和考古題兩種類型
- 可以指定知識點、題型、難度、題目數量等參數
- 支持自然語言描述需求，如"幫我創建20題計算機概論的單選題"

重要：當使用工具時，請直接返回工具的完整回應，不要重新格式化或摘要。特別是考卷生成工具的回應包含重要的JSON數據，必須完整保留。

記住：你是一個助手，不是工具本身。請使用工具來幫助用戶，而不是直接回答問題。"""

        # 創建提示詞模板 - 移除chat_history變數
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])

        # 創建主代理人
        agent = create_tool_calling_agent(llm, tools, prompt)
        
        # 創建執行器 - 設置為不重新格式化工具回應
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=False,  # 不返回中間步驟
            max_iterations=1  # 限制迭代次數，避免AI重新處理
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
        from src.memory_manager import add_user_message, add_ai_message
        
        # 檢查是否為考卷生成請求
        if _is_quiz_generation_request(message):
            logger.info("🎯 檢測到考卷生成請求，直接調用工具")
            
            # 直接調用考卷生成工具
            from src.web_ai_assistant import create_quiz_generator_tool
            quiz_tool = create_quiz_generator_tool()
            response = quiz_tool.invoke(message)
            
            # 添加AI回應到記憶
            add_ai_message(user_id, response)
            
            return {
                'success': True,
                'message': response,
                'timestamp': datetime.now().isoformat()
            }
        
        # 添加用戶訊息到記憶
        add_user_message(user_id, message)
        
        # 獲取服務
        service = get_web_ai_service()
        
        # 使用主代理人處理其他請求
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
            'error': f'處理訊息失敗：{str(e)}',
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
