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
from accessories import init_ai, init_ollama, init_gemini

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
- **格式要求**：可以使用Markdown格式來增強可讀性：
  - 使用 **粗體** 標記重點概念或關鍵詞
  - 使用換行來分隔不同段落，讓內容更清晰
  - 重要的步驟或要點可以用空行分隔
  - 語氣要自然流暢，像在跟學生聊天一樣

**學習評估標準**：
- 學生能用自己的話解釋題目核心概念
- 學生能用自己的話解釋答案的邏輯
- 學生能舉出相關的例子或應用
- 學生表現出對題目和答案的深度理解

現在，讓我們開始一場有深度的學習對話。
"""

# ==================== 核心功能 ====================

def handle_direct_answer(question: str, user_email: str = None) -> str:
    """
    直接解答問題 - 使用RAG檢索相關知識，直接給出答案和解釋
    不使用引導式教學，不進行評分，不管理學習進度
    
    Args:
        question: 用戶的問題
        user_email: 用戶email（可選，用於日誌記錄）
    
    Returns:
        str: 直接給出的答案和詳細解釋
    """
    try:
        logger.info(f"📝 開始直接解答問題: {question[:50]}...")
        
        # 構建直接解答的提示詞
        direct_answer_prompt = f"""你是一位資管系教授，負責直接解答學生的問題。

**你的任務**：
- 直接回答問題，不需要引導式提問
- 提供清晰、完整的解釋
- 如果問題涉及計算或步驟，詳細說明過程
- 語氣親切自然，但要直接明確
- 可以使用Markdown格式來增強可讀性（粗體、換行等）

**問題**：
{question}

請直接給出答案和詳細解釋："""

        # 使用RAG增強提示詞（檢索相關知識）
        enhanced_prompt = enhance_prompt_with_knowledge(direct_answer_prompt, question)
        logger.info(f"📚 RAG增強後的提示詞長度: {len(enhanced_prompt)} 字符")
        
        # 調用AI獲取回應
        ai_response = call_gemini_api(enhanced_prompt)
        
        # 檢查回應是否有效
        if not ai_response or not ai_response.strip():
            logger.warning(f"⚠️ AI回應為空，問題: {question[:50]}...")
            return "抱歉，AI無法生成回答。請重新提問或稍後再試。"
        
        logger.info(f"✅ 成功生成直接解答，回應長度: {len(ai_response)} 字符")
        
        # 直接返回回應（不需要清理評分等，因為直接解答不會有評分）
        return ai_response.strip()
            
    except Exception as e:
        logger.error(f"❌ 直接解答失敗: {e}", exc_info=True)
        return f"抱歉，處理問題時發生錯誤：{str(e)}"

def handle_tutoring_conversation(user_email: str, question: str, user_answer: str, correct_answer: str, user_input: str = None, grading_feedback: dict = None) -> dict:
    """
    處理AI教學對話 - 重構版本
    整合了會話管理、知識檢索、AI回應和學習進度更新
    新增：支援AI批改的評分反饋和學習分析資料
    """
    try:
        # 1. 獲取或創建會話
        session = get_or_create_session(user_email, question)
        conversation_history = session.get('conversation_history', [])

        # 2. 判斷是否為初始化（基於更新前的對話歷史）
        original_history_length = len(conversation_history)
        is_initial = original_history_length == 0

        # 3. 獲取學生的學習分析資料（如果可用）
        learning_context = get_student_learning_context(user_email, question)

        # 4. 構建AI提示詞
        if is_initial:
            # 初始化：分析學生答案，提出引導問題
            prompt = build_initial_prompt(question, user_answer, correct_answer, grading_feedback, learning_context)
        else:
            # 後續對話：基於學生回答進行教學
            prompt = build_followup_prompt(question, user_answer, correct_answer, user_input, conversation_history, grading_feedback, learning_context)
        
        # 4. 增強提示詞（RAG功能）
        enhanced_prompt = enhance_prompt_with_knowledge(prompt, question)
        
        # 5. 調用AI獲取回應（傳遞對話歷史以維護上下文）
        ai_response = call_gemini_api(enhanced_prompt, ai_type='gemini', conversation_history=conversation_history)
        
        # 5.5. 檢查並確保回應包含評分（如果不是初始化階段）
        if not is_initial and user_input:
            score = extract_score_from_response(ai_response)
            if score is None:
                # 如果沒有評分，嘗試添加一個預設評分
                logger.warning(f"⚠️ AI回應中沒有評分，嘗試添加預設評分")
                # 根據學生回答的長度和內容，給出一個基礎評分
                if len(user_input.strip()) > 10:
                    default_score = 50  # 基礎分數
                    ai_response = ai_response.rstrip() + f"\n\n評分：{default_score}分"
                    logger.info(f"✅ 已添加預設評分：{default_score}分")
                else:
                    default_score = 30  # 較低分數
                    ai_response = ai_response.rstrip() + f"\n\n評分：{default_score}分"
                    logger.info(f"✅ 已添加預設評分：{default_score}分")
        
        # 6. 清理AI回應（移除評分等內部信息）
        clean_response = clean_ai_response(ai_response)
        
        # 7. 記錄對話歷史（先記錄，再更新學習進度）
        if user_input:
            conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": clean_response})
        session['conversation_history'] = conversation_history
        
        # 8. 更新學習進度
        # 判斷邏輯：如果有 user_input，說明這是用戶的回答，應該更新評分
        # 初始化階段（is_initial = True）只有 AI 回應，沒有用戶輸入，所以跳過
        raw_score = None
        if user_input:  # 如果有用戶輸入，說明用戶回答了問題，應該評分
            raw_score = extract_score_from_response(ai_response)
            if raw_score is not None:
                print(f"📊 用戶回答後，提取到AI評分：{raw_score}分，開始更新學習進度")
                update_learning_progress(session, question, ai_response, conversation_history)
            else:
                print(f"⚠️ 用戶回答後未能提取評分，跳過學習進度更新")
        else:
            print(f"🎯 初始化階段（無用戶輸入），跳過評分更新")
        
        # 9. 保存會話到全局字典（使用與 get_or_create_session 相同的邏輯）
        clean_question = question.strip().replace('\n', ' ').replace('\r', ' ')
        # 組合用戶email和題目hash，確保唯一性
        session_key = f"{user_email}_question_{hash(clean_question)}"
        
        # 確保會話被正確保存
        learning_sessions[session_key] = session
        
        # 保存到文件以確保持久化
        #save_sessions_to_file()
        
        # 10. 計算對話次數
        conversation_count = (len(conversation_history) - 1) // 2
        
        # 11. 返回結果 - 優化版本，包含更多信息
        return {
            'response': clean_response,
            'raw_score': raw_score,  # AI 原始評分（可能為 None）
            'smart_score': session.get('understanding_level', 0),  # 智能評分後的結果
            'learning_stage': session.get('learning_stage', 'core_concept_confirmation'),
            'concept_progress': session.get('concept_progress', []),
            'conversation_count': conversation_count,
            'is_initial': is_initial
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
        # 對話歷史格式：assistant（初始）, user, assistant, user, assistant, ...
        # 計算實際的對話輪數：統計 user 角色的數量
        user_count = sum(1 for msg in conversation_history if msg.get('role') == 'user')
        conversation_count = user_count
        
        # 3. 獲取當前階段（在計算評分前）
        old_level = session.get('understanding_level', 0)
        old_stage = session.get('learning_stage', 'core_concept_confirmation')
        
        # 調試信息（在old_level定義後）
        print(f"📊 計算對話次數：對話歷史長度={len(conversation_history)}, user數量={user_count}, conversation_count={conversation_count}")
        print(f"📊 當前分數：{old_level}, AI評分：{score}")
        
        # 4. 智能評分計算（傳入當前階段和session，確保不跳階段並支援強制完成）
        # 注意：傳入當前的AI原始評分，用於強制完成判斷
        smart_score = calculate_smart_score(old_level, score, conversation_count, old_stage, session)
        session['understanding_level'] = smart_score
        
        
        # 5. 更新學習階段（基於新分數）
        new_stage = determine_learning_stage(smart_score)
        session['learning_stage'] = new_stage
        
        if old_stage != new_stage:
            print(f"🔄 學習階段更新：{old_stage} → {new_stage}")
        
        # 6. 記錄進度（在計算smart_score之後記錄，這樣下次計算時可以參考）
        record_progress(session, score, smart_score, new_stage)
        
        # 6. 保存更新後的會話
        #save_sessions_to_file()

        
    except Exception as e:
        logger.error(f"❌ 學習進度更新失敗: {e}")

def calculate_smart_score(current_score: int, ai_score: int, conversation_count: int = 0, current_stage: str = None, session: dict = None) -> int:
    """
    智能評分計算 - 不限制加分版本，帶強制完成機制
    確保每個階段都被經歷過，避免直接跳階段
    在理解驗證階段，如果持續表現良好，自動提升到99分
    """
    try:
        # 定義階段分數範圍（每個階段的上限 = 下一階段下限 - 1）
        # 最後一個階段（理解驗證）包含99分，因為99分是完成標記
        stage_ranges = {
            'core_concept_confirmation': (0, 39),      # 核心概念確認：0-39分
            'related_concept_guidance': (40, 69),     # 相關概念引導：40-69分
            'application_understanding': (70, 89),    # 應用理解：70-89分
            'understanding_verification': (90, 98),   # 理解驗證：90-98分（可通過機制達到99分）
            'completed': (99, 99)                      # 完成：99分（狀態標記）
        }
        
        # 初始化階段：不給分數
        if conversation_count == 0:
            return 0
        
        elif conversation_count == 1:
            # 第一個問題回答：根據AI評分調整為合理範圍（0-30分）
            # 將AI評分映射到0-30分的範圍，作為初始評分
            # 例如：85分 -> 30分，60分 -> 20分，30分 -> 10分
            if ai_score >= 80:
                initial_score = 30  # 高分映射到30分
            elif ai_score >= 60:
                initial_score = 20  # 中等分映射到20分
            elif ai_score >= 40:
                initial_score = 15  # 偏低分映射到15分
            elif ai_score >= 20:
                initial_score = 10  # 低分映射到10分
            else:
                initial_score = 5   # 很低分映射到5分
            
            print(f"✅ 第一個問題回答（conversation_count=1），AI評分{ai_score}分，調整為初始評分{initial_score}分")
            print(f"📊 當前分數：{current_score} -> 新分數：{initial_score}")
            return initial_score
        
        # 之後的邏輯完全基於階段，不依賴對話次數
        # 根據當前分數確定當前階段（如果未提供）
        if not current_stage:
            if current_score >= 90:
                current_stage = 'understanding_verification'
            elif current_score >= 70:
                current_stage = 'application_understanding'
            elif current_score >= 40:
                current_stage = 'related_concept_guidance'
            else:
                current_stage = 'core_concept_confirmation'
        
        # 獲取當前階段的範圍
        stage_min, stage_max = stage_ranges.get(current_stage, (0, 99))
        
        print(f"📊 當前階段：{current_stage}，階段範圍：{stage_min}-{stage_max}，當前分數：{current_score}，AI評分：{ai_score}")
        
        if ai_score > current_score:
            # AI 評分更高：不限制加分，但不超過當前階段上限
            # 特殊處理：理解驗證階段的強制完成機制
            if current_stage == 'understanding_verification':
                # 方案1：如果AI直接給99分，允許達到99分
                if ai_score >= 99:
                    print(f"🎯 AI評分99分，直接完成")
                    return 99
                
                # 方案2：如果達到98分且AI評分>=95，直接提升到99分
                if current_score >= 98 and ai_score >= 95:
                    print(f"🎯 達到98分且AI評分{ai_score}分，自動提升到99分（完成）")
                    return 99
                
                # 方案3：如果當前分數>=97分且AI評分>=95分，自動提升到99分（強制完成）
                if current_score >= 97 and ai_score >= 95:
                    print(f"🎯 理解驗證階段高分表現（當前{current_score}分，AI評{ai_score}分），自動提升到99分（完成）")
                    return 99
                
                # 方案4：追蹤高分成績，如果連續多次高分，自動完成
                if session:
                    concept_progress = session.get('concept_progress', [])
                    # 檢查最近在理解驗證階段的原始AI評分
                    recent_scores = [
                        p.get('score', 0) for p in concept_progress 
                        if p.get('stage') == 'understanding_verification'
                    ][-2:]  # 最近2次（不包括當前這次，因為還沒記錄）
                    
                    # 如果最近2次AI原始評分都>=95分，且當前也>=95分，自動提升到99分
                    if len(recent_scores) >= 2 and all(s >= 95 for s in recent_scores) and ai_score >= 95:
                        print(f"🎯 理解驗證階段連續多次高分（歷史{recent_scores}，當前AI評{ai_score}分），自動提升到99分（完成）")
                        return 99
                    
                    # 方案5：如果在理解驗證階段停留時間過長且表現良好，自動完成
                    # 統計在理解驗證階段的對話次數
                    verification_count = len([
                        p for p in concept_progress 
                        if p.get('stage') == 'understanding_verification'
                    ])
                    
                    # 如果在理解驗證階段已經有3次以上對話，且當前分數>=95，AI評分>=95，自動完成
                    if verification_count >= 3 and current_score >= 95 and ai_score >= 95:
                        print(f"🎯 理解驗證階段已進行{verification_count}次對話，表現良好（當前{current_score}分，AI評{ai_score}分），自動提升到99分（完成）")
                        return 99
            
            # 一般情況：基於當前階段推進
            # 如果還沒達到當前階段上限，在階段範圍內提升
            if current_score < stage_max:
                new_score = min(stage_max, ai_score)
                new_score = max(current_score, new_score)
                print(f"✅ 當前階段{current_stage}內提升：{current_score} -> {new_score}（階段上限：{stage_max}）")
                return new_score
            
            # 如果已經達到當前階段上限，且AI評分更高，進入下一個階段（不能跳階段）
            elif current_score >= stage_max and ai_score > stage_max:
                # 已達到階段上限，只允許進入下一個階段（逐步推進）
                stage_order = ['core_concept_confirmation', 'related_concept_guidance', 'application_understanding', 'understanding_verification', 'completed']
                current_index = stage_order.index(current_stage) if current_stage in stage_order else 0
                
                # 只進入下一個階段，不能跳階段
                if current_index < len(stage_order) - 1:
                    next_stage = stage_order[current_index + 1]
                    # 獲取下一個階段的範圍
                    next_min, next_max = stage_ranges.get(next_stage, (0, 99))
                    
                    # 進入下一個階段時，分數應該是下一個階段的最小值或AI評分（取較高者，但不超過階段上限）
                    # 例如：從39分（核心概念確認上限）進入下一個階段，應該至少40分（相關概念引導最小值）
                    new_score = max(next_min, min(next_max, ai_score))
                    print(f"🎯 達到階段上限{stage_max}分（{current_stage}），AI評{ai_score}分，進入下一個階段{next_stage}，新分數：{new_score}分（範圍：{next_min}-{next_max}）")
                    return new_score
                else:
                    # 已經是最後階段，直接返回階段上限
                    print(f"🎯 已達最後階段{current_stage}上限{stage_max}分，AI評{ai_score}分，保持{stage_max}分")
                    return stage_max
            else:
                # 已經達到階段上限，但AI評分沒有更高，保持當前分數
                print(f"⚠️ 已達階段上限{stage_max}分，AI評{ai_score}分 <= 當前{current_score}分，保持當前分數")
                return current_score
        else:
            # AI 評分更低：給予扣分（但扣分幅度較小），確保不低於階段最小值
            penalty = min(2, current_score - ai_score)
            new_score = max(stage_min, current_score - penalty)
            print(f"⚠️ AI評分{ai_score}分 <= 當前{current_score}分，扣分後：{new_score}分（階段範圍：{stage_min}-{stage_max}）")
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
    """將中文問題翻譯成英文"""
    try:
        # 使用 Gemini 進行翻譯
        model = init_ai(ai_type='gemini')
        if not model:
            return "Translation failed: Gemini service unavailable"

        prompt = f"""請將以下中文問題翻譯成英文，保持專業術語的準確性：

中文問題：{text}

請只返回英文翻譯，不要添加任何解釋或額外文字。"""

        # 使用 invoke 方法
        response = model.invoke(prompt)

        # 檢查回應是否有效
        if not response:
            return "Translation failed: Invalid response format"

        # 處理 AI 回應（支援 Ollama 和 Gemini）
        try:
            if hasattr(response, 'content') and response.content:
                english_text = str(response.content).strip()
            elif hasattr(response, 'text'):
                # 處理Gemini回應
                if callable(response.text):
                    english_text = str(response.text()).strip()
                else:
                    english_text = str(response.text).strip()
            else:
                english_text = str(response).strip()
        except Exception as e:
            logger.error(f"處理翻譯回應時出錯: {e}")
            return "Translation failed: Response processing error"

        if english_text:
            return english_text
        else:
            return "Translation failed: Empty response"
            # 嘗試其他方式提取文字
            english_text = str(response).strip()
            if english_text:
                return english_text
            else:
                return "Translation failed: Cannot extract response text"
                
    except Exception as e:
        logger.error(f"翻譯失敗: {e}")
        import traceback
        traceback.print_exc()
        return f"Translation failed: {str(e)}"


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

def get_student_learning_context(user_email: str, question: str) -> dict:
    """
    獲取學生的學習上下文資訊
    包括學習分析、歷史記錄、弱點分析等
    """
    try:
        context = {
            'learning_analytics': {},
            'historical_performance': {},
            'weakness_analysis': {},
            'recent_activities': []
        }

        # 嘗試從學習分析模組獲取資料
        try:
            from ..learning_analytics import get_student_quiz_records, get_concept_name_by_id
            quiz_records = get_student_quiz_records(user_email)

            if quiz_records:
                # 計算整體統計
                total_attempts = len(quiz_records)
                correct_attempts = sum(1 for record in quiz_records if record.get('is_correct', False))
                recent_records = quiz_records[:10]  # 最近10次
                recent_correct = sum(1 for record in recent_records if record.get('is_correct', False))

                context['learning_analytics'] = {
                    'total_attempts': total_attempts,
                    'overall_accuracy': correct_attempts / total_attempts if total_attempts > 0 else 0,
                    'recent_accuracy': recent_correct / len(recent_records) if recent_records else 0,
                    'recent_attempts': len(recent_records)
                }
        except Exception as e:
            logger.warning(f"無法獲取學習分析資料: {e}")

        # 嘗試獲取相關概念的歷史表現
        try:
            # 基於問題內容嘗試推斷相關概念
            # 這裡簡化處理，可以根據實際需要擴展
            context['historical_performance'] = {
                'recent_accuracy': f"{context['learning_analytics'].get('recent_accuracy', 0):.1%}",
                'common_mistakes': ['概念理解不夠深入', '計算過程有誤', '邏輯推理不足'],  # 預設常見錯誤
                'improvement_trend': '持續學習中'
            }
        except Exception as e:
            logger.warning(f"無法獲取歷史表現資料: {e}")

        # 弱點分析 - 基於答題記錄分析
        try:
            analytics = context['learning_analytics']
            if analytics.get('recent_accuracy', 0) < 0.6:  # 準確率低於60%
                context['weakness_analysis'] = {
                    'weak_concepts': ['基礎概念理解', '問題分析能力', '解題技巧'],
                    'improvement_suggestions': [
                        '建議多做練習題來鞏固基礎',
                        '可以請求AI導師的詳細講解',
                        '參考教材重新學習相關概念'
                    ],
                    'performance_level': '需要加強' if analytics.get('recent_accuracy', 0) < 0.4 else '進步空間大'
                }
            else:
                context['weakness_analysis'] = {
                    'weak_concepts': [],
                    'improvement_suggestions': ['繼續保持良好的學習習慣'],
                    'performance_level': '表現良好'
                }
        except Exception as e:
            logger.warning(f"無法獲取弱點分析資料: {e}")

        return context

    except Exception as e:
        logger.error(f"獲取學生學習上下文失敗: {e}")
        return {
            'learning_analytics': {},
            'historical_performance': {},
            'weakness_analysis': {},
            'recent_activities': []
        }

def build_initial_prompt(question: str, user_answer: str, correct_answer: str, grading_feedback: dict = None, learning_context: dict = None) -> str:
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

    # 添加學習上下文資訊
    context_section = ""
    if learning_context:
        analytics = learning_context.get('learning_analytics', {})
        weakness = learning_context.get('weakness_analysis', {})

        if analytics.get('attention_items') or weakness.get('weak_concepts'):
            context_section = f"""

**學生的學習背景資訊（請參考制定教學策略）：**
"""

            # 弱點概念
            if weakness.get('weak_concepts'):
                weak_list = weakness['weak_concepts'][:3]  # 只顯示前3個
                context_section += f"- 學生較弱的概念：{', '.join(weak_list)}\n"

            # 學習分析
            if analytics.get('weak_domains'):
                weak_domains = analytics['weak_domains'][:2]  # 只顯示前2個
                context_section += f"- 需要關注的領域：{', '.join(weak_domains)}\n"

            # 改進建議
            if analytics.get('improvement_items'):
                improvement = analytics['improvement_items'][:2]  # 只顯示前2個
                context_section += "- 整體學習建議：" + "；".join([item.get('suggestion', '') for item in improvement if item.get('suggestion')]) + "\n"

    return f"""{TEACHER_STYLE}

**題目：** {question}
**學生答案：** {user_answer}
**正確答案：** {correct_answer}{feedback_section}{context_section}

請分析學生的答案，找出需要改進的地方，並提出一個具體的引導問題來開始教學。

**重要：** 初始化階段不給分數，只提出引導問題。

**回應要求：**
- 語氣親切自然，如同真正的老師
- 分析學生答案的優缺點（可參考AI批改反饋）
- 根據學生的學習背景制定個性化教學策略
- 提出具體的引導問題
- 不要給出評分（初始化階段）
- 絕對不要包含「評分：」字樣

請現在生成開場白："""

def build_followup_prompt(question: str, user_answer: str, correct_answer: str, user_input: str, conversation_history: list, grading_feedback: dict = None, learning_context: dict = None) -> str:
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

**⚠️ 重要：你必須在回應的最後一行給出評分，格式為「評分：XX分」，這是系統運作的必要條件！**

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
- **絕對不要重複問學生已經回答過的問題**
- **仔細閱讀對話歷史，確保不會重複提問**
- 如果學生已經回答過某個問題，直接基於學生的回答進行下一步教學
- 不要重複問學生「你知道嗎？」或「你覺得呢？」
- 如果學生回答錯誤，直接給出正確答案
- 避免陷入循環提問
- 每次都要給出評分
- **如果對話歷史中已經有相關問題和回答，請直接使用該信息，不要再次提問**

**評分邏輯：**
1. 第一個問題：根據學生回答質量，給予0-95分的基礎評分
2. 後續問題：基於當前分數，給予適當加分（1-10分）
3. 達到95分時：進入反向教導階段
4. 反向教導完成：直接給出100分

**⚠️ 強制評分要求（必須遵守）：**
- **必須**在回應的最後一行給出評分
- **必須**使用格式：「評分：[分數]分」（例如：評分：85分）
- 評分範圍：0-100分
- 根據學生回答的質量給予適當分數
- **如果沒有評分，系統將無法正常工作！**
- **即使學生回答正確或表現優秀，也必須給出評分！**

**評分邏輯指南：**
- 如果學生回答正確或理解正確：給予高分（70-95分）
- 如果學生回答部分正確：給予中等分數（40-69分）
- 如果學生回答錯誤但顯示思考：給予基礎分數（20-39分）
- 如果學生完全理解錯誤：給予低分（0-19分）

**評分格式示例（必須照此格式）：**
同學，你的分析非常詳細！你正確指出了這個操作在特定情況下會為0。

評分：90分

**最後再次強調：**
- 回應的最後一行**必須**是「評分：[數字]分」
- 不要使用其他格式，如「得分：XX」或「分數：XX」
- 必須使用中文冒號「：」和「分」字
- 這是系統運作的必要條件，**絕對不能省略！**

**⚠️ 最終提醒：**
你的回應格式必須是：
[教學內容]

評分：[0-100之間的數字]分

請現在分析學生的回答並提供教學指導，記住：回應的最後一行必須是「評分：XX分」格式！"""

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
    """根據理解程度確定學習階段 - 優化版本"""
    if understanding_level >= 99:
        return 'completed'                       # 完成階段（99分）
    elif understanding_level >= 90:
        return 'understanding_verification'      # 反向教導（90-98分，可達到99分）
    elif understanding_level >= 70:
        return 'application_understanding'       # 應用理解（70-89分）
    elif understanding_level >= 40:
        return 'related_concept_guidance'        # 相關概念引導（40-69分）
    else:
        return 'core_concept_confirmation'       # 核心概念確認（0-39分）

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
您目前處於理解驗證階段（反向教導）。請：
- 要求學生用自己的話重新解釋題目和答案
- 評估學生是否真正理解了題目和答案的邏輯
- 如果學生解釋不清楚，你直接給出正確答案，幫助學生更加理解題目跟答案
- 持續修正學生的錯誤和知識盲點，直到達到 99 分
""",
        'completed': f"""
恭喜！學生已經完全理解這道題目，達到 99 分。
可以進入下一題了。
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
        'completed': '學習完成',
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
        # 尋找評分格式：評分：[分數]分（支援多種格式）
        score_patterns = [
            r'評分[：:]\s*(\d+)\s*分',  # 評分：85分 或 評分: 85分
            r'評分[：:]\s*(\d+)',        # 評分：85
            r'評分[為是]\s*(\d+)\s*分',  # 評分為85分 或 評分是85分
            r'得分[：:]\s*(\d+)\s*分',  # 得分：85分
            r'分數[：:]\s*(\d+)\s*分',  # 分數：85分
            r'(\d+)\s*分\s*$',           # 最後一行的「85分」
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
        
        # 優先檢查回應的最後幾行（評分通常在最後）
        lines = ai_response.strip().split('\n')
        last_lines = '\n'.join(lines[-5:]) if len(lines) > 5 else ai_response  # 檢查最後5行
        
        # 如果找到評分，返回分數
        for pattern in score_patterns:
            # 先檢查最後幾行（更準確）
            match = re.search(pattern, last_lines, re.IGNORECASE | re.MULTILINE)
            if not match:
                # 如果最後幾行沒找到，檢查全文
                match = re.search(pattern, ai_response, re.IGNORECASE | re.MULTILINE)
            
            if match:
                score = int(match.group(1))
                # 確保分數在合理範圍內
                if 0 <= score <= 100:
                    logger.info(f"✅ 成功提取評分：{score}分（模式匹配）")
                    return score
                else:
                    logger.warning(f"⚠️ 提取到異常評分：{score}，超出0-100範圍")
                    continue  # 繼續嘗試其他模式
        
        # 如果所有模式都沒匹配到，記錄詳細警告
        logger.warning(f"⚠️ 未能從AI回應中提取評分")
        logger.warning(f"   回應長度：{len(ai_response)}字符")
        logger.warning(f"   最後200字符：{ai_response[-200:]}")
        
        # 作為備用方案，嘗試從最後幾行提取數字
        for line in reversed(lines[-3:] if len(lines) >= 3 else lines):
            if '評分' in line or '分數' in line or '得分' in line:
                # 嘗試提取數字
                numbers_in_line = re.findall(r'\d+', line)
                if numbers_in_line:
                    score = int(numbers_in_line[0])
                    if 0 <= score <= 100:
                        logger.info(f"✅ 備用方案提取評分：{score}分（從行：{line[:50]}）")
                        return score
        
        logger.error(f"❌ 完全無法提取評分，回應內容：{ai_response[-300:]}")
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


def call_gemini_api(prompt: str, ai_type: str = 'gemini', conversation_history: list = None) -> str:
    """
    調用 AI API（預設使用 Ollama，可選擇 Gemini）
    
    Args:
        prompt: 提示詞
        ai_type: 'gemini' (預設) 或 'ollama'
        conversation_history: 對話歷史列表（可選），格式：[{'role': 'user', 'content': '...'}, ...]
    """
    try:
        # 使用指定的AI類型
        model = init_ai(ai_type=ai_type)
        if not model:
            return f"抱歉，{ai_type.upper()} 服務暫時不可用，請稍後再試。"
            
            # 如果有對話歷史，構建消息列表；否則使用單一提示詞
            if conversation_history and len(conversation_history) > 0:
                # 將對話歷史轉換為 Ollama 格式
                messages = []
                for msg in conversation_history:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    # 轉換角色名稱
                    if role == 'user':
                        ollama_role = 'user'
                    elif role == 'assistant':
                        ollama_role = 'assistant'
                    else:
                        ollama_role = 'user'
                    messages.append({
                        'role': ollama_role,
                        'content': content
                    })
                # 添加當前提示詞作為最後一條用戶消息
                messages.append({
                    'role': 'user',
                    'content': prompt
                })
                # 使用消息列表調用
                response = model.invoke(messages)
            else:
                # 使用 LangChain 的 invoke 方法
                response = model.invoke(prompt)
        else:
            # 使用 Gemini
            model = init_gemini(model_name='gemini-2.5-flash')
            if not model:
                return "抱歉，Gemini 服務暫時不可用，請稍後再試。"
            # 設置生成參數
            generation_config = {
                'max_output_tokens': 8192,
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40
            }
            response = model.generate_content(prompt, generation_config=generation_config)
        logger.info(f"📥 AI API回應接收，類型: {type(response).__name__}")
        
        # 檢查回應是否有效
        if not response:
            logger.error(f"❌ {ai_type.upper()} API返回空回應")
            return "抱歉，AI回應格式不正確，請稍後再試。"
        
        # 處理 Ollama 回應（LangChain AIMessage）
        if ai_type == 'ollama':
            try:
                if hasattr(response, 'content'):
                    text = response.content
                    if text and text.strip():
                        logger.info(f"✅ 從response.content獲取回應，長度: {len(text)} 字符")
                        return text.strip()
            except Exception as e:
                logger.debug(f"無法從response.content獲取: {e}")
        
        # 處理 Gemini 回應
        else:
            # 方法1：直接檢查text屬性
            try:
                if hasattr(response, 'text'):
                    text = response.text
                    if text and text.strip():
                        logger.info(f"✅ 從response.text獲取回應，長度: {len(text)} 字符")
                        return text.strip()
            except Exception as e:
                logger.debug(f"無法從response.text獲取: {e}")
            
            # 方法2：檢查candidates
            try:
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        if hasattr(content, 'parts'):
                            text_parts = []
                            for part in content.parts:
                                if hasattr(part, 'text'):
                                    text_parts.append(part.text)
                            if text_parts:
                                full_text = ''.join(text_parts).strip()
                                if full_text:
                                    logger.info(f"✅ 從candidates.content.parts獲取回應，長度: {len(full_text)} 字符")
                                    return full_text
            except Exception as e:
                logger.debug(f"無法從candidates提取: {e}")
        
        # 嘗試直接轉為字符串
        try:
            response_str = str(response)
            if response_str and response_str.strip() and len(response_str) > 10:
                logger.info(f"✅ 從字符串轉換獲取回應，長度: {len(response_str)} 字符")
                return response_str.strip()
        except Exception as e:
            logger.debug(f"無法轉換為字符串: {e}")
        
        logger.error(f"❌ 無法從回應中提取文字")
        logger.error(f"   回應類型: {type(response).__name__}")
        logger.error(f"   回應屬性: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        return "抱歉，無法存取AI回應，請稍後再試。"
        
    except Exception as e:
        logger.error(f"❌ {ai_type.upper()} API調用失敗: {e}", exc_info=True)
        return "抱歉，AI回應生成失敗，請稍後再試。"
