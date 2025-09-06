#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG AI 教學系統 - 重構版本
簡化函數結構，真正實現 RAG 功能
"""

from tool.api_keys import get_api_key
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import chromadb
from chromadb.config import Settings
from accessories import init_gemini

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 全局變數 ====================

# 學習會話管理
learning_sessions = {}

# 會話持久化文件路徑
import os
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learning_sessions.json")

def save_sessions_to_file():
    """將會話保存到文件目前先註解掉之後我再看看是不是要用"""
    # 創建可序列化的會話副本
    serializable_sessions = {}
    for key, session in learning_sessions.items():
        serializable_session = session.copy()
        # 確保 datetime 對象被轉換為字符串
        if 'created_at' in serializable_session and isinstance(serializable_session['created_at'], datetime):
            serializable_session['created_at'] = serializable_session['created_at'].isoformat()
        serializable_sessions[key] = serializable_session
    
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_sessions, f, ensure_ascii=False, indent=2)

def load_sessions_from_file():
    """從文件載入會話"""
    if not os.path.exists(SESSION_FILE):
        return
    
    with open(SESSION_FILE, 'r', encoding='utf-8') as f:
        sessions = json.load(f)
        # 轉換回字典
        for key, value in sessions.items():
            # 確保 datetime 字符串被正確處理
            if 'created_at' in value and isinstance(value['created_at'], str):
                try:
                    value['created_at'] = datetime.fromisoformat(value['created_at'])
                except ValueError:
                    # 如果解析失敗，使用當前時間
                    value['created_at'] = datetime.now()
            learning_sessions[key] = value

# 在模組載入時載入會話
load_sessions_from_file()

def cleanup_old_sessions(max_age_hours: int = 24):
    """清理過期的會話，避免記憶體洩漏"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_key, session_data in learning_sessions.items():
        if 'created_at' in session_data:
            try:
                created_time = (datetime.fromisoformat(session_data['created_at']) 
                              if isinstance(session_data['created_at'], str) 
                              else session_data['created_at'])
                
                age_hours = (current_time - created_time).total_seconds() / 3600
                if age_hours > max_age_hours:
                    expired_sessions.append(session_key)
            except:
                # 如果時間解析失敗，保留會話
                pass
    
    # 刪除過期會話
    for session_key in expired_sessions:
        del learning_sessions[session_key]
    
    return len(expired_sessions)

# 定期清理會話（每小時清理一次）
import threading
import time

def auto_cleanup_sessions():
    """自動清理會話的後台任務"""
    while True:
        try:
            time.sleep(3600)  # 每小時執行一次
            cleanup_old_sessions()
        except Exception as e:
            print(f"⚠️ 自動清理失敗：{e}")

# 啟動自動清理（在後台執行）
cleanup_thread = threading.Thread(target=auto_cleanup_sessions, daemon=True)
cleanup_thread.start()

# 教學風格提示詞
TEACHER_STYLE = """你是一位經驗豐富的資管系教授，正在一對一輔導學生，幫助學生透過逐步引導方式理解考題與資管系相關知識，確保學生真正掌握概念，而不只是背誦答案。

**你的教學原則**：
- **從核心開始**：從與這道題目最直接相關的核心概念開始，而不是從最基礎的概念開始
- **概念連貫性**：確保每個問題都與題目核心概念相關，避免概念跳脫
- **蘇格拉底式提問**：透過引導性問題，讓學生自己思考並得出答案
- **精確評分**：每次學生回答後，給出0-100分的具體評分，評估學生對題目的理解程度
- **理解驗證**：當學生理解程度達到95分時，要求學生用自己的話重新解釋題目和答案

**評分標準**：
- **0-30分**：完全不理解或回答錯誤，需要從基礎概念開始解釋
- **31-60分**：有基本概念但理解不深，需要進一步引導和解釋
- **61-80分**：理解較好，能回答相關問題，可以進入應用層面
- **81-90分**：理解很好，接近完全掌握，可以深入探討細節
- **90-99分**：進入反向教導階段，學生用自己的話向AI解釋題目和答案，AI不斷修正錯誤直到99分
- **99分**：可以進入下一題

**教學流程**：
1. **核心概念確認階段**：評估學生對題目核心概念的掌握程度
2. **相關概念引導階段**：圍繞核心概念，逐步引導學生理解相關知識點
3. **應用理解階段**：讓學生將理解應用到題目情境中
4. **反向教導階段**：當理解程度達到90分時，學生用自己的話向AI解釋題目和答案，AI不斷修正學生錯誤以及知識盲點
5. **完成階段**：達到99分時，學生完全掌握，可以進入下一題

**回應要求**：
- 語氣親切自然，如同真正的老師
- 每次回答後，必須給出0-100分的具體評分，格式為「評分：[分數]分」
- 根據評分給出相應的引導問題或進入下一階段
- 當評分達到90分時，進入反向教導階段，要求學生用自己的話向AI解釋題目和答案
- 在反向教導階段，AI要不斷修正學生說錯或理解錯的地方，直到達到99分
- 嚴禁使用任何格式化標題，直接以自然段落呈現內容

**學習評估標準**：
- 學生能用自己的話解釋題目核心概念
- 學生能用自己的話解釋答案的邏輯
- 學生能舉出相關的例子或應用
- 學生表現出對題目和答案的深度理解

現在，讓我們開始一場有深度的學習對話。
"""

# ==================== 核心功能 ====================

def handle_tutoring_conversation(user_email: str, question: str, user_answer: str, correct_answer: str, user_input: str = None, grading_feedback: dict = None) -> dict:
    """
    處理AI教學對話 - 重構版本
    整合了會話管理、知識檢索、AI回應和學習進度更新
    新增：支援AI批改的評分反饋
    """
    try:
        # 1. 獲取或創建會話
        session = get_or_create_session(user_email, question)
        conversation_history = session.get('conversation_history', [])
        
        # 2. 判斷是否為初始化（基於更新前的對話歷史）
        original_history_length = len(conversation_history)
        is_initial = original_history_length == 0
        
        # 3. 構建AI提示詞
        if is_initial:
            # 初始化：分析學生答案，提出引導問題
            prompt = build_initial_prompt(question, user_answer, correct_answer, grading_feedback)
        else:
            # 後續對話：基於學生回答進行教學
            prompt = build_followup_prompt(question, user_answer, correct_answer, user_input, conversation_history, grading_feedback)
        
        # 4. 增強提示詞（RAG功能）
        enhanced_prompt = enhance_prompt_with_knowledge(prompt, question)
        
        # 5. 調用AI獲取回應
        ai_response = call_gemini_api(enhanced_prompt)
        
        # 6. 清理AI回應（移除評分等內部信息）
        clean_response = clean_ai_response(ai_response)
        
        # 7. 記錄對話歷史（先記錄，再更新學習進度）
        if user_input:
            conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": clean_response})
        session['conversation_history'] = conversation_history
        
        # 8. 更新學習進度（只在非初始化階段）
        if not is_initial:
            update_learning_progress(session, question, ai_response, conversation_history)
        else:
            print(f"🎯 初始化階段，跳過評分更新")
        
        # 9. 保存會話到全局字典（使用與 get_or_create_session 相同的邏輯）
        clean_question = question.strip().replace('\n', ' ').replace('\r', ' ')
        # 組合用戶email和題目hash，確保唯一性
        session_key = f"{user_email}_question_{hash(clean_question)}"
        
        # 確保會話被正確保存
        learning_sessions[session_key] = session
        
        # 保存到文件以確保持久化
        #save_sessions_to_file()
        
        # 9. 返回結果
        return {
            'response': clean_response,
            'learning_stage': session.get('learning_stage', 'core_concept_confirmation'),
            'understanding_level': session.get('understanding_level', 0),
            'concept_progress': session.get('concept_progress', [])
        }
        
    except Exception as e:
        logger.error(f"❌ 教學對話處理失敗: {e}")
        return {
            'response': '抱歉，系統出現問題，請稍後再試。',
            'learning_stage': 'core_concept_confirmation',
            'understanding_level': 0,
            'concept_progress': []
        }

def update_learning_progress(session: dict, question: str, ai_response: str, conversation_history: list):
    """
    更新學習進度 - 整合版本
    包含評分提取、智能評分計算和學習階段更新
    """
    try:
        # 1. 提取AI評分
        score = extract_score_from_response(ai_response)
        if score is None:
            print(f"⚠️ 未提取到評分，跳過學習進度更新")
            return
        
        # 2. 計算對話次數
        # 對話歷史格式：user, assistant, user, assistant, ...
        # 所以對話次數 = (總長度 - 1) // 2（減1是因為最後一條是AI回應）
        conversation_count = (len(conversation_history) - 1) // 2

        
        # 3. 智能評分計算
        old_level = session.get('understanding_level', 0)
        smart_score = calculate_smart_score(old_level, score, conversation_count)
        session['understanding_level'] = smart_score

        
        # 4. 更新學習階段
        old_stage = session.get('learning_stage', 'core_concept_confirmation')
        new_stage = determine_learning_stage(smart_score)
        session['learning_stage'] = new_stage
        
        if old_stage != new_stage:
            print(f"🔄 學習階段更新：{old_stage} → {new_stage}")
        
        # 5. 記錄進度
        record_progress(session, score, smart_score, new_stage)
        
        # 6. 保存更新後的會話
        #save_sessions_to_file()

        
    except Exception as e:
        logger.error(f"❌ 學習進度更新失敗: {e}")

def calculate_smart_score(current_score: int, ai_score: int, conversation_count: int = 0) -> int:
    """
    智能評分計算 - 實現新的評分邏輯
    """
    try:

        # 初始化階段：不給分數
        if conversation_count == 0:
            return 0
        
        # 第一個問題：給予基礎評分 0-95
        elif conversation_count == 1:
            base_score = min(95, max(0, ai_score))
            return base_score
        
        # 後續問題：基於當前分數給予加分
        else:
            if ai_score > current_score:
                bonus = min(10, ai_score - current_score)
                new_score = min(95, current_score + bonus)
                return new_score
            else:
                penalty = min(2, current_score - ai_score)
                new_score = max(0, current_score - penalty)
                return new_score
            
    except Exception as e:
        logger.error(f"❌ 智能評分計算失敗: {e}")
        return current_score

# ==================== RAG 功能 ====================

def should_search_database(question: str) -> bool:
    """
    智能判斷是否需要查詢向量資料庫
    過濾掉非學術問題，只對MIS相關的技術概念進行知識檢索
    """
    try:
        # 使用簡單的關鍵字判斷，避免調用AI進行判斷
        mis_keywords = [
            '網路', '拓樸', '資料庫', '演算法', '程式設計', '作業系統',
            '記憶體', 'CPU', '硬碟', '軟體', '硬體', '系統分析',
            '資訊管理', '電腦科學', '資料結構', '網路安全', '雲端計算',
            '大數據', '人工智慧', '機器學習', '資料庫管理', '網路管理',
            '系統設計', '軟體工程', '專案管理', '企業資源規劃', '客戶關係管理'
        ]
        
        # 檢查問題是否包含MIS相關關鍵字
        question_lower = question.lower()
        has_mis_content = any(keyword in question_lower for keyword in mis_keywords)
        
        # 過濾掉明顯的非學術問題
        non_academic_patterns = [
            '你好', '早安', '晚安', '謝謝', '不客氣', '你是誰', '自我介紹',
            '天氣', '心情', '閒聊', '1+1', '簡單計算'
        ]
        
        is_non_academic = any(pattern in question_lower for pattern in non_academic_patterns)
        
        should_search = has_mis_content and not is_non_academic
        
        return should_search
        
    except Exception as e:
        logger.error(f"❌ RAG判斷失敗: {e}")
        return False  # 預設不檢索

def enhance_prompt_with_knowledge(prompt: str, question: str) -> str:
    """
    使用RAG增強提示詞 - 真正的RAG功能
    """
    try:
        # 1. 判斷是否需要檢索知識
        if not should_search_database(question):
            return prompt
        
        # 2. 初始化向量資料庫
        client, collection = init_vector_database()
        if not collection:
            print(f"⚠️ 向量資料庫不可用，使用原始提示詞")
            return prompt
        
        # 3. 檢索相關知識
        knowledge_results = search_knowledge(question, top_k=2)  # 減少檢索數量
        
        if knowledge_results:
            # 4. 構建知識增強部分
            knowledge_context = "\n\n**相關知識參考：**\n"
            for i, result in enumerate(knowledge_results, 1):
                knowledge_context += f"{i}. {result['content'][:200]}...\n"
            
            # 5. 增強提示詞
            enhanced_prompt = prompt + knowledge_context
            return enhanced_prompt
        else:
            return prompt
            
    except Exception as e:
        logger.error(f"❌ RAG增強失敗: {e}")
        return prompt

def search_knowledge(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    從向量資料庫檢索知識 - 真正的RAG檢索
    自動將中文問題翻譯成英文進行檢索
    """
    try:
        client, collection = init_vector_database()
        if not collection:
            return []
        
        # 1. 先將中文問題翻譯成英文（因為向量資料庫是英文教材）
        english_query = translate_to_english(query)
        
        # 2. 執行相似性搜索
        results = collection.query(
            query_texts=[english_query],
            n_results=top_k
        )
        
        # 3. 格式化結果
        knowledge_items = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                knowledge_items.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                    'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0
                })
        
        return knowledge_items
        
    except Exception as e:
        logger.error(f"❌ 知識檢索失敗: {e}")
        return []

def translate_to_english(text: str) -> str:
    # 使用Gemini進行翻譯
    model = init_gemini(model_name = 'gemini-1.5-flash')
    prompt = f"""請將以下中文問題翻譯成英文，保持專業術語的準確性：

中文問題：{text}

請只返回英文翻譯，不要添加任何解釋或額外文字。"""
    
    response = model.generate_content(prompt)
    
    # 檢查回應是否有效
    if not response or not hasattr(response, 'text'):
        return "Translation failed: Invalid response format"
    
    # 檢查安全評級
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
            # 檢查是否有安全問題
            for rating in candidate.safety_ratings:
                if rating.category in ['HARM_CATEGORY_HARASSMENT', 'HARM_CATEGORY_HATE_SPEECH', 
                                     'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_DANGEROUS_CONTENT']:
                    if rating.probability in ['HIGH', 'MEDIUM']:
                        return "Translation failed: Response blocked by safety filter"
    
    # 安全地存取回應文字
    try:
        if response.text:
            english_text = response.text.strip()
            return english_text
        else:
            return "Translation failed: Empty response"
    except Exception as text_error:
        logger.error(f"無法存取回應文字: {text_error}")
        return "Translation failed: Cannot access response text"


# ==================== 輔助功能 ====================

def get_or_create_session(user_email: str, question: str) -> dict:
    """獲取或創建學習會話"""
    # 使用用戶email + 題目內容的組合，確保每個用戶的每道題目都有獨立會話
    clean_question = question.strip().replace('\n', ' ').replace('\r', ' ')
    # 組合用戶email和題目hash，確保唯一性
    session_key = f"{user_email}_question_{hash(clean_question)}"
    
    # 顯示當前用戶的所有會話
    user_sessions = [key for key in learning_sessions.keys() if key.startswith(f"{user_email}_")]
    
    # 顯示會話統計信息
    if learning_sessions:
        # 統計不同用戶的會話數量
        user_counts = {}
        for key in learning_sessions.keys():
            if '_question_' in key:
                user_part = key.split('_question_')[0]
                user_counts[user_part] = user_counts.get(user_part, 0) + 1
        

    
    # 檢查是否已存在會話
    if session_key in learning_sessions:
        existing_session = learning_sessions[session_key]
        return existing_session
    
    # 如果沒有找到會話，創建新會話
    learning_sessions[session_key] = {
        'user_email': user_email,
        'question': question,
        'conversation_history': [],
        'understanding_level': 0,
        'learning_stage': 'core_concept_confirmation',
        'concept_progress': [],
        'created_at': datetime.now().isoformat()
    }
    
    # 立即保存到文件
    #save_sessions_to_file()

    
    return learning_sessions[session_key]

def build_initial_prompt(question: str, user_answer: str, correct_answer: str, grading_feedback: dict = None) -> str:
    """構建初始化提示詞"""
    
    # 如果有AI批改的評分反饋，加入提示詞中
    feedback_section = ""
    if grading_feedback:
        feedback_section = f"""

**AI批改評分反饋（請參考使用）：**
- 優點：{grading_feedback.get('strengths', '無')}
- 需要改進：{grading_feedback.get('weaknesses', '無')}
- 學習建議：{grading_feedback.get('suggestions', '無')}
- 評分說明：{grading_feedback.get('explanation', '無')}
"""
    
    return f"""{TEACHER_STYLE}

**題目：** {question}
**學生答案：** {user_answer}
**正確答案：** {correct_answer}{feedback_section}

請分析學生的答案，找出需要改進的地方，並提出一個具體的引導問題來開始教學。

**重要：** 初始化階段不給分數，只提出引導問題。

**回應要求：**
- 語氣親切自然，如同真正的老師
- 分析學生答案的優缺點（可參考AI批改反饋）
- 提出具體的引導問題
- 不要給出評分（初始化階段）
- 絕對不要包含「評分：」字樣

請現在生成開場白："""

def build_followup_prompt(question: str, user_answer: str, correct_answer: str, user_input: str, conversation_history: list, grading_feedback: dict = None) -> str:
    """構建後續對話提示詞"""
    # 獲取當前學習階段指導
    current_stage = 'core_concept_confirmation'  # 預設值
    
    # 從對話歷史中推斷當前階段，而不是重新查找會話
    if conversation_history:
        # 根據對話長度判斷階段
        if len(conversation_history) >= 6:  # 3輪對話
            current_stage = 'related_concept_guidance'
        elif len(conversation_history) >= 4:  # 2輪對話
            current_stage = 'core_concept_confirmation'
        else:
            current_stage = 'core_concept_confirmation'
    
    stage_guidance = get_stage_guidance(current_stage)
    
    # 如果有AI批改的評分反饋，加入提示詞中
    feedback_section = ""
    if grading_feedback:
        feedback_section = f"""

**AI批改評分反饋（請參考使用）：**
- 優點：{grading_feedback.get('strengths', '無')}
- 需要改進：{grading_feedback.get('weaknesses', '無')}
- 學習建議：{grading_feedback.get('suggestions', '無')}
- 評分說明：{grading_feedback.get('explanation', '無')}
"""
    
    return f"""{TEACHER_STYLE}

**題目：** {question}
**正確答案：** {correct_answer}
**學生最新回答：** {user_input}{feedback_section}

**對話歷史：**
{format_conversation_history(conversation_history)}

**當前學習階段指導：**
{stage_guidance}

請基於學生的回答進行教學指導，並按照以下步驟進行：

**教學步驟：**
1. **評估學生回答**：分析學生回答的質量
2. **給出正確答案**：如果學生回答錯誤，直接給出正確答案
3. **提出下一個問題**：基於當前進度，提出相關的延伸問題
4. **給出評分**：根據學生回答質量給予適當分數

**重要要求：**
- 不要重複問學生「你知道嗎？」或「你覺得呢？」
- 如果學生回答錯誤，直接給出正確答案
- 避免陷入循環提問
- 每次都要給出評分

**評分邏輯：**
1. 第一個問題：根據學生回答質量，給予0-95分的基礎評分
2. 後續問題：基於當前分數，給予適當加分（1-10分）
3. 達到95分時：進入反向教導階段
4. 反向教導完成：直接給出100分

**重要提醒：**
- 你必須在回應的最後給出評分，格式為「評分：[分數]分」
- 評分範圍：0-100分
- 根據學生回答的質量給予適當分數
- 這是強制要求，必須遵守！
- 如果沒有評分，系統將無法正常工作！

**評分格式示例：**
同學，你的回答很好！讓我們繼續深入探討...

評分：85分

**再次強調：**
- 回應的最後必須包含「評分：[分數]分」
- 這是系統運作的必要條件
- 請嚴格遵守評分格式要求！

請現在分析學生的回答並提供教學指導："""

def format_conversation_history(conversation_history: list) -> str:
    """格式化對話歷史"""
    if not conversation_history:
        return "無"
    
    formatted = ""
    for i, msg in enumerate(conversation_history[-4:], 1):  # 只顯示最近4條
        role = "學生" if msg['role'] == 'user' else "AI導師"
        formatted += f"{i}. {role}: {msg['content'][:100]}...\n"
    
    return formatted

def determine_learning_stage(understanding_level: int) -> str:
    """根據理解程度確定學習階段"""
    if understanding_level >= 95:
        return 'understanding_verification'      # 反向教導
    elif understanding_level >= 80:
        return 'application_understanding'       # 應用理解
    elif understanding_level >= 60:
        return 'application_understanding'       # 應用理解
    elif understanding_level >= 30:
        return 'related_concept_guidance'        # 相關概念引導
    else:
        return 'core_concept_confirmation'       # 核心概念確認

def get_stage_guidance(stage: str) -> str:
    """根據學習階段提供指導"""
    stage_guidance = {
        'core_concept_confirmation': f"""
您目前處於核心概念確認階段。請：
- 從這道題目最核心的概念開始提問
- 評估學生對題目核心概念的掌握程度
- 如果學生對核心概念不清楚，請先解釋核心概念
- 避免跳脫到不相關的基礎概念，絕對必須保持與題目的相關性
""",
        'related_concept_guidance': f"""
您目前處於相關概念引導階段。請：
- 圍繞題目核心概念，逐步引導學生理解相關知識點
- 確保每個問題都與題目核心概念相關
- 你可以使用具體例子幫助學生理解抽象概念
- 觀察學生的回答與反饋，適時調整問題難度
""",
        'application_understanding': f"""
您目前處於應用理解階段。請：
- 讓學生將理解應用到題目情境中
- 提供與題目相關的練習問題或案例
- 觀察學生是否能正確應用概念到題目
- 如果學生應用正確，可以進入理解驗證階段
""",
        'understanding_verification': f"""
您目前處於理解驗證階段。請：
- 要求學生用自己的話重新解釋題目和答案
- 評估學生是否真正理解了題目和答案的邏輯
- 如果學生解釋清楚，可以進入下一題或下一階段
- 如果學生解釋不清楚，你直接給出正確答案，幫助學生更加理解題目跟答案
"""
    }
    
    return stage_guidance.get(stage, stage_guidance['core_concept_confirmation'])

def get_stage_display_name(stage: str) -> str:
    """獲取學習階段的中文顯示名稱"""
    stage_names = {
        'core_concept_confirmation': '核心概念確認',
        'related_concept_guidance': '相關概念引導',
        'application_understanding': '應用理解',
        'understanding_verification': '理解驗證',
        'unknown': '未知階段'
    }
    return stage_names.get(stage, stage)

def record_progress(session: dict, score: int, smart_score: int, stage: str):
    """記錄學習進度"""
    if 'concept_progress' not in session:
        session['concept_progress'] = []
    
    session['concept_progress'].append({
        'stage': stage,
        'understanding_level': smart_score,
        'score': score,
        'timestamp': datetime.now().isoformat()
    })

def extract_score_from_response(ai_response: str) -> int:
    """從AI回應中提取評分"""
    try:
        # 尋找評分格式：評分：[分數]分
        score_patterns = [
            r'評分[：:]\s*(\d+)分',
            r'評分[：:]\s*(\d+)',
            r'分數[：:]\s*(\d+)分',
            r'分數[：:]\s*(\d+)',
            r'(\d+)分',
            r'評分[：:]\s*(\d+)',
            r'理解程度[：:]\s*(\d+)',
            r'評分[：:]\s*(\d+)\s*分',
            r'評分[：:]\s*(\d+)\s*',
            r'(\d+)\s*分',
            r'評分[：:]\s*(\d+)',
            r'分數[：:]\s*(\d+)'
        ]
        
        for i, pattern in enumerate(score_patterns):
            match = re.search(pattern, ai_response)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score
                else:
                    print(f"⚠️ 評分超出範圍：{score}")
        
        print(f"❌ 未找到任何評分格式")
        numbers = re.findall(r'\d+', ai_response)
        
        # 如果沒有找到評分，嘗試從最後幾行中尋找
        lines = ai_response.strip().split('\n')
        last_lines = lines[-3:] if len(lines) >= 3 else lines
        
        for line in reversed(last_lines):
            if '評分' in line or '分數' in line:
                # 嘗試提取數字
                numbers_in_line = re.findall(r'\d+', line)
                if numbers_in_line:
                    score = int(numbers_in_line[0])
                    if 0 <= score <= 100:
                        return score
        
        return None
        
    except Exception as e:
        logger.error(f"❌ 評分提取失敗: {e}")
        return None

def clean_ai_response(ai_response: str) -> str:
    """清理AI回應，移除評分等內部信息"""
    try:
        # 移除評分格式
        cleaned = re.sub(r'評分[：:]\s*\d+分', '', ai_response)
        # 清理多餘空行
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        if not cleaned:
            return "同學，我已經分析了您的回答。讓我們繼續學習吧！"
        
        return cleaned
        
    except Exception as e:
        logger.error(f"❌ 回應清理失敗: {e}")
        return ai_response

# ==================== 初始化函數 ====================

def init_vector_database():
    """初始化向量資料庫"""
    try:
        import os
        
        # 獲取當前文件的絕對路徑
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 構建向量資料庫的絕對路徑
        db_path = os.path.join(current_dir, "data", "knowledge_db", "chroma_db")
        
        
        chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 獲取或創建集合
        collection = chroma_client.get_or_create_collection(
            name="textbook_knowledge",  # 使用有數據的集合
            metadata={"hnsw:space": "cosine"}
        )
        
        return chroma_client, collection
        
    except Exception as e:
        logger.warning(f"⚠️ 向量資料庫初始化失敗: {e}")
        return None, None


def call_gemini_api(prompt: str) -> str:
    """調用Gemini API"""
    try:
        model = init_gemini(model_name = 'gemini-1.5-flash')
        if not model:
            return "抱歉，AI服務暫時不可用，請稍後再試。"
        
        # 設置生成參數，確保回應完整
        generation_config = {
            'max_output_tokens': 4000,  # 增加最大輸出長度
            'temperature': 0.7,
            'top_p': 0.8,
            'top_k': 40
        }
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # 檢查回應是否有效
        if not response or not hasattr(response, 'text'):
            return "抱歉，AI回應格式不正確，請稍後再試。"
        
        # 檢查安全評級
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                # 檢查是否有安全問題
                for rating in candidate.safety_ratings:
                    if rating.category in ['HARM_CATEGORY_HARASSMENT', 'HARM_CATEGORY_HATE_SPEECH', 
                                         'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_DANGEROUS_CONTENT']:
                        if rating.probability in ['HIGH', 'MEDIUM']:
                            return "抱歉，AI回應被安全過濾器阻擋，請稍後再試。"
        
        # 安全地存取回應文字
        try:
            return response.text
        except Exception as text_error:
            logger.error(f"無法存取回應文字: {text_error}")
            return "抱歉，無法存取AI回應，請稍後再試。"
        
    except Exception as e:
        logger.error(f"❌ Gemini API調用失敗: {e}")
        return "抱歉，AI回應生成失敗，請稍後再試。"
