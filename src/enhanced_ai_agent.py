# enhanced_ai_agent.py
"""
增強版AI Agent - 整合RAG向量資料庫
結合原有的LangGraph架構與新的RAG系統
"""

import os
import sys
from pathlib import Path
from langgraph.graph import StateGraph
from langchain.schema.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from flask import Blueprint, request, jsonify
from typing import TypedDict, List, Dict, Any, Optional

# 添加ocr目錄到路徑以導入RAG處理器
current_dir = Path(__file__).parent
ocr_dir = current_dir.parent.parent / "ocr"
sys.path.append(str(ocr_dir))

try:
    from enhanced_rag_processor import EnhancedRAGProcessor
    RAG_AVAILABLE = True
except ImportError:
    print("⚠️ RAG處理器不可用，將使用原始的FAISS檢索")
    RAG_AVAILABLE = False

enhanced_ai_agent_bp = Blueprint('enhanced_ai_agent', __name__)

class EnhancedGraphState(TypedDict):
    question: str
    docs: List
    chat_history: List[BaseMessage]
    answer: str
    rag_sources: List[Dict]  # 新增：RAG來源信息

class EnhancedAIAgent:
    """增強版AI Agent類"""
    
    def __init__(self):
        self.retriever = None
        self.rag_processor = None
        self.chat_memory = []
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
        
        # 初始化RAG系統
        if RAG_AVAILABLE:
            self._init_rag_system()
        
    def _init_rag_system(self):
        """初始化RAG系統"""
        try:
            print("🔧 正在初始化RAG系統...")
            
            # 設置RAG處理器
            self.rag_processor = EnhancedRAGProcessor(
                use_chromadb=True,
                chromadb_path=str(ocr_dir / "knowledge_db")
            )
            
            # 嘗試載入現有向量資料庫
            if not self.rag_processor.load_vector_database("textbook_knowledge"):
                print("📚 未找到現有RAG資料庫，將使用傳統FAISS檢索")
                self.rag_processor = None
            else:
                print("✅ RAG系統初始化成功")
                
        except Exception as e:
            print(f"❌ RAG系統初始化失敗: {e}")
            self.rag_processor = None

    def init_embeddings_from_txt(self, txt_path: str):
        """初始化傳統FAISS向量資料庫（備用方案）"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            docs = [Document(page_content=content)]
            chunks = CharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            self.retriever = FAISS.from_documents(chunks, embedding=embeddings).as_retriever()
            print("✅ 傳統FAISS檢索器初始化成功")
        except Exception as e:
            print(f"❌ FAISS檢索器初始化失敗: {e}")

    def retrieve_context(self, question: str) -> tuple[str, List[Dict]]:
        """
        檢索相關上下文
        
        Returns:
            tuple: (context_text, rag_sources)
        """
        rag_sources = []
        
        # 優先使用RAG系統
        if self.rag_processor:
            try:
                rag_results = self.rag_processor.search(question, top_k=3)
                if rag_results:
                    context_parts = []
                    for result in rag_results:
                        metadata = result["metadata"]
                        content = result["content"]
                        
                        # 格式化上下文
                        context_part = f"""
來源：{metadata.get('chapter', 'N/A')} - {metadata.get('section', 'N/A')}
頁碼：{metadata.get('page_number', 'N/A')}
內容：{content[:400]}...
"""
                        context_parts.append(context_part)
                        
                        # 保存來源信息
                        rag_sources.append({
                            "chapter": metadata.get('chapter', 'N/A'),
                            "section": metadata.get('section', 'N/A'),
                            "page": metadata.get('page_number', 'N/A'),
                            "content_preview": content[:200] + "...",
                            "similarity": 1 - result.get('distance', 0)
                        })
                    
                    return "\n".join(context_parts), rag_sources
            except Exception as e:
                print(f"❌ RAG檢索失敗: {e}")
        
        # 備用：使用傳統FAISS檢索
        if self.retriever:
            try:
                docs = self.retriever.invoke(question)
                context = "\n".join([doc.page_content for doc in docs])
                return context, []
            except Exception as e:
                print(f"❌ 傳統檢索失敗: {e}")
        
        return "沒有找到相關資料。", []

    def generate_answer(self, state: dict) -> dict:
        """生成答案節點（LangGraph）"""
        question = state["question"]
        history = state.get("chat_history", [])
        
        # 檢索相關上下文
        context, rag_sources = self.retrieve_context(question)
        
        # 對話歷史格式化
        history_str = "\n".join(
            [f"使用者：{msg.content}" if isinstance(msg, HumanMessage) else f"AI：{msg.content}"
             for msg in history[-6:]]  # 只保留最近3輪對話
        )
        
        # 建立增強的prompt
        prompt = f"""你是一個專業的教學助理，請根據提供的教材內容回答問題。

先前的對話紀錄：
{history_str}

相關教材內容：
{context}

問題：{question}

請根據教材內容提供準確、詳細的回答。如果教材中沒有相關信息，請誠實說明。
回答時請：
1. 直接回答問題
2. 引用相關的教材內容
3. 如果有多個相關概念，請分點說明
4. 保持回答的學術性和準確性
"""
        
        # 呼叫Gemini LLM
        result = self.llm.invoke(prompt)
        
        return {
            "answer": result.content,
            "rag_sources": rag_sources
        }

    def build_graph(self):
        """建立LangGraph"""
        builder = StateGraph(dict)
        builder.add_node("generate_answer", self.generate_answer)
        builder.set_entry_point("generate_answer")
        builder.set_finish_point("generate_answer")
        return builder.compile()

    def answer_with_langgraph(self, question: str, history: List[BaseMessage]) -> Dict[str, Any]:
        """使用LangGraph回答問題"""
        graph = self.build_graph()
        result = graph.invoke({
            "question": question,
            "chat_history": history
        })
        return result

    def ask_question(self, question: str) -> Dict[str, Any]:
        """處理問題並返回答案"""
        try:
            # 加入對話歷史（使用者問題）
            self.chat_memory.append(HumanMessage(content=question))
            
            # 回答問題
            result = self.answer_with_langgraph(question, self.chat_memory)
            answer = result["answer"]
            rag_sources = result.get("rag_sources", [])
            
            # 加入對話歷史（AI回答）
            self.chat_memory.append(AIMessage(content=answer))
            
            # 限制對話歷史長度
            if len(self.chat_memory) > 20:
                self.chat_memory = self.chat_memory[-20:]
            
            return {
                "answer": answer,
                "sources": rag_sources,
                "has_rag": self.rag_processor is not None
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "answer": "抱歉，處理您的問題時發生錯誤。",
                "sources": [],
                "has_rag": False
            }

    def clear_memory(self):
        """清除對話記憶"""
        self.chat_memory = []

    def get_memory_summary(self) -> Dict[str, Any]:
        """獲取記憶摘要"""
        return {
            "total_messages": len(self.chat_memory),
            "recent_questions": [
                msg.content for msg in self.chat_memory[-6:] 
                if isinstance(msg, HumanMessage)
            ][-3:]
        }

# 全局AI Agent實例
ai_agent = EnhancedAIAgent()

# API端點
@enhanced_ai_agent_bp.route("/ask", methods=["POST"])
def ask():
    """處理問答請求"""
    data = request.get_json()
    question = data.get("question", "")
    
    if not question:
        return jsonify({"error": "請輸入問題"}), 400
    
    result = ai_agent.ask_question(question)
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)

@enhanced_ai_agent_bp.route("/memory/clear", methods=["POST"])
def clear_memory():
    """清除對話記憶"""
    ai_agent.clear_memory()
    return jsonify({"message": "對話記憶已清除"})

@enhanced_ai_agent_bp.route("/memory/summary", methods=["GET"])
def memory_summary():
    """獲取記憶摘要"""
    summary = ai_agent.get_memory_summary()
    return jsonify(summary)

@enhanced_ai_agent_bp.route("/status", methods=["GET"])
def status():
    """獲取系統狀態"""
    return jsonify({
        "rag_available": ai_agent.rag_processor is not None,
        "fallback_retriever": ai_agent.retriever is not None,
        "memory_size": len(ai_agent.chat_memory)
    })

# 初始化函數（在app.py中調用）
def init_enhanced_ai_agent(txt_path: str = None):
    """初始化增強版AI Agent"""
    global ai_agent
    
    print("🚀 正在初始化增強版AI Agent...")
    
    # 如果提供了txt文件路徑，初始化備用檢索器
    if txt_path and os.path.exists(txt_path):
        ai_agent.init_embeddings_from_txt(txt_path)
    
    print("✅ 增強版AI Agent初始化完成")
    return ai_agent
