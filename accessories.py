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

sqldb = SQLAlchemy()
mail = Mail()
redis_client = FlaskRedis()
token_store = FlaskRedis()
mongo = PyMongo()
login_manager = LoginManager()
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.students.find_one({'_id': ObjectId(user_id)})
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


def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])



def verify_token(token, expiration=3600):
    serializer = get_serializer()
    try:
        user_id = serializer.loads(
            token,
            salt=current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except Exception as e:
        return None
    return user_id

def init_mongo_data():
    try:
        exam_count = mongo.db.exam.count_documents({})
        
        if exam_count == 0:
            print("檢測到exam collection為空，開始初始化資料...")
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(current_dir, 'data', 'merged_results.json')
            
            if not os.path.exists(json_file_path):
                print(f"錯誤：找不到檔案 {json_file_path}")
                return False
            
            with open(json_file_path, 'r', encoding='utf-8') as file:
                exam_data = json.load(file)
            
            if not exam_data:
                print("錯誤：json檔案為空或格式不正確")
                return False
            
            # 扁平化資料結構
            flattened_data = []
            for item in exam_data:
                flattened_item = {
                    'type': item.get('type'),
                    'school': item.get('school'),
                    'department': item.get('department'),
                    'year': item.get('year'),
                    'question_number': item.get('question_number'),
                    'question_text': item.get('question_text'),
                    'options': item.get('options'),
                    'answer': item.get('answer'),
                    'answer_type': item.get('answer_type'),
                    'image_file': item.get('image_file'),
                    'detail-answer': item.get('detail-answer'),
                    'key_points': item.get('key-points'),
                    'difficulty level': item.get('difficulty level'),
                }
                flattened_data.append(flattened_item)
           
            result = mongo.db.exam.insert_many(flattened_data)
            
            print(f"成功初始化考試資料，共插入 {len(result.inserted_ids)} 筆資料")
            return True
            
        else:
            print(f"exam collection已有 {exam_count} 筆資料，無需初始化")
            return True
            
    except FileNotFoundError:
        print("錯誤：找不到correct_exam.json檔案")
        return False
    except json.JSONDecodeError:
        print("錯誤：json檔案格式不正確")
        return False
    except Exception as e:
        print(f"初始化考試資料時發生錯誤：{str(e)}")
        return False



