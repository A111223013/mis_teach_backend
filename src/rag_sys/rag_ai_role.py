import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import google.generativeai as genai

# 導入配置
try:
    from . import config
    from .config import Config
    GEMINI_AVAILABLE = True
except ImportError:
    import config
    from config import Config
    GEMINI_AVAILABLE = True

# 延遲導入 RAGBuilder 以避免循環導入
RAGBuilder = None

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MultiAITutor 類別 ====================

class MultiAITutor:
    """Gemini智能教師"""

    def __init__(self, rag_processor=None):
        """初始化教師"""
        # 設置日誌級別
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
        logging.getLogger('chromadb').setLevel(logging.WARNING)

        # 初始化AI回應器
        self.ai_responder = AIResponder(language='chinese', rag_processor=rag_processor)

        # 初始化向量資料庫連接
        self._init_vector_database()

        # 初始化Gemini模型
        self._init_gemini()

        # 教學會話管理
        self.learning_sessions = {}  # 存儲學習會話

        # 核心變數
        self.original_question = ""
        self.context = ""
        self.topic_knowledge = ""

        # 教學風格提示詞
        self.TEACHER_STYLE = """你是一位經驗豐富的資管系教授，正在一對一輔導學生，幫助學生透過逐步引導方式理解考題與資管系相關知識，確保學生真正掌握概念，而不只是背誦答案。


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

    def _init_gemini(self):
        """初始化Gemini模型"""
        if not GEMINI_AVAILABLE:
            raise ImportError("Gemini不可用，請安裝google-generativeai")

        try:
            # 從GEMINI_CONFIG中獲取API key
            api_key = config.GEMINI_CONFIG.get('api_key')
            if not api_key:
                raise ValueError("未設置Gemini API Key")

            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel(config.GEMINI_CONFIG.get('model', 'gemini-1.5-flash'))
            self.model_config = config.GEMINI_CONFIG
        except Exception as e:
            logging.error(f"❌ Gemini初始化失敗: {e}")
            raise RuntimeError(f"Gemini初始化失敗: {e}")

    def _init_vector_database(self):
        """初始化向量資料庫連接"""
        try:
            import chromadb
            from chromadb.config import Settings

            self.chroma_client = chromadb.PersistentClient(
                path=config.CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )

            # 嘗試獲取現有集合
            try:
                self.collection = self.chroma_client.get_collection(config.COLLECTION_NAME)
                count = self.collection.count()
            except Exception:
                logger.warning("⚠️ 未找到現有向量資料庫")
                self.collection = None

        except Exception as e:
            logger.error(f"❌ 向量資料庫初始化失敗: {e}")
            self.collection = None

    def _should_search_database(self, question: str) -> bool:
        """智能判斷是否需要查詢向量資料庫"""
        try:
            # 使用Gemini判斷是否需要查詢資料庫
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
-回答AI的提問

請只回答「需要查詢」或「不需要查詢」，不要解釋。
"""

            response = self.gemini_model.generate_content(prompt)
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

    def get_topic_knowledge(self, question: str) -> str:
        """智能獲取主題相關知識"""
        try:
            # 智能判斷是否需要查詢向量資料庫
            if not self._should_search_database(question):
                return ""

            # 先翻譯成英文搜索，因為向量資料庫是英文教材
            english_question = self._translate_to_english(question)

            # 使用向量資料庫搜索
            search_results = self.search_knowledge(english_question, top_k=3)

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

    def _translate_to_english(self, text: str) -> str:
        """翻譯成英文"""
        try:
            prompt = f"Translate to English: {text}"
            response = self.gemini_model.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
        except Exception as e:
            logging.warning(f"翻譯失敗: {e}")
        return text

    def create_learning_session(self, user_id: str, wrong_questions: List[Dict]) -> Dict[str, Any]:
        """創建學習會話"""
        session_id = f"learning_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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

        self.learning_sessions[session_id] = session

        return {
            'success': True,
            'session_id': session_id,
            'total_wrong_questions': len(wrong_questions),
            'current_question': wrong_questions[0] if wrong_questions else None,
            'message': f'開始學習 {len(wrong_questions)} 道錯題'
        }

    def handle_tutoring_conversation(self, session_id: str, question: str, user_id: str) -> str:
        """處理教學對話"""
        session = self.learning_sessions.get(session_id)
        if not session:
            return "學習會話不存在，請重新開始。"

        current_question = session['wrong_questions'][session['current_question_index']]
        conversation_history = session.get('conversation_history', [])
        student_level = session.get('student_level', 'beginner')
        understanding_level = session.get('current_topic_understanding', 0)

        # 構建智能教學提示詞
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

**學生當前問題**：{question}

**教學策略**：
1. 始終記住學生的原始錯誤答案，當學生問「為什麼我的答案不對」時，要具體解釋
2. 如果學生問為什麼某個答案不正確，要解釋該答案的問題所在
3. 使用對比方式說明錯誤答案vs正確答案的差異
4. 引導學生理解概念的精確定義
5. 確保每次回答都推進學生對當前錯題的理解

**特別注意**：
- 如果學生問「為什麼答案不是...」，要解釋為什麼那個答案不夠準確或完整
- 要具體指出學生原答案的不足之處
- 幫助學生理解正確答案的關鍵要素

請回應學生的問題：
"""

        try:
            response = self.gemini_model.generate_content(teaching_prompt)
            if response and hasattr(response, 'text') and response.text:
                ai_response = response.text.strip()

                # 更新會話記錄
                self._update_learning_progress(session_id, question, ai_response)

                return ai_response
        except Exception as e:
            logger.error(f"智能教學回應失敗: {e}")

        # 備用回應
        return f"關於「{current_question['question_text']}」這個問題，讓我們一起深入探討。您剛才提到的「{question}」是一個很好的切入點。您能告訴我您對這個概念的理解嗎？"

    def _update_learning_progress(self, session_id: str, question: str, response: str):
        """更新學習進度"""
        session = self.learning_sessions.get(session_id)
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

    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相關知識點

        Args:
            query: 搜索查詢
            top_k: 返回結果數量

        Returns:
            List[Dict]: 搜索結果列表
        """
        if not self.collection:
            logger.warning("⚠️ 向量資料庫未初始化")
            return []

        try:
            # 使用ChromaDB搜索
            results = self.collection.query(
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

    def ask_ai(self, student_input: str, is_new_question: bool = False) -> str:
        """統一的AI回應函式"""

        # 構建提示詞
        if is_new_question:
            prompt = f"""{self.TEACHER_STYLE}

你當前的對話歷史如下：
{self.context}

學生提出新問題：{student_input}

{f"相關知識：{self.topic_knowledge}" if self.topic_knowledge else "請憑通用知識回答。"}

請先確認題目方向，然後**簡潔地解釋這個概念的核心要點**。
隨後，請從最基礎的相關概念開始，提出一個引導性問題。
例如：如果問「銀行家演算法」，你可以先簡述它是避免死鎖的演算法，然後問學生「你知道什麼是死鎖嗎？」
請確保你的回答語氣親切、專業，並且**不要使用任何格式化標題**。
"""
        else:
            # 分析對話進度，避免重複
            conversation_turns = len(self.context.split('\n\n')) // 2 if self.context else 0

            prompt = f"""{self.TEACHER_STYLE}

你當前的對話歷史如下：
{self.context}

原始問題：「{self.original_question}」
學生對你上一個引導問題的回答是：{student_input}
對話輪次：第{conversation_turns + 1}輪

{f"相關知識：{self.topic_knowledge}" if self.topic_knowledge else "請憑通用知識回答。"}

**重要指導原則**：
- 這是第{conversation_turns + 1}輪對話，請根據對話進度調整教學策略
- 絕對不要重複之前已經問過的問題或要求相同類型的例子
- 要根據學生的回答程度決定是否深入或轉換角度

**教學策略**：
1. **評估學生回答**：
   - 如果學生回答正確且充分：給予肯定，然後**深入探討原理、應用或進階概念，每次的提問都要繼續深入問題**
   - 如果學生回答部分正確：肯定正確部分，補充不足，然後**從不同角度繼續**
   - 如果學生回答錯誤或不清楚：提供簡單解釋，然後**降低難度重新引導**

2. **進階引導方向**（根據對話輪次選擇）：
   - 第1-2輪：基本概念和生活例子
   - 第3-4輪：技術原理和實作細節
   - 第5輪以上：應用場景、優缺點、比較分析

3. **避免重複**：
   - 不要再問「還有什麼例子」或「除了...還有」
   - 不要重複要求相同類型的回答
   - 要從原理、應用、比較等不同維度深入

請根據以上原則，評估學生回答並提出**不同於之前的**深入問題。
"""

        return self._call_ai(prompt)

    def _call_ai(self, prompt: str) -> str:
        """調用Gemini AI"""
        try:
            response = self.gemini_model.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            else:
                return "抱歉，Gemini模型無法回應，可能與安全設置有關。"

        except Exception as e:
            logging.error(f"調用Gemini時發生錯誤: {e}")
            return "請稍等，讓我重新思考一下。"

    def start_new_question(self, question: str) -> str:
        """開始新問題"""
        self.original_question = question
        self.context = ""
        self.topic_knowledge = self.get_topic_knowledge(question)

        response = self.ask_ai(question, is_new_question=True)
        self.context = f"學生問：{question}\n老師：{response}"

        return response

    def continue_conversation(self, student_answer: str) -> str:
        """繼續對話"""
        if not self.original_question:
            return "請先提出一個問題開始學習。"
        response = self.ask_ai(student_answer, is_new_question=False)

        # 更新上下文
        self.context += f"\n\n學生：{student_answer}\n老師：{response}"

        # 保持上下文在合理長度
        if len(self.context) > 1500:
            parts = self.context.split('\n\n')
            if len(parts) > 6:
                self.context = '\n\n'.join(parts[-6:])

        return response

    def reset(self):
        """重置對話"""
        self.original_question = ""
        self.context = ""
        self.topic_knowledge = ""

# ==================== AIResponder 類別 ====================

class AIResponder:

    def __init__(self, language: str = 'chinese', rag_processor: Optional[Any] = None, ai_model: str = None):
        """
        初始化AI回應器

        Args:
            language: 語言設定（固定為中文）
            rag_processor: RAG處理器實例（已廢棄，保留向後兼容）
            ai_model: AI模型名稱
        """
        self.ai_model = ai_model

        # 初始化 Gemini 模型
        try:
            api_key = config.GEMINI_CONFIG.get('api_key')
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel(config.GEMINI_CONFIG.get('model', 'gemini-1.5-flash'))
            else:
                self.gemini_model = None
        except Exception as e:
            logger.warning(f"Gemini 初始化失敗: {e}")
            self.gemini_model = None

        # 初始化向量資料庫連接
        self._init_vector_database()

    def _init_vector_database(self):
        """初始化向量資料庫連接"""
        try:
            import chromadb
            from chromadb.config import Settings

            self.chroma_client = chromadb.PersistentClient(
                path=config.CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )

            # 嘗試獲取現有集合
            try:
                self.collection = self.chroma_client.get_collection(config.COLLECTION_NAME)
            except Exception:
                logger.warning("⚠️ AIResponder 未找到向量資料庫")
                self.collection = None

        except Exception as e:
            logger.error(f"❌ AIResponder 向量資料庫初始化失敗: {e}")
            self.collection = None

    def answer_question(self, question: str, use_ai: bool = True) -> Dict[str, Any]:
        """
        回答問題的主要方法

        Args:
            question: 用戶問題
            use_ai: 是否使用AI（保留參數，實際總是使用AI）

        Returns:
            Dict: 包含回答和相關信息的字典
        """
        try:
            # 1. AI智能問題分類 - 判斷是否需要查詢資料庫
            question_category = self._classify_question_intent(question)

            # 2. 根據問題類型決定處理方式
            if question_category == 'non_academic':
                # 非學術問題，不需要查詢資料庫
                return self._handle_non_academic(question)
            else:
                return self._handle_academic(question)

        except Exception as e:
            logger.error(f"❌ 回答問題時發生錯誤: {e}")
            return {
                "詳細回答": "抱歉，處理您的問題時遇到了技術問題。請稍後再試，或者換個方式提問。",
            }

    def _classify_question_intent(self, question: str) -> str:
        """
        使用AI智能分類問題意圖，判斷是否需要查詢資料庫

        Args:
            question: 用戶問題

        Returns:
            str: 問題類型 ('non_academic', 'mis_academic')
        """
        try:
            if not self.gemini_model:
                # 如果沒有 Gemini 模型，使用簡單的關鍵詞判斷
                return self._simple_classify(question)

            # 使用 Gemini 進行問題分類
            classification_prompt = f"""你是一位專業的教學助理。請分析以下問題，判斷它是否為資管學術問題：

問題：{question}

分類標準：
- mis_academic（資管學術）：資訊管理、作業系統、資料庫、網路、程式設計、演算法、資料結構、系統分析、軟體工程等專業問題
- non_academic（非學術）：問候語、身份詢問、能力詢問、感謝、道別、一般知識等其他問題

請只回答：mis_academic 或 non_academic"""

            response = self.gemini_model.generate_content(classification_prompt)

            if response and hasattr(response, 'text') and response.text:
                ai_response = response.text.strip().lower()
                if 'mis_academic' in ai_response or '資管學術' in ai_response:
                    return 'mis_academic'
                else:
                    return 'non_academic'

        except Exception as e:
            logger.warning(f"AI分類失敗: {e}")
            return self._simple_classify(question)

    def _handle_non_academic(self, question: str) -> Dict[str, Any]:
        """
        處理非學術問題，使用AI直接回答，不查詢資料庫
        """
        try:
            if self.gemini_model:
                prompt = f"""你是一位友善的資管系智能教學助理。請回答以下問題：

問題：{question}

請提供自然、有用的回答。如果是問候或身份詢問，請介紹自己是資管系AI教學助理。
如果是一般知識問題，請提供簡潔的回答"""
                response = self.gemini_model.generate_content(prompt)
                if response and hasattr(response, 'text') and response.text:
                    detailed_answer = response.text.strip()
        except Exception as e:
            logger.warning(f"AI回答非學術問題失敗: {e}")
            detailed_answer = f"您好！我是資管系智能教學助理。關於「{question}」，我很樂意為您解答。有什麼資管相關問題想要討論嗎？"
        return {
            "詳細回答": detailed_answer,
            "時間戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def _handle_academic(self, question: str) -> Dict[str, Any]:
        """
        處理資管學術問題，查詢向量資料庫
        """
        # 使用整合的向量資料庫搜索
        if self.collection:
            try:
                # 搜索相關知識
                search_results = self._search_knowledge(question, top_k=5)
                if search_results:
                    # 基於搜索結果生成回答
                    return self._generate_answer_from_search(question, search_results)
            except Exception as e:
                logger.warning(f"⚠️ 向量資料庫查詢錯誤: {e}")
        else:
            logger.warning("⚠️ 向量資料庫未初始化")


    def _search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相關知識點

        Args:
            query: 搜索查詢
            top_k: 返回結果數量

        Returns:
            List[Dict]: 搜索結果列表
        """
        if not self.collection:
            return []

        try:
            # 使用ChromaDB搜索
            results = self.collection.query(
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

    def _generate_answer_from_search(self, question: str, search_results: List[Dict]) -> Dict[str, Any]:
        """基於搜索結果生成回答"""
        # 提取最相關的結果
        best_result = search_results[0] if search_results else {}

        # 構建基於搜索結果的回答
        content = best_result.get('content', '')
        title = best_result.get('title', '相關知識')

        detailed_answer = f"""
📚 **關於「{question}」的回答**

**基本概念：**
{content}

**相關知識點：**
{title}

**學習建議：**
建議您深入理解這個概念的核心原理，並嘗試將其與實際應用場景結合。

💡 **提示**：如需更詳細的解釋，請提出更具體的問題。
"""

        return {
            "科目": best_result.get('subject', '資訊管理'),
            "教材": best_result.get('source', '教學資料'),
            "知識點": title,
            "詳細回答": detailed_answer.strip(),
            "相關概念": " | ".join(best_result.get('keywords', ['相關概念'])),
            "時間戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def format_response_for_display(self, response: Dict) -> str:
        """格式化回應以供顯示"""
        if isinstance(response, dict) and '詳細回答' in response:
            return response['詳細回答']
        elif isinstance(response, str):
            return response
        else:
            return "抱歉，無法格式化回應。"

# ==================== RAG Assistant Service 類別 ====================

class RAGAssistantService:
    """RAG智能教學助理服務"""

    def __init__(self):
        """初始化服務"""
        self.tutors = {}  # 存儲每個用戶的tutor實例
        self.processors = {}  # 存儲每個用戶的processor實例
        self.user_sessions = {}  # 存儲用戶會話數據
        self.conversation_histories = {}  # 存儲對話歷史

        # 初始化RAG處理器（使用整合的類別）
        try:
            # 使用整合後的 RAGBuilder 作為處理器
            self.shared_processor = RAGBuilder(Config())
            self.shared_ai_responder = AIResponder(
                language='chinese',
                rag_processor=self.shared_processor
            )
        except Exception as e:
            logger.error(f"❌ RAG系統初始化失敗: {e}")
            self.shared_processor = None
            self.shared_ai_responder = None

