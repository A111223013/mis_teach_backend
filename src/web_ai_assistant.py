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
# from memory_manager import add_user_message, add_ai_message

# 本地模組導入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tool.api_keys import get_api_key
from accessories import refresh_token

# LINE Bot 工具導入
from src.linebot import (
    generate_quiz_question,
    generate_knowledge_point,
    grade_answer,
    provide_tutoring
)

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
            return_intermediate_steps=True,  # 啟用 intermediate_steps 以便提取工具結果
            max_iterations=10  # 增加迭代次數，允許AI完成複雜任務
        )
        
        return platform_executor
        
    except Exception as e:
        logger.error(f"❌ 創建 {platform} 平台主代理人失敗: {e}")
        raise

# ==================== 核心處理函數 ====================

def get_web_ai_service():
    """獲取Web AI服務 - 延遲初始化"""
    global llm, tools, agent_executor
    
    if llm is None:
        llm = init_llm()
    if not tools:
        tools = get_platform_specific_tools("web")
    if agent_executor is None:
        agent_executor = create_platform_specific_agent("web")
    
    return {
        'llm': llm,
        'tools': tools,
        'agent_executor': agent_executor
    }

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
            create_linebot_calendar_view_tool(),
            create_linebot_calendar_add_tool(),
            create_linebot_calendar_update_tool(),
            create_linebot_calendar_delete_tool(),
            create_memory_tool()
        ]
    else:
        # 網站完整工具集
        return [
            create_website_guide_tool(),
            create_learning_progress_tool(),
            create_ai_tutor_tool(),
            create_memory_tool(),
            create_quiz_generator_tool(),
            create_university_quiz_tool(),
            create_knowledge_quiz_tool()
        ]

def create_quiz_generator_tool():
    """創建考卷生成工具 - 調用quiz_generator.py中的函數"""
    from langchain_core.tools import tool
    
    @tool
    def quiz_generator_tool(requirements: str) -> str:
        """考卷生成工具，根據用戶需求自動創建考卷並保存到數據庫"""
        try:
            # 檢查生成方式
            import re
            
            # 檢查是否為基於選中文字的生成請求
            if "請根據以下內容生成一道題目：" in requirements:
                # 提取選中的文字
                match = re.search(r'請根據以下內容生成一道題目：(.+)', requirements)
                if match:
                    selected_text = match.group(1).strip()
                    logger.info(f"🎯 檢測到基於選中文字的題目生成請求: {selected_text[:50]}...")
                    
                    # 使用新的SimilarQuizGenerator來生成基於選中文字的題目
                    from src.quiz_generator import SimilarQuizGenerator
                    similar_generator = SimilarQuizGenerator()
                    result = similar_generator.generate_similar_quiz(selected_text)
                    
                    if result['success']:
                        questions = result['questions']
                        quiz_info = result['quiz_info']
                        database_ids = result.get('database_ids', [])
                        
                        # 構建回應
                        response = f"✅ 基於選中內容的題目生成成功！\n\n"
                        response += f"📝 **{quiz_info['title']}**\n"
                        response += f"📚 基於內容: {selected_text[:50]}...\n"
                        response += f"🎯 主題: {quiz_info['topic']}\n"
                        response += f"🔢 題目數量: {quiz_info['question_count']} 題\n"
                        response += f"⏱️ 時間限制: {quiz_info['time_limit']} 分鐘\n\n"
                        
                        # 顯示第一題預覽
                        if questions:
                            first_question = questions[0]
                            response += "📋 題目預覽:\n"
                            response += f"1. {first_question['question_text'][:80]}...\n\n"
                        
                        # 使用第一個數據庫 ID 作為考卷 ID
                        quiz_id = database_ids[0] if database_ids else f"similar_quiz_{int(time.time())}"
                        
                        response += "🚀 **開始測驗**\n\n"
                        response += f"📋 考卷ID: `{quiz_id}`"
                        
                        return response
                    else:
                        return f"❌ 基於選中內容的題目生成失敗: {result.get('error', '未知錯誤')}"
            
            # 導入quiz_generator.py中的主要函數（原本的生成方式）
            from src.quiz_generator import execute_quiz_generation, execute_content_based_quiz_generation
            
            # 檢查是否為基於內容的生成請求
            content_keywords = ['根據以下內容', '基於以下內容', '根據內容', '基於內容', '以下內容', '內容如下']
            
            # 智能檢測：如果文本包含具體的技術內容且沒有明確的題目生成指令，則視為基於內容的請求
            technical_content_indicators = [
                '進位系統', '二進制', '八進制', '十六進制', '十進制',
                '數字表示', '數值轉換', '位元', '位元組',
                '演算法', '資料結構', '程式設計', '作業系統',
                '記憶體', 'CPU', '硬體', '軟體'
            ]
            
            # 明確的題目生成指令
            quiz_generation_keywords = ['生成', '創建', '建立', '製作', '產生', '考卷', '測驗', '題目', '考試']
            
            # 檢查是否包含明確的題目生成指令
            has_quiz_generation_keyword = any(keyword in requirements for keyword in quiz_generation_keywords)
            
            # 檢查是否包含技術內容
            has_technical_content = any(indicator in requirements for indicator in technical_content_indicators)
            
            # 如果包含明確的內容關鍵詞，直接視為基於內容的請求
            if any(keyword in requirements for keyword in content_keywords):
                # 使用基於內容的生成
                result = execute_content_based_quiz_generation(requirements)
                logger.info(f"🔍 基於內容生成結果: {result[:100]}...")
                return result
            # 如果包含技術內容但沒有明確的題目生成指令，視為基於內容的請求
            elif has_technical_content and not has_quiz_generation_keyword:
                # 使用基於內容的生成
                result = execute_content_based_quiz_generation(requirements)
                logger.info(f"🔍 基於內容生成結果: {result[:100]}...")
                return result
            else:
                # 使用原本的生成方式
                result = execute_quiz_generation(requirements)
                logger.info(f"🔍 標準生成結果: {result[:100]}...")
                return result
                
        except Exception as e:
            logger.error(f"❌ 考卷生成工具執行失敗: {e}")
            return f"❌ 考卷生成失敗，請稍後再試。錯誤: {str(e)}"
    
    return quiz_generator_tool

def get_platform_specific_system_prompt(platform: str = "web") -> str:
    """根據平台獲取對應的系統提示詞"""
    if platform == "linebot":
        return """你是一個智慧 LINE Bot 助手，負責協助用戶學習與管理行事曆。

⚠️ 重要：你必須調用工具來處理用戶請求，不要只回應文字說明！

當用戶說「修改ID7標題為123內容為456然後五分鐘後提醒我」時：
1. 提取 line_id = "U3fae4f436edf551db5f5c6773c98f8c7"
2. 使用完整時間計算：完整時間 + 5分鐘 = "2025-10-12 21:59"
3. 調用 linebot_calendar_update_tool(line_id, 7, "123", "456", "2025-10-12 21:59")

【你的工具】
1️⃣ linebot_quiz_generator_tool - AI測驗生成（選擇題/知識問答題）
2️⃣ linebot_knowledge_tool - 隨機知識點
3️⃣ linebot_grade_tool - 答案批改和解釋
4️⃣ linebot_tutor_tool - AI導師教學指導
5️⃣ linebot_learning_analysis_tool - 學習分析（已實現）
6️⃣ linebot_goal_setting_tool - 目標設定（已實現）
7️⃣ linebot_news_exam_tool - 最新消息/考試資訊（開發中）
8️⃣ linebot_calendar_view_tool - 查看行事曆（已實現）
9️⃣ linebot_calendar_add_tool - 新增行事曆事件（已實現）
🔟 linebot_calendar_update_tool - 修改行事曆事件（已實現）
1️⃣1️⃣ linebot_calendar_delete_tool - 刪除行事曆事件（已實現）
1️⃣2️⃣ memory_tool - 記憶管理

---
重要：記憶管理是核心功能！
- 使用 memory_tool('view', user_id) 查看對話歷史
- 每次對話都會自動記錄到記憶中
- 測驗流程中必須維護上下文連貫性

【測驗流程和記憶管理】
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

【行事曆操作邏輯】
從 input_text 解析出：
- line_id: 從「用戶ID: line_XXXX」提取並移除 "line_" 前綴
- 當前日期: 從「當前日期: 」後面提取
- event_date: 解析時間（今天、明天、五分鐘後、下午X點）
- 操作類型：
  - 包含「查看行事曆」→ view
  - 包含「新增事件」→ add
  - 包含「修改事件」或「修改ID」→ update
  - 包含「刪除事件」或「刪除ID」→ delete

---

【行事曆範例】
1️⃣ 新增事件：
  用戶：「新增事件 標題:英文小考 內容:複習單字 時間:明天晚上9點」
  → 調用 linebot_calendar_add_tool(line_id, "英文小考", "複習單字", "YYYY-MM-DD 21:00")

2️⃣ 查看行事曆：
  用戶：「行事曆」或「查看行事曆」
  → 調用 linebot_calendar_view_tool(line_id)

3️⃣ 修改事件：
  用戶：「修改事件 ID=3 標題改成資管作業 時間改成今天晚上8點」
  → 使用完整時間：2025-10-12 21:54 + 0分鐘 = "2025-10-12 20:00"
  → 調用 linebot_calendar_update_tool(line_id, "3", "資管作業", "", "2025-10-12 20:00")
  
  用戶：「修改ID7標題為123內容為456然後五分鐘後提醒我」
  → 使用完整時間：2025-10-12 21:54 + 5分鐘 = "2025-10-12 21:59"
  → 調用 linebot_calendar_update_tool(line_id, "7", "123", "456", "2025-10-12 21:59")

4️⃣ 刪除事件：
  用戶：「刪除事件 ID=5」
  → 調用 linebot_calendar_delete_tool(line_id, "5")

---

【時間解析規則 - 使用提供的時間信息】
從 input_text 中提取：
- 完整時間: YYYY-MM-DD HH:MM 格式（用於計算相對時間）
- 當前日期: YYYY年MM月DD日 格式（用於絕對時間）
- 當前時間: HH:MM 格式（用於參考）

計算規則：
- 「五分鐘後」= 完整時間 + 5分鐘，格式：YYYY-MM-DD HH:MM
- 「十分鐘後」= 完整時間 + 10分鐘，格式：YYYY-MM-DD HH:MM
- 「半小時後」= 完整時間 + 30分鐘，格式：YYYY-MM-DD HH:MM
- 「一小時後」= 完整時間 + 1小時，格式：YYYY-MM-DD HH:MM
- 「今天下午2點」= 當前日期 + 14:00，格式：YYYY-MM-DD 14:00
- 「明天晚上9點」= 當前日期+1天 + 21:00，格式：YYYY-MM-DD 21:00
- 「今天晚上9點」= 當前日期 + 21:00，格式：YYYY-MM-DD 21:00

重要：使用 input_text 中提供的完整時間進行計算，確保時間準確！

---

【重要規則】
1️⃣ 一定要呼叫對應工具，不要只回應文字。
2️⃣ 直接輸出工具結果，不要自行加格式。
3️⃣ 當用戶說「修改ID7標題為123內容為456然後五分鐘後提醒我」時，必須調用 linebot_calendar_update_tool。
4️⃣ 時間解析：五分鐘後 = 當前時間 + 5分鐘，直接計算並調用工具。
5️⃣ 不要要求用戶提供具體時間，AI 應該自己解析自然語言時間表達。

---

【測驗流程摘要】
1. 選擇測驗類型 → 生成題目
2. 用戶答題 → 批改並回饋
3. 可請求導師指導 → linebot_tutor_tool

請根據用戶的訊息，自動選擇最合適的工具調用。"""
    else:
        return """你是一個智能網站助手，能夠幫助用戶了解網站功能、查詢學習進度、提供AI教學指導，以及創建考卷。

       你有以下工具可以使用：
       1. website_guide_tool - 網站導覽和功能介紹
       2. learning_progress_tool - 查詢學習進度和統計
       3. ai_tutor_tool - AI智能教學指導
       4. quiz_generator_tool - 考卷生成和測驗
       5. create_university_quiz_tool - 創建大學考古題測驗
       6. create_knowledge_quiz_tool - 創建知識點測驗

請根據用戶的問題，選擇最適合的工具來幫助他們。如果用戶的問題不屬於以上任何類別，請禮貌地引導他們使用適當的功能。

關於測驗創建功能：
- 當用戶要求創建大學考古題測驗時，使用 create_university_quiz_tool 工具
- 當用戶要求創建知識點測驗時，使用 create_knowledge_quiz_tool 工具
- 支持自然語言描述需求，如"我要考中央大學113資訊管理考古題"

關於考卷生成功能：
- 當用戶要求創建考卷、測驗或題目時，使用 quiz_generator_tool
- 支持知識點測驗和考古題兩種類型
- 可以指定知識點、題型、難度、題目數量等參數
- 支持自然語言描述需求，如"幫我創建20題計算機概論的單選題"

重要：當使用工具時，請直接返回工具的完整回應，不要重新格式化或摘要，也不要包裝成 JSON 格式。

記住：你是一個助手，請使用工具來幫助用戶，並直接返回工具的結果給用戶。"""

def process_message(message: str, user_id: str = "default", platform: str = "web") -> Dict[str, Any]:
    """處理用戶訊息 - 主代理人模式，支援平台區分"""
    try:
        # 添加用戶訊息到記憶
        try:
            from src.memory_manager import add_user_message, add_ai_message
            add_user_message(user_id, message)
        except Exception as e:
            logger.warning(f"添加用戶訊息到記憶失敗: {e}")
        
        # 在進入代理前做快速意圖偵測：若為「解釋/說明」需求，直接產生解釋回覆，而非導師引導
        def is_explain_request(text: str) -> bool:
            try:
                import re
                pattern = r"(請?解釋|解釋以下|說明一下|請?說明|定義是什麼|介紹一下|幫我解釋)"
                return re.search(pattern, text) is not None
            except Exception:
                return False

        if is_explain_request(message):
            try:
                if llm is None:
                    # 直接初始化簡短回答模型（沿用現有初始化）
                    llm_local = init_llm()
                else:
                    llm_local = llm

                explain_prompt = (
                    "你是一位講解清晰的助教，任務是直接、完整地『解釋』使用者提出的概念或段落，不要反問、不要引導式教學。\n"
                    "請用繁體中文，以條列與小節呈現：\n"
                    "- 核心定義\n- 關鍵觀念/要點\n- 簡短例子或應用\n- 容易混淆之處與澄清（如有）\n"
                    "若原句含英文名稱，保留並對齊中文術語。以下是要解釋的內容：\n\n{query}"
                )

                result_text = llm_local.invoke(explain_prompt.format(query=message))
                response_text = result_text.content if hasattr(result_text, "content") else str(result_text)
                return {
                    'success': True,
                    'content': response_text,
                    'message': response_text,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ 解釋流程失敗: {e}")
                # 若解釋流程失敗，退回主代理人
                pass

        # 根據平台創建對應的主代理人
        platform_executor = create_platform_specific_agent(platform)
        
        if platform_executor is None:
            logger.error("❌ 無法創建平台特定代理人")
            return {
                'success': False,
                'error': '無法創建AI代理人',
                'timestamp': datetime.now().isoformat()
            }
        
        # 使用平台特定的主代理人處理
        # 對於 LINE Bot，將 user_id 和詳細時間信息包含在 input 中，讓工具能獲取到
        if platform == "linebot":
            now = datetime.now()
            current_date = now.strftime("%Y年%m月%d日")
            current_datetime = now.strftime("%Y-%m-%d %H:%M")
            current_time = now.strftime("%H:%M")
            enhanced_input = f"用戶ID: {user_id}\n當前日期: {current_date}\n當前時間: {current_time}\n完整時間: {current_datetime}\n\n{message}"
        else:
            enhanced_input = message
            
        result = platform_executor.invoke({
            "input": enhanced_input,
            "context": {"user_id": user_id, "platform": platform}
        })
        
        # 調試：打印主代理人的完整回應
        print(f"🔍 主代理人完整回應：{result}")
        print(f"🔍 回應類型：{type(result)}")
        print(f"🔍 回應鍵值：{list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # 格式化回應
        response = result.get("output", "抱歉，我無法理解您的請求。")
        print(f"🔍 提取的回應內容：{response}")
        print(f"🔍 回應內容長度：{len(response) if response else 0}")
        
        # 如果 output 為空，嘗試其他可能的字段
        if not response or response.strip() == "":
            print("🔍 output 為空，嘗試其他字段...")
            
            # 嘗試從 intermediate_steps 中提取工具結果
            if "intermediate_steps" in result:
                print(f"🔍 找到 intermediate_steps 字段")
                intermediate_steps = result["intermediate_steps"]
                if intermediate_steps and len(intermediate_steps) > 0:
                    # 獲取最後一個工具調用的結果
                    last_step = intermediate_steps[-1]
                    if len(last_step) >= 2:
                        tool_result = last_step[1]
                        if hasattr(tool_result, 'content'):
                            response = tool_result.content
                        elif isinstance(tool_result, dict) and 'content' in tool_result:
                            response = tool_result['content']
                        elif isinstance(tool_result, str):
                            response = tool_result
                        print(f"🔍 從 intermediate_steps 提取的內容：{response[:100]}...")
            
            # 如果還是沒有，嘗試 messages 字段
            if (not response or response.strip() == "") and "messages" in result:
                print(f"🔍 找到 messages 字段：{result['messages']}")
                # 嘗試從 messages 中提取最後一條消息
                if isinstance(result["messages"], list) and len(result["messages"]) > 0:
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        response = last_message.content
                    elif isinstance(last_message, dict) and 'content' in last_message:
                        response = last_message['content']
                    print(f"🔍 從 messages 提取的內容：{response}")
        
        # 檢查回應是否為 JSON 格式，如果是則提取實際內容
        if isinstance(response, str) and response.strip().startswith('{') and response.strip().endswith('}'):
            try:
                import json
                response_data = json.loads(response)
                print(f"🔍 解析 JSON 回應，鍵值: {list(response_data.keys())}")
                
                # 遞歸提取所有可能的 output 內容
                def extract_output(data):
                    if isinstance(data, dict):
                        if 'output' in data:
                            return data['output']
                        else:
                            # 遞歸查找所有值中的 output
                            for value in data.values():
                                result = extract_output(value)
                                if result:
                                    return result
                    return None
                
                extracted_output = extract_output(response_data)
                if extracted_output:
                    response = extracted_output
                else:
                    print(f"🔍 未找到 output 內容，使用原始回應")
            except Exception as e:
                print(f"🔍 JSON 解析失敗: {e}，使用原始回應")
        
        
        # 添加AI回應到記憶
        try:
            add_ai_message(user_id, response)
        except Exception as e:
            logger.warning(f"添加AI回應到記憶失敗: {e}")
        
        return {
            'success': True,
            'content': response,
            'message': response,  # 保持向後兼容
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
            # 為web_ai_assistant提供默認參數
            user_email = "web_user"
            question = query
            user_answer = "未提供"
            correct_answer = "未提供"
            user_input = query
            
            result = handle_tutoring_conversation(user_email, question, user_answer, correct_answer, user_input)
            return result.get('response', '抱歉，AI導師回應失敗，請稍後再試。')
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

def create_university_quiz_tool():
    """創建大學考古題測驗工具"""
    from langchain_core.tools import tool
    
    @tool
    def create_university_quiz_tool(university: str, department: str, year: int) -> str:
        """創建大學考古題測驗"""
        from src.web_automation import create_university_quiz
        return create_university_quiz(university, department, year)
    
    return create_university_quiz_tool

def create_knowledge_quiz_tool():
    """創建知識點測驗工具"""
    from langchain_core.tools import tool
    
    @tool
    def create_knowledge_quiz_tool(knowledge_point: str, difficulty: str, question_count: int) -> str:
        """創建知識點測驗"""
        from src.web_automation import create_knowledge_quiz
        return create_knowledge_quiz(knowledge_point, difficulty, question_count)
    
    return create_knowledge_quiz_tool

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
        """LINE Bot 批改工具 - 直接使用提供的題目信息進行批改"""
        # 直接調用批改函數，主代理人會提供完整的上下文
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
    """創建 LINE Bot 學習分析工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_learning_analysis_tool(input_text: str = "") -> str:
        """LINE Bot 學習分析工具 - 獲取用戶學習分析數據"""
        from src.learning_analytics import get_learning_analysis_for_linebot
        # 從輸入中提取 user_id
        import re
        # 嘗試多種格式匹配
        user_id_match = re.search(r'用戶ID: (line_[^\n]+)', input_text)
        if not user_id_match:
            # 如果沒有找到「用戶ID:」格式，直接尋找 line_ 開頭的ID
            user_id_match = re.search(r'(line_[a-zA-Z0-9]+)', input_text)
        
        if user_id_match:
            user_id = user_id_match.group(1)
            # 移除 line_ 前綴，獲取純粹的 LINE ID
            clean_line_id = user_id.replace('line_', '') if user_id.startswith('line_') else user_id
            return get_learning_analysis_for_linebot(clean_line_id)
        else:
            return "❌ 無法獲取用戶ID，請重新綁定帳號"
    
    return linebot_learning_analysis_tool

def create_linebot_goal_setting_tool():
    """創建 LINE Bot 目標設定工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_goal_setting_tool(input_text: str = "") -> str:
        """LINE Bot 目標設定工具 - 管理學習目標"""
        from src.dashboard import get_goals_for_linebot
        # 從輸入中提取 user_id
        import re
        # 嘗試多種格式匹配
        user_id_match = re.search(r'用戶ID: (line_[^\n]+)', input_text)
        if not user_id_match:
            # 如果沒有找到「用戶ID:」格式，直接尋找 line_ 開頭的ID
            user_id_match = re.search(r'(line_[a-zA-Z0-9]+)', input_text)
        
        if user_id_match:
            user_id = user_id_match.group(1)
            # 移除 line_ 前綴，獲取純粹的 LINE ID
            clean_line_id = user_id.replace('line_', '') if user_id.startswith('line_') else user_id
            return get_goals_for_linebot(clean_line_id)
        else:
            return "❌ 無法獲取用戶ID，請重新綁定帳號"
    
    return linebot_goal_setting_tool

def create_linebot_news_exam_tool():
    """創建 LINE Bot 最新消息/考試資訊工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_news_exam_tool(query: str = "") -> str:
        """LINE Bot 最新消息/考試資訊工具 - 獲取最新資訊"""
        return "📰 最新消息功能\n\n請在 LINE Bot 中使用「最新消息」指令來獲取最新資訊！\n\n💡 功能包括：\n• 考試資訊推送\n• 重要公告\n• 學習資源更新\n• 活動通知"
    
    return linebot_news_exam_tool

def create_linebot_calendar_view_tool():
    """創建 LINE Bot 行事曆查看工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_calendar_view_tool(line_id: str) -> str:
        """LINE Bot 行事曆查看工具 - 查看學習計畫
        
        Args:
            line_id: LINE 用戶 ID
        """
        from src.dashboard import get_calendar_for_linebot
        
        return get_calendar_for_linebot(line_id)
    
    return linebot_calendar_view_tool

def create_linebot_calendar_add_tool():
    """創建 LINE Bot 行事曆新增工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_calendar_add_tool(line_id: str, title: str, content: str, event_date: str) -> str:
        """LINE Bot 行事曆新增工具 - 當用戶要新增事件時調用此工具
        
        Args:
            line_id: LINE 用戶 ID (從 input_text 提取)
            title: 事件標題 (從用戶訊息中提取)
            content: 事件內容 (從用戶訊息中提取)
            event_date: 事件日期時間 (從用戶訊息中提取並解析，格式: 2024-01-01 10:00)
        """
        from src.dashboard import add_calendar_event_for_linebot
        
        if not title:
            return "❌ 標題為必填欄位！"
        
        # AI 已經計算好時間，直接使用
        if not event_date or event_date == "":
            return "❌ 請提供事件時間！"
        
        return add_calendar_event_for_linebot(line_id, title, content, event_date)
    
    return linebot_calendar_add_tool

def create_linebot_calendar_update_tool():
    """創建 LINE Bot 行事曆修改工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_calendar_update_tool(line_id: str, event_id: int, title: str, content: str, event_date: str) -> str:
        """LINE Bot 行事曆修改工具 - 修改學習計畫
        
        Args:
            line_id: LINE 用戶 ID
            event_id: 事件 ID
            title: 事件標題
            content: 事件內容
            event_date: 事件日期時間 (支援格式: 2024-01-01 10:00, 2024-01-01T10:00, 2024-01-01)
        """
        from src.dashboard import update_calendar_event_for_linebot
        
        if not title:
            return "❌ 標題為必填欄位！"
        
        # AI 已經計算好時間，直接使用
        if not event_date or event_date == "":
            return "❌ 請提供事件時間！"
        
        return update_calendar_event_for_linebot(line_id, event_id, title, content, event_date)
    
    return linebot_calendar_update_tool

def create_linebot_calendar_delete_tool():
    """創建 LINE Bot 行事曆刪除工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_calendar_delete_tool(line_id: str, event_id: int) -> str:
        """LINE Bot 行事曆刪除工具 - 刪除學習計畫
        
        Args:
            line_id: LINE 用戶 ID
            event_id: 事件 ID
        """
        from src.dashboard import delete_calendar_event_for_linebot
        
        return delete_calendar_event_for_linebot(line_id, event_id)
    
    return linebot_calendar_delete_tool

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

@web_ai_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """聊天API - 接收用戶訊息並返回AI回應，支援平台區分"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True}), 204
    
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': '缺少必要參數'}), 400
        
        message = data['message']
        user_id = data.get('user_id', 'default')
        platform = data.get('platform', 'web')  # 新增平台參數
        
        # 檢查是否為 LINE Bot 請求（不需要認證）
        if platform == 'linebot':
            print(f"🤖 收到 LINE Bot 請求：用戶={user_id}, 平台={platform}")
            # 處理訊息
            result = process_message(message, user_id, platform)
        else:
            # 其他平台需要認證
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'token': None, 'message': '未提供token'}), 401
            
            token = auth_header.split(" ")[1]
            # 處理訊息
            result = process_message(message, user_id, platform)
        
        # 返回前端期待的格式
        if result['success']:
            response_data = {
                'success': True,
                'content': result['message'],
                'timestamp': result['timestamp']
            }
            # 只有非 LINE Bot 請求才返回 token
            if platform != 'linebot':
                response_data['token'] = refresh_token(token)
            return jsonify(response_data)
        else:
            response_data = {
                'success': False,
                'error': result.get('error', '處理失敗')
            }
            # 只有非 LINE Bot 請求才返回 token
            if platform != 'linebot':
                response_data['token'] = refresh_token(token)
            return jsonify(response_data), 500
        
    except Exception as e:
        logger.error(f"❌ 聊天API錯誤: {e}")
        return jsonify({
            'success': False,
            'error': f'聊天API錯誤：{str(e)}'
        }), 500

@web_ai_bp.route('/quick-action', methods=['POST', 'OPTIONS'])
def quick_action():
    """快速動作API - 處理預定義的快速動作"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True}), 204
    
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'token': None, 'message': '未提供token'}), 401
        
        token = auth_header.split(" ")[1]
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
            'token': refresh_token(token),
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


# =============== 轉發/對齊前端期待的資料端點 ===============

@web_ai_bp.route('/status', methods=['GET', 'OPTIONS'])
def get_status():
    """獲取助手狀態"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 204
    
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': '未提供token'}), 401
        
        token = auth_header.split(" ")[1]
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'status': 'active',
            'message': 'Web AI 助手運行正常',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 狀態檢查錯誤: {e}")
        return jsonify({
            'success': False,
            'error': f'狀態檢查失敗：{str(e)}'
        }), 500

@web_ai_bp.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """健康檢查"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 204
    
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': '未提供token'}), 401
        
        token = auth_header.split(" ")[1]
        
        # 檢查 AI 服務是否可用
        try:
            # 嘗試初始化 LLM 來檢查服務狀態
            test_llm = init_llm()
            ai_status = 'healthy'
            ai_message = 'AI 服務正常'
        except Exception as e:
            ai_status = 'unhealthy'
            ai_message = f'AI 服務異常: {str(e)}'
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'health': {
                'overall': 'healthy',
                'ai_service': ai_status,
                'message': ai_message
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 健康檢查錯誤: {e}")
        return jsonify({
            'success': False,
            'error': f'健康檢查失敗：{str(e)}'
        }), 500

@web_ai_bp.route('/get-quiz-from-database', methods=['POST', 'OPTIONS'])
def web_get_quiz_from_database():
    
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True}), 204
    
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'token': None, 'message': '未提供token'}), 401
        
        token = auth_header.split(" ")[1]

        data = request.get_json(silent=True) or {}
        quiz_ids = data.get('quiz_ids', [])

        if not quiz_ids:
            return jsonify({'success': False, 'message': '缺少考卷ID'}), 400

        # 從 ai_teacher 匯入核心實作並呼叫
        from .ai_teacher import get_quiz_from_database
        result = get_quiz_from_database(quiz_ids)
        return jsonify({'token': refresh_token(token), 'data': result})

    except Exception as e:
        logger.error(f"❌ web-ai/get-quiz-from-database 錯誤: {e}")
        return jsonify({'success': False, 'message': f'獲取考卷數據失敗：{str(e)}'}), 500


