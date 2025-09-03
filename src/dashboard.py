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
import schedule

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



@dashboard_bp.route('/get-user-name  ', methods=['POST', 'OPTIONS'])
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


def init_calendar_tables():
    """初始化行事曆資料表"""
    try:
        # 使用現有的 SQLAlchemy 連線
        with sqldb.engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    event_date DATETIME NOT NULL,
                    notify_enabled BOOLEAN DEFAULT FALSE,
                    notify_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            '''))
            
            # MySQL 不支援 CREATE INDEX IF NOT EXISTS，需要先檢查索引是否存在
            try:
                conn.execute(text('''
                    CREATE INDEX idx_calendar_events_user_id 
                    ON calendar_events(user_id)
                '''))
            except Exception as e:
                if "Duplicate key name" not in str(e):
                    print(f"建立 user_id 索引時發生錯誤: {e}")
            
            try:
                conn.execute(text('''
                    CREATE INDEX idx_calendar_events_date 
                    ON calendar_events(event_date)
                '''))
            except Exception as e:
                if "Duplicate key name" not in str(e):
                    print(f"建立 event_date 索引時發生錯誤: {e}")
            conn.commit()
        
        print("行事曆資料表初始化完成")
    except Exception as e:
        print(f"初始化行事曆資料表失敗: {e}")

@dashboard_bp.route('/calendar/events', methods=['GET'])
def get_calendar_events():
    """取得用戶的行事曆事件"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # 使用現有的 SQLAlchemy 連線
        with sqldb.engine.connect() as conn:
            result = conn.execute(text('''
                SELECT id, title, event_date, notify_enabled, notify_time
                FROM calendar_events 
                WHERE user_id = :user_id
                ORDER BY event_date ASC
            '''), {'user_id': user_id})
        
        events = []
        for row in result:
            event = {
                'id': row[0],
                'title': row[1],
                'start': row[2],
                'meta': {
                    'id': row[0],
                    'notify': bool(row[3]),
                    'notifyTime': row[4]
                }
            }
            events.append(event)
        
        return jsonify({'events': events})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/calendar/events', methods=['POST'])
def create_calendar_event():
    """新增行事曆事件"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        title = data.get('title')
        event_date = data.get('start')
        notify_enabled = data.get('meta', {}).get('notify', False)
        notify_time = data.get('meta', {}).get('notifyTime')
        
        if not title or not event_date:
            return jsonify({'error': '標題和日期為必填欄位'}), 400
        
        # 使用現有的 SQLAlchemy 連線
        with sqldb.engine.connect() as conn:
            result = conn.execute(text('''
                INSERT INTO calendar_events 
                (user_id, title, event_date, notify_enabled, notify_time)
                VALUES (:user_id, :title, :event_date, :notify_enabled, :notify_time)
            '''), {
                'user_id': user_id,
                'title': title,
                'event_date': event_date,
                'notify_enabled': notify_enabled,
                'notify_time': notify_time
            })
            
            # 取得新插入的 ID
            event_id = result.lastrowid
            conn.commit()
        
        # 如果有設定通知，加入 Redis 佇列
        if notify_enabled and notify_time:
            add_notification_to_redis(user_id, event_id, title, notify_time)
        
        return jsonify({'id': event_id, 'message': '事件新增成功'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/calendar/events/<int:event_id>', methods=['PUT'])
def update_calendar_event(event_id):
    """更新行事曆事件"""
    try:
        data = request.get_json()
        title = data.get('title')
        event_date = data.get('start')
        notify_enabled = data.get('meta', {}).get('notify', False)
        notify_time = data.get('meta', {}).get('notifyTime')
        
        if not title or not event_date:
            return jsonify({'error': '標題和日期為必填欄位'}), 400
        
        # 使用現有的 SQLAlchemy 連線
        with sqldb.engine.connect() as conn:
            result = conn.execute(text('''
                UPDATE calendar_events 
                SET title = :title, event_date = :event_date, notify_enabled = :notify_enabled, 
                    notify_time = :notify_time, updated_at = CURRENT_TIMESTAMP
                WHERE id = :event_id
            '''), {
                'title': title,
                'event_date': event_date,
                'notify_enabled': notify_enabled,
                'notify_time': notify_time,
                'event_id': event_id
            })
            
            if result.rowcount == 0:
                return jsonify({'error': '事件不存在'}), 404
            
            conn.commit()
        
        # 更新 Redis 通知佇列
        if notify_enabled and notify_time:
            add_notification_to_redis('default_user', event_id, title, notify_time)
        
        return jsonify({'message': '事件更新成功'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/calendar/events/<int:event_id>', methods=['DELETE'])
def delete_calendar_event(event_id):
    """刪除行事曆事件"""
    try:
        # 使用現有的 SQLAlchemy 連線
        with sqldb.engine.connect() as conn:
            result = conn.execute(text('DELETE FROM calendar_events WHERE id = :event_id'), {'event_id': event_id})
            
            if result.rowcount == 0:
                return jsonify({'error': '事件不存在'}), 404
            
            conn.commit()
        
        # 從 Redis 移除通知
        remove_notification_from_redis(event_id)
        
        return jsonify({'message': '事件刪除成功'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def add_notification_to_redis(user_id: str, event_id: int, title: str, notify_time: str):
    """將通知加入 Redis 佇列"""
    try:
        # 使用現有的 Redis 連線
        notification_data = {
            'user_id': user_id,
            'event_id': event_id,
            'title': title,
            'notify_time': notify_time
        }
        
        # 使用 notify_time 作為 key，儲存通知資料
        key = f"notification:{notify_time}:{event_id}"
        redis_client.setex(key, 86400 * 7, json.dumps(notification_data))  # 7天過期
        
        print(f"通知已加入 Redis: {key}")
        
    except Exception as e:
        print(f"加入 Redis 通知失敗: {e}")

def remove_notification_from_redis(event_id: int):
    """從 Redis 移除通知"""
    try:
        # 使用現有的 Redis 連線
        # 搜尋並刪除相關的通知
        pattern = f"notification:*:{event_id}"
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            print(f"已從 Redis 移除 {len(keys)} 個通知")
        
    except Exception as e:
        print(f"從 Redis 移除通知失敗: {e}")

# 移除自動初始化，改為在應用程式啟動時初始化



