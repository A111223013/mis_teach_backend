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
                
                # 構建考卷數據
                current_timestamp = int(time.time())
                quiz_data = {
                    'quiz_id': f"ai_generated_{current_timestamp}",  # 添加quiz_id
                    'template_id': current_timestamp,  # 使用整數timestamp作為template_id
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
                
                # 清理和驗證JSON數據
                try:
                    # 生成JSON字符串
                    json_str = json.dumps(quiz_data, ensure_ascii=False, indent=2)
                    
                    # 清理JSON字符串，移除控制字符和修復格式問題
                    import re
                    
                    # 移除控制字符（除了換行符和製表符）
                    cleaned_json = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', json_str)
                    
                    # 修復可能的字符串終止問題
                    # 檢查雙引號是否平衡
                    quote_count = cleaned_json.count('"')
                    if quote_count % 2 != 0:
                        # 如果雙引號數量為奇數，在末尾添加一個雙引號
                        cleaned_json += '"'
                        logger.info("修復雙引號不平衡問題")
                    
                    # 檢查大括號是否平衡
                    brace_count = cleaned_json.count('{') - cleaned_json.count('}')
                    if brace_count > 0:
                        # 如果大括號不平衡，在末尾添加缺少的大括號
                        cleaned_json += '}' * brace_count
                        logger.info(f"修復大括號不平衡問題，添加了 {brace_count} 個大括號")
                    
                    # 檢查中括號是否平衡
                    bracket_count = cleaned_json.count('[') - cleaned_json.count(']')
                    if bracket_count > 0:
                        # 如果中括號不平衡，在末尾添加缺少的中括號
                        cleaned_json += ']' * bracket_count
                        logger.info(f"修復中括號不平衡問題，添加了 {bracket_count} 個中括號")
                    
                    # 驗證JSON是否有效
                    json.loads(cleaned_json)
                    
                    # 使用清理後的JSON
                    response += "```json\n"
                    response += cleaned_json
                    response += "\n```\n\n"
                    
                    logger.info("✅ JSON生成成功，格式正確")
                    
                except Exception as json_error:
                    logger.error(f"JSON生成失敗: {json_error}")
                    # 如果JSON生成失敗，使用簡化的格式
                    response += "```json\n"
                    response += json.dumps({
                        'quiz_id': quiz_data['quiz_id'],
                        'template_id': quiz_data['template_id'],  # 現在是整數
                        'title': quiz_info['title'],
                        'topic': quiz_info['topic'],
                        'question_count': len(questions),
                        'time_limit': quiz_info['time_limit'],
                        'total_score': quiz_info['total_score']
                    }, ensure_ascii=False, indent=2)
                    response += "\n```\n\n"
                    logger.warning("使用簡化JSON格式")
                
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
        'question_count': 5,  # 改為5題默認，更合理
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
    
    # 檢測題目數量 - 改進數量檢測邏輯
    import re
    
    # 方法1: 檢測 "X題" 格式
    count_match = re.search(r'(\d+)題', text)
    if count_match:
        count = int(count_match.group(1))
        requirements['question_count'] = count
        logger.info(f"檢測到題目數量: {count}題")
    
    # 方法2: 檢測 "X道題" 格式
    count_match = re.search(r'(\d+)道題', text)
    if count_match:
        count = int(count_match.group(1))
        requirements['question_count'] = count
        logger.info(f"檢測到題目數量: {count}道題")
    
    # 方法3: 檢測 "X個題目" 格式
    count_match = re.search(r'(\d+)個題目', text)
    if count_match:
        count = int(count_match.group(1))
        requirements['question_count'] = count
        logger.info(f"檢測到題目數量: {count}個題目")
    
    # 方法4: 檢測 "X個問題" 格式
    count_match = re.search(r'(\d+)個問題', text)
    if count_match:
        count = int(count_match.group(1))
        requirements['question_count'] = count
        logger.info(f"檢測到題目數量: {count}個問題")
    
    # 方法5: 檢測 "X個" 格式（如果前面有相關詞）
    count_match = re.search(r'(\d+)個', text)
    if count_match and any(word in text for word in ['題目', '問題', '測驗', '考試']):
        count = int(count_match.group(1))
        requirements['question_count'] = count
        logger.info(f"檢測到題目數量: {count}個")
    
    # 確保題目數量在合理範圍內
    if requirements['question_count'] > 50:
        requirements['question_count'] = 50
        logger.warning(f"題目數量過多，限制為50題")
    elif requirements['question_count'] < 1:
        requirements['question_count'] = 1
        logger.warning(f"題目數量過少，設置為1題")
    
    logger.info(f"最終題目數量設置為: {requirements['question_count']}題")
    
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
            max_iterations=5  # 增加迭代次數，允許AI完成複雜任務
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
        
        # 格式化回應 - 處理代理人的回應格式
        response = result.get("output", "抱歉，我無法理解您的請求。")
        
        # 如果回應包含工具調用結果，提取實際內容
        if isinstance(response, str) and "quiz_generator_tool_response" in response:
            try:
                import json
                import re
                
                # 使用更簡單的方法找到JSON部分
                if "{" in response and "}" in response:
                    brace_start = response.find("{")
                    brace_end = response.rfind("}")
                    if brace_end > brace_start:
                        tool_response = response[brace_start:brace_end + 1]
                        logger.info(f"找到JSON部分，長度: {len(tool_response)}")
                        
                        try:
                            # 使用更強健的JSON清理方法
                            cleaned_json = _clean_json_string(tool_response)
                            parsed = json.loads(cleaned_json)
                            
                            if "quiz_generator_tool_response" in parsed:
                                response = parsed["quiz_generator_tool_response"]["output"]
                                logger.info("✅ 成功解析工具回應")
                            else:
                                logger.warning("JSON中不包含quiz_generator_tool_response")
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON解析失敗: {e}")
                            # 嘗試修復JSON
                            try:
                                fixed_json = _fix_incomplete_json(tool_response)
                                parsed = json.loads(fixed_json)
                                if "quiz_generator_tool_response" in parsed:
                                    response = parsed["quiz_generator_tool_response"]["output"]
                                    logger.info("✅ 使用修復後的JSON成功解析工具回應")
                                else:
                                    logger.warning("修復後的JSON中仍不包含quiz_generator_tool_response")
                            except Exception as fix_error:
                                logger.warning(f"JSON修復失敗: {fix_error}")
                                
            except Exception as e:
                logger.warning(f"解析工具回應失敗: {e}")
                # 如果解析失敗，保持原始回應
        
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
