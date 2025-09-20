#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE Bot Blueprint - 只負責接收訊息、調用主代理人、回復訊息
"""

from flask import Blueprint, request, jsonify
import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional
import sys

# LINE Bot 相關導入
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest, 
    PushMessageRequest, TextMessage, FlexMessage, FlexContainer
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent

# 本地模組導入
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from tool.api_keys import get_api_key

# 創建 Blueprint
linebot_bp = Blueprint('linebot', __name__)

# ===== 配置 =====
LINE_CHANNEL_ACCESS_TOKEN = "4tzbGJjk7YixaQv5kFpbav+aneeMQIb2aoJxlr3ddKLzE9kNYuv+fDb6+hjMIalKE63HILajU7wsJSsoOB6XjYHIPzUbpxyk6JBoZj4vpXoE9DdXm1sbubfacwPd69mf7LjD8c31cSZFHsoQVRtkUQdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "57456fb2f7e66d780b9f9daf80934468"

# 主代理人配置 - 使用現有的 web_ai_assistant
MAIN_AGENT_API_URL = "http://localhost:5000/web-ai/chat"  # 現有的主代理人端點

# 初始化 LINE Bot
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
line_bot_api = MessagingApi(ApiClient(configuration))

# ===== 全局變數 =====
# 移除 user_quiz_data，現在使用主代理人的記憶管理

# ===== Line 綁定功能 =====
import qrcode
import io
import base64
import redis
from accessories import redis_client

@linebot_bp.route('/generate-qr', methods=['POST', 'OPTIONS'])
def generate_line_qr():
    """生成 Line Bot 綁定 QR Code"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供認證 token'}), 401
    
    token = auth_header.split(" ")[1]
    from src.api import get_user_info
    student_email = get_user_info(token, 'email')
    data = request.get_json()
    binding_token = data.get('bindingToken')
    
    if not binding_token:
        return jsonify({'token': None, 'message': '缺少綁定 token'}), 400
    
    try:
        # 使用正確的加好友連結生成 QR Code
        line_bot_url = "https://lin.ee/rG5sXkM"  # 正確的加好友連結
        
        print(f"🔗 使用正確的加好友連結: {line_bot_url}")
        
        # 生成 QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(line_bot_url)
        qr.make(fit=True)
        
        # 創建 QR Code 圖片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 轉換為 base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        print("✅ 成功生成 QR Code")
        
        # 儲存綁定 token 到 Redis (3分鐘過期)
        redis_client.setex(f"line_binding:{binding_token}", 180, student_email)
        
        print(f"✅ QR Code 生成成功，綁定 token: {binding_token}")
        
        from accessories import refresh_token
        refreshed_token = refresh_token(token)
        return jsonify({
            'token': refreshed_token, 
            'qrCodeUrl': f"data:image/png;base64,{img_str}",
            'bindingToken': binding_token
        })
        
    except Exception as e:
        print(f"❌ 生成 QR Code 失敗: {e}")
        return jsonify({'token': None, 'message': f'生成 QR Code 失敗: {str(e)}'}), 500

@linebot_bp.route('/check-binding', methods=['POST', 'OPTIONS'])
def check_line_binding():
    """檢查 Line 綁定狀態"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供認證 token'}), 401
    
    token = auth_header.split(" ")[1]
    from src.api import get_user_info
    student_email = get_user_info(token, 'email')
    data = request.get_json()
    binding_token = data.get('bindingToken')
    
    if not binding_token:
        return jsonify({'token': None, 'message': '缺少綁定 token'}), 400
    
    # 檢查 Redis 中是否有綁定成功的記錄
    binding_key = f"line_binding_success:{binding_token}"
    line_user_id = redis_client.get(binding_key)
    
    if line_user_id:
        # 綁定成功，更新用戶資料
        line_user_id = line_user_id.decode('utf-8')
        
        # 更新 MongoDB 中的用戶資料
        from accessories import mongo
        result = mongo.db.user.update_one(
            {"email": student_email},
            {"$set": {"lineId": line_user_id}}
        )
        
        if result.matched_count == 0:
            print(f"❌ 找不到用戶: {student_email}")
            return jsonify({'token': None, 'message': '找不到用戶資料'}), 404
        
        print(f"✅ 成功更新用戶 {student_email} 的 LINE ID: {line_user_id}")
        
        # 清除綁定記錄
        redis_client.delete(binding_key)
        redis_client.delete(f"line_binding:{binding_token}")
        
        from accessories import refresh_token
        refreshed_token = refresh_token(token)
        return jsonify({
            'token': refreshed_token,
            'bound': True,
            'lineId': line_user_id
        })
    else:
        from accessories import refresh_token
        refreshed_token = refresh_token(token)
        return jsonify({
            'token': refreshed_token,
            'bound': False
        })

# ===== 主代理人調用 =====
def call_main_agent(user_message: str, user_id: str) -> str:
    """調用現有的主代理人系統 (web_ai_assistant)"""
    try:
        print(f"🔍 調用主代理人：用戶={user_id}, 消息={user_message}")
        
        # 準備請求數據 - 符合現有主代理人的格式，並標識為 LINE Bot
        request_data = {
            "message": user_message,
            "user_id": f"line_{user_id}",  # 加上 line_ 前綴區分來源
            "platform": "linebot",  # 標識為 LINE Bot 平台
            "conversation_id": f"line_{user_id}",  # 添加對話ID，用於記憶管理
            "maintain_context": True  # 標識需要保持對話上下文
        }
        
        print(f"📤 發送請求到：{MAIN_AGENT_API_URL}")
        print(f"📤 請求數據：{request_data}")
        
        # 調用現有的主代理人 API
        response = requests.post(
            MAIN_AGENT_API_URL,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📥 收到回應：狀態碼={response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📥 回應內容：{result}")
            
            if result.get('success'):
                message = result.get("content", result.get("message", "主代理人回應格式錯誤"))
                print(f"✅ 成功獲取回應：{message[:50]}...")
                return message
            else:
                error_msg = result.get("error", "未知錯誤")
                print(f"❌ 主代理人處理失敗: {error_msg}")
                return f"抱歉，主代理人處理失敗：{error_msg}"
        else:
            print(f"❌ 主代理人 API 錯誤: {response.status_code} - {response.text}")
            return f"抱歉，主代理人系統暫時無法使用。錯誤代碼：{response.status_code}"
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 調用主代理人 API 失敗: {e}")
        return "抱歉，無法連接到主代理人系統，請稍後再試"
    except Exception as e:
        print(f"❌ 調用主代理人失敗: {e}")
        return f"抱歉，主代理人系統暫時無法使用。錯誤：{str(e)}"

# ===== 消息處理 =====
def reply_text(reply_token: str, text: str):
    """發送文字回覆"""
    try:
        # 檢查消息是否為空
        if not text or not text.strip():
            print("警告：嘗試發送空消息")
            text = "抱歉，系統暫時無法回應，請稍後再試。"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )
        print(f"✅ 成功發送消息：{text[:50]}...")
    except Exception as e:
        print(f"❌ 發送消息失敗: {e}")

def send_thinking_message(reply_token: str):
    """發送思考中提示訊息"""
    try:
        thinking_text = "🤔 小幫手正在思考中，請稍候..."
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=thinking_text)]
            )
        )
        print("✅ 成功發送思考中提示")
    except Exception as e:
        print(f"❌ 發送思考中提示失敗: {e}")

def push_text_message(user_id: str, text: str):
    """發送推播訊息（用於後續回應）"""
    try:
        # 檢查消息是否為空
        if not text or not text.strip():
            print("警告：嘗試發送空消息")
            text = "抱歉，系統暫時無法回應，請稍後再試。"
        
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=text)]
            )
        )
        print(f"✅ 成功發送推播消息：{text[:50]}...")
    except Exception as e:
        print(f"❌ 發送推播消息失敗: {e}")

def send_error_message(reply_token: str):
    """發送錯誤訊息"""
    try:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="抱歉，消息發送失敗，請稍後再試。")]
            )
        )
    except Exception as fallback_error:
        print(f"❌ 錯誤消息發送也失敗: {fallback_error}")

def handle_binding_command(user_id: str, binding_token: str, reply_token: str):
    """處理綁定指令"""
    try:
        print(f"🔍 處理綁定指令：用戶={user_id}, 綁定碼={binding_token}")
        
        # 檢查綁定 token 是否存在
        binding_key = f"line_binding:{binding_token}"
        user_email = redis_client.get(binding_key)
        
        print(f"🔍 Redis 查詢結果：{user_email}")
        
        if user_email:
            user_email = user_email.decode('utf-8')
            
            # 記錄綁定成功
            success_key = f"line_binding_success:{binding_token}"
            redis_client.setex(success_key, 180, user_id)
            
            print(f"✅ 用戶 {user_id} 綁定成功，對應網站用戶 {user_email}")
            
            # 發送確認訊息給用戶
            reply_text(reply_token, "🎉 綁定成功！您已成功綁定 Line Bot，現在可以使用所有功能了！")
            
        else:
            print(f"❌ 無效的綁定 token: {binding_token}")
            print(f"🔍 檢查的 Redis key: {binding_key}")
            
            # 列出所有相關的 Redis keys 進行調試
            try:
                all_keys = redis_client.keys("line_binding:*")
                print(f"🔍 所有綁定相關的 Redis keys: {all_keys}")
            except Exception as e:
                print(f"🔍 無法列出 Redis keys: {e}")
            
            reply_text(reply_token, f"❌ 綁定失敗，綁定碼無效或已過期。\n\n請確認：\n1. 綁定碼是否正確複製\n2. 是否在 3 分鐘內完成綁定\n3. 是否重新生成了 QR Code\n\n當前綁定碼：{binding_token}")
            
    except Exception as e:
        print(f"❌ 處理綁定指令失敗: {e}")
        reply_text(reply_token, "❌ 綁定過程中發生錯誤，請稍後再試。")

def handle_test_binding(user_id: str, reply_token: str):
    """處理綁定測試指令"""
    try:
        print(f"🔍 測試綁定狀態：用戶={user_id}")
        
        # 檢查用戶是否已綁定
        from accessories import mongo
        user = mongo.db.user.find_one({"lineId": user_id})
        
        if user:
            # 用戶已綁定
            test_message = f"""✅ 綁定狀態測試成功！

👤 用戶姓名：{user.get('name', '未知')}
📧 綁定帳號：{user.get('email', '未知')}
🏫 學校：{user.get('school', '未知')}
🆔 LINE ID：{user_id}

🎉 您已成功綁定 MIS 教學助手！
現在可以使用所有功能了。"""
        else:
            # 用戶未綁定
            test_message = """❌ 您尚未綁定 MIS 教學助手

📋 綁定步驟：
1. 在網站設定頁面生成 QR Code
2. 複製顯示的綁定碼
3. 直接發送綁定碼（以 bind_ 開頭）

💡 例如：bind_1757907057155_e47dt5lib"""
        
        reply_text(reply_token, test_message)
        
    except Exception as e:
        print(f"❌ 測試綁定狀態失敗: {e}")
        reply_text(reply_token, "❌ 測試過程中發生錯誤，請稍後再試。")

def handle_message(event: MessageEvent):
    """處理用戶文字消息"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    

    # 檢查是否為綁定碼格式（以 bind_ 開頭）
    if user_message.startswith('bind_'):
        binding_token = user_message.strip()
        print(f"🔍 檢測到綁定碼格式：{user_message}")
        print(f"🔍 使用綁定碼：{binding_token}")
        handle_binding_command(user_id, binding_token, event.reply_token)
        return
    
    # 檢查是否為測試指令
    if user_message.lower() in ['測試綁定', 'test', '檢查綁定', '我是誰']:
        handle_test_binding(user_id, event.reply_token)
        return
    
    # 所有其他訊息都交給主代理人處理，包括測驗答案
    # 主代理人會自動維護對話上下文和記憶
    
    # 檢查是否為測驗答案（根據前一次對話判斷）
    def is_likely_quiz_answer(message: str, user_id: str) -> bool:
        """根據前一次對話智能判斷是否為測驗答案"""
        try:
            from src.memory_manager import _user_memories
            user_memory_key = f"line_{user_id}"
            
            # 檢查是否有對話記憶
            if user_memory_key not in _user_memories or not _user_memories[user_memory_key]:
                print(f"📝 用戶 {user_id} 沒有對話記憶")
                return False
            
            # 獲取最近的對話記錄
            recent_messages = _user_memories[user_memory_key][-3:]  # 最近3條
            print(f"📝 用戶 {user_id} 的最近對話：{recent_messages}")
            
            # 檢查前一次對話是否包含測驗題目
            def has_quiz_context(messages: list) -> bool:
                """檢查對話中是否包含測驗題目"""
                for msg in messages:
                    msg_lower = msg.lower()
                    quiz_indicators = [
                        "測驗", "題目", "選擇題", "問題", "a)", "b)", "c)", "d)",
                        "quiz", "question", "test", "選擇", "答案", "請輸入您的答案"
                    ]
                    if any(indicator in msg_lower for indicator in quiz_indicators):
                        return True
                return False
            
            # 如果前一次對話包含測驗題目，且當前輸入是簡短答案，則可能是測驗答案
            if has_quiz_context(recent_messages):
                message_clean = message.strip().upper()
                
                # 檢查是否為可能的測驗答案格式
                if message_clean in ["A", "B", "C", "D"]:
                    return True
                
                if any(pattern in message_clean for pattern in ["(A)", "(B)", "(C)", "(D)", "A)", "B)", "C)", "D)"]):
                    return True
                
                # 簡短答案但排除常見單詞
                if len(message_clean) <= 3 and any(option in message_clean for option in ["A", "B", "C", "D"]):
                    common_words = ["HI", "HEY", "YES", "NO", "OK", "BYE", "THX", "THANKS"]
                    if message_clean not in common_words:
                        return True
            
            return False
            
        except Exception as e:
            print(f"❌ 檢查測驗答案失敗：{e}")
            return False
    
    if is_likely_quiz_answer(user_message, user_id):
        print(f"🎯 檢測到測驗答案：{user_message}")
        
        # 從記憶管理器中獲取最近的對話上下文
        try:
            from src.memory_manager import _user_memories
            user_memory_key = f"line_{user_id}"
            
            if user_memory_key in _user_memories and _user_memories[user_memory_key]:
                # 獲取最近的對話記錄
                recent_messages = _user_memories[user_memory_key][-5:]  # 最近5條
                context = "\n".join(recent_messages)
                
                # 構建包含上下文的測驗批改請求
                grading_request = f"用戶剛才進行了測驗，現在輸入答案：{user_message}\n\n對話上下文：\n{context}\n\n請進行測驗批改，包含：1. 答案是否正確 2. 如果錯誤，解釋為什麼錯誤 3. 提供學習建議。要求：內容要簡潔明瞭，適合 LINE Bot 顯示，包含適當的表情符號"
                
                print(f"📝 發送測驗批改請求：{grading_request[:100]}...")
                response = call_main_agent(grading_request, user_id)
                reply_text(event.reply_token, response)
                return
            else:
                print("📝 沒有找到對話記憶，按一般訊息處理")
        except Exception as e:
            print(f"❌ 獲取記憶失敗：{e}，按一般訊息處理")
    
    # 處理特殊指令
    if user_message in ["@每日測驗"]:
        print(f"🎯 收到測驗指令：{user_message}")
        # 發送測驗選擇輪盤
        try:
            print("🔄 正在創建測驗選擇輪盤...")
            carousel = create_quiz_selection_carousel()
            print("✅ 輪盤樣板創建成功")
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[carousel]
                )
            )
            print("✅ 成功發送測驗選擇輪盤")
            return
        except Exception as e:
            print(f"❌ 發送測驗輪盤失敗: {e}")
            print(f"❌ 錯誤詳情: {type(e).__name__}: {str(e)}")
            # 如果輪盤發送失敗，回退到文字回應
            response = "🎯 開始測驗！\n\n請選擇知識點：\n• 基本計概\n• 數位邏輯\n• 作業系統\n• 程式語言\n• 資料結構\n• 網路通訊\n• 資料庫\n• AI與機器學習\n• 資訊安全\n• 雲端運算\n• MIS系統\n• 軟體工程\n• 隨機\n\n系統會自動生成隨機題型（選擇題或知識問答題）"
            reply_text(event.reply_token, response)
            return
    
    # 處理測驗知識點選擇指令
    if user_message.startswith("@測驗 "):
        topic = user_message.replace("@測驗 ", "").strip()
        print(f"📝 用戶選擇知識點：{topic}")
        
        # 直接調用主代理人生成隨機測驗（不顯示答案）
        if topic == "隨機":
            prompt = "請生成一道隨機測驗題目，題型隨機（選擇題或知識問答題），適合 LINE Bot 顯示。要求：1. 直接生成題目內容，不要有任何前綴說明如「好的，這是一道...」或「---」等 2. 只顯示題目和選項，絕對不要顯示正確答案 3. 如果是選擇題，提供4個選項（A、B、C、D） 4. 如果是知識問答題，只顯示問題 5. 內容要專注於資管相關的計算機科學知識 6. 包含適當的表情符號和格式 7. 重要：不要顯示「正確答案：」或任何答案相關信息"
        else:
            prompt = f"請生成一道關於「{topic}」的隨機測驗題目，題型隨機（選擇題或知識問答題），適合 LINE Bot 顯示。要求：1. 直接生成題目內容，不要有任何前綴說明如「好的，這是一道...」或「---」等 2. 只顯示題目和選項，絕對不要顯示正確答案 3. 如果是選擇題，提供4個選項（A、B、C、D） 4. 如果是知識問答題，只顯示問題 5. 內容要專注於資管相關的計算機科學知識 6. 包含適當的表情符號和格式 7. 重要：不要顯示「正確答案：」或任何答案相關信息"
        
        # 發送思考中提示
        send_thinking_message(event.reply_token)
        
        response = call_main_agent(prompt, user_id)
        
        # 添加答題說明
        if "選擇題" in response or "A)" in response or "B)" in response:
            response += "\n\n💡 請輸入您的答案（A、B、C 或 D）："
        else:
            response += "\n\n💡 請輸入您的答案："
        push_text_message(user_id, response)
        return
    
    # 直接調用現有的主代理人處理所有其他訊息
    # 發送思考中提示
    send_thinking_message(event.reply_token)
    
    response = call_main_agent(user_message, user_id)
    # 使用推播訊息發送最終回應（因為 reply_token 已經用過）
    push_text_message(user_id, response)

def handle_postback(event: PostbackEvent):
    """處理用戶按鈕點擊事件"""
    data = event.postback.data
    user_id = event.source.user_id
    
    print(f"📱 收到 postback: {data}")
    
    # 將按鈕點擊事件交給主代理人處理
    user_message = f"按鈕點擊: {data}"
    response = call_main_agent(user_message, user_id)
    reply_text(event.reply_token, response)

# ===== LINE Bot 事件處理 =====
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message_event(event):
    """LINE Bot 文字消息事件處理"""
    handle_message(event)

@handler.add(PostbackEvent)
def handle_postback_event(event):
    """LINE Bot 按鈕點擊事件處理"""
    handle_postback(event)

# 添加 Follow 事件處理器
from linebot.v3.webhooks import FollowEvent

@handler.add(FollowEvent)
def handle_follow_event(event):
    """處理用戶加好友事件"""
    try:
        user_id = event.source.user_id
        print(f"🎉 用戶 {user_id} 加好友")
        
        # 檢查用戶是否已經綁定
        from accessories import mongo
        user = mongo.db.user.find_one({"lineId": user_id})
        
        if user:
            # 用戶已綁定
            welcome_message = f"""🎉 歡迎回來，{user.get('name', '用戶')}！

✅ 您已經成功綁定 MIS 教學助手
📧 綁定帳號：{user.get('email', '未知')}

💡 現在您可以使用所有功能：
• 問我任何資管相關問題
• 生成隨機測驗題目
• 獲得學習建議

直接發送訊息開始使用吧！"""
        else:
            # 用戶未綁定
            redis_client.setex(f"line_user:{user_id}", 3600, "pending_binding")
            
            welcome_message = """🎉 歡迎使用 MIS 教學助手！

📋 綁定步驟：
1. 在網站設定頁面生成 QR Code
2. 複製顯示的綁定碼
3. 直接發送綁定碼（以 bind_ 開頭）

💡 例如：bind_1757907057155_e47dt5lib

🔧 如果沒有綁定碼，請先在網站上生成 QR Code"""
        
        reply_text(event.reply_token, welcome_message)
        
    except Exception as e:
        print(f"❌ 處理加好友事件失敗: {e}")

# 添加 Unfollow 事件處理器
from linebot.v3.webhooks import UnfollowEvent

@handler.add(UnfollowEvent)
def handle_unfollow_event(event):
    """處理用戶取消好友事件"""
    try:
        user_id = event.source.user_id
        print(f"👋 用戶 {user_id} 取消好友")
        
        # 清除相關記錄
        redis_client.delete(f"line_user:{user_id}")
        
    except Exception as e:
        print(f"❌ 處理取消好友事件失敗: {e}")

# ===== Blueprint 路由 =====
@linebot_bp.route("/webhook", methods=['POST'])
def webhook():
    """LINE Bot Webhook 回調"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    return jsonify({'status': 'OK'})

# ==================== LINE Bot 純邏輯函數 ====================

def generate_quiz_question(requirements: str) -> str:
    """生成測驗題目的純邏輯 - 調用 Gemini API"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = get_api_key()
        if not api_key:
            return "❌ 無法獲取 Gemini API Key"
        
        # 初始化 Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        
        # 構建提示詞
        prompt = f"""請根據以下需求生成一道測驗題目：

需求：{requirements}

要求：
1. 直接生成題目內容，不要有任何前綴說明如「好的，這是一道...」或「---」等
2. 如果是選擇題，請提供 4 個選項，並標記正確答案
3. 如果是知識問答題，請提供問題和參考答案
4. 題目內容要適合 LINE Bot 顯示（簡潔明瞭）
5. 包含適當的表情符號和格式
6. 題目內容要專注於資管相關的計算機科學知識，如：
   - 基本計算機概論
   - 數位邏輯與設計
   - 作業系統原理
   - 程式語言基礎
   - 資料結構與演算法
   - 網路通訊技術
   - 資料庫系統
   - 人工智慧與機器學習
   - 資訊安全基礎
   - 雲端運算概念
   - 管理資訊系統(MIS)
   - 軟體工程基礎

請生成題目："""
        
        # 調用 Gemini API
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        print(f"測驗生成失敗: {e}")
        return f"❌ 測驗生成失敗，請稍後再試。錯誤: {str(e)}"

def generate_knowledge_point(query: str) -> str:
    """生成知識點的純邏輯 - 調用 Gemini API"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = get_api_key()
        if not api_key:
            return "❌ 無法獲取 Gemini API Key"
        
        # 初始化 Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.8
        )
        
        # 構建提示詞
        if query and query.strip():
            # 根據用戶查詢生成相關知識
            prompt = f"""請生成一個關於「{query}」的資管計算機科學知識點。

要求：
1. 直接生成知識點內容，不要有任何前綴說明
2. 內容要簡潔明瞭，適合 LINE Bot 顯示（每行不要太長）
3. 使用簡單的格式，避免複雜的 Markdown 語法
4. 包含適當的表情符號
5. 提供實用的學習建議
6. 如果是專業術語，請提供簡單解釋
7. 專注於資管相關的計算機科學知識
8. 使用換行符號分隔段落，不要使用複雜的列表格式

請生成知識點："""
        else:
            # 隨機生成一個知識點
            prompt = """請隨機生成一個資管計算機科學的知識點，主題可以是：
- 基本計算機概論
- 數位邏輯與設計
- 作業系統原理
- 程式語言基礎
- 資料結構與演算法
- 網路通訊技術
- 資料庫系統
- 人工智慧與機器學習
- 資訊安全基礎
- 雲端運算概念
- 管理資訊系統(MIS)
- 軟體工程基礎

要求：
1. 直接生成知識點內容，不要有任何前綴說明如「好的，這是一個...」或「---」等
2. 內容要簡潔明瞭，適合 LINE Bot 顯示（每行不要太長）
3. 使用簡單的格式，避免複雜的 Markdown 語法
4. 包含適當的表情符號
5. 提供實用的學習建議
6. 知識點要有實用價值，專注於資管領域
7. 使用換行符號分隔段落，不要使用複雜的列表格式

請生成知識點："""
        
        # 調用 Gemini API
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        print(f"知識點生成失敗: {e}")
        return f"❌ 知識點生成失敗，請稍後再試。錯誤: {str(e)}"

def grade_answer(answer: str, correct_answer: str, question: str) -> str:
    """批改答案的純邏輯 - 調用 Gemini API"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = get_api_key()
        if not api_key:
            return "❌ 無法獲取 Gemini API Key"
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.3
        )
        
        prompt = f"""請批改以下測驗答案：

問題：{question}
用戶答案：{answer}
正確答案：{correct_answer}

請進行智能批改，包含：
1. 答案是否正確
2. 如果錯誤，解釋為什麼錯誤
3. 提供學習建議

要求：
1. 直接生成批改結果，不要有任何前綴說明如「好的，我來批改...」或「---」等
2. 內容要簡潔明瞭，適合 LINE Bot 顯示
3. 包含適當的表情符號"""
        
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        return f"❌ 批改失敗：{str(e)}"

def provide_tutoring(question: str, user_answer: str, correct_answer: str) -> str:
    """提供教學指導的純邏輯 - 調用 Gemini API"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = get_api_key()
        if not api_key:
            return "❌ 無法獲取 Gemini API Key"
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        
        prompt = f"""請作為 AI 導師，為以下問題提供教學指導：

問題：{question}
用戶答案：{user_answer}
正確答案：{correct_answer}

請提供：
1. 為什麼答案錯誤的解釋
2. 正確的學習方法
3. 相關知識點複習建議
4. 練習建議

要求：
1. 直接生成教學指導內容，不要有任何前綴說明如「好的，我來指導...」或「---」等
2. 內容要簡潔明瞭，適合 LINE Bot 顯示
3. 包含適當的表情符號"""
        
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        return f"❌ 導師指導失敗：{str(e)}"

# ==================== 開發中功能 ====================

def learning_analysis_placeholder() -> str:
    """學習分析功能 - 開發中"""
    return "📊 學習分析功能\n\n🚧 此功能正在開發中，敬請期待！\n\n💡 功能預覽：\n• 學習進度追蹤\n• 弱點分析\n• 個人化建議\n• 學習報告"

def goal_setting_placeholder() -> str:
    """目標設定功能 - 開發中"""
    return "🎯 目標設定功能\n\n🚧 此功能正在開發中，敬請期待！\n\n💡 功能預覽：\n• 學習目標設定\n• 進度追蹤\n• 提醒通知\n• 成就系統"

def news_exam_info_placeholder() -> str:
    """最新消息/考試資訊功能 - 開發中"""
    return "📰 最新消息/考試資訊\n\n🚧 此功能正在開發中，敬請期待！\n\n💡 功能預覽：\n• 考試資訊推送\n• 重要公告\n• 學習資源更新\n• 活動通知"

def calendar_placeholder() -> str:
    """行事曆功能 - 開發中"""
    return "📅 行事曆功能\n\n🚧 此功能正在開發中，敬請期待！\n\n💡 功能預覽：\n• 學習計畫排程\n• 考試提醒\n• 作業截止日\n• 個人化行事曆"

# ==================== 測驗輪盤樣板 ====================

def create_quiz_selection_carousel() -> FlexMessage:
    """創建測驗選擇輪播樣板 - 使用 LINE Bot SDK v3 Flex Message 格式"""
    from linebot.v3.messaging import FlexMessage, FlexCarousel, FlexBubble, FlexBox, FlexText, FlexButton, MessageAction
    
    # 創建輪播樣板 - 5張卡片
    carousel = FlexCarousel(
        contents=[
            # 第一張卡片：基本計概、數位邏輯、作業系統
            FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(text="🎯 每日測驗 - 基礎知識", weight="bold", size="xl", align="center", color="#1DB446"),
                        FlexText(text="選擇您想要測驗的基礎知識點：", size="sm", align="center", color="#666666", margin="md")
                    ]
                ),
                footer=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="基本計概", text="@測驗 基本計概")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="數位邏輯", text="@測驗 數位邏輯")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="作業系統", text="@測驗 作業系統")
                        )
                    ],
                    spacing="sm"
                )
            ),
            
            # 第二張卡片：程式語言、資料結構、網路通訊
            FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(text="💻 每日測驗 - 程式技術", weight="bold", size="xl", align="center", color="#1DB446"),
                        FlexText(text="選擇您想要測驗的程式技術知識點：", size="sm", align="center", color="#666666", margin="md")
                    ]
                ),
                footer=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="程式語言", text="@測驗 程式語言")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="資料結構", text="@測驗 資料結構")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="網路通訊", text="@測驗 網路通訊")
                        )
                    ],
                    spacing="sm"
                )
            ),
            
            # 第三張卡片：資料庫、AI與機器學習、資訊安全
            FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(text="🔐 每日測驗 - 進階技術", weight="bold", size="xl", align="center", color="#1DB446"),
                        FlexText(text="選擇您想要測驗的進階技術知識點：", size="sm", align="center", color="#666666", margin="md")
                    ]
                ),
                footer=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="資料庫", text="@測驗 資料庫")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="AI與機器學習", text="@測驗 AI與機器學習")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="資訊安全", text="@測驗 資訊安全")
                        )
                    ],
                    spacing="sm"
                )
            ),
            
            # 第四張卡片：雲端運算、MIS系統、軟體工程
            FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(text="☁️ 每日測驗 - 系統應用", weight="bold", size="xl", align="center", color="#1DB446"),
                        FlexText(text="選擇您想要測驗的系統應用知識點：", size="sm", align="center", color="#666666", margin="md")
                    ]
                ),
                footer=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="雲端運算", text="@測驗 雲端運算")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="MIS系統", text="@測驗 MIS系統")
                        ),
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="軟體工程", text="@測驗 軟體工程")
                        )
                    ],
                    spacing="sm"
                )
            ),
            
            # 第五張卡片：隨機（只有一個按鈕）
            FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(text="🎲 每日測驗 - 隨機挑戰", weight="bold", size="xl", align="center", color="#1DB446"),
                        FlexText(text="讓系統為您隨機選擇知識點和題型：", size="sm", align="center", color="#666666", margin="md")
                    ]
                ),
                footer=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexButton(
                            style="primary",
                            color="#1DB446",
                            height="sm",
                            action=MessageAction(label="🎲 隨機測驗", text="@測驗 隨機")
                        )
                    ],
                    spacing="sm"
                )
            )
        ]
    )
    
    return FlexMessage(
        alt_text="選擇測驗知識點",
        contents=carousel
    )

