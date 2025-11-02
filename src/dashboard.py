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

@dashboard_bp.route('/get-user-info', methods=['POST', 'OPTIONS'])
def get_user_info_api():
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'message': '未提供token'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'message': 'Token無效或已過期'}), 401
        
        # 從 MongoDB 獲取用戶資料
        user = mongo.db.user.find_one({"email": user_email})
        if not user:
            return jsonify({'message': '找不到用戶資料'}), 404
        
        # 返回用戶資料
        user_data = {
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'birthday': user.get('birthday', ''),
            'school': user.get('school', ''),
            'lineId': user.get('lineId', ''),
            'avatar': user.get('avatar', ''),
            'learningGoals': user.get('learningGoals', [])
        }
        
        refreshed_token = refresh_token(token)
        return jsonify({
            'token': refreshed_token, 
            'user': user_data
        }), 200
        
    except Exception as e:
        print(f"獲取用戶資料錯誤: {e}")
        return jsonify({'message': '伺服器錯誤'}), 500

@dashboard_bp.route('/update-user-info', methods=['POST', 'OPTIONS'])
def update_user_info():
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'message': '未提供token'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'message': 'Token無效或已過期'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'message': '未提供資料'}), 400
        
       
        update_data = {}
        allowed_fields = ['name', 'birthday', 'school', 'lineId', 'avatar', 'learningGoals']
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            return jsonify({'message': '沒有可更新的資料'}), 400
        
        
        result = mongo.db.user.update_one(
            {"email": user_email},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'message': '找不到用戶資料'}), 404
        
        refreshed_token = refresh_token(token)
        return jsonify({
            'token': refreshed_token,
            'message': '用戶資料更新成功'
        }), 200
        
    except Exception as e:
        print(f"更新用戶資料錯誤: {e}")
        return jsonify({'message': '伺服器錯誤'}), 500




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



def setup_event_notification(student_email: str, event_id: int, title: str, content: str, event_date: str, user_id: str = None):
    """設置事件通知到 Redis"""
    from datetime import datetime, timedelta

    event_datetime = datetime.fromisoformat(event_date.replace('Z', ''))

    # 設置通知時間為事件時間前5分鐘
    notify_datetime =event_datetime
    notify_time_str = notify_datetime.strftime('%Y-%m-%d %H:%M')
    
    notification_data = {
        'student_email': student_email,
        'user_id': user_id,  # LINE 用戶 ID
        'event_id': event_id,
        'title': title,
        'content': content,
        'event_date': event_date,
        'notify_time': notify_time_str
    }
    
    # 使用 Redis List 儲存通知
    redis_client.lpush('event_notification', json.dumps(notification_data))

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
                break
        except json.JSONDecodeError:
            continue

# 移除自動初始化，改為在應用程式啟動時初始化

# ==================== LINE Bot 專用函數 ====================

def get_goals_for_linebot(line_id: str) -> str:
    """LINE Bot 專用的目標查看函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "❌ 請先綁定您的帳號才能使用目標設定功能！"
        
        user_name = user.get('name', '同學')
        learning_goals = user.get('learningGoals', [])
        
        if learning_goals:
            goals_text = f"🎯 您的學習目標 - {user_name}\n\n"
            for i, goal in enumerate(learning_goals, 1):
                goals_text += f"{i}. {goal}\n"
            
            goals_text += f"\n總共 {len(learning_goals)}/10 個目標\n"
            goals_text += "\n💡 使用「新增目標:目標內容」來新增目標\n"
            goals_text += "使用「刪除目標:編號」來刪除目標"
            
            return goals_text
        else:
            return f"""🎯 您的學習目標 - {user_name}

📋 您目前還沒有設定學習目標

💡 建議目標範例：
• 每日答題數：10-20 題
• 每週學習天數：5-7 天
• 目標掌握度：70% 以上
• 重點領域：根據弱項設定

📱 使用「新增目標:目標內容」來設定您的第一個學習目標！"""
        
    except Exception as e:
        print(f"❌ LINE Bot 查看目標失敗: {e}")
        return "❌ 查看目標功能暫時無法使用，請稍後再試。"

def add_goal_for_linebot(line_id: str, goal: str) -> str:
    """LINE Bot 專用的新增目標函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "❌ 請先綁定您的帳號才能使用目標設定功能！"
        
        user_name = user.get('name', '同學')
        learning_goals = user.get('learningGoals', [])
        
        # 檢查目標數量限制
        if len(learning_goals) >= 10:
            return "❌ 最多只能設定 10 個學習目標！\n請先刪除一些目標再新增。"
        
        # 檢查目標是否已存在
        if goal in learning_goals:
            return f"❌ 目標「{goal}」已經存在了！"
        
        # 新增目標
        learning_goals.append(goal)
        
        # 更新到資料庫
        mongo.db.user.update_one(
            {"lineId": line_id},
            {"$set": {"learningGoals": learning_goals}}
        )
        
        return f"✅ 成功新增學習目標！\n\n目標: {goal}\n目前共有 {len(learning_goals)}/10 個目標\n\n使用「查看目標」來查看所有目標"
        
    except Exception as e:
        print(f"❌ LINE Bot 新增目標失敗: {e}")
        return "❌ 新增目標失敗，請稍後再試。"

def delete_goal_for_linebot(line_id: str, goal_index: int) -> str:
    """LINE Bot 專用的刪除目標函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "❌ 請先綁定您的帳號才能使用目標設定功能！"
        
        user_name = user.get('name', '同學')
        learning_goals = user.get('learningGoals', [])
        
        # 檢查索引是否有效
        if not learning_goals:
            return "❌ 您目前沒有任何學習目標！"
        
        # 將索引轉換為 0-based（用戶輸入的是 1-based）
        actual_index = goal_index - 1
        
        if actual_index < 0 or actual_index >= len(learning_goals):
            return f"❌ 目標編號無效！請輸入 1 到 {len(learning_goals)} 之間的數字。\n\n使用「查看目標」來查看所有目標的編號"
        
        # 刪除目標
        deleted_goal = learning_goals.pop(actual_index)
        
        # 更新到資料庫
        mongo.db.user.update_one(
            {"lineId": line_id},
            {"$set": {"learningGoals": learning_goals}}
        )
        
        remaining_count = len(learning_goals)
        result_text = f"✅ 成功刪除學習目標！\n\n已刪除: {deleted_goal}\n目前共有 {remaining_count}/10 個目標"
        
        if remaining_count > 0:
            result_text += "\n\n使用「查看目標」來查看所有目標"
        
        return result_text
        
    except Exception as e:
        print(f"❌ LINE Bot 刪除目標失敗: {e}")
        return "❌ 刪除目標失敗，請稍後再試。"

@dashboard_bp.route('/dashboard-stats', methods=['POST', 'OPTIONS'])
@cross_origin()
def get_dashboard_stats():
    """獲取 dashboard 快速統計數據"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': '未提供認證 token'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        user_email = get_user_info(token, 'email')
        
        # 統計資料變數
        stats = {
            'today_quizzes': 0,
            'week_study_time': 0,
            'reviews_needed': 0,
            'avg_score': 0
        }
        
        with sqldb.engine.connect() as conn:
            # 今日測驗次數
            today_result = conn.execute(text("""
                SELECT COUNT(*) FROM quiz_history 
                WHERE user_email = :user_email 
                AND DATE(created_at) = CURDATE()
            """), {'user_email': user_email})
            stats['today_quizzes'] = today_result.fetchone()[0]
            
            # 本週學習時間（小時）
            week_result = conn.execute(text("""
                SELECT SUM(total_time_taken) / 3600 as hours
                FROM quiz_history 
                WHERE user_email = :user_email 
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """), {'user_email': user_email})
            hours = week_result.fetchone()[0]
            stats['week_study_time'] = round(hours if hours else 0, 1)
            
            # 待複習題數（從錯題統計）
            reviews_result = conn.execute(text("""
                SELECT COUNT(DISTINCT question_id) 
                FROM error_questions 
                WHERE user_email = :user_email
                AND is_reviewed = 0
            """), {'user_email': user_email})
            stats['reviews_needed'] = reviews_result.fetchone()[0]
            
            # 最近平均得分
            recent_score_result = conn.execute(text("""
                SELECT AVG(average_score) 
                FROM quiz_history 
                WHERE user_email = :user_email 
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """), {'user_email': user_email})
            avg_score = recent_score_result.fetchone()[0]
            stats['avg_score'] = round(avg_score if avg_score else 0, 1)
        
        refreshed_token = refresh_token(token)
        return jsonify({'token': refreshed_token, 'stats': stats})
    
    except Exception as e:
        print(f"❌ 獲取 dashboard 統計失敗: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/recent-activities', methods=['POST', 'OPTIONS'])
@cross_origin()
def get_recent_activities():
    """獲取最近活動列表"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': '未提供認證 token'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        user_email = get_user_info(token, 'email')
        
        activities = []
        
        with sqldb.engine.connect() as conn:
            # 獲取最近的測驗記錄（最多 5 筆）
            quiz_result = conn.execute(text("""
                SELECT id, quiz_template_id, quiz_type, average_score, 
                       total_questions, correct_count, created_at
                FROM quiz_history 
                WHERE user_email = :user_email 
                ORDER BY created_at DESC 
                LIMIT 5
            """), {'user_email': user_email})
            
            for row in quiz_result:
                activities.append({
                    'type': 'quiz',
                    'id': row[0],
                    'title': row[2] or '測驗',
                    'quiz_id': row[1],
                    'score': round(row[3], 1),
                    'total': row[4],
                    'correct': row[5],
                    'date': row[6].isoformat() if row[6] else None
                })
            
            # 獲取最近的錯題記錄（最多 3 筆）
            error_result = conn.execute(text("""
                SELECT question_id, concept_name, created_at
                FROM error_questions 
                WHERE user_email = :user_email 
                AND is_reviewed = 0
                ORDER BY created_at DESC 
                LIMIT 3
            """), {'user_email': user_email})
            
            for row in error_result:
                activities.append({
                    'type': 'error',
                    'id': row[0],
                    'title': '錯題提醒',
                    'concept': row[1],
                    'date': row[2].isoformat() if row[2] else None
                })
            
            # 依日期排序（最新的在前）
            activities.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        refreshed_token = refresh_token(token)
        return jsonify({'token': refreshed_token, 'activities': activities[:8]})
    
    except Exception as e:
        print(f"❌ 獲取最近活動失敗: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/daily-checkin', methods=['POST', 'OPTIONS'])
@cross_origin()
def daily_checkin():
    """每日簽到功能"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': '未提供認證 token'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        user_email = get_user_info(token, 'email')
        user_name = get_user_info(token, 'name')
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 使用 Redis 檢查今日是否已簽到
        checkin_key = f'checkin:{user_email}:{today}'
        already_checked = redis_client.exists(checkin_key)
        
        if already_checked:
            # 已簽到，返回簽到信息
            checkin_data = redis_client.get(checkin_key)
            checkin_info = json.loads(checkin_data) if checkin_data else {}
            
            refreshed_token = refresh_token(token)
            return jsonify({
                'token': refreshed_token,
                'already_checked': True,
                'checkin_time': checkin_info.get('checkin_time'),
                'message': '今日已簽到'
            })
        
        # 執行簽到
        checkin_time = datetime.now().isoformat()
        
        # 1. 保存到 Redis
        redis_client.setex(checkin_key, 86400, json.dumps({
            'user_email': user_email,
            'user_name': user_name,
            'checkin_time': checkin_time,
            'date': today
        }))
        
        # 2. 更新 MongoDB user 簽到記錄
        # 獲取或創建用戶的簽到統計
        user = mongo.db.user.find_one({'email': user_email})
        
        if user:
            last_checkin_date = user.get('last_checkin_date', '')
            checkin_streak = user.get('checkin_streak', 0)
            
            # 計算連續簽到天數
            if last_checkin_date == today:
                # 今天已經簽到過了（理論上不會發生，因為 Redis 已檢查）
                new_streak = checkin_streak
            else:
                # 檢查是否連續簽到
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                if last_checkin_date == yesterday:
                    # 連續簽到
                    new_streak = checkin_streak + 1
                else:
                    # 中斷了，重新開始
                    new_streak = 1
            
            # 更新簽到統計
            mongo.db.user.update_one(
                {'email': user_email},
                {
                    '$set': {
                        'last_checkin_date': today,
                        'checkin_streak': new_streak,
                        'total_checkin_days': user.get('total_checkin_days', 0) + 1
                    }
                }
            )
        else:
            # 新用戶，創建簽到記錄
            new_streak = 1
            mongo.db.user.update_one(
                {'email': user_email},
                {
                    '$set': {
                        'last_checkin_date': today,
                        'checkin_streak': new_streak,
                        'total_checkin_days': 1
                    }
                },
                upsert=True
            )
        
        refreshed_token = refresh_token(token)
        return jsonify({
            'token': refreshed_token,
            'already_checked': False,
            'checkin_time': checkin_time,
            'checkin_streak': new_streak,
            'message': '簽到成功'
        })
    
    except Exception as e:
        print(f"❌ 簽到失敗: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/checkin-status', methods=['POST', 'OPTIONS'])
@cross_origin()
def get_checkin_status():
    """獲取簽到狀態"""
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': '未提供認證 token'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        user_email = get_user_info(token, 'email')
        
        today = datetime.now().strftime('%Y-%m-%d')
        checkin_key = f'checkin:{user_email}:{today}'
        
        # 檢查今日簽到狀態
        checked_today = redis_client.exists(checkin_key)
        
        # 從 MongoDB 獲取簽到統計
        user = mongo.db.user.find_one({'email': user_email})
        
        if user:
            checkin_streak = user.get('checkin_streak', 0)
            total_checkin_days = user.get('total_checkin_days', 0)
            last_checkin_date = user.get('last_checkin_date', '')
        else:
            checkin_streak = 0
            total_checkin_days = 0
            last_checkin_date = ''
        
        refreshed_token = refresh_token(token)
        return jsonify({
            'token': refreshed_token,
            'checked_today': bool(checked_today),
            'checkin_streak': checkin_streak,
            'total_checkin_days': total_checkin_days,
            'last_checkin_date': last_checkin_date
        })
    
    except Exception as e:
        print(f"❌ 獲取簽到狀態失敗: {e}")
        return jsonify({'error': str(e)}), 500


def get_calendar_for_linebot(line_id: str) -> str:
    """LINE Bot 專用的行事曆查看函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "請先綁定您的帳號才能使用行事曆功能！"
        
        user_email = user.get('email')
        user_name = user.get('name', '同學')
        
        # 獲取行事曆數據
        with sqldb.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, title, content, event_date, notify_enabled 
                FROM schedule 
                WHERE student_email = :email 
                ORDER BY event_date ASC 
                LIMIT 10
            """), {"email": user_email})
            
            events = []
            for row in result:
                events.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'event_date': row[3],
                    'notify_enabled': row[4]
                })
        
        if events:
            calendar_text = f"您的行事曆事件 - {user_name}\n\n"
            for i, event in enumerate(events, 1):
                title = event.get('title', '無標題')
                event_date = event.get('event_date', '')
                content = event.get('content', '')
                event_id = event.get('id')
                
                # 格式化日期
                try:
                    if event_date:
                        from datetime import datetime
                        date_obj = datetime.fromisoformat(str(event_date).replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%m/%d %H:%M')
                    else:
                        formatted_date = "未設定時間"
                except:
                    formatted_date = str(event_date)
                
                calendar_text += f"{i}. {title} (ID:{event_id})\n"
                calendar_text += f"   {formatted_date}\n"
                if content:
                    calendar_text += f"   {content[:50]}{'...' if len(content) > 50 else ''}\n"
                calendar_text += "\n"
            
            calendar_text += "使用「新增事件:標題|內容|日期時間」來新增事件\n"
            calendar_text += "使用「修改事件:ID|標題|內容|日期時間」來修改事件\n"
            calendar_text += "使用「刪除事件:ID」來刪除事件"
        else:
            calendar_text = f"您的行事曆目前沒有事件 - {user_name}\n\n使用「新增事件:標題|內容|日期時間」來新增您的第一個學習計畫！"
        
        return calendar_text
        
    except Exception as e:
        print(f"❌ LINE Bot 行事曆失敗: {e}")
        return "行事曆功能暫時無法使用，請稍後再試。"

def add_calendar_event_for_linebot(line_id: str, title: str, content: str, event_date: str) -> str:
    """LINE Bot 專用的新增行事曆事件函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "請先綁定您的帳號才能使用行事曆功能！"
        
        user_email = user.get('email')
        user_name = user.get('name', '同學')
        
        # 格式化日期時間
        try:
            from datetime import datetime
            # 支援多種日期格式
            if 'T' in event_date:
                # ISO 格式: 2024-01-01T10:00
                event_datetime = datetime.fromisoformat(event_date.replace('Z', ''))
            elif ' ' in event_date:
                # 簡單格式: 2024-01-01 10:00
                event_datetime = datetime.strptime(event_date, '%Y-%m-%d %H:%M')
            else:
                # 只有日期: 2024-01-01
                event_datetime = datetime.strptime(event_date, '%Y-%m-%d')
            
            formatted_date = event_datetime.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            return f"日期格式錯誤: {event_date}\n請使用格式: 2024-01-01 10:00 或 2024-01-01T10:00"
        
        # 新增事件到資料庫
        with sqldb.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO schedule (student_email, title, content, event_date, notify_enabled)
                VALUES (:student_email, :title, :content, :event_date, :notify_enabled)
            """), {
                'student_email': user_email,
                'title': title,
                'content': content or '',
                'event_date': formatted_date,
                'notify_enabled': True  # 啟用通知
            })
            
            event_id = result.lastrowid
            conn.commit()
        
        # 設置通知到 Redis
        try:
            setup_event_notification(
                student_email=user_email,
                event_id=event_id,
                title=title,
                content=content or '',
                event_date=formatted_date,
                user_id=line_id  # 添加 LINE 用戶 ID
            )
        except Exception as e:
            print(f"設置通知失敗: {e}")
        
        return f"成功新增行事曆事件！\n\n標題: {title}\n內容: {content or '無'}\n時間: {event_datetime.strftime('%Y年%m月%d日 %H:%M')}\n事件ID: {event_id}\n\n使用「查看行事曆」來查看所有事件"
        
    except Exception as e:
        print(f"❌ LINE Bot 新增行事曆事件失敗: {e}")
        return "新增行事曆事件失敗，請稍後再試。"

def update_calendar_event_for_linebot(line_id: str, event_id: int, title: str, content: str, event_date: str) -> str:
    """LINE Bot 專用的修改行事曆事件函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "請先綁定您的帳號才能使用行事曆功能！"
        
        user_email = user.get('email')
        user_name = user.get('name', '同學')
        
        # 如果標題或內容為空，先查詢原始事件
        original_title = title
        original_content = content
        if not title or title.strip() == '' or title.strip().lower() in ['一樣', '一樣的', 'same', '不變', '不改']:
            with sqldb.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT title, content FROM schedule 
                    WHERE id = :event_id AND student_email = :student_email
                """), {
                    'event_id': event_id,
                    'student_email': user_email
                })
                row = result.fetchone()
                if row:
                    original_title = row[0] or title
                    if not content or content.strip() == '':
                        original_content = row[1] or ''
        else:
            # 如果標題有值但內容為空，查詢原始內容
            if not content or content.strip() == '':
                with sqldb.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT content FROM schedule 
                        WHERE id = :event_id AND student_email = :student_email
                    """), {
                        'event_id': event_id,
                        'student_email': user_email
                    })
                    row = result.fetchone()
                    if row:
                        original_content = row[0] or ''
        
        # 使用原始值
        final_title = original_title if original_title else title
        final_content = original_content if original_content else content
        
        if not final_title or final_title.strip() == '':
            return "標題為必填欄位！"
        
        # 格式化日期時間
        try:
            from datetime import datetime
            # 支援多種日期格式
            if 'T' in event_date:
                # ISO 格式: 2024-01-01T10:00
                event_datetime = datetime.fromisoformat(event_date.replace('Z', ''))
            elif ' ' in event_date:
                # 簡單格式: 2024-01-01 10:00
                event_datetime = datetime.strptime(event_date, '%Y-%m-%d %H:%M')
            else:
                # 只有日期: 2024-01-01
                event_datetime = datetime.strptime(event_date, '%Y-%m-%d')
            
            formatted_date = event_datetime.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            return f"日期格式錯誤: {event_date}\n請使用格式: 2024-01-01 10:00 或 2024-01-01T10:00"
        
        # 更新事件
        with sqldb.engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE schedule 
                SET title = :title, content = :content, event_date = :event_date, 
                    updated_at = CURRENT_TIMESTAMP, notify_enabled = :notify_enabled
                WHERE id = :event_id AND student_email = :student_email
            """), {
                'title': final_title,
                'content': final_content or '',
                'event_date': formatted_date,
                'event_id': event_id,
                'student_email': user_email,
                'notify_enabled': True  # 啟用通知
            })
            
            if result.rowcount == 0:
                return f"找不到事件ID {event_id} 或您沒有權限修改此事件"
            
            conn.commit()
        
        # 先移除舊通知，再設置新通知
        try:
            remove_notification_from_redis(event_id)
            setup_event_notification(
                student_email=user_email,
                event_id=event_id,
                title=final_title,
                content=final_content or '',
                event_date=formatted_date,
                user_id=line_id  # 添加 LINE 用戶 ID
            )
        except Exception as e:
            print(f"更新通知失敗: {e}")
        
        return f"成功修改行事曆事件！\n\n標題: {final_title}\n內容: {final_content or '無'}\n時間: {event_datetime.strftime('%Y年%m月%d日 %H:%M')}\n事件ID: {event_id}\n\n使用「查看行事曆」來查看所有事件"
        
    except Exception as e:
        print(f"❌ LINE Bot 修改行事曆事件失敗: {e}")
        return "修改行事曆事件失敗，請稍後再試。"

def delete_calendar_event_for_linebot(line_id: str, event_id: int) -> str:
    """LINE Bot 專用的刪除行事曆事件函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "請先綁定您的帳號才能使用行事曆功能！"
        
        user_email = user.get('email')
        user_name = user.get('name', '同學')
        
        # 先獲取事件資訊
        with sqldb.engine.connect() as conn:
            # 先查詢事件是否存在
            check_result = conn.execute(text("""
                SELECT title, event_date FROM schedule 
                WHERE id = :event_id AND student_email = :student_email
            """), {'event_id': event_id, 'student_email': user_email})
            
            event_info = check_result.fetchone()
            if not event_info:
                return f"❌ 找不到事件ID {event_id} 或您沒有權限刪除此事件"
            
            # 刪除事件
            result = conn.execute(text("""
                DELETE FROM schedule 
                WHERE id = :event_id AND student_email = :student_email
            """), {'event_id': event_id, 'student_email': user_email})
            
            conn.commit()
        
        # 從 Redis 移除通知
        remove_notification_from_redis(event_id)
        
        return f"成功刪除行事曆事件！\n\n已刪除: {event_info[0]}\n事件ID: {event_id}\n\n使用「查看行事曆」來查看剩餘事件"
        
    except Exception as e:
        print(f"❌ LINE Bot 刪除行事曆事件失敗: {e}")
        return "刪除行事曆事件失敗，請稍後再試。"

