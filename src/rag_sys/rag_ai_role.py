import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import google.generativeai as genai
import os
from tool.api_keys import get_api_key
GEMINI_AVAILABLE = True

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 全局變數 ====================

# 學習會話管理
learning_sessions = {}

# 教學風格提示詞
TEACHER_STYLE = """你是一位經驗豐富的資管系教授，正在一對一輔導學生，幫助學生透過逐步引導方式理解考題與資管系相關知識，確保學生真正掌握概念，而不只是背誦答案。

**你的教學原則**：
- **引導式對話**：透過一步步提問，引導學生自行思考並得出答案，而非直接給予解答。
- **針對性反饋**：精準評價學生回答，肯定其正確部分，並禮貌地指出需要補充或糾正之處。
- **概念拆解與類比**：當學生不理解時，將複雜概念拆解為更小步驟，並使用生活化例子或類比幫助理解。
- **動態調整難度**：根據學生回答判斷其掌握度，靈活調整問題難度，促進深度學習。
- **避免重複**：回答中絕不重複學生已經說過或你之前說過的內容，力求簡潔有效。

**回應要求**：
- 語氣親切自然，如同真正的老師。
- 回答後，必須提出一個清晰的引導問題，推進學生對當前概念的理解。
- 嚴禁使用任何格式化標題（如 "💡 詳細回答"），直接以自然段落呈現內容。
- 禁止暴露你的思考過程。

現在，讓我們開始一場有深度的學習對話。
"""

# ==================== 初始化函數 ====================

def init_vector_database():
    """初始化向量資料庫"""
    try:
        import chromadb
        from chromadb.config import Settings
        
        
        chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )

        
        # 獲取或創建集合
        collection = chroma_client.get_or_create_collection(
            name="mis_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        
        return chroma_client, collection
        
    except Exception as e:
        logger.warning(f"⚠️ 向量資料庫初始化失敗: {e}")
        return None, None

def init_gemini():
    """初始化Gemini模型"""
    if not GEMINI_AVAILABLE:
        raise ImportError("Gemini不可用，請安裝google-generativeai")

    try:
        api_key = get_api_key()
        genai.configure(api_key=api_key)
        
        # 創建模型
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        return model
        
    except Exception as e:
        print(f"❌ Gemini初始化失敗: {e}")
        raise

# ==================== 智能判斷函數 ====================

def should_search_database(question: str) -> bool:
    """智能判斷是否需要查詢向量資料庫"""
    model = init_gemini()
    prompt = f"""
你是一個智能助理，需要判斷學生的問題是否需要查詢MIS（資訊管理系）的學術資料庫。

問題：「{question}」

請仔細分析這個問題，然後根據以下標準判斷：

**需要查詢資料庫的情況**（學術問題）：
- 詢問MIS相關的技術概念：作業系統、資料庫、網路、演算法、程式設計
- 詢問具體技術術語：FIFO、LIFO、死鎖、排程、記憶體管理等
- 詢問系統分析、資訊管理、電腦科學相關概念
- 以「什麼是...」開頭的技術問題
- 詢問技術原理、方法、應用的問題

**不需要查詢資料庫的情況**（非學術問題）：
- 問候語：你好、早安、晚安
- 自我介紹相關：你是誰、自我介紹、你叫什麼名字
- 感謝語：謝謝、不客氣
- 日常對話：天氣、心情、閒聊
- 基本數學：1+1、簡單計算
- 一般常識：不涉及MIS專業知識的問題
- 回答AI的提問

請只回答「需要查詢」或「不需要查詢」，不要解釋。
"""

    response = model.generate_content(prompt)
    if response and hasattr(response, 'text') and response.text:
        result = response.text.strip()

        # 修復字符串匹配邏輯 - 先檢查「不需要查詢」
        should_search = False  # 預設不查詢

        if "不需要查詢" in result:
            should_search = False
        elif "需要查詢" in result:
            should_search = True
        else:
            should_search = False  # 預設不查詢
        return should_search
    else:
        logging.warning("⚠️ AI無回應，使用備用判斷")
        return False

def get_topic_knowledge(question: str) -> str:
    """智能獲取主題相關知識"""
    try:
        # 智能判斷是否需要查詢向量資料庫
        if not should_search_database(question):
            return ""

                # 先翻譯成英文搜索，因為向量資料庫是英文教材
        english_question = translate_to_english(question)

        # 使用向量資料庫搜索
        search_results = search_knowledge(english_question, top_k=3)

        if search_results:
            # 提取前3個結果的內容
            knowledge = "\n".join([
                result.get('content', '')[:400]
                for result in search_results[:4]
            ])
            return knowledge
        return ""
    except Exception as e:
        logging.warning(f"獲取主題知識失敗: {e}")
    return ""
def translate_to_english(text: str) -> str:
    """翻譯成英文"""
    try:
        gemini_model = init_gemini()
        prompt = f"Translate to English: {text}"
        response = gemini_model.generate_content(prompt)
        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
    except Exception as e:
        logging.warning(f"翻譯失敗: {e}")
    return text

def search_knowledge(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """搜索相關知識點"""
    try:
        chroma_client, collection = init_vector_database()
        if not collection:
            logger.warning("⚠️ 向量資料庫未初始化")
            return []

        # 使用ChromaDB搜索
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )

        # 格式化結果
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 0

                formatted_results.append({
                    'content': doc,
                    'metadata': metadata,
                    'similarity': 1 - distance,  # 轉換為相似度
                    'title': metadata.get('title', '相關知識'),
                    'source': metadata.get('source_file', '教學資料'),
                    'chapter': metadata.get('chapter', '相關章節'),
                    'keywords': metadata.get('keywords', [])
                })
        return formatted_results

    except Exception as e:
        logger.error(f"❌ 搜索知識點時發生錯誤: {e}")
        return []


# ==================== 核心功能函數 ====================

def create_session_from_quiz_result(session_id: str, user_id: str) -> dict:
    """從測驗結果創建學習會話"""
    try:
        # 從會話ID提取測驗結果ID
        parts = session_id.split('_')
        if len(parts) < 3:
            raise ValueError("無效的會話ID格式")
        
        # 新格式: learning_{timestamp}_{result_35}
        # 需要提取 result_35 格式
        if len(parts) >= 4 and parts[-2] == 'result':
            result_id = f"{parts[-2]}_{parts[-1]}"
        else:
            result_id = parts[-1]
        

        
        # 直接查詢資料庫獲取測驗結果
        from accessories import sqldb, mongo
        from sqlalchemy import text
        import json
        
        with sqldb.engine.connect() as conn:
            # 解析 result_id 格式：result_<quiz_history_id>
            if not result_id.startswith('result_'):
                raise ValueError("無效的測驗結果ID格式")
            
            try:
                quiz_history_id = int(result_id.split('_')[1])
            except (ValueError, IndexError) as e:
                raise ValueError("無法解析測驗歷史ID")
            
            # 查詢測驗結果
            history_result = conn.execute(text("""
                SELECT qh.id, qh.quiz_template_id, qh.user_email, qh.quiz_type, 
                       qh.total_questions, qh.answered_questions, qh.correct_count, qh.wrong_count,
                       qh.accuracy_rate, qh.average_score, qh.total_time_taken, 
                       qh.submit_time, qh.status, qh.created_at,
                       qt.question_ids
                FROM quiz_history qh
                LEFT JOIN quiz_templates qt ON qh.quiz_template_id = qt.id
                WHERE qh.id = :quiz_history_id
            """), {
                'quiz_history_id': quiz_history_id
            }).fetchone()
            
            if not history_result:
                raise ValueError(f"未找到測驗歷史記錄，quiz_history_id: {quiz_history_id}")
            
            # 獲取錯題詳情
            error_result = conn.execute(text("""
                SELECT mongodb_question_id, user_answer, score, time_taken, created_at
                FROM quiz_errors 
                WHERE quiz_history_id = :quiz_history_id
                ORDER BY created_at
            """), {
                'quiz_history_id': quiz_history_id
            }).fetchall()
            
            # 構建錯題字典
            error_dict = {}
            for error in error_result:
                question_id = error[0]
                user_answer = error[1]
                error_dict[question_id] = {
                    'user_answer': user_answer,
                    'score': error[2],
                    'time_taken': error[3]
                }
            
            # 解析題目ID列表
            question_ids_str = history_result[14]
            print(f"🔍 原始題目ID字串: {question_ids_str}")
            
            if question_ids_str:
                try:
                    question_ids = json.loads(question_ids_str)
                    print(f"🔍 解析後的題目ID: {question_ids}")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失敗: {e}")
                    question_ids = []
            else:
                print("❌ 題目ID字串為空")
                question_ids = []
            
            print(f"🔍 最終題目ID數量: {len(question_ids)}")
            
            # 構建題目陣列
            questions = []
            for i, question_id in enumerate(question_ids):
                try:
                    print(f"🔍 處理題目 {i+1}: {question_id}")
                    # 將字串轉換為 ObjectId
                    from bson import ObjectId
                    question_obj = mongo.db.exam.find_one({'_id': ObjectId(question_id)})
                    
                    if question_obj:
                        # 檢查是否為錯題
                        is_correct = question_id not in error_dict
                        user_answer = error_dict.get(question_id, {}).get('user_answer', '')
                        
                        # 解析用戶答案JSON
                        try:
                            if user_answer and user_answer.startswith('{'):
                                answer_data = json.loads(user_answer)
                                actual_user_answer = answer_data.get('answer', user_answer)
                            else:
                                actual_user_answer = user_answer
                        except json.JSONDecodeError:
                            actual_user_answer = user_answer
                        
                        # 調試：檢查 MongoDB 欄位
                        print(f"🔍 MongoDB 題目欄位: {list(question_obj.keys())}")
                        print(f"🔍 題目內容: {question_obj.get('question_text', 'N/A')}")
                        print(f"🔍 備用欄位: {question_obj.get('question', 'N/A')}")
                        
                        question_data = {
                            'question_id': str(question_obj['_id']),
                            'question_text': question_obj.get('question_text', question_obj.get('question', '')),
                            'correct_answer': question_obj.get('answer', ''),
                            'user_answer': actual_user_answer or '未作答',
                            'is_correct': is_correct,
                            'topic': question_obj.get('topic', '計算機概論'),
                            'difficulty': question_obj.get('difficulty', 2)
                        }
                        
                        questions.append(question_data)
                        
                except Exception as e:
                    print(f"❌ 處理題目 {i+1} 時發生錯誤: {e}")
                    continue
            
            # 創建學習會話
            session_data = {
                'session_id': session_id,
                'user_id': user_id,
                'quiz_result_id': result_id,
                'questions': questions,
                'current_question_index': 0,
                'conversation_history': [],
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            learning_sessions[session_id] = session_data
            return session_data
            
    except Exception as e:
        raise

def handle_tutoring_conversation(session_id: str, question: str, user_id: str, mode: str = "general") -> str:
    """處理AI教學對話"""
    try:
        # 檢查會話是否存在
        if session_id not in learning_sessions:
            # 嘗試創建新會話
            try:
                create_session_from_quiz_result(session_id, user_id)
            except Exception as e:
                return f"學習會話不存在，請重新開始。錯誤: {str(e)}"
        
        session = learning_sessions[session_id]
        conversation_history = session.get('conversation_history', [])
        
        # 調試：檢查會話資料
        print(f"🔍 會話資料: {session}")
        print(f"🔍 題目數量: {len(session.get('questions', []))}")
        print(f"🔍 對話歷史長度: {len(conversation_history)}")
        print(f"🔍 用戶輸入: '{question}'")
        
        # 如果是第一次對話或用戶輸入為空，生成歡迎訊息
        if len(conversation_history) == 0:
            questions = session.get('questions', [])
            if questions:
                current_question = questions[0]
                print(f"🔍 當前題目: {current_question}")
                
                welcome_message = f"""🎓 歡迎來到 AI 智能教學！

我們將一起學習您的錯題。讓我們從第一道題開始：

**題目：** {current_question['question_text']}

我看到您的答案是「{current_question['user_answer']}」，正確答案是「{current_question['correct_answer']}」。

讓我們一起探討這個概念。您有什麼問題想問我嗎？"""
                
                session['conversation_history'].append({
                    'question': '系統歡迎訊息', 
                    'response': welcome_message, 
                    'timestamp': datetime.now().isoformat()
                })
                return welcome_message
        
        # 智能判斷是否需要查詢資料庫
        topic_knowledge = ""
        if should_search_database(question):
            topic_knowledge = get_topic_knowledge(question)
        
        # 初始化Gemini
        try:
            model = init_gemini()
        except Exception as e:
            return f"AI服務暫時不可用，請稍後再試。錯誤: {str(e)}"
        
        # 構建教學提示詞
        questions = session.get('questions', [])
        current_question = questions[session.get('current_question_index', 0)] if questions else None
        
        if current_question:
            # 如果有相關知識，加入提示詞
            knowledge_context = f"\n**相關知識背景：**\n{topic_knowledge}" if topic_knowledge else ""
            
            teaching_prompt = f"""
{TEACHER_STYLE}

**當前學習題目：**
題目：{current_question['question_text']}
用戶答案：{current_question['user_answer']}
正確答案：{current_question['correct_answer']}
主題：{current_question['topic']}
難度：{current_question['difficulty']}{knowledge_context}

**對話歷史：**
{chr(10).join([f"用戶: {conv['question']} - AI: {conv['response']}" for conv in conversation_history[-3:]])}

**用戶當前問題：** {question}

請根據以上信息，提供有針對性的教學指導。
"""
        else:
            teaching_prompt = f"""
{TEACHER_STYLE}

**用戶問題：** {question}

請提供有幫助的回答。
"""
        
        # 生成回應
        try:
            response = model.generate_content(teaching_prompt)
            ai_response = response.text
            
            # 更新會話歷史
            session['conversation_history'].append({
                'question': question,
                'response': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return ai_response
            
        except Exception as e:
            pass
    except Exception as e:
        return f"處理您的問題時發生錯誤，請稍後再試。錯誤: {str(e)}"

