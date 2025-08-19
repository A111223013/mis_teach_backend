import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import google.generativeai as genai
import os

# 導入配置
try:
    from . import config
    from .config import Config
    GEMINI_AVAILABLE = True
except ImportError:
    import config
    from config import Config
    GEMINI_AVAILABLE = True

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 全局變數 ====================

# 學習會話管理
learning_sessions = {}  # 存儲學習會話

# 核心變數
original_question = ""
context = ""
topic_knowledge = ""

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

# 蘇格拉底式教學提示詞
SOCRATIC_TEACHING_STYLE = """你是一位採用蘇格拉底式教學法的資管系教授。你的教學目標是通過提問引導學生自己發現答案，而不是直接告訴他們。

**蘇格拉底式教學原則**：
1. **提問引導**：通過一系列精心設計的問題，引導學生逐步思考
2. **啟發思考**：幫助學生發現自己知識中的漏洞和矛盾
3. **自主發現**：讓學生通過自己的思考得出結論
4. **循序漸進**：從簡單問題開始，逐步深入複雜概念

**教學流程**：
- 先了解學生的基本理解
- 提出引導性問題
- 根據學生回答調整問題難度
- 幫助學生發現概念間的聯繫
- 引導學生總結和歸納

**回應要求**：
- 每次只提出1-2個問題
- 問題要具體、清晰、有針對性
- 根據學生回答調整教學策略
- 鼓勵學生表達自己的想法
"""

# 一般回答模式提示詞
GENERAL_ANSWER_STYLE = """你是一位資管系教授，負責回答學生的問題。請提供清晰、準確、有幫助的回答。

**回答原則**：
1. **準確性**：確保信息準確無誤
2. **清晰性**：用簡單明了的語言解釋複雜概念
3. **實用性**：提供實際應用的例子
4. **完整性**：涵蓋問題的核心要點

**回答結構**：
- 直接回答問題
- 提供相關例子或解釋
- 指出關鍵概念
- 建議進一步學習方向
"""

# ==================== 初始化函數 ====================

def init_gemini():
    """初始化Gemini模型"""
    if not GEMINI_AVAILABLE:
        raise ImportError("Gemini不可用，請安裝google-generativeai")

    try:
        # 使用後端的API密鑰管理器
        try:
            # 嘗試多種導入方式
            api_key = None
            try:
                # 方式1：直接導入
                from tool.api_keys import get_api_key
                api_key = get_api_key()
                print(f"🔑 方式1成功：直接導入API密鑰管理器")
            except ImportError:
                try:
                    # 方式2：添加路徑後導入
                    import sys
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
                    from tool.api_keys import get_api_key
                    api_key = get_api_key()
                    print(f"🔑 方式2成功：添加路徑後導入API密鑰管理器")
                except ImportError:
                    try:
                        # 方式3：使用絕對路徑
                        import sys
                        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                        sys.path.insert(0, backend_path)
                        from tool.api_keys import get_api_key
                        api_key = get_api_key()
                        print(f"🔑 方式3成功：使用絕對路徑導入API密鑰管理器")
                    except ImportError as e:
                        print(f"⚠️ 所有導入方式都失敗: {e}")
                        api_key = None
            
            if api_key:
                print(f"🔑 成功獲取API密鑰: {api_key[:20]}...")
            else:
                raise ImportError("無法導入API密鑰管理器")
                
        except Exception as e:
            print(f"⚠️ 無法使用API密鑰管理器: {e}")
            # 如果無法導入，使用配置檔案中的預設值
            api_key = config.GEMINI_CONFIG.get('api_key')
            print(f"⚠️ 回退到配置檔案中的API Key")
        
        if not api_key:
            raise ValueError("未設置Gemini API Key")
        
        print(f"✅ 成功獲取Gemini API Key")
        
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(config.GEMINI_CONFIG.get('model', 'gemini-1.5-flash'))
        model_config = config.GEMINI_CONFIG
        return gemini_model, model_config
    except Exception as e:
        print(f"❌ Gemini初始化失敗: {e}")
        raise RuntimeError(f"Gemini初始化失敗: {e}")

def init_vector_database():
    """初始化向量資料庫連接"""
    try:
        import chromadb
        from chromadb.config import Settings

        chroma_client = chromadb.PersistentClient(
            path=config.CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 獲取或創建集合
        collection = chroma_client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        
        return chroma_client, collection
    except Exception as e:
        logging.error(f"❌ 向量資料庫初始化失敗: {e}")
        raise RuntimeError(f"向量資料庫初始化失敗: {e}")

# ==================== 智能判斷函數 ====================

def should_search_database(question: str) -> bool:
    """智能判斷是否需要查詢向量資料庫"""
    try:
        # 使用Gemini判斷是否需要查詢資料庫
        gemini_model, _ = init_gemini()
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

        response = gemini_model.generate_content(prompt)
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
    except Exception as e:
        logging.warning(f"AI判斷失敗: {e}")
        # 預設情況下，只對明確的學術關鍵詞進行查詢
        academic_keywords = [
            '作業系統', 'operating system', '資料庫', 'database',
            '網路', 'network', 'FIFO', 'LIFO', '演算法', 'algorithm',
            '程式設計', 'programming', '死鎖', 'deadlock', '排程', 'scheduling',
            '記憶體', 'memory', 'cpu', '處理器', 'processor'
        ]
        # 排除一般對話關鍵詞
        general_keywords = [
            '你好', 'hello', '你是誰', 'who are you', '謝謝', 'thank you',
            '自我介紹', 'introduce', '天氣', 'weather', '心情', 'mood'
        ]

        question_lower = question.lower()

        # 如果包含一般對話關鍵詞，不查詢
        if any(keyword in question_lower for keyword in general_keywords):
            return False

        # 如果包含學術關鍵詞，查詢
        should_search = any(keyword in question_lower for keyword in academic_keywords)
        return should_search

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
        else:
            logging.info("⚠️ 未找到相關知識點")
    except Exception as e:
        logging.warning(f"獲取主題知識失敗: {e}")
    return ""

def translate_to_english(text: str) -> str:
    """翻譯成英文"""
    try:
        gemini_model, _ = init_gemini()
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
    # 檢查會話ID格式：learning_user_{timestamp}_{resultId}
    if not session_id.startswith('learning_user_'):
        return None
        
    try:
        # 提取resultId
        parts = session_id.split('_')
        if len(parts) < 4:
            return None
            
        result_id = '_'.join(parts[3:])
        
        # 直接從資料庫查詢測驗結果數據，避免循環導入
        from accessories import sqldb, mongo
        from sqlalchemy import text
        import json
        
        # 解析 result_id 格式：result_<quiz_history_id>
        if not result_id.startswith('result_'):
            return None
        
        try:
            quiz_history_id = int(result_id.split('_')[1])
        except (ValueError, IndexError):
            return None
        
        print(f"📝 RAG系統正在查詢測驗結果，quiz_history_id: {quiz_history_id}")
        
        with sqldb.engine.connect() as conn:
            # 查詢 quiz_history 和 quiz_templates
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
                print(f"⚠️ RAG系統未找到測驗歷史記錄")
                return None
            
            # 獲取錯題詳情
            error_result = conn.execute(text("""
                SELECT mongodb_question_id, user_answer, score, time_taken, created_at
                FROM quiz_errors 
                WHERE quiz_history_id = :quiz_history_id
                ORDER BY created_at
            """), {
                'quiz_history_id': quiz_history_id
            }).fetchall()
            
            if not error_result:
                print(f"⚠️ RAG系統未找到錯題記錄")
                return None
            
            # 從MongoDB獲取題目詳情
            exam_collection = mongo.db.exam
            
            # 創建會話
            wrong_questions = []
            for i, error in enumerate(error_result):
                try:
                    mongodb_question_id = error[0]
                    user_answer = error[1]
                    
                    # 解析用戶答案 JSON 格式
                    try:
                        if user_answer and user_answer.startswith('{'):
                            answer_data = json.loads(user_answer)
                            actual_user_answer = answer_data.get('answer', user_answer)
                        else:
                            actual_user_answer = user_answer
                    except json.JSONDecodeError:
                        actual_user_answer = user_answer
                    
                    # 從MongoDB獲取題目詳情
                    from bson import ObjectId
                    question_detail = exam_collection.find_one({"_id": ObjectId(mongodb_question_id)})
                    
                    if question_detail:
                        wrong_questions.append({
                            'question_text': question_detail.get('question_text', f'題目 {i+1}'),
                            'user_answer': actual_user_answer or '未作答',
                            'correct_answer': question_detail.get('answer', '無參考答案'),
                            'topic': question_detail.get('topic', '計算機概論')
                        })
                except Exception as e:
                    print(f"❌ RAG系統處理錯題 {i+1} 時發生錯誤: {e}")
                    continue
            
            if not wrong_questions:
                print(f"⚠️ RAG系統無法載入任何錯題")
                return None
            
            session = {
                'session_id': session_id,
                'user_id': user_id,
                'wrong_questions': wrong_questions,
                'current_question_index': 0,
                'completed_questions': [],
                'start_time': datetime.now().isoformat(),
                'status': 'active',
                'student_level': 'beginner',
                'conversation_history': [],
                'current_topic_understanding': 0
            }
            
            # 保存會話
            learning_sessions[session_id] = session
            print(f"✅ RAG系統創建學習會話: {session_id}, 包含 {len(wrong_questions)} 道錯題")
            
            return session
            
    except Exception as e:
        print(f"❌ RAG系統創建學習會話失敗: {e}")
        return None

def handle_tutoring_conversation(session_id: str, question: str, user_id: str, mode: str = "general") -> str:
    """處理教學對話"""
    # 獲取或創建學習會話
    session = learning_sessions.get(session_id)
    
    # 如果會話不存在，自動創建
    if not session:
        session = create_session_from_quiz_result(session_id, user_id)
        if not session:
            return "學習會話不存在，請重新開始。"
    
    current_question = session['wrong_questions'][session['current_question_index']]
    conversation_history = session.get('conversation_history', [])
    student_level = session.get('student_level', 'beginner')
    understanding_level = session.get('current_topic_understanding', 0)
    
    # 檢查是否是第一條訊息（會話剛開始）
    if len(conversation_history) == 0:
        # 第一條訊息：顯示歡迎訊息和題目信息
        welcome_message = f"""🎓 歡迎來到 AI 智能教學！

我們將一起學習您的錯題。讓我們從第一道題開始：

**題目：** {current_question['question_text']}

我看到您的答案是「{current_question['user_answer']}」，正確答案是「{current_question['correct_answer']}」。

讓我們一起探討這個概念。您有什麼問題想問我嗎？"""
        
        # 將歡迎訊息加入對話歷史
        session['conversation_history'].append({
            'question': '系統歡迎訊息',
            'response': welcome_message,
            'timestamp': datetime.now().isoformat()
        })
        
        return welcome_message
    
    # 後續對話：結合題目背景和用戶問題
    # 根據模式選擇提示詞
    if mode == "socratic":
        base_prompt = SOCRATIC_TEACHING_STYLE
    elif mode == "general":
        base_prompt = GENERAL_ANSWER_STYLE
    else:
        base_prompt = TEACHER_STYLE
    
    # 構建智能教學提示詞，包含完整的對話上下文
    teaching_prompt = f"""
你是一位經驗豐富的資管系教授，正在進行一對一錯題輔導。

**當前錯題信息**：
- 題目：{current_question['question_text']}
- 學生的錯誤答案：{current_question['user_answer']}
- 正確答案：{current_question['correct_answer']}
- 主題：{current_question.get('topic', '資管概念')}

**重要背景**：學生原本回答「{current_question['user_answer']}」，但正確答案是「{current_question['correct_answer']}」。

**學生狀態**：
- 程度：{student_level}
- 當前理解度：{understanding_level}%
- 對話輪次：{len(conversation_history)}

**對話歷史**：
{chr(10).join([f"- 學生：{conv['question']} | AI：{conv['response'][:100]}..." for conv in conversation_history[-3:]])}

**學生當前問題**：{question}

**教學策略**：
1. 始終記住學生的原始錯誤答案，當學生問「為什麼我的答案不對」時，要具體解釋
2. 如果學生問為什麼某個答案不正確，要解釋該答案的問題所在
3. 使用對比方式說明錯誤答案vs正確答案的差異
4. 引導學生理解概念的精確定義
5. 確保每次回答都推進學生對當前錯題的理解
6. 參考之前的對話歷史，保持對話的連貫性

**特別注意**：
- 如果學生問「為什麼答案不是...」，要解釋為什麼那個答案不夠準確或完整
- 要具體指出學生原答案的不足之處
- 幫助學生理解正確答案的關鍵要素
- 根據對話歷史，避免重複已經說過的話

請回應學生的問題，記住題目背景和對話歷史：
"""
    
    try:
        # 初始化Gemini模型
        gemini_model, _ = init_gemini()
        
        # 生成回應
        response = gemini_model.generate_content(teaching_prompt)
        ai_response = response.text
        
        # 更新會話記錄
        update_learning_progress(session_id, question, ai_response)
        
        return ai_response
        
    except Exception as e:
        print(f"❌ RAG系統AI回應生成失敗: {e}")
        print(f"  - 錯誤類型: {type(e).__name__}")
        print(f"  - 錯誤詳情: {str(e)}")
        
        # 提供更好的預設回應，保持上下文連貫性
        user_answer = current_question['user_answer']
        correct_answer = current_question['correct_answer']
        
        # 根據學生的問題提供針對性回應
        if "我的答案是對的吧" in question or "對嗎" in question:
            # 學生在詢問答案是否正確
            if user_answer == correct_answer:
                return f"是的，您的答案「{user_answer}」是正確的！您對這個概念理解得很好。"
            else:
                return f"不完全是。您的答案是「{user_answer}」，但正確答案是「{correct_answer}」。讓我們一起分析一下差異：\n\n**您的答案**：{user_answer}\n**正確答案**：{correct_answer}\n\n您能告訴我您為什麼選擇「{user_answer}」嗎？這樣我可以幫您理解概念。"
        
        elif "為什麼" in question or "原因" in question:
            # 學生在詢問原因
            return f"好問題！關於「{current_question['question_text']}」，正確答案是「{correct_answer}」的原因如下：\n\n1. **概念定義**：區域網路(LAN)確實是用於連接辦公室或家庭設備的網路類型\n2. **您的答案**：「{user_answer}」這個選項可能存在一些不準確的地方\n\n您能具體說說您對「{user_answer}」的理解嗎？"
        
        else:
            # 一般性回應
            return f"關於「{current_question['question_text']}」這個問題，讓我們一起深入探討。\n\n**您的答案**：{user_answer}\n**正確答案**：{correct_answer}\n\n您剛才提到的「{question}」很有意思。您能告訴我您對這個概念的理解嗎？這樣我可以更好地幫助您。"

def update_learning_progress(session_id: str, question: str, response: str):
    """更新學習進度"""
    session = learning_sessions.get(session_id)
    if not session:
        return

    # 添加對話記錄
    session['conversation_history'].append({
        'question': question,
        'response': response,
        'timestamp': datetime.now().isoformat()
    })

    # 簡單的理解度評估（基於對話輪次）
    conversation_count = len(session['conversation_history'])
    if conversation_count >= 3:
        session['current_topic_understanding'] = min(80, conversation_count * 20)

    # 動態調整學生程度
    if conversation_count >= 2:
        if '很好' in response or '正確' in response:
            session['student_level'] = 'intermediate'
        elif conversation_count >= 4:
            session['student_level'] = 'advanced'

