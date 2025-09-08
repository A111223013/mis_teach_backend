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
    
    refreshed_token = refresh_token(token)
    return jsonify({'token': refreshed_token, 'name': user_name}), 200




@dashboard_bp.route('/events', methods=['POST', 'OPTIONS'])
def get_calendar_events():
    """取得行事曆事件"""
    if request.method == 'OPTIONS':
        return '', 204
    
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
        'notifyEnabled': bool(row[4]),
        'notifyTime': row[5].isoformat() if row[5] else None
    } for row in result]
    
    refreshed_token = refresh_token(token)
    
    return jsonify({'token': refreshed_token, 'events': events})

@dashboard_bp.route('/events/create', methods=['POST', 'OPTIONS'])
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
    
    if not data.get('title') or not data.get('start'):
        return jsonify({'token': None, 'message': '標題和日期為必填欄位'}), 400
    
    # 直接使用前端傳來的時間格式
    event_date = data.get('start')
    if event_date:
        # 簡單轉換為 MySQL 格式
        event_date = event_date.replace('T', ' ').replace('Z', '').split('.')[0]
    
    notify_time = data.get('notifyTime')
    if notify_time:
        # 將 ISO 8601 格式轉換為 MySQL 日期格式
        if 'T' in notify_time:
            notify_time = notify_time.replace('T', ' ').replace('Z', '').split('.')[0]
    
    with sqldb.engine.connect() as conn:
        result = conn.execute(text('''
            INSERT INTO schedule (student_email, title, content, event_date, notify_enabled, notify_time)
            VALUES (:student_email, :title, :content, :event_date, :notify_enabled, :notify_time)
        '''), {
            'student_email': student_email,
            'title': data.get('title'),
            'content': data.get('content', ''),
            'event_date': event_date,
            'notify_enabled': data.get('notifyEnabled', False),
            'notify_time': notify_time
        })
        
        event_id = result.lastrowid
        conn.commit()
    
    # 如果啟用通知，添加到 Redis
    notify_enabled = data.get('notifyEnabled', False)
    notify_time = data.get('notifyTime')
    if notify_enabled and notify_time:
        add_notification_to_redis(student_email, event_id, data.get('title'), data.get('content', ''), data.get('start'), notify_time)
    
    refreshed_token = refresh_token(token)
    return jsonify({'token': refreshed_token, 'id': event_id})




@dashboard_bp.route('/events/update', methods=['POST', 'OPTIONS'])
def update_calendar_event():
    """更新行事曆事件"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供認證 token'}), 401
    
    token = auth_header.split(" ")[1]
    student_email = get_user_info(token, 'email')
    data = request.get_json()
    event_id = data.get('event_id')
    
    if not event_id:
        return jsonify({'token': None, 'message': '缺少事件ID'}), 400
    
    if not data.get('title') or not data.get('start'):
        return jsonify({'token': None, 'message': '標題和日期為必填欄位'}), 400
    
    # 直接使用前端傳來的時間格式
    event_date = data.get('start')
    if event_date:
        # 簡單轉換為 MySQL 格式
        event_date = event_date.replace('T', ' ').replace('Z', '').split('.')[0]
        # 如果只有日期，補上時間
        if len(event_date) == 10:
            event_date = event_date + ' 00:00:00'
    
    notify_time = data.get('notifyTime')
    if notify_time:
        # 將 ISO 8601 格式轉換為 MySQL 日期格式
        if 'T' in notify_time:
            notify_time = notify_time.replace('T', ' ').replace('Z', '').split('.')[0]
    
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
            'event_date': event_date,
            'notify_enabled': data.get('notifyEnabled', False),
            'notify_time': notify_time,
            'event_id': event_id,
            'student_email': student_email
        })
        
        if result.rowcount == 0:
            return jsonify({'token': None, 'message': '事件不存在或無權限修改'}), 404
        
        conn.commit()
    
    # 更新 Redis 通知佇列
    notify_enabled = data.get('notifyEnabled', False)
    notify_time = data.get('notifyTime')
    if notify_enabled and notify_time:
        add_notification_to_redis(student_email, event_id, data.get('title'), data.get('content', ''), data.get('start'), notify_time)
    
    refreshed_token = refresh_token(token)
    return jsonify({'token': refreshed_token, 'message': '事件更新成功'})

@dashboard_bp.route('/events/delete', methods=['POST', 'OPTIONS'])
def delete_calendar_event():
    """刪除行事曆事件"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供認證 token'}), 401
    
    token = auth_header.split(" ")[1]
    student_email = get_user_info(token, 'email')
    data = request.get_json()
    event_id = data.get('event_id')
    
    if not event_id:
        return jsonify({'token': None, 'message': '缺少事件ID'}), 400
    
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
    
    refreshed_token = refresh_token(token)
    return jsonify({'token': refreshed_token, 'message': '事件刪除成功'})



def add_notification_to_redis(student_email: str, event_id: int, title: str, content: str, event_date: str, notify_time: str):
    """將通知加入 Redis 列表"""
    from datetime import datetime
    # 直接使用前端傳來的時間格式，確保只取到分鐘
    notify_datetime = datetime.fromisoformat(notify_time.replace('Z', ''))
    notify_time_str = notify_datetime.strftime('%Y-%m-%d %H:%M')
    
    notification_data = {
        'student_email': student_email,
        'event_id': event_id,
        'title': title,
        'content': content,
        'event_date': event_date,
        'notify_time': notify_time_str
    }
    
    # 使用 Redis List 儲存通知
    redis_client.lpush('event_notification', json.dumps(notification_data))


def remove_notification_from_redis(event_id: int):
    """從 Redis 列表移除通知"""
    # 獲取所有通知
    notifications = redis_client.lrange('event_notification', 0, -1)
    for notification in notifications:
        try:
            data = json.loads(notification)
            if data.get('event_id') == event_id:
                # 移除這個通知
                redis_client.lrem('event_notification', 1, notification)
                print(f"已從 Redis List 移除事件 {event_id} 的通知")
                break
        except json.JSONDecodeError:
            continue

# 移除自動初始化，改為在應用程式啟動時初始化



