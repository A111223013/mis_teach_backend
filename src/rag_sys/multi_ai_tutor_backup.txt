import logging
from . import config
from .rag_ai_responder import AIResponder
# 導入配置和AI回應器
import google.generativeai as genai
GEMINI_AVAILABLE = True


# 設定日誌
logger = logging.getLogger(__name__)

class MultiAITutor:
    """Gemini智能教師"""

    def __init__(self, rag_processor=None):
        """初始化教師"""
        # 設置日誌級別
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
        logging.getLogger('chromadb').setLevel(logging.WARNING)

        # 初始化AI回應器
        self.ai_responder = AIResponder(language='chinese', rag_processor=rag_processor)

        # 初始化Gemini模型
        self._init_gemini()

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
            logging.info("✅ Gemini模型初始化成功")
        except Exception as e:
            logging.error(f"❌ Gemini初始化失敗: {e}")
            raise RuntimeError(f"Gemini初始化失敗: {e}")
    

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
            # 使用RAG處理器搜索
            if hasattr(self.ai_responder, 'rag_processor') and self.ai_responder.rag_processor:
                search_results = self.ai_responder.rag_processor.search_knowledge(english_question, top_k=3)

                if search_results:
                    # 提取前3個結果的內容
                    knowledge = "\n".join([
                        result.get('content', '')[:400]
                        for result in search_results[:4]
                    ])
                    return knowledge
                else:
                    logging.info("⚠️ 未找到相關知識點")
            else:
                logging.warning("❌ RAG處理器不可用")
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
   - 如果學生回答正確且充分：給予肯定，然後**深入探討原理、應用或進階概念**
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