# ai_agent.py
from langgraph.graph import StateGraph
from langchain.schema.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from flask import Blueprint, request, jsonify
from typing import TypedDict, List

ai_agent_bp = Blueprint('ai_agent', __name__)
retriever = None
chat_memory = []  # 用於儲存整段對話歷史

class GraphState(TypedDict):
    question: str
    docs: List
    chat_history: List[BaseMessage]
    answer: str

# 初始化向量資料庫
def init_embeddings_from_txt(txt_path: str):
    global retriever
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    docs = [Document(page_content=content)]
    chunks = CharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    retriever = FAISS.from_documents(chunks, embedding=embeddings).as_retriever()

# 節點：生成答案（包含 chat_history）
def generate_answer(state: dict) -> dict:
    question = state["question"]
    history = state.get("chat_history", [])

    # 語意檢索取得相關資料
    docs = retriever.invoke(question)
    context = "\n".join([doc.page_content for doc in docs])

    # 對話歷史格式化
    history_str = "\n".join(
        [f"使用者：{msg.content}" if isinstance(msg, HumanMessage) else f"AI：{msg.content}"
         for msg in history]
    )

    # 建立 prompt
    prompt = f"""這是先前的對話紀錄：
    {history_str}

    以下是相關資料：
    {context}

    問題：{question}
    請根據對話上下文與資料回覆。"""

    # 呼叫 Gemini LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
    result = llm.invoke(prompt)

    return {"answer": result.content}

# 建立 LangGraph
def build_graph():
    builder = StateGraph(dict)
    builder.add_node("generate_answer", generate_answer)
    builder.set_entry_point("generate_answer")
    builder.set_finish_point("generate_answer")
    return builder.compile()

# 將問題與對話歷史傳入 LangGraph
def answer_with_langgraph(question: str, history: List[BaseMessage]) -> str:
    if retriever is None:
        raise ValueError("Retriever 尚未初始化")
    graph = build_graph()
    result = graph.invoke({
        "question": question,
        "chat_history": history
    })
    return result["answer"]

# API 端點：處理 POST 請求
@ai_agent_bp.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "請輸入問題"}), 400
    try:
        # 加入對話歷史（使用者問題）
        chat_memory.append(HumanMessage(content=question))

        # 回答問題
        answer = answer_with_langgraph(question, chat_memory)

        # 加入對話歷史（AI 回答）
        chat_memory.append(AIMessage(content=answer))

        return jsonify({"answer": answer})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
