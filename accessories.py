from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_mail import Message
from flask_redis import FlaskRedis
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, request, url_for
from flask_login import LoginManager, UserMixin
from queue import Queue
from flask_pymongo import PyMongo
from datetime import datetime, timezone, timedelta
from bson.objectid import ObjectId
import uuid
from sqlalchemy import text
import jwt
from sqlalchemy.exc import OperationalError
import time
import json
import os
import google.generativeai as genai
from tool.api_keys import get_api_key
# 條件性導入 neo4j 以避免環境相容性問題
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
    print("✅ [DEBUG] Neo4j 導入成功")
except Exception as e:
    print(f"⚠️ [DEBUG] Neo4j 導入失敗（跳過相關功能）: {type(e).__name__}: {e}")
    GraphDatabase = None
    NEO4J_AVAILABLE = False

sqldb = SQLAlchemy()
mail = Mail()
redis_client = FlaskRedis()
token_store = FlaskRedis()
mongo = PyMongo()
login_manager = LoginManager()
login_manager.login_view = "login"

# Neo4j 驅動程式
neo4j_driver = None

def init_neo4j():
    """初始化 Neo4j 連接"""
    global neo4j_driver
    try:
        if not NEO4J_AVAILABLE:
            print("⚠️ Neo4j 不可用，跳過初始化")
            return None
            
        from config import Config
        neo4j_driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
        print(f"✅ Neo4j 連接成功: {Config.NEO4J_URI}")
        return neo4j_driver
    except Exception as e:
        print(f"❌ Neo4j 連接失敗: {e}")
        return None

def get_neo4j_driver():
    """獲取 Neo4j 驅動程式"""
    global neo4j_driver
    if not NEO4J_AVAILABLE:
        return None
    if neo4j_driver is None:
        neo4j_driver = init_neo4j()
    return neo4j_driver

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.user.find_one({'_id': ObjectId(user_id)})
    return user_data

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.password = user_data['password']
    @property
    def is_active(self):
        return True if self.password else False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id
    

def update_json_in_mongo(data, collection_name, doc_name, save_history=True):
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    collection = mongo.db[collection_name]
    history_collection = mongo.db[f"{collection_name}_history"]

    existing_doc = collection.find_one({"_id": doc_name})

    if existing_doc:
        if save_history:
            history_doc = existing_doc.copy()
            history_doc["_id"] = f"{doc_name}_{current_time}"
            history_collection.insert_one(history_doc)

        for key, value in data.items():
            existing_doc[key] = value

        existing_doc['last_updated'] = current_time

        collection.replace_one({"_id": doc_name}, existing_doc)

    else:
        data["_id"] = doc_name
        data['last_updated'] = current_time
        collection.insert_one(data)



def save_json_to_mongo(data_dict, collection_name, document_name, save_history=True):
    collection = mongo.db[collection_name]
    history_collection = mongo.db[f"{collection_name}_history"]
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    data_dict["create_time"] = current_time
    existing_document = collection.find_one({"_id": document_name})
    if existing_document:
        existing_document["archived_time"] = current_time
        if save_history:
            history_collection.insert_one({
                **existing_document,
                "_id": f"{document_name}_{current_time}"
            })
        collection.delete_one({"_id": document_name})

    collection.insert_one({
        "_id": document_name,
        **data_dict
    })

def remove_json_in_mongo(collection_name, doc_name, save_history=True):
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    collection = mongo.db[collection_name]
    history_collection = mongo.db[f"{collection_name}_history"]

    existing_doc = collection.find_one({"_id": doc_name})

    if existing_doc:
        if save_history:
            history_doc = existing_doc.copy()
            history_doc["_id"] = f"{doc_name}_{current_time}"
            history_collection.insert_one(history_doc)
        collection.delete_one({"_id": doc_name})





def refresh_token(old_token):   
    try:
        decoded_token = jwt.decode(old_token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        access_exp_time = datetime.now() + timedelta(hours=3)
        new_access_token = jwt.encode({
            'user': decoded_token['user'],
            'exp': int(access_exp_time.timestamp())
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        return new_access_token
    except Exception as e:
        print(f"❌ Token 刷新失敗: {e}")
        return None
    
def init_gemini(model_name = 'gemini-2.5-flash'):
    """初始化主要的Gemini API（優先使用新版 SDK）"""
    try:
        api_key = get_api_key()  # 使用tool/api_keys.py
        # 強制優先使用新版 Google GenAI SDK
        try:
            # 嘗試多種導入方式
            try:
                import google.genai as new_genai
                from google.genai import types
                print("🔍 [DEBUG] 成功導入新版 Google GenAI SDK (方式1)")
            except ImportError:
                from google import genai as new_genai
                from google.genai import types
                print("🔍 [DEBUG] 成功導入新版 Google GenAI SDK (方式2)")
            except ImportError:
                raise ImportError("無法導入新版 SDK")
            
            client = new_genai.Client(api_key=api_key)
            # 創建一個包裝器以保持 API 兼容性
            class GeminiWrapper:
                def __init__(self, client, model_name):
                    self.client = client
                    self.model_name = model_name
                    self.sdk_version = "new"
                    print(f"🔍 [DEBUG] GeminiWrapper 初始化完成，模型: {model_name}")
                
                def generate_content(self, contents, generation_config=None):
                    """兼容舊版 API 的 generate_content 方法，優化圖片處理"""
                    print(f"🔍 [DEBUG] generate_content 被呼叫，contents 類型: {type(contents)}")
                    if generation_config:
                        print(f"🔍 [DEBUG] 包含 generation_config: {generation_config}")
                    
                    # 準備請求參數
                    request_params = {
                        'model': self.model_name,
                        'contents': contents if isinstance(contents, list) else [contents]
                    }
                    
                    # 新版 SDK 的 generation_config 參數名稱可能不同
                    if generation_config:
                        # 將舊版參數轉換為新版參數
                        config = {}
                        if 'max_output_tokens' in generation_config:
                            config['max_output_tokens'] = generation_config['max_output_tokens']
                        if 'temperature' in generation_config:
                            config['temperature'] = generation_config['temperature']
                        if 'top_p' in generation_config:
                            config['top_p'] = generation_config['top_p']
                        if 'top_k' in generation_config:
                            config['top_k'] = generation_config['top_k']
                        
                        if config:
                            request_params['config'] = config
                    
                    if isinstance(contents, str):
                        print("🔍 [DEBUG] 處理純文字內容")
                    elif isinstance(contents, list):
                        print(f"🔍 [DEBUG] 處理列表內容，項目數: {len(contents)}")
                        
                        # 檢查是否包含圖片
                        has_images = False
                        for i, item in enumerate(contents):
                            item_type = type(item).__name__
                            if 'Part' in item_type:
                                print(f"🔍 [DEBUG] 項目 {i}: {item_type} (圖片 Part 物件)")
                                has_images = True
                            else:
                                print(f"🔍 [DEBUG] 項目 {i}: {item_type} - {str(item)[:50]}...")
                        
                        if has_images:
                            print("🔍 [DEBUG] 檢測到圖片內容，使用新版 SDK 圖片處理")
                    else:
                        print(f"🔍 [DEBUG] 處理其他格式內容: {type(contents)}")
                    
                    try:
                        response = self.client.models.generate_content(**request_params)
                        print(f"🔍 [DEBUG] 新版 SDK 回應類型: {type(response)}")
                        return response
                    except Exception as e:
                        print(f"⚠️ [DEBUG] 新版 SDK 參數失敗，嘗試簡化版本: {e}")
                        # 如果參數有問題，回退到基本版本
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=contents if isinstance(contents, list) else [contents]
                        )
                        print(f"🔍 [DEBUG] 簡化版本回應類型: {type(response)}")
                        return response
            
            wrapper = GeminiWrapper(client, model_name)
            print("✅ Gemini API 初始化成功 (新版 SDK - 圖片優化)")
            return wrapper
            
        except ImportError as e:
            print(f"⚠️ [DEBUG] 新版 SDK 導入失敗: {e}")
            # 回退到舊版 SDK
            print("🔍 [DEBUG] 回退到舊版 SDK")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            print("✅ Gemini API 初始化成功 (舊版 SDK)")
            return model
            
    except Exception as e:
        print(f"❌ Gemini API 初始化失敗: {e}")
        import traceback
        print(f"🔍 [DEBUG] 完整錯誤堆疊:")
        traceback.print_exc()
        return None


def init_mongo_data():
    try:
        exam_count = mongo.db.exam.count_documents({})
        if exam_count == 0:
            print("檢測到exam collection為空，開始初始化資料...")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(current_dir, 'data', '20250918_ai_judged_final.json')
            if not os.path.exists(json_file_path):
                print(f"錯誤：找不到檔案 {json_file_path}")
                return False
            with open(json_file_path, 'r', encoding='utf-8') as file:
                exam_data = json.load(file)
            
            # 處理不同類型的題目結構
            processed_data = []
            for item in exam_data:
                if item.get('type') == 'single':
                    # 單題結構
                    processed_item = {
                        'type': item.get('type'),
                        'school': item.get('school'),
                        'department': item.get('department'),
                        'year': item.get('year'),
                        'question_number': item.get('question_number'),
                        'question_text': item.get('question_text'),
                        'options': item.get('options', []),
                        'answer': item.get('answer'),
                        'answer_type': item.get('answer_type'),
                        'image_file': item.get('image_file', []),
                        'detail-answer': item.get('detail-answer'),
                        'key-points': item.get('key-points'),
                        'micro_concepts': item.get('micro_concepts', []),
                        'difficulty level': item.get('difficulty level'),
                        'error reason': item.get('error reason', '')  # 新增 error reason 欄位
                    }
                    processed_data.append(processed_item)
                
                elif item.get('type') == 'group':
                    # 群組題結構
                    group_item = {
                        'type': item.get('type'),
                        'school': item.get('school'),
                        'department': item.get('department'),
                        'year': item.get('year'),
                        'group_question_text': item.get('group_question_text'),
                        'key-points': item.get('key-points'),
                        'micro_concepts': item.get('micro_concepts', []),
                        'sub_questions': []
                    }
                    
                    # 處理子題目
                    if 'sub_questions' in item and isinstance(item['sub_questions'], list):
                        for sub_item in item['sub_questions']:
                            try:
                                sub_question = {
                                    'question_number': sub_item.get('question_number'),
                                    'question_text': sub_item.get('question_text'),
                                    'options': sub_item.get('options', []),
                                    'answer': sub_item.get('answer'),
                                    'answer_type': sub_item.get('answer_type'),
                                    'image_file': sub_item.get('image_file', []),
                                    'detail-answer': sub_item.get('detail-answer'),
                                    'key-points': sub_item.get('key-points'),
                                    'difficulty level': sub_item.get('difficulty level'),
                                
                                }
                                group_item['sub_questions'].append(sub_question)
                            except Exception:
                                continue
                    
                    processed_data.append(group_item)
                
                else:
                    # 其他類型，保持原始結構
                    processed_data.append(item)
           
            result = mongo.db.exam.insert_many(processed_data)
            print(f"包含單題和群組題的完整結構")
            return True    
        else:
            print(f"exam collection已有 {exam_count} 筆資料，無需初始化")
            return True
    except FileNotFoundError:
        print("錯誤：找不到20250918_ai_judged_final.json檔案")
        return False



def send_mail(sender, receiver, subject,content):
    if not sender or not receiver:
        raise ValueError("Sender email or receiver is missing!")
    mail_id = None
    taipei_tz = timezone(timedelta(hours=8))  
    created_at = datetime.now(taipei_tz)  
    content = content.replace("\n", "<br>")
    subject = subject.replace("\n", " ")
    create_mail_info= text("""
        CREATE TABLE IF NOT EXISTS mail_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sender VARCHAR(255) NOT NULL,
            receiver VARCHAR(255) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            argument TEXT NULL,
            content TEXT NOT NULL,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_time INT NOT NULL,
            mail_type INT NOT NULL
        );
    """)
    insert_mail = text("""
        INSERT INTO mail_info (sender, receiver, subject, content, time)
        VALUES (:sender, :receiver, :subject, :content, :time)
    """)
    delay = 1
    max_retries = 3
    for attempt in range(max_retries):
        try:
            sqldb.session.execute(create_mail_info)
            result = sqldb.session.execute(insert_mail, {
                "sender": sender,
                "receiver": receiver,
                "subject": subject,
                "content": content,
                "time": created_at.strftime('%Y-%m-%d %H:%M:%S'),  
            })
            mail_id = result.lastrowid
            sqldb.session.commit()
            break  
        except OperationalError:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2  
            else:
                print(f"資料庫操作失敗，已重試 {max_retries} 次")
                return {"error": "Database operation failed"}
    
    receiver_data = mongo.db.user.find_one({"email": receiver})
    notification_method = receiver_data.get("notification_method", {}) if isinstance(receiver_data, dict) and isinstance(receiver_data.get("notification_method", {}), dict) else {}
    mail_notification = notification_method.get("mail", True)
    if mail_notification:
        body = f"""
        <strong>{subject}</strong>
        {content}
        """
        msg = Message(
            subject=f"訊息通知 - {subject}",
            recipients=[receiver],
            html=body,
            sender="misteacher011@gmail.com"
        )
        mail.send(msg)
    return {"mail_id": mail_id}

def send_calendar_notification(student_email: str, event_title: str, event_content: str, event_date: str):
    """發送行事曆事件通知郵件"""
    try:
        # 從 MongoDB 獲取學生資料
        student_data = mongo.db.user.find_one({"email": student_email})
        if not student_data:
            print(f"❌ 找不到學生資料: {student_email}")
            return False
        
        student_name = student_data.get('name', '同學')
        
        # 格式化事件日期
        try:
            event_datetime = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            formatted_date = event_datetime.strftime('%Y年%m月%d日 %H:%M')
        except:
            formatted_date = event_date
        
        # 創建郵件內容
        subject = f"📅 行事曆提醒 - {event_title}"
        content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">📅 行事曆提醒</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #e74c3c; margin-top: 0;">{event_title}</h3>
                <p style="color: #7f8c8d; font-size: 14px;">⏰ 事件時間: {formatted_date}</p>
                {f'<p style="color: #34495e;">{event_content}</p>' if event_content else ''}
            </div>
            <p style="color: #95a5a6; font-size: 12px;">
                此為系統自動發送的通知郵件，請勿回覆。
            </p>
        </div>
        """
        
        # 發送郵件
        msg = Message(
            subject=subject,
            recipients=[student_email],
            html=content,
            sender="misteacher011@gmail.com"
        )
        mail.send(msg)
        
        print(f"✅ 行事曆通知郵件已發送給 {student_name} ({student_email})")
        return True
        
    except Exception as e:
        print(f"❌ 發送行事曆通知郵件失敗: {e}")
        return False

