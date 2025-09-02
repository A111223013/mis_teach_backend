#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
儀表板API - 提供學習數據和分析功能
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import google.generativeai as genai
from tool.api_keys import get_api_key
import json
import re
from datetime import datetime, timedelta
from accessories import mongo, sqldb
from bson import ObjectId
import jwt
from flask import current_app
import uuid
from accessories import mail, redis_client, save_json_to_mongo
from src.api import get_user_info, verify_token
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import random
from flask_sqlalchemy import SQLAlchemy
import redis, json ,time
from flask_mail import Mail, Message
from accessories import mail, redis_client
from sqlalchemy import text

dashboard_bp = Blueprint('dashboard', __name__)

# 配置多個 Gemini API Keys
def create_gemini_model(api_key):
    """為指定的API key創建Gemini模型"""
    try:    
        genai.configure(api_key=api_key)
        # 使用正確的模型名稱
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 測試API是否工作
        try:
            test_response = model.generate_content(
                "測試",
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 10,
                    'candidate_count': 1
                }
            )
            if test_response and hasattr(test_response, 'text'):
                print(f"✅ API Key 測試成功: {api_key[:8]}...")
                return model
            else:
                print(f"❌ API Key 測試失敗 (無回應): {api_key[:8]}...")
                return None
        except Exception as test_error:
            print(f"❌ API Key 測試失敗: {api_key[:8]}... - {str(test_error)}")
            return None
            
    except Exception as e:
        print(f"❌ API Key 初始化失敗: {api_key[:8]}... - {e}")
        return None

def init_gemini():
    """初始化主要的Gemini API（向後兼容）"""
    try:
        api_key = get_api_key()  # 使用tool/api_keys.py
        genai.configure(api_key=api_key)
        # 使用正確的模型名稱
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Gemini API 初始化成功")
        return model
    except Exception as e:
        print(f"❌ Gemini API 初始化失敗: {e}")
        return None



@dashboard_bp.route('/  ', methods=['POST', 'OPTIONS'])
def get_user_name():
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'message': '未提供token'}), 401
    # 檢查Authorization header格式
    if not auth_header.startswith('Bearer '):
        return jsonify({'message': 'Token格式錯誤'}), 401
    token = auth_header.split(" ")[1]
    
    try:
        user_name = get_user_info(token, 'name')
        return jsonify({'name': user_name}), 200
    except ValueError as e:
        error_msg = str(e)
        if "expired" in error_msg.lower():
            return jsonify({'message': 'Token已過期，請重新登錄', 'code': 'TOKEN_EXPIRED'}), 401
        elif "invalid" in error_msg.lower():
            return jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
        else:
            return jsonify({'message': '認證失敗', 'code': 'AUTH_FAILED'}), 401
    except Exception as e:
        print(f"獲取用戶名稱時發生錯誤: {str(e)}")
        return jsonify({'message': '服務器內部錯誤', 'code': 'SERVER_ERROR'}), 500

r = redis.Redis(host='localhost', port=3306, db=0)
with sqldb.engine.connect() as conn:
    conn.execute(sqldb.text("""
        CREATE TABLE Calendar_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            start DATETIME NOT NULL,
            end DATETIME NOT NULL,
            notify BOOLEAN DEFAULT FALSE,
            notify_time DATETIME NULL,
            status ENUM('pending', 'done', 'cancelled') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_start (start),
            INDEX idx_end (end),
            INDEX idx_notify_time (notify_time),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))
    conn.commit()
@dashboard_bp.route('/date/events',  methods=['GET', 'POST'])
def create_event():
    data = request.json
    with sqldb.engine.connect() as conn:
        result = conn.execute(sqldb.text("""
            INSERT INTO Calendar_records (user_id, title, start, end, notify, notify_time, status)
            VALUES (:user_id, :title, :start, :end, :notify, :notify_time, :status)
        """), {
            "user_id": data['user_id'],
            "title": data['title'],
            "start": data['start'],
            "end": data['end'],
            "notify": data['notify'],
            "notify_time": data['notify_time'],
            "status": data.get('status', 'pending')
        })

        new_id = result.lastrowid

        # 如果要通知，存進 Redis
        if data['notify'] and data['notify_time']:
            r.set(f"notify:{new_id}", json.dumps({
                'id': new_id,
                'title': data['title'],
                'user_id': data['user_id'],
                'notify_time': data['notify_time']
            }))

    return jsonify({'id': new_id}), 201


@dashboard_bp.route('/date/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    with sqldb.engine.connect() as conn:
        conn.execute(sqldb.text("DELETE FROM Calendar_records WHERE id=:id"), {"id": event_id})
        r.delete(f"notify:{event_id}")
    return '', 204
