from flask import Flask, request, abort
import json
import random
import os

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

# 你的 LINE Bot 資訊
configuration = Configuration(access_token='z3GgS2onWJTinTT8GGXgmFbRJWyA/6weeCHOCoGgmZ9K3WRQFe/XYL8WUGPwRoXXNnR0jUrEvdJJRNESQw/oIXj0+t1JQboEvWidsMwMmdSf1a2jFY2j1wuIr7BjJBzAlKiJI+BANxXRJb9o663CEQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('a82de65b67e6a9b26ba1ede6cc190962')

app = Flask(__name__)

# 使用者狀態字典，用來儲存每個使用者目前回答的題目
# 格式: {user_id: {"question_data": 題目完整的字典}}
user_state = {}

# 載入題庫 JSON 檔案
def load_quiz_data(filepath='src/error_questions.json'):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 因為檔案只有一題，所以直接返回該題的字典
            return data
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：{filepath} 不是有效的 JSON 檔案")
        return None

# 全域變數來儲存題庫
quiz_questions = load_quiz_data()

# Webhook 處理路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    if not quiz_questions:
        reply_text(event.reply_token, "題庫載入失敗或沒有單選題，請檢查後台檔案。")
        return

    user_id = event.source.user_id
    user_message = event.message.text.strip().lower()

    # 處理使用者正在回答的題目
    if user_id in user_state:
        current_question = user_state[user_id]["question_data"]
        
        # 檢查是否要求詳解
        if user_message == '詳解':
            detail_answer = current_question.get("detail-answer", "抱歉，此題沒有提供詳解。")
            reply_text(event.reply_token, f"【詳解】\n{detail_answer}\n\n輸入『題目』可以開始下一題。")
            del user_state[user_id] # 顯示詳解後清除狀態
            return
        is_correct = False
        question_type = current_question.get("type")
        correct_answer = str(current_question.get("answer", "")).strip().lower()
        
        if question_type == "single-choice":
            if user_message == correct_answer:
                is_correct = True
        elif question_type == "short-answer":
            # 簡答題比對邏輯: 答案包含在正確答案中，或是正確答案包含在使用者答案中
            # 也可以只比對部分關鍵字
            if user_message in correct_answer or correct_answer in user_message:
                 is_correct = True
        
        # 檢查答案是否正確
        correct_answer = str(current_question.get("answer")).strip().lower()
        if user_message == correct_answer:
            reply_text(event.reply_token, "恭喜你，答對了！\n輸入『題目』可以開始下一題。\n如果想看詳解，請輸入『詳解』。")
            del user_state[user_id] # 答對後清除狀態
        else:
            reply_text(event.reply_token, "答案不對喔，再試試看！\n輸入『題目』可以開始下一題。\n如果想看詳解，請輸入『詳解』。")
    
    # 使用者輸入『題目』或『開始』時，出題
    elif user_message in ['題目', '開始']:
        random_question = random.choice(quiz_questions)
        
        # 建立題目顯示格式
        question_text = (
            f"【{random_question.get('school', '')}】\n"
            f"【{random_question.get('department', '')}】\n"
            f"【{random_question.get('year', '')}年 第{random_question.get('question_number', '')}題】\n\n"
            f"{random_question.get('question_text', '')}\n\n"
        )
        
        # 如果有選項，則加入選項
        options = random_question.get("options")
        if options:
            options_text = ""
            for option in options:
                options_text += f"{option}\n"
            question_text += options_text
        
        # 儲存使用者狀態 (現在存完整的題目字典)
        user_state[user_id] = {"question_data": random_question}
        
        # 回覆題目給使用者
        reply_text(event.reply_token, question_text)
    
    # 預設回覆，引導使用者
    else:
        reply_text(event.reply_token, "哈囉！這是一個簡單的問答遊戲。\n輸入『題目』來開始遊戲吧！")


# 封裝回覆訊息的函式，簡化程式碼
def reply_text(reply_token, text):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )

if __name__ == "__main__":
    app.run()