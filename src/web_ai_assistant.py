#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web AI 助理模組 - 整合多種AI工具
"""

from flask import Blueprint, request, jsonify
import logging
import json
import threading
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

# 使用線程本地存儲來傳遞上下文（user_id 和 input_text）
_thread_local = threading.local()

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
            max_output_tokens=8192,  # 增加輸出長度限制，確保完整回答（特別是錯題解析）
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
            create_linebot_goal_view_tool(),
            create_linebot_goal_add_tool(),
            create_linebot_goal_delete_tool(),
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
            create_website_knowledge_tool(),  # 網站知識檢索工具（新增）
            create_website_guide_tool(),
            create_learning_progress_tool(),
            create_ai_tutor_tool(),  # 引導式教學工具
            create_direct_answer_tool(),  # 直接解答工具
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

重要：你必須調用工具來處理用戶請求，不要只回應文字說明！

【上下文管理規則】
系統會自動將最近的對話記錄注入到每次請求中，你可以在 input_text 中看到【對話上下文（最近5條記錄）】部分。
請充分利用這些上下文信息來理解用戶的意圖和連續對話。

1. **上下文理解**：
   - 當用戶使用「一樣是」、「還是」、「不改」等詞語時，表示要延續上一個操作
   - 當用戶提到「剛才」、「剛剛」、「之前」時，請查看對話上下文
   - 行事曆修改時，如果用戶沒有明確指定標題或內容，應該從對話上下文中推斷

2. **連續對話處理**：
   - 如果用戶連續對話（例如：先說「修改ID14時間」，再說「一樣是閱讀資料結構第一章」），必須結合上下文理解
   - 當用戶只提到部分信息（如只說時間），應從上下文或資料庫中獲取完整信息

當用戶說「修改ID7標題為123內容為456然後五分鐘後提醒我」時：
1. 提取 line_id = "U3fae4f436edf551db5f5c6773c98f8c7"
2. 使用完整時間計算：完整時間 + 5分鐘 = "2025-10-12 21:59"
3. 調用 linebot_calendar_update_tool(line_id, 7, "123", "456", "2025-10-12 21:59")

當用戶說「學習分析」時：
1. 調用 linebot_learning_analysis_tool(完整的 input_text)
2. 不要只傳遞「學習分析」，要傳遞完整的 input_text

範例：
- 用戶：「學習分析」
- 調用：linebot_learning_analysis_tool("用戶ID: line_U3fae4f436edf551db5f5c6773c98f8c7\n當前日期: 2025年10月12日\n當前時間: 22:23\n完整時間: 2025-10-12 22:23\n\n學習分析")

【你的工具】
1. linebot_quiz_generator_tool(requirements) - AI測驗生成
2. linebot_knowledge_tool(query) - 隨機知識點
3. linebot_grade_tool(answer, correct_answer, question) - 答案批改和解釋
4. linebot_tutor_tool(query) - AI導師教學指導
5. linebot_learning_analysis_tool(input_text) - 學習分析（傳遞完整 input_text）
6. linebot_goal_view_tool(line_id) - 查看學習目標
7. linebot_goal_add_tool(line_id, goal) - 新增學習目標
8. linebot_goal_delete_tool(line_id, goal_index) - 刪除學習目標
9. linebot_news_exam_tool(query) - 最新消息/考試資訊
10. linebot_calendar_view_tool(line_id) - 查看行事曆
11. linebot_calendar_add_tool(line_id, title, content, event_date) - 新增行事曆事件
12. linebot_calendar_update_tool(line_id, event_id, title, content, event_date) - 修改行事曆事件
13. linebot_calendar_delete_tool(line_id, event_id) - 刪除行事曆事件
14. memory_tool(action, user_id) - 記憶管理（可選使用，系統已自動提供對話上下文）

---
重要：上下文管理
- 系統會自動將最近的對話記錄注入到每次請求中，你可以在 input_text 中看到【對話上下文（最近5條記錄）】
- 請充分利用這些上下文信息來理解用戶的意圖
- 每次對話都會自動記錄到記憶中
- 測驗流程中必須維護上下文連貫性
- 行事曆操作必須結合上下文理解用戶意圖

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

【目標設定操作邏輯】
從 input_text 解析出：
- line_id: 從「用戶ID: line_XXXX」提取並移除 "line_" 前綴
- 操作類型：
  - 包含「查看目標」、「目標設定」、「我的目標」→ view
  - 包含「新增目標」、「設定目標」、「加入目標」→ add
  - 包含「刪除目標」、「移除目標」→ delete

---

【目標設定範例】
1. 查看目標：
  用戶：「查看目標」或「我的學習目標」或「目標設定」
  → 調用 linebot_goal_view_tool(line_id)

2. 新增目標：
  用戶：「新增目標:每日答題數10題」或「我想設定目標每日答題數10題」
  → 提取目標內容：從「新增目標:」後面或「設定目標」後面提取
  → 調用 linebot_goal_add_tool(line_id, "每日答題數10題")

3. 刪除目標：
  用戶：「刪除目標:1」或「移除第1個目標」
  → 提取目標編號：從用戶訊息中提取數字（對應用戶看到的編號，從1開始）
  → 調用 linebot_goal_delete_tool(line_id, 1)

重要規則：
- 目標編號從 1 開始，對應用戶看到的編號
- 最多可以設定 10 個目標
- 目標內容不能為空
- 不能新增重複的目標

---

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
1. 新增事件：
  用戶：「新增事件 標題:英文小考 內容:複習單字 時間:明天晚上9點」
  → 調用 linebot_calendar_add_tool(line_id, "英文小考", "複習單字", "YYYY-MM-DD 21:00")

2. 查看行事曆：
  用戶：「行事曆」或「查看行事曆」
  → 調用 linebot_calendar_view_tool(line_id)

3. 修改事件（結合上下文）：
  範例1：完整指定
  用戶：「修改事件 ID=3 標題改成資管作業 時間改成今天晚上8點」
  → 使用完整時間：2025-10-12 21:54 + 0分鐘 = "2025-10-12 20:00"
  → 調用 linebot_calendar_update_tool(line_id, "3", "資管作業", "", "2025-10-12 20:00")
  
  範例2：只有部分信息
  用戶：「修改ID7標題為123內容為456然後五分鐘後提醒我」
  → 使用完整時間：2025-10-12 21:54 + 5分鐘 = "2025-10-12 21:59"
  → 調用 linebot_calendar_update_tool(line_id, "7", "123", "456", "2025-10-12 21:59")
  
  範例3：上下文延續（重要！）
  第一條訊息：用戶：「幫我修改id14時間變成晚上6點」
  第二條訊息：用戶：「標題一樣」
  → 必須結合上下文理解：用戶想保持標題不變，只修改時間
  → 調用 linebot_calendar_update_tool(line_id, 14, "一樣", "", "2025-11-01 18:00")
  → 工具會自動從資料庫獲取ID14的原始標題和內容，只更新時間
  
  範例4：部分修改
  第一條訊息：用戶：「修改ID14時間變成今天晚上6點」
  → 如果用戶沒有提到標題或內容，表示只修改時間，標題和內容保持不變
  → 調用 linebot_calendar_update_tool(line_id, 14, "", "", "2025-11-01 18:00")
  → 工具會自動從資料庫獲取原始標題和內容

4. 刪除事件：
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
1. 一定要呼叫對應工具，不要只回應文字。
2. 直接輸出工具結果，不要自行加格式。
3. **記憶查詢處理**：
   - 當用戶問「我剛剛做了什麼」、「我剛才做了什麼」、「剛才我做了什麼」等問題時
   - 請直接查看 input_text 中的【對話上下文（最近5條記錄）】部分
   - 根據對話上下文回答用戶最近做了什麼，不要只重複用戶的問題
   - 不需要額外調用 memory_tool，系統已經自動提供了上下文
4. 當用戶說「修改ID7標題為123內容為456然後五分鐘後提醒我」時，必須調用 linebot_calendar_update_tool。
5. 時間解析：五分鐘後 = 當前時間 + 5分鐘，直接計算並調用工具。
6. 不要要求用戶提供具體時間，AI 應該自己解析自然語言時間表達。
7. 上下文優先：當用戶使用「一樣是」、「還是」、「不改」、「標題一樣」等詞語時，表示保持原有值不變。
8. 行事曆修改時，如果用戶沒有明確指定標題或內容，應該：
   - 調用 linebot_calendar_update_tool 時，將對應參數設為空字符串 "" 或 "一樣"
   - 工具會自動從資料庫查詢原始事件的標題和內容
   - 不要要求用戶提供標題或內容，工具會自動處理
9. 當用戶只提到修改時間時，標題和內容參數都應該為空，讓工具從原始事件獲取。

---

【測驗流程摘要】
1. 選擇測驗類型 → 生成題目
2. 用戶答題 → 批改並回饋
3. 可請求導師指導 → linebot_tutor_tool

請根據用戶的訊息，自動選擇最合適的工具調用。"""
    else:
        return """你是一個智能網站助手，能夠幫助用戶了解網站功能、查詢學習進度、提供AI教學指導，以及創建考卷。

       你有以下工具可以使用：
       1. website_knowledge_tool - 網站知識檢索工具（優先使用！當用戶詢問網站功能、操作說明、頁面介紹等問題時，應優先使用此工具）
       2. website_guide_tool - 網站導覽和功能介紹
       3. learning_progress_tool - 查詢學習進度和統計
       4. ai_tutor_tool - AI引導式教學（透過提問引導學生思考，幫助學生理解概念）
       5. direct_answer_tool - 直接解答工具（直接給出問題的答案和詳細解釋）
       6. quiz_generator_tool - 考卷生成和測驗
       7. create_university_quiz_tool - 創建大學考古題測驗
       8. create_knowledge_quiz_tool - 創建知識點測驗

**重要：網站知識檢索工具的使用時機**
當用戶詢問以下類型問題時，應優先使用 website_knowledge_tool：
- 「如何使用測驗功能？」、「測驗中心怎麼用？」
- 「學習成效分析是什麼？」、「如何查看學習分析？」
- 「如何新增行事曆事件？」、「行事曆功能介紹」
- 「系統設定在哪裡？」、「如何修改個人資料？」
- 「科技趨勢頁面有什麼功能？」
- 任何關於網站功能、操作步驟、頁面介紹的問題

使用 website_knowledge_tool 後，根據檢索結果回答用戶問題，可以結合其他工具提供更完整的幫助。

**重要：兩種教學工具的選擇**
- **ai_tutor_tool（引導式教學）**：當用戶想要透過提問和思考來理解概念時使用。適合：
  * 用戶明確說「引導我理解」、「幫助我思考」、「教我理解」、「引導式教學」
  * 學習新概念，需要逐步理解
  * **不適合**：錯題複習、直接分析錯誤原因
  
- **direct_answer_tool（直接解答）**：當用戶想要快速獲得答案和解釋時使用。適合：
  * 用戶只有問問題時，例如「死鎖是什麼？」
  * 簡單的概念問題，需要快速了解
  * 用戶只是想確認答案或解釋
  * **特別適合**：錯題分析、分析錯誤原因、直接解答錯題（當用戶提到「直接解答」、「直接分析」、「不需要引導」等關鍵詞時，必須使用此工具）
  * **一般情況優先使用此工具**
請根據用戶的問題和意圖，選擇最適合的工具來幫助他們。如果用戶的問題不屬於以上任何類別，請禮貌地引導他們使用適當的功能。

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
            
            # 自動獲取對話記憶並注入到輸入中
            conversation_context = ""
            try:
                from src.memory_manager import get_user_memory
                memory = get_user_memory(user_id)
                if memory:
                    # 只使用最近的5條對話記錄作為上下文（避免 token 過多）
                    recent_messages = memory[-5:]
                    conversation_context = "\n\n【對話上下文（最近5條記錄）】\n" + "\n".join(recent_messages) + "\n"
            except Exception as e:
                logger.warning(f"獲取對話記憶失敗: {e}")
            
            enhanced_input = f"用戶ID: {user_id}\n當前日期: {current_date}\n當前時間: {current_time}\n完整時間: {current_datetime}{conversation_context}\n用戶當前訊息: {message}"
        else:
            # Web 平台也可以選擇性添加記憶
            conversation_context = ""
            try:
                from src.memory_manager import get_user_memory
                memory = get_user_memory(user_id)
                if memory:
                    recent_messages = memory[-3:]  # Web 平台使用較少的上下文
                    conversation_context = "\n\n【最近的對話記錄】\n" + "\n".join(recent_messages) + "\n"
            except Exception as e:
                logger.warning(f"獲取對話記憶失敗: {e}")
            
            enhanced_input = message + conversation_context
        
        # 將 user_id 和 enhanced_input 存儲到線程本地變量，供 memory_tool 使用
        _thread_local.current_user_id = user_id
        _thread_local.current_input_text = enhanced_input
        
        try:
            result = platform_executor.invoke({
                "input": enhanced_input,
                "context": {"user_id": user_id, "platform": platform}
            })
        finally:
            # 清理線程本地變量
            if hasattr(_thread_local, 'current_user_id'):
                delattr(_thread_local, 'current_user_id')
            if hasattr(_thread_local, 'current_input_text'):
                delattr(_thread_local, 'current_input_text')
        
        # 調試：打印主代理人的完整回應
        
        # 格式化回應
        response = result.get("output", "抱歉，我無法理解您的請求。")
        
        # 如果 output 為空，嘗試其他可能的字段
        if not response or response.strip() == "":
            
            # 嘗試從 intermediate_steps 中提取工具結果
            if "intermediate_steps" in result:
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
            
            # 如果還是沒有，嘗試 messages 字段
            if (not response or response.strip() == "") and "messages" in result:
                # 嘗試從 messages 中提取最後一條消息
                if isinstance(result["messages"], list) and len(result["messages"]) > 0:
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        response = last_message.content
                    elif isinstance(last_message, dict) and 'content' in last_message:
                        response = last_message['content']
        
        # 檢查回應是否為 JSON 格式，如果是則提取實際內容
        if isinstance(response, str) and response.strip().startswith('{') and response.strip().endswith('}'):
            try:
                import json
                response_data = json.loads(response)
                
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

def create_website_knowledge_tool():
    """創建網站知識檢索工具"""
    from langchain_core.tools import tool
    
    @tool
    def website_knowledge_tool(query: str) -> str:
        """
        網站知識檢索工具，用於回答網站功能、操作說明等相關問題
        
        使用時機：
        - 用戶詢問網站功能如何使用
        - 用戶詢問系統操作說明
        - 用戶詢問頁面功能介紹
        - 用戶詢問系統設定、測驗、學習分析等功能
        
        這個工具會從網站知識庫中檢索相關資訊，幫助準確回答用戶問題。
        """
        try:
            from src.website_knowledge_db import retrieve_website_knowledge
            
            # 檢索網站知識（使用 ChromaDB）
            results = retrieve_website_knowledge(query, max_results=3)
            
            if not results:
                return "抱歉，我找不到相關的網站資訊。請嘗試使用其他工具或直接詢問我。"
            
            # 格式化結果
            response = "根據網站知識庫，以下是相關資訊：\n\n"
            for i, result in enumerate(results, 1):
                response += f"**{i}. {result.get('title', '無標題')}**\n"
                content = result.get('content', '')
                # 限制內容長度，避免過長
                if len(content) > 500:
                    content = content[:500] + "..."
                response += f"{content}\n"
                if result.get('page_path'):
                    response += f"相關頁面：{result.get('page_path')}\n"
                response += "\n"
            
            return response
        except Exception as e:
            logger.error(f"網站知識檢索工具執行失敗: {e}")
            return f"❌ 網站知識檢索失敗：{str(e)}"
    
    return website_knowledge_tool

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
    """創建AI導師工具引用（引導式教學）"""
    from langchain_core.tools import tool
    
    @tool
    def ai_tutor_tool(query: str, user_answer: str = "", correct_answer: str = "") -> str:
        """AI導師工具（引導式教學），透過提問引導學生思考，幫助學生理解概念"""
        try:
            # 調用其他.py文件中的實現
            from src.rag_sys.rag_ai_role import handle_tutoring_conversation
            # 為web_ai_assistant提供默認參數
            user_email = "web_user"
            question = query
            
            if not user_answer:
                user_answer = "未提供"
            if not correct_answer:
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

def create_direct_answer_tool():
    """創建直接解答工具引用（直接給答案）"""
    from langchain_core.tools import tool
    
    @tool
    def direct_answer_tool(question: str) -> str:
        """直接解答工具，直接給出問題的答案和詳細解釋，不進行引導式提問
        
        適用於：
        - 用戶明確要求「直接解答」、「直接給答案」
        - 簡單的概念問題
        - 需要快速獲得答案的情況
        
        與引導式教學的區別：
        - 引導式教學：透過提問幫助學生思考，逐步理解
        - 直接解答：直接給出答案和解釋，適合快速了解
        
        Args:
            question: 用戶的問題
            
        Returns:
            str: 直接給出的答案和詳細解釋
        """
        try:
            logger.info(f"🔧 direct_answer_tool 被調用，問題: {question[:100]}...")
            from src.ai_teacher import direct_answer_question
            result = direct_answer_question(question, user_email="web_user")
            
            if not result or not result.strip():
                logger.warning(f"⚠️ direct_answer_tool 返回空結果")
                return "抱歉，無法生成回答。請重新提問或稍後再試。"
            
            logger.info(f"✅ direct_answer_tool 成功返回，長度: {len(result)} 字符")
            return result
        except ImportError as e:
            logger.error(f"❌ 直接解答系統導入失敗: {e}")
            return "❌ 直接解答系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"❌ 直接解答工具執行失敗: {e}", exc_info=True)
            return f"❌ 直接解答失敗：{str(e)}"
    
    return direct_answer_tool

def create_memory_tool(input_text_getter=None):
    """創建記憶管理工具引用
    
    Args:
        input_text_getter: 可選的函數，用於獲取當前的 input_text（用於提取 user_id）
    """
    from langchain_core.tools import tool
    import re
    
    @tool
    def memory_tool(action: str, user_id: str = None) -> str:
        """記憶管理工具，管理用戶對話記憶
        
        當用戶問「我剛剛做了什麼」、「我剛才做了什麼」、「剛才我做了什麼」等問題時，必須使用此工具查看對話歷史。
        
        Args:
            action: 操作類型，必須是 'view'（查看）、'clear'（清除）或 'stats'（統計）
            user_id: 用戶ID，如果為 None，會自動從 input_text 中提取「用戶ID: line_XXXX」，使用完整的 line_XXXX
        
        使用範例：
        - memory_tool('view') 或 memory_tool('view', 'line_U3fae4f436edf551db5f5c6773c98f8c7') 查看該用戶的對話歷史
        - memory_tool('clear') 或 memory_tool('clear', 'line_U3fae4f436edf551db5f5c6773c98f8c7') 清除該用戶的對話記憶
        
        重要：
        1. 如果沒有提供 user_id，系統會自動從 input_text 中提取
        2. 當用戶詢問過去做了什麼時，必須先調用此工具查看記憶，然後根據記憶內容回答
        3. 建議直接調用 memory_tool('view')，讓系統自動提取 user_id
        """
        try:
            # 如果沒有提供 user_id，嘗試從線程本地變量或 input_text 中提取
            extracted_user_id = user_id
            if not extracted_user_id or extracted_user_id == "default":
                # 優先從線程本地變量獲取
                if hasattr(_thread_local, 'current_user_id'):
                    extracted_user_id = _thread_local.current_user_id
                    logger.info(f"從線程本地變量獲取到 user_id: {extracted_user_id}")
                
                # 如果還是沒有，嘗試從線程本地變量的 input_text 中提取
                if (not extracted_user_id or extracted_user_id == "default") and hasattr(_thread_local, 'current_input_text'):
                    input_text = _thread_local.current_input_text
                    user_id_match = re.search(r'用戶ID:\s*(line_[^\s\n]+)', str(input_text))
                    if user_id_match:
                        extracted_user_id = user_id_match.group(1)
                        logger.info(f"從線程本地變量的 input_text 提取到 user_id: {extracted_user_id}")
                
                # 如果還是沒有找到，嘗試從調用棧查找（fallback）
                if not extracted_user_id or extracted_user_id == "default":
                    import sys
                    frame = sys._getframe(2)  # 向上查找兩層
                    
                    # 在不同層級查找 input_text
                    for i in range(5):
                        try:
                            frame_vars = frame.f_locals
                            if 'input_text' in frame_vars:
                                input_text = frame_vars['input_text']
                                user_id_match = re.search(r'用戶ID:\s*(line_[^\s\n]+)', str(input_text))
                                if user_id_match:
                                    extracted_user_id = user_id_match.group(1)
                                    logger.info(f"從調用棧提取到 user_id: {extracted_user_id}")
                                    break
                            elif 'input' in frame_vars:
                                input_val = frame_vars['input']
                                if isinstance(input_val, str):
                                    user_id_match = re.search(r'用戶ID:\s*(line_[^\s\n]+)', input_val)
                                    if user_id_match:
                                        extracted_user_id = user_id_match.group(1)
                                        logger.info(f"從調用棧的 input 提取到 user_id: {extracted_user_id}")
                                        break
                        except Exception:
                            pass
                        
                        try:
                            frame = frame.f_back
                        except:
                            break
                
                # 如果還是沒有找到，嘗試使用 input_text_getter（如果提供）
                if (not extracted_user_id or extracted_user_id == "default") and input_text_getter:
                    try:
                        input_text = input_text_getter()
                        user_id_match = re.search(r'用戶ID:\s*(line_[^\s\n]+)', str(input_text))
                        if user_id_match:
                            extracted_user_id = user_id_match.group(1)
                    except Exception:
                        pass
            
            # 如果還是沒有找到，使用 default（但會記錄警告）
            if not extracted_user_id or extracted_user_id == "default":
                logger.warning(f"無法提取 user_id，使用 default。action={action}")
                extracted_user_id = "default"
            
            # 調用其他.py文件中的實現
            from src.memory_manager import manage_user_memory
            return manage_user_memory(action, extracted_user_id)
        except ImportError:
            return "記憶管理系統暫時不可用，請稍後再試。"
        except Exception as e:
            logger.error(f"記憶管理工具執行失敗: {e}")
            return f"記憶管理失敗：{str(e)}"
    
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

def create_linebot_goal_view_tool():
    """創建 LINE Bot 目標查看工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_goal_view_tool(line_id: str) -> str:
        """LINE Bot 目標查看工具 - 查看學習目標
        
        Args:
            line_id: LINE 用戶 ID
        """
        from src.dashboard import get_goals_for_linebot
        
        return get_goals_for_linebot(line_id)
    
    return linebot_goal_view_tool

def create_linebot_goal_add_tool():
    """創建 LINE Bot 目標新增工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_goal_add_tool(line_id: str, goal: str) -> str:
        """LINE Bot 目標新增工具 - 新增學習目標
        
        Args:
            line_id: LINE 用戶 ID
            goal: 要新增的目標內容（從用戶訊息中提取）
        """
        from src.dashboard import add_goal_for_linebot
        
        if not goal or not goal.strip():
            return "❌ 請提供目標內容！"
        
        return add_goal_for_linebot(line_id, goal.strip())
    
    return linebot_goal_add_tool

def create_linebot_goal_delete_tool():
    """創建 LINE Bot 目標刪除工具"""
    from langchain_core.tools import tool
    
    @tool
    def linebot_goal_delete_tool(line_id: str, goal_index: int) -> str:
        """LINE Bot 目標刪除工具 - 刪除學習目標
        
        Args:
            line_id: LINE 用戶 ID
            goal_index: 目標編號（從 1 開始，對應用戶看到的編號）
        """
        from src.dashboard import delete_goal_for_linebot
        
        if not goal_index or goal_index < 1:
            return "❌ 請提供有效的目標編號（從 1 開始）！"
        
        return delete_goal_for_linebot(line_id, goal_index)
    
    return linebot_goal_delete_tool

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
            return "標題為必填欄位！"
        
        # AI 已經計算好時間，直接使用
        if not event_date or event_date == "":
            return "請提供事件時間！"
        
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
            title: 事件標題（如果為空、'一樣'、'不變'等，會自動從原始事件獲取）
            content: 事件內容（如果為空，會自動從原始事件獲取）
            event_date: 事件日期時間 (支援格式: 2024-01-01 10:00, 2024-01-01T10:00, 2024-01-01)
        """
        from src.dashboard import update_calendar_event_for_linebot
        
        # AI 已經計算好時間，直接使用
        if not event_date or event_date == "":
            return "請提供事件時間！"
        
        # title 和 content 可以為空，工具會自動從原始事件獲取
        return update_calendar_event_for_linebot(line_id, event_id, title or '', content or '', event_date)
    
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
            from src.website_guide import get_website_guide
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


@web_ai_bp.route('/execute-action', methods=['POST', 'OPTIONS'])
def execute_action_endpoint():
    """執行操作（供前端調用）"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 204
        
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'success': False, 'message': '未提供token'}), 401
        
        token = auth_header.split(" ")[1]
        
        data = request.get_json(silent=True) or {}
        action_id = data.get('action_id')
        params = data.get('params', {})
        
        if not action_id:
            return jsonify({'success': False, 'message': '缺少操作ID'}), 400
        
        # 整合 execute_action 邏輯
        from .website_guide import get_action, validate_action_params
        
        # 獲取操作配置
        action = get_action(action_id)
        if not action:
            return jsonify({
                'token': refresh_token(token),
                'success': False,
                'message': f'找不到操作配置: {action_id}'
            }), 400
        
        # 驗證參數
        is_valid, missing = validate_action_params(action_id, params)
        if not is_valid:
            return jsonify({
                'token': refresh_token(token),
                'success': False,
                'message': f'缺少必要參數: {", ".join(missing)}'
            }), 400
        
        # 根據操作類型構建結果
        result = {
            "success": True,
            "action": action_id,
            "action_type": action.action_type.value,
            "params": params
        }
        
        if action.route:
            result["route"] = action.route
        
        if action.api_endpoint:
            result["api_endpoint"] = action.api_endpoint
            result["api_method"] = action.api_method or "POST"
            
            # 構建 API 請求體
            api_body = {}
            if action.id == "create_university_quiz":
                api_body = {
                    "type": "pastexam",
                    "school": params.get("university"),
                    "year": params.get("year"),
                    "department": params.get("department")
                }
            elif action.id == "create_knowledge_quiz":
                api_body = {
                    "type": "knowledge",
                    "topic": params.get("knowledge_point"),
                    "difficulty": params.get("difficulty"),
                    "count": params.get("question_count")
                }
            result["api_body"] = api_body
        
        return jsonify({
            'token': refresh_token(token),
            'success': result.get('success', False),
            'data': result
        })
    except Exception as e:
        logger.error(f"❌ 執行操作失敗: {e}")
        return jsonify({'success': False, 'message': f'執行操作失敗：{str(e)}'}), 500


