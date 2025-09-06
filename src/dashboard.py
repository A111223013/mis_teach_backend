#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
儀表板API - 提供學習數據和分析功能
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from tool.api_keys import get_api_key
from accessories import init_gemini
import json
import re
from datetime import datetime, timedelta
from accessories import mongo, sqldb, refresh_token
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


def init_calendar_tables():
    """初始化行事曆資料表"""
    try:
        # 使用現有的 SQLAlchemy 連線
        with sqldb.engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS schedule (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_email VARCHAR(255) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    content TEXT,
                    event_date DATETIME NOT NULL,
                    notify_enabled BOOLEAN DEFAULT FALSE,
                    notify_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            '''))
            conn.commit()        
        print("行事曆資料表初始化完成")
    except Exception as e:
        print(f"初始化行事曆資料表失敗: {e}")






@dashboard_bp.route('/get-user-name', methods=['POST', 'OPTIONS'])
def get_user_name():
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'message': '未提供token'}), 401
    token = auth_header.split(" ")[1]
    user_name = get_user_info(token, 'name')
    
    return jsonify({'token': refresh_token(token), 'name': user_name}), 200




@dashboard_bp.route('/calendar/events', methods=['GET'])
def get_calendar_events():
    """取得用戶的行事曆事件"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'events': []}), 401
    
    token = auth_header.split(" ")[1]
    student_email = get_user_info(token, 'email')
    
    with sqldb.engine.connect() as conn:
        result = conn.execute(text('''
            SELECT id, title, content, event_date, notify_enabled, notify_time
            FROM schedule 
            WHERE student_email = :student_email
            ORDER BY event_date ASC
        '''), {'student_email': student_email})
    
    events = [{
        'id': row[0],
        'title': row[1],
        'content': row[2] or '',
        'start': row[3].isoformat() if row[3] else None,
        'meta': {
            'id': row[0],
            'notifyEnabled': bool(row[4]),
            'notifyTime': row[5].isoformat() if row[5] else None
        }
    } for row in result]
    
    return jsonify({'token': refresh_token(token), 'events': events})

@dashboard_bp.route('/calendar/events', methods=['POST', 'OPTIONS'])
def create_calendar_event():
    """新增行事曆事件"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'id': None}), 401
    
    token = auth_header.split(" ")[1]
    student_email = get_user_info(token, 'email')
    data = request.get_json()
    
    with sqldb.engine.connect() as conn:
        result = conn.execute(text('''
            INSERT INTO schedule 
            (student_email, title, content, event_date, notify_enabled, notify_time)
            VALUES (:student_email, :title, :content, :event_date, :notify_enabled, :notify_time)
        '''), {
            'student_email': student_email,
            'title': data.get('title'),
            'content': data.get('content', ''),
            'event_date': data.get('start'),
            'notify_enabled': data.get('meta', {}).get('notifyEnabled', False),
            'notify_time': data.get('meta', {}).get('notifyTime')
        })
        
        event_id = result.lastrowid
        conn.commit()
    
    # 如果有設定通知，加入 Redis 佇列
    notify_enabled = data.get('meta', {}).get('notifyEnabled', False)
    notify_time = data.get('meta', {}).get('notifyTime')
    if notify_enabled and notify_time:
        add_notification_to_redis(student_email, event_id, data.get('title'), data.get('content', ''), data.get('start'), notify_time)
    
    return jsonify({'token': refresh_token(token), 'id': event_id})

@dashboard_bp.route('/calendar/events/<int:event_id>', methods=['PUT'])
def update_calendar_event(event_id):
    """更新行事曆事件"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供認證 token'}), 401
    
    token = auth_header.split(" ")[1]
    student_email = get_user_info(token, 'email')
    data = request.get_json()
    
    if not data.get('title') or not data.get('start'):
        return jsonify({'token': None, 'message': '標題和日期為必填欄位'}), 400
    
    with sqldb.engine.connect() as conn:
        result = conn.execute(text('''
            UPDATE schedule 
            SET title = :title, content = :content, event_date = :event_date, 
                notify_enabled = :notify_enabled, notify_time = :notify_time, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :event_id AND student_email = :student_email
        '''), {
            'title': data.get('title'),
            'content': data.get('content', ''),
            'event_date': data.get('start'),
            'notify_enabled': data.get('meta', {}).get('notifyEnabled', False),
            'notify_time': data.get('meta', {}).get('notifyTime'),
            'event_id': event_id,
            'student_email': student_email
        })
        
        if result.rowcount == 0:
            return jsonify({'token': None, 'message': '事件不存在或無權限修改'}), 404
        
        conn.commit()
    
    # 更新 Redis 通知佇列
    notify_enabled = data.get('meta', {}).get('notifyEnabled', False)
    notify_time = data.get('meta', {}).get('notifyTime')
    if notify_enabled and notify_time:
        add_notification_to_redis(student_email, event_id, data.get('title'), data.get('content', ''), data.get('start'), notify_time)
    
    return jsonify({'token': refresh_token(token), 'message': '事件更新成功'})

@dashboard_bp.route('/calendar/events/<int:event_id>', methods=['DELETE'])
def delete_calendar_event(event_id):
    """刪除行事曆事件"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供認證 token'}), 401
    
    token = auth_header.split(" ")[1]
    student_email = get_user_info(token, 'email')
    
    with sqldb.engine.connect() as conn:
        result = conn.execute(text('''
            DELETE FROM schedule 
            WHERE id = :event_id AND student_email = :student_email
        '''), {'event_id': event_id, 'student_email': student_email})
        
        if result.rowcount == 0:
            return jsonify({'token': None, 'message': '事件不存在或無權限刪除'}), 404
        
        conn.commit()
    
    # 從 Redis 移除通知
    remove_notification_from_redis(event_id)
    
    return jsonify({'token': refresh_token(token), 'message': '事件刪除成功'})

def add_notification_to_redis(student_email: str, event_id: int, title: str, content: str, event_date: str, notify_time: str):
    """將通知加入 Redis 佇列"""
    from datetime import datetime
    notify_datetime = datetime.fromisoformat(notify_time.replace('Z', '+00:00'))
    notify_time_str = notify_datetime.strftime('%Y-%m-%d %H:%M')
    
    notification_data = {
        'student_email': student_email,
        'event_id': event_id,
        'title': title,
        'content': content,
        'event_date': event_date,
        'notify_time': notify_time_str
    }
    
    key = f"notification:{notify_time_str}:{event_id}"
    redis_client.setex(key, 86400 * 7, json.dumps(notification_data))  # 7天過期
    print(f"通知已加入 Redis: {key}")

def remove_notification_from_redis(event_id: int):
    """從 Redis 移除通知"""
    pattern = f"notification:*:{event_id}"
    keys = redis_client.keys(pattern)
    
    if keys:
        redis_client.delete(*keys)
        print(f"已從 Redis 移除 {len(keys)} 個通知")

# 移除自動初始化，改為在應用程式啟動時初始化



