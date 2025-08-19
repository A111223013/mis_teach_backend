from flask import Flask, request, abort
import json
import random
import os

import google.generativeai as genai

# 設定 Gemini API
genai.configure(api_key="AIzaSyDFUrwhpMzjOJ54acVG6V-oA3DNobTfgi4")
model = genai.GenerativeModel("gemini-1.5-flash")  # 或 gemini-1.5-pro

# ===== 主題清單 =====
knowledge_points = [
    "基本計概", "數位邏輯", "作業系統", "程式語言", "資料結構",
    "網路", "資料庫", "AI與機器學習", "資訊安全", "雲端與虛擬化",
    "MIS", "軟體工程與系統開發"
]

# ===== 出題 Prompt 生成器 =====
def generate_quiz_prompt(subject: str, question_type: str, difficulty: str):
    prompt = f"""
    請從「{subject}」這個主題中，生成一題資訊科技相關的題目。

    規則：
    1.  **題目類型**：{question_type}。
    2.  **難度**：{difficulty}。
    3.  **答案**：明確簡短直接，不能是「請參考詳細解答」。
    4.  **輸出格式**：必須是 JSON 格式。

    JSON 格式應包含以下欄位：
    - `question_text`: 題目的完整敘述。
    - `question_type`: 題目的類型，如 "single-choice" 或 "short-answer"。
    - `answer`: 正確答案。
    - `detail-answer`: 詳細的解答或解釋。
    - `key-points`: 題目所屬的知識點，例如 "基本計概"。
    - `difficulty level`: 題目的難度，如 "簡單"。

    如果題目類型是「選擇題」，請額外包含一個 `options` 欄位，它是一個包含四個選項（A, B, C, D）的列表。答案欄位則應為 "A", "B", "C" 或 "D"。
    如果題目類型是「問答題」，則無需 `options` 欄位。

    請確保所有內容都是以**繁體中文**呈現。
    """
    return prompt


# ===== 實際出題函式 =====
def generate_question(subject="random"):
    # 決定主題
    selected_subject = subject if subject in knowledge_points else random.choice(knowledge_points)

    # 隨機決定題型
    qtype = random.choice(["multiple-choice", "short-answer"])

    # 隨機決定難度
    if qtype == "multiple-choice":
        difficulty = random.choice(["簡單", "中等", "困難"])
    else:
        difficulty = "簡單"

    prompt = generate_quiz_prompt(selected_subject, qtype, difficulty)
    response = model.generate_content(prompt)

    try:
        text = response.candidates[0].content.parts[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]  # 取出中間部分
            text = text.replace("json", "", 1).strip()  # 移除可能的 "json" 標籤
        quiz_data = json.loads(text)
        return quiz_data
    except Exception as e:
        print("解析錯誤:", e, response)
        return None


# ====== LINE Bot 設定 ======
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

configuration = Configuration(access_token="z3GgS2onWJTinTT8GGXgmFbRJWyA/6weeCHOCoGgmZ9K3WRQFe/XYL8WUGPwRoXXNnR0jUrEvdJJRNESQw/oIXj0+t1JQboEvWidsMwMmdSf1a2jFY2j1wuIr7BjJBzAlKiJI+BANxXRJb9o663CEQdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler("a82de65b67e6a9b26ba1ede6cc190962")
line_bot_api = MessagingApi(ApiClient(configuration))

app = Flask(__name__)

# 使用者狀態
user_states = {}


def reply_text(reply_token, text):
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=text)]
        )
    )


# ====== Line 訊息處理 ======
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text.strip()
    user_id = event.source.user_id

    # 檢查是否在答題中
    if user_id in user_states:
        state = user_states[user_id]
        correct_answer = state["answer"]

        if user_message.lower() == correct_answer.lower():
            reply_text(event.reply_token, f"✅ 答對了！\n\n{state['detail-answer']}\n\n輸入『題目』可以開始下一題。")
        else:
            reply_text(event.reply_token, f"❌ 答錯了！正確答案是 {correct_answer}\n\n{state['detail-answer']}\n\n輸入『題目』可以開始下一題。")

        del user_states[user_id]
        return

    # 使用者要求出題
    if user_message.startswith("題目"):
        parts = user_message.split()
        subject = parts[1] if len(parts) > 1 else "random"

        random_question = generate_question(subject=subject)
        if not random_question:
            reply_text(event.reply_token, "抱歉，出題失敗了，請再試一次！")
            return

        question_text = random_question["question_text"]
        options = random_question.get("options", [])

        if options:
            options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
            question_message = f"{question_text}\n\n{options_text}\n\n👉 請輸入答案 (例如 A, B, C)"
        else:
            question_message = question_text + "\n\n👉 請輸入你的答案"

        reply_text(event.reply_token, question_message)

        user_states[user_id] = {
            "question": question_text,
            "options": options,
            "answer": random_question["answer"],
            "detail-answer": random_question.get("detail-answer", "")
        }

    else:
        reply_text(event.reply_token, "嗨！輸入『題目』即可開始測驗。\n你也可以輸入『題目 主題』指定題目範圍。")


# ====== Flask Webhook ======
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


if __name__ == "__main__":
    app.run()
