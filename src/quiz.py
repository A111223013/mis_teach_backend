from flask import jsonify, request, Blueprint, current_app, Response
import uuid
from accessories import mongo, sqldb, refresh_token
from src.api import get_user_info, verify_token
import jwt
from datetime import datetime
import random
import base64
import os
import json
from sqlalchemy import text
from bson import ObjectId
from src.grade_answer import batch_grade_ai_questions
import time
import hashlib
import logging
from typing import List

quiz_bp = Blueprint('quiz', __name__)

# 設置日誌
logger = logging.getLogger(__name__)

# ==================== 工具函數 ====================

def get_quiz_from_database(quiz_ids: List[str]) -> dict:
    """從資料庫獲取考卷數據"""
    try:
        # quiz_ids 現在是 template_id 列表，取第一個作為 template_id
        template_id = quiz_ids[0] if quiz_ids else None
        if not template_id:
            return {
                'success': False,
                'message': '沒有提供有效的template_id'
            }
        
        # 先查詢SQL template獲取所有題目ID
        try:
            from accessories import sqldb
            from sqlalchemy import text
            import json
            
            # 查詢SQL template獲取question_ids
            template_query = text("""
                SELECT question_ids FROM quiz_templates 
                WHERE id = :template_id
            """)
            
            with sqldb.engine.connect() as conn:
                result = conn.execute(template_query, {'template_id': template_id})
                template_row = result.fetchone()
                
                if not template_row:
                    return {
                        'success': False,
                        'message': '找不到測驗模板'
                    }
                
                question_ids_json = template_row[0]
                question_ids = json.loads(question_ids_json)
                
                # 查詢所有題目
                questions = []
                for q_id in question_ids:
                    try:
                        object_id = ObjectId(q_id)
                        question_doc = mongo.db.exam.find_one({"_id": object_id})
                        if question_doc:
                            questions.append(question_doc)
                    except Exception as e:
                        continue
                
                if not questions:
                    return {
                        'success': False,
                        'message': '沒有找到任何題目數據'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'message': f'查詢題目時發生錯誤: {str(e)}'
            }
        
        # 轉換題目格式為前端需要的格式
        formatted_questions = []
        for i, question in enumerate(questions):
            # 處理題目類型映射
            question_type = question.get('type', 'single')
            answer_type = question.get('answer_type', 'single-choice')
            
            # 根據題目類型設置正確的type字段
            if question_type == 'group':
                formatted_type = 'group'
            else:
                # 單題：使用answer_type作為type
                formatted_type = answer_type
            
            # 處理選項格式
            options = question.get('options', [])
            if isinstance(options, str):
                options = [opt.strip() for opt in options.split(',') if opt.strip()]
            elif not isinstance(options, list):
                options = []
            
            formatted_question = {
                'id': i + 1,  # 使用數字ID，從1開始
                'question_text': question.get('question_text', ''),
                'type': formatted_type,
                'options': options,
                'correct_answer': question.get('answer', question.get('correct_answer', '')),
                'original_exam_id': str(question.get('_id', question.get('id', ''))),
                'image_file': question.get('image_file', ''),
                'key_points': question.get('key-points', question.get('key_points', '')),
                'explanation': question.get('detail-answer', question.get('explanation', '')),
                'topic': question.get('topic', ''),
                'difficulty': question.get('difficulty_level', question.get('difficulty', 'medium')),
                'micro_concepts': question.get('micro_concepts', []),
                'difficulty_level': question.get('difficulty_level', '中等'),
                'error_reason': question.get('error_reason', ''),
                'created_at': str(question.get('created_at', '')) if question.get('created_at') else ''
            }
            formatted_questions.append(formatted_question)
        
        # 從SQL模板獲取測驗信息
        template_info = {}
        try:
            with sqldb.engine.connect() as conn:
                template_query = text("""
                    SELECT template_type, school, department, year, created_at
                    FROM quiz_templates 
                    WHERE id = :template_id
                """)
                
                result = conn.execute(template_query, {'template_id': template_id})
                template_row = result.fetchone()
                
                if template_row:
                    template_type = template_row[0]
                    school = template_row[1] or ''
                    department = template_row[2] or ''
                    year = template_row[3] or ''
                    created_at = template_row[4]
                    
                    # 根據測驗類型生成標題
                    if template_type == 'pastexam':
                        quiz_title = f"{school} - {year}年 - {department}"
                    else:  # knowledge
                        topic = questions[0].get('key-points', '計算機概論') if questions else '計算機概論'
                        quiz_title = f"{topic} - 知識測驗"
                    
                    template_info = {
                        'title': quiz_title,
                        'exam_type': template_type,
                        'school': school,
                        'department': department,
                        'year': year,
                        'topic': questions[0].get('key-points', '計算機概論') if questions else '計算機概論',
                        'difficulty': questions[0].get('difficulty_level', 'medium') if questions else 'medium',
                        'question_count': len(formatted_questions),
                        'time_limit': 60,
                        'total_score': len(formatted_questions) * 5,
                        'created_at': created_at.isoformat() if created_at else datetime.now().isoformat()
                    }
        except Exception as e:
            print(f"⚠️ 獲取模板信息失敗: {e}")
            # 使用默認信息
            template_info = {
                'title': f"測驗 ({template_id})",
                'exam_type': 'knowledge',
                'topic': questions[0].get('key-points', '計算機概論') if questions else '計算機概論',
                'difficulty': questions[0].get('difficulty_level', 'medium') if questions else 'medium',
                'question_count': len(formatted_questions),
                'time_limit': 60,
                'total_score': len(formatted_questions) * 5,
                'created_at': datetime.now().isoformat()
            }
        
        # 構建考卷數據 (從單個題目中提取信息)
        quiz_data = {
            'quiz_id': str(template_id), # 使用template_id作為quiz_id
            'template_id': str(template_id),
            'title': template_info.get('title', f"測驗 ({template_id})"),
            'questions': formatted_questions,
            'time_limit': 60, # Default time limit for single question
            'quiz_info': template_info,
            'database_ids': [str(q_id) for q_id in question_ids] # 儲存所有題目ID，確保是字串
        }
        
        return {
            'success': True,
            'data': quiz_data
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'獲取考卷數據失敗: {str(e)}'
        }


def init_quiz_tables():
    """初始化測驗相關的SQL表格 - 最終優化版本"""
    try:
        with current_app.app_context():
            # 創建quiz_templates表 - 存儲考卷模板
            with sqldb.engine.connect() as conn:
                conn.execute(sqldb.text("""
                    CREATE TABLE IF NOT EXISTS quiz_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_email VARCHAR(255) NOT NULL,
                        template_type ENUM('knowledge', 'pastexam') NOT NULL,
                        question_ids JSON NOT NULL,
                        school VARCHAR(100) DEFAULT '',
                        department VARCHAR(100) DEFAULT '',
                        year VARCHAR(20) DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_email (user_email),
                        INDEX idx_template_type (template_type),
                        INDEX idx_school (school),
                        INDEX idx_department (department),
                        INDEX idx_year (year),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                
                conn.commit()
            
            # 創建quiz_history表 - 存儲測驗歷史記錄（最終簡化版）
            with sqldb.engine.connect() as conn:
                conn.execute(sqldb.text("""
                    CREATE TABLE IF NOT EXISTS quiz_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        quiz_template_id INT NULL,
                        user_email VARCHAR(255) NOT NULL,
                        quiz_type ENUM('knowledge', 'pastexam') NOT NULL,
                        total_questions INT DEFAULT 0,
                        answered_questions INT DEFAULT 0,
                        correct_count INT DEFAULT 0,
                        wrong_count INT DEFAULT 0,
                        accuracy_rate DECIMAL(5,2) DEFAULT 0,
                        average_score DECIMAL(5,2) DEFAULT 0,
                        total_time_taken INT DEFAULT 0,
                        submit_time DATETIME NOT NULL,
                        status ENUM('incomplete', 'completed', 'abandoned') DEFAULT 'incomplete',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (quiz_template_id) REFERENCES quiz_templates(id) ON DELETE SET NULL,
                        INDEX idx_user_email (user_email),
                        INDEX idx_quiz_template_id (quiz_template_id),
                        INDEX idx_submit_time (submit_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            
            # 創建quiz_errors表 - 存儲考生錯題（最終簡化版）
            with sqldb.engine.connect() as conn:
                conn.execute(sqldb.text("""
                    CREATE TABLE IF NOT EXISTS quiz_errors (
                        error_id INT AUTO_INCREMENT PRIMARY KEY,
                        quiz_history_id INT NOT NULL,
                        user_email VARCHAR(255) NOT NULL,
                        mongodb_question_id VARCHAR(50) NOT NULL,
                        user_answer TEXT,
                        score DECIMAL(5,2) DEFAULT 0,
                        time_taken INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (quiz_history_id) REFERENCES quiz_history(id) ON DELETE CASCADE,
                        INDEX idx_user_email (user_email),
                        INDEX idx_mongodb_question_id (mongodb_question_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            
            # 創建quiz_answers表 - 存儲所有題目的用戶答案
            with sqldb.engine.connect() as conn:
                conn.execute(sqldb.text("""
                    CREATE TABLE IF NOT EXISTS quiz_answers (
                        answer_id INT AUTO_INCREMENT PRIMARY KEY,
                        quiz_history_id INT NOT NULL,
                        user_email VARCHAR(255) NOT NULL,
                        mongodb_question_id VARCHAR(50) NOT NULL,
                        user_answer TEXT NOT NULL,
                        is_correct BOOLEAN NOT NULL DEFAULT FALSE,
                        score DECIMAL(5,2) DEFAULT 0,
                        feedback JSON,
                        answer_time_seconds INT DEFAULT 0,  -- 新增：每題作答時間（秒）
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (quiz_history_id) REFERENCES quiz_history(id) ON DELETE CASCADE,
                        INDEX idx_quiz_history_id (quiz_history_id),
                        INDEX idx_user_email (user_email),
                        INDEX idx_mongodb_question_id (mongodb_question_id),
                        INDEX idx_is_correct (is_correct),
                        INDEX idx_created_at (created_at),
                        INDEX idx_answer_time (answer_time_seconds)  -- 新增：作答時間索引
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            
            # 創建長答案存儲表
            with sqldb.engine.connect() as conn:
                conn.execute(sqldb.text("""
                    CREATE TABLE IF NOT EXISTS long_answers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        quiz_history_id INT NOT NULL,
                        question_id VARCHAR(255) NOT NULL,
                        user_email VARCHAR(255) NOT NULL,
                        question_type VARCHAR(50) NOT NULL,
                        full_answer LONGTEXT NOT NULL,
                        answer_hash VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_quiz_question (quiz_history_id, question_id),
                        INDEX idx_user (user_email)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            

            return True
    except Exception as e:
        print(f"❌ Failed to initialize quiz tables: {e}")
        return False



@quiz_bp.route('/submit-quiz', methods=['POST', 'OPTIONS'])
def submit_quiz():
    """提交測驗 API - 全AI評分版本"""
    if request.method == 'OPTIONS':
        return jsonify({'token': None, 'message': 'CORS preflight'}), 200
    
    # 驗證用戶身份
    token = request.headers.get('Authorization').split(" ")[1]
    user_email = verify_token(token)
    if not user_email:
        return jsonify({'token': None, 'message': '無效的token'}), 401
    
    # 獲取請求數據
    data = request.get_json()
    template_id = data.get('template_id')
    answers = data.get('answers', {})
    time_taken = data.get('time_taken', 0)
    question_answer_times = data.get('question_answer_times', {})  # 新增：提取每題作答時間
    frontend_questions = data.get('questions', [])  # 新增：提取前端發送的題目數據
    
    # 調試日誌
    
    if not template_id:
        return jsonify({
            'token': None,
            'message': '缺少考卷模板ID'
        }), 400
    

    
    # 生成唯一的進度追蹤ID
    progress_id = f"progress_{user_email}_{int(time.time())}"
    
    # 階段1: 試卷批改 - 獲取題目數據

    
    # 更新進度狀態為第1階段
    update_progress_status(progress_id, False, 1, "正在獲取題目數據...")
    
    # 這裡可以發送進度更新到前端（如果使用WebSocket或Server-Sent Events）
    # 目前先打印進度，後續可以實現即時通訊
    
    # 從SQL獲取模板信息
    with sqldb.engine.connect() as conn:
        template_id_int = int(template_id)
        template = conn.execute(text("""
            SELECT * FROM quiz_templates WHERE id = :template_id
        """), {'template_id': template_id_int}).fetchone()
        
        if not template:
            return jsonify({
                'token': None,
                'message': '考卷模板不存在'
            }), 404
        
        # 從模板獲取題目ID列表
        question_ids = json.loads(template.question_ids)
        total_questions = len(question_ids)
        quiz_type = template.template_type
        
        # 從模板獲取題目數量
        
        # 優先使用前端發送的題目數據，如果沒有則從MongoDB獲取
        if frontend_questions and len(frontend_questions) > 0:
            questions = frontend_questions
        else:
            # 從MongoDB exam集合獲取題目詳情
            questions = []
            for i, question_id in enumerate(question_ids):
                # 嘗試使用ObjectId查詢
                exam_question = mongo.db.exam.find_one({"_id": ObjectId(question_id)})
                if not exam_question:
                    # 如果ObjectId查詢失敗，嘗試直接查詢
                    exam_question = mongo.db.exam.find_one({"_id": question_id})
                
                if exam_question:
                    # 使用與 create-quiz 相同的題目處理邏輯
                    exam_type = exam_question.get('type', 'single')
                    if exam_type == 'group':
                        # 題組：保留群組題外層資訊，展開子題但一併回傳
                        group_question_text = exam_question.get('group_question_text') or exam_question.get('question_text', '')
                        if not group_question_text:
                            print(f"⚠️ 警告：題組 {i+1} (ID: {exam_question.get('_id')}) 的 group_question_text 和 question_text 都為空")
                            group_question_text = f"題組 {i+1} (無題目文字)"
                        
                        micro_concepts = exam_question.get('micro_concepts', [])
                        key_points = exam_question.get('key-points', '')
                        # 處理 key-points 可能是陣列或字串的情況
                        if isinstance(key_points, list):
                            key_points = ', '.join(key_points) if key_points else ''
                        parent_id = str(exam_question.get('_id', ''))

                        # 構建子題清單
                        sub_qs_raw = exam_question.get('sub_questions', []) or []
                        sub_qs = []
                        for sub in sub_qs_raw:
                            sub_options = sub.get('options', [])
                            if isinstance(sub_options, str):
                                sub_options = [opt.strip() for opt in sub_options.split(',') if opt.strip()]
                            elif not isinstance(sub_options, list):
                                sub_options = []

                            sub_image = sub.get('image_file', '')

                            sub_qs.append({
                                'question_number': sub.get('question_number', ''),
                                'question_text': sub.get('question_text', ''),
                                'options': sub_options,
                                'answer': sub.get('answer', ''),
                                'answer_type': sub.get('answer_type', 'single-choice'),
                                'image_file': sub_image,
                                'detail_answer': sub.get('detail-answer', ''),
                                'key_points': ', '.join(sub.get('key-points', [])) if isinstance(sub.get('key-points', []), list) else sub.get('key-points', ''),
                                'difficulty_level': sub.get('difficulty level', sub.get('difficulty_level', '')),
                                'original_exam_id': parent_id
                            })

                        group_question = {
                            'id': i + 1,
                            'type': 'group',
                            'group_question_text': group_question_text,
                            'micro_concepts': micro_concepts,
                            'key_points': key_points,
                            'original_exam_id': parent_id,
                            'sub_questions': sub_qs
                        }

                        # 題組外層若也有圖片，轉換為 base64
                        group_image_file = exam_question.get('image_file', '')
                        group_image_data_list = []
                        negative_values = ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']
                        if group_image_file and group_image_file not in negative_values:
                            group_image_filenames = []
                            if isinstance(group_image_file, list):
                                group_image_filenames = [img for img in group_image_file if img and img not in negative_values]
                            elif isinstance(group_image_file, str):
                                group_image_filenames = [group_image_file]
                            
                            # 將每個圖片檔案轉換為 base64
                            for group_image_filename in group_image_filenames:
                                group_image_base64 = get_image_base64(group_image_filename)
                                if group_image_base64:
                                    # 判斷圖片格式
                                    image_ext = os.path.splitext(group_image_filename)[1].lower()
                                    mime_type = 'image/jpeg'
                                    if image_ext in ['.png']:
                                        mime_type = 'image/png'
                                    elif image_ext in ['.gif']:
                                        mime_type = 'image/gif'
                                    elif image_ext in ['.webp']:
                                        mime_type = 'image/webp'
                                    
                                    group_image_data_list.append(f"data:{mime_type};base64,{group_image_base64}")
                            
                            # 如果只有一張圖片，直接返回字串；多張圖片返回陣列
                            if len(group_image_data_list) == 1:
                                group_question['image_file'] = group_image_data_list[0]
                            elif len(group_image_data_list) > 1:
                                group_question['image_file'] = group_image_data_list
                            else:
                                group_question['image_file'] = ''
                        else:
                            group_question['image_file'] = ''

                        questions.append(group_question)
                    else:
                        # 單題：保持原有行為
                        question_type = exam_question.get('answer_type', 'single-choice')
                        
                        # 調試信息：檢查題目文字
                        question_text = exam_question.get('question_text', '')
                        if not question_text:
                            print(f"⚠️ 警告：題目 {i+1} (ID: {exam_question.get('_id')}) 的 question_text 為空")
                            print(f"   學校: {exam_question.get('school')}, 科系: {exam_question.get('department')}, 年份: {exam_question.get('year')}")
                            print(f"   答案: {exam_question.get('answer', '')[:100]}...")
                            # 嘗試從其他欄位獲取題目文字
                            if exam_question.get('answer'):
                                question_text = f"題目 {i+1}: {exam_question.get('answer', '')[:200]}..."
                            else:
                                question_text = f"題目 {i+1} (無題目文字)"
                        
                        question = {
                            'id': i + 1,
                            'question_text': question_text,
                            'type': question_type,
                            'options': exam_question.get('options'),
                            'correct_answer': exam_question.get('answer', ''),
                            'original_exam_id': str(exam_question.get('_id', '')),
                            'image_file': exam_question.get('image_file'),
                            'key_points': ', '.join(exam_question.get('key-points', [])) if isinstance(exam_question.get('key-points', []), list) else exam_question.get('key-points', ''),
                            'answer_type': question_type,
                            'detail_answer': exam_question.get('detail-answer', '')
                        }
                        
                        # 處理選項格式
                        if isinstance(question['options'], str):
                            question['options'] = [opt.strip() for opt in question['options'].split(',') if opt.strip()]
                        elif not isinstance(question['options'], list):
                            question['options'] = []
                        
                        # 處理圖片檔案（單題）- 轉換為 base64
                        image_file = exam_question.get('image_file', '')
                        negative_values = ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']
                        image_data_list = []
                        if image_file and image_file not in negative_values:
                            image_filenames = []
                            if isinstance(image_file, list):
                                image_filenames = [img for img in image_file if img and img not in negative_values]
                            elif isinstance(image_file, str):
                                image_filenames = [image_file]
                            
                            # 將每個圖片檔案轉換為 base64
                            for image_filename in image_filenames:
                                image_base64 = get_image_base64(image_filename)
                                if image_base64:
                                    # 判斷圖片格式
                                    image_ext = os.path.splitext(image_filename)[1].lower()
                                    mime_type = 'image/jpeg'
                                    if image_ext in ['.png']:
                                        mime_type = 'image/png'
                                    elif image_ext in ['.gif']:
                                        mime_type = 'image/gif'
                                    elif image_ext in ['.webp']:
                                        mime_type = 'image/webp'
                                    
                                    image_data_list.append(f"data:{mime_type};base64,{image_base64}")
                            
                            # 如果只有一張圖片，直接返回字串；多張圖片返回陣列
                            if len(image_data_list) == 1:
                                question['image_file'] = image_data_list[0]
                            elif len(image_data_list) > 1:
                                question['image_file'] = image_data_list
                            else:
                                question['image_file'] = ''
                        else:
                            question['image_file'] = ''

                        questions.append(question)
                else:
                    print(f"⚠️ 找不到題目ID: {question_id}")
                    # 創建一個空的題目記錄
                    question = {
                        'id': i + 1,
                        'question_text': f'題目 {i + 1} (ID: {question_id})',
                        'type': 'single-choice',
                        'options': [],
                        'correct_answer': '',
                        'original_exam_id': question_id,
                        'image_file': '',
                        'key_points': ''
                    }
                    questions.append(question)
        
        # 成功獲取題目詳情
    
    # 階段2: 計算分數 - 分類題目
    
    # 更新進度狀態為第2階段
    update_progress_status(progress_id, False, 2, "正在分類題目...")
    
    # 評分和分析 - 全AI評分邏輯
    correct_count = 0
    wrong_count = 0
    total_score = 0
    wrong_questions = []
    unanswered_count = 0
    
    # 分類題目：已作答題目和未作答題目（所有已作答題目都使用AI評分）
    answered_questions = []  # 已作答題目（所有類型都使用AI評分）
    unanswered_questions = []    # 未作答題目
    
    # 處理已作答題目
    for i, question in enumerate(questions):
        question_id = question.get('original_exam_id', '')
        user_answer = answers.get(str(i), '')
        question_type = question.get('type', '')
        
        if question_type == 'group':
            # GROUP 題特殊處理：處理子題答案
            sub_questions = question.get('sub_questions', [])
            group_answered = False
            group_sub_answers = []  # 收集所有子題答案
            
            for sub_idx, sub_question in enumerate(sub_questions):
                sub_answer_key = f"{i}_sub_{sub_idx}"  # 子題答案鍵值格式：主題索引_sub_子題索引
                sub_user_answer = answers.get(sub_answer_key, '')
                
                if sub_user_answer:  # 子題有答案
                    group_answered = True
                    answer_time_seconds = question_answer_times.get(sub_answer_key, 0)
                    group_sub_answers.append(sub_user_answer)
                    
                    # 為每個子題創建獨立的評分資料
                    sub_q_data = {
                        'index': i,
                        'sub_index': sub_idx,
                        'question': {
                            'id': f"{i}_{sub_idx}",
                            'question_text': sub_question.get('question_text', ''),
                            'type': sub_question.get('answer_type', 'single-choice'),
                            'options': sub_question.get('options', []),
                            'correct_answer': sub_question.get('answer', ''),
                            'original_exam_id': sub_question.get('original_exam_id', question_id),
                            'image_file': sub_question.get('image_file', ''),
                            'key_points': sub_question.get('key_points', ''),
                            'question_number': sub_question.get('question_number', ''),
                            'is_sub_question': True,
                            'parent_question_id': question_id,
                            'parent_question_text': question.get('group_question_text', '')
                        },
                        'user_answer': sub_user_answer,
                        'answer_time_seconds': answer_time_seconds
                    }
                    
                    answered_questions.append(sub_q_data)
            
            # 如果沒有找到標準格式的子題答案，檢查是否有其他格式的答案
            if not group_answered:
                # 檢查是否有以主題索引為鍵的答案（可能是子題答案陣列）
                main_answer = answers.get(str(i), '')
                if isinstance(main_answer, list) and len(main_answer) > 0:
                    # 如果主答案是一個陣列，可能是子題答案
                    group_answered = True
                    group_sub_answers = main_answer
                    for sub_idx, sub_question in enumerate(sub_questions):
                        if sub_idx < len(main_answer):
                            sub_user_answer = main_answer[sub_idx]
                            answer_time_seconds = question_answer_times.get(str(i), 0) // len(sub_questions)  # 平均分配時間
                            
                            # 為每個子題創建獨立的評分資料
                            sub_q_data = {
                                'index': i,
                                'sub_index': sub_idx,
                                'question': {
                                    'id': f"{i}_{sub_idx}",
                                    'question_text': sub_question.get('question_text', ''),
                                    'type': sub_question.get('answer_type', 'single-choice'),
                                    'options': sub_question.get('options', []),
                                    'correct_answer': sub_question.get('answer', ''),
                                    'original_exam_id': sub_question.get('original_exam_id', question_id),
                                    'image_file': sub_question.get('image_file', ''),
                                    'key_points': sub_question.get('key_points', ''),
                                    'question_number': sub_question.get('question_number', ''),
                                    'is_sub_question': True,
                                    'parent_question_id': question_id,
                                    'parent_question_text': question.get('group_question_text', '')
                                },
                                'user_answer': sub_user_answer,
                                'answer_time_seconds': answer_time_seconds
                            }
                            
                            answered_questions.append(sub_q_data)
                
                # 如果還是沒有找到，檢查所有答案中是否有陣列格式的答案
                if not group_answered:
                    for answer_key, answer_value in answers.items():
                        if isinstance(answer_value, list) and len(answer_value) > 0:
                            # 假設這個陣列答案對應當前 Group 題目
                            group_answered = True
                            group_sub_answers = answer_value
                            # 找到陣列格式答案，處理 Group 題目
                            
                            for sub_idx, sub_question in enumerate(sub_questions):
                                if sub_idx < len(answer_value):
                                    sub_user_answer = answer_value[sub_idx]
                                    answer_time_seconds = question_answer_times.get(answer_key, 0) // len(sub_questions)
                                    
                                    # 為每個子題創建獨立的評分資料
                                    sub_q_data = {
                                        'index': i,
                                        'sub_index': sub_idx,
                                        'question': {
                                            'id': f"{i}_{sub_idx}",
                                            'question_text': sub_question.get('question_text', ''),
                                            'type': sub_question.get('answer_type', 'single-choice'),
                                            'options': sub_question.get('options', []),
                                            'correct_answer': sub_question.get('answer', ''),
                                            'original_exam_id': sub_question.get('original_exam_id', question_id),
                                            'image_file': sub_question.get('image_file', ''),
                                            'key_points': sub_question.get('key_points', ''),
                                            'question_number': sub_question.get('question_number', ''),
                                            'is_sub_question': True,
                                            'parent_question_id': question_id,
                                            'parent_question_text': question.get('group_question_text', '')
                                        },
                                        'user_answer': sub_user_answer,
                                        'answer_time_seconds': answer_time_seconds
                                    }
                                    
                                    answered_questions.append(sub_q_data)
                            break  # 只處理第一個找到的陣列答案
            
            # 為 Group 題目本身創建一個整體的答案記錄
            if group_answered:
                # 計算 Group 題目的整體作答時間
                group_answer_time = question_answer_times.get(str(i), 0)
                if not group_answer_time:
                    # 如果沒有找到主題索引的時間，嘗試從子題時間計算
                    group_answer_time = sum(q_data.get('answer_time_seconds', 0) for q_data in answered_questions 
                                          if q_data.get('index') == i and q_data.get('question', {}).get('is_sub_question'))
                
                # 創建 Group 題目的整體答案資料
                group_q_data = {
                    'index': i,
                    'question': {
                        'id': str(i),
                        'question_text': question.get('group_question_text', ''),
                        'type': 'group',
                        'options': [],
                        'correct_answer': '',  # Group 題目沒有單一正確答案
                        'original_exam_id': question_id,
                        'image_file': question.get('image_file', ''),
                        'key_points': question.get('key_points', ''),
                        'is_sub_question': False,
                        'parent_question_id': None,
                        'parent_question_text': None,
                        'sub_questions': sub_questions
                    },
                    'user_answer': group_sub_answers,  # 子題答案陣列
                    'answer_time_seconds': group_answer_time
                }
                
                answered_questions.append(group_q_data)
            else:
                # 整個題組都沒有答案
                unanswered_count += 1
                unanswered_questions.append({
                    'index': i,
                    'question': question,
                    'user_answer': '',
                    'question_type': 'group'
                })
        else:
            # 單題處理
            if user_answer:  # 只處理有答案的題目
                # 獲取作答時間（秒數）
                answer_time_seconds = question_answer_times.get(str(i), 0)
                
                # 調試日誌
                
                # 構建題目資料
                q_data = {
                    'index': i,
                    'question': question,
                    'user_answer': user_answer,
                    'answer_time_seconds': answer_time_seconds  # 每題作答時間（秒）
                }
                
                answered_questions.append(q_data)
            else:
                # 未作答題目：收集到未作答列表
                unanswered_count += 1
                unanswered_questions.append({
                    'index': i,
                    'question': question,
                    'user_answer': '',
                    'question_type': question_type
                })

    
    # 更新進度狀態為第3階段
    update_progress_status(progress_id, False, 3, "AI正在進行智能評分...")
    
    # 批量AI評分所有已作答題目
    if answered_questions:
        # 準備AI評分數據
        ai_questions_data = []
        for q_data in answered_questions:
            question = q_data['question']
            user_answer = q_data['user_answer']
            question_type = question.get('type', '')
            
            # 對於AI評分，使用原始完整答案，不進行截斷
            # 這樣AI能看到完整的圖片內容，評分更準確
            ai_question_data = {
                'question_id': question.get('original_exam_id', ''),
                'user_answer': user_answer,  # 使用原始完整答案
                'question_type': question_type,
                'question_text': question.get('question_text', ''),
                'options': question.get('options', []),
                'correct_answer': question.get('correct_answer', ''),
                'key_points': question.get('key_points', '')
            }
            
            # 如果是子題，添加額外信息
            if question.get('is_sub_question', False):
                ai_question_data.update({
                    'is_sub_question': True,
                    'question_number': question.get('question_number', ''),
                    'parent_question_id': question.get('parent_question_id', ''),
                    'parent_question_text': question.get('parent_question_text', ''),
                    'sub_index': q_data.get('sub_index', 0)
                })
            
            ai_questions_data.append(ai_question_data)
        
        # 使用AI批改模組進行批量評分
        ai_results = batch_grade_ai_questions(ai_questions_data)
        
        # 處理AI評分結果
        for i, result in enumerate(ai_results):
            q_data = answered_questions[i]
            question = q_data['question']
            question_id = question.get('original_exam_id', '')
            
            is_correct = result.get('is_correct', False)
            score = result.get('score', 0)
            feedback = result.get('feedback', {})
            
            # 統計正確和錯誤題數
            if is_correct:
                correct_count += 1
                total_score += score
            else:
                wrong_count += 1
                # 收集錯題信息
                wrong_question_info = {
                    'question_id': question.get('id', q_data['index'] + 1),
                    'question_text': question.get('question_text', ''),
                    'question_type': question.get('type', ''),  # 從question對象獲取type
                    'user_answer': q_data['user_answer'],
                    'correct_answer': question.get('correct_answer', ''),
                    'options': question.get('options', []),
                    'image_file': question.get('image_file', ''),
                    'original_exam_id': question.get('original_exam_id', ''),
                    'question_index': q_data['index'],
                    'score': score,
                    'feedback': feedback
                }
                
                # 如果是子題，添加額外信息
                if question.get('is_sub_question', False):
                    wrong_question_info.update({
                        'is_sub_question': True,
                        'question_number': question.get('question_number', ''),
                        'parent_question_id': question.get('parent_question_id', ''),
                        'parent_question_text': question.get('parent_question_text', ''),
                        'sub_index': q_data.get('sub_index', 0)
                    })
                
                wrong_questions.append(wrong_question_info)
            
            # 保存AI評分結果到 answered_questions 中，供後續使用
            q_data['ai_result'] = {
                'is_correct': is_correct,
                'score': score,
                'feedback': feedback
            }
        
        # AI批量評分完成
    else:
        pass

    # 更新進度狀態為第4階段
    if progress_id:
        update_progress_status(progress_id, False, 4, "正在統計結果...")
    
    # 計算統計數據
    answered_count = len(answered_questions)
    unanswered_count = len(unanswered_questions)
    
    # 計算統計數據
    accuracy_rate = (correct_count / total_questions * 100) if total_questions > 0 else 0
    average_score = (total_score / answered_count) if answered_count > 0 else 0
    
    # 更新或創建SQL記錄
    with sqldb.engine.connect() as conn:
        # 使用從測驗數據獲取的類型
        quiz_template_id = template_id_int  # 使用實際的模板ID
        
        # 查找現有的quiz_history記錄
        existing_record = conn.execute(text("""
            SELECT id FROM quiz_history 
            WHERE user_email = :user_email AND quiz_type = :quiz_type
            ORDER BY created_at DESC LIMIT 1
        """), {
            'user_email': user_email,
            'quiz_type': quiz_type
        }).fetchone()
        
        if existing_record:
            # 更新現有記錄
            quiz_history_id = existing_record[0]
            conn.execute(text("""
                UPDATE quiz_history 
                SET answered_questions = :answered_questions,
                    correct_count = :correct_count,
                    wrong_count = :wrong_count,
                    accuracy_rate = :accuracy_rate,
                    average_score = :average_score,
                    total_time_taken = :time_taken,
                    submit_time = :submit_time,
                    status = 'completed'
                WHERE id = :quiz_history_id
            """), {
                'answered_questions': answered_count,
                'correct_count': correct_count,
                'wrong_count': wrong_count,
                'accuracy_rate': round(accuracy_rate, 2),
                'average_score': round(average_score, 2),
                'time_taken': time_taken,
                                'submit_time': datetime.now(),
                'quiz_history_id': quiz_history_id
            })
        else:
            # 創建新記錄
            # 對於AI生成的考卷，quiz_template_id設為NULL（資料庫允許NULL）
            # 對於傳統考卷，使用整數template_id
            db_quiz_template_id = None if quiz_template_id is None else quiz_template_id
            
            result = conn.execute(text("""
                INSERT INTO quiz_history 
                (quiz_template_id, user_email, quiz_type, total_questions, answered_questions,
                 correct_count, wrong_count, accuracy_rate, average_score, total_time_taken, submit_time, status)
                VALUES (:quiz_template_id, :user_email, :quiz_type, :total_questions, :answered_questions,
                       :correct_count, :wrong_count, :accuracy_rate, :average_score, :total_time_taken, :submit_time, :status)
            """), {
                'quiz_template_id': db_quiz_template_id,
                'user_email': user_email,
                'quiz_type': quiz_type,
                'total_questions': total_questions,
                'answered_questions': answered_count,
                'correct_count': correct_count,
                'wrong_count': wrong_count,
                'accuracy_rate': round(accuracy_rate, 2),
                'average_score': round(average_score, 2),
                'total_time_taken': time_taken,
                'submit_time': datetime.now(),
                'status': 'completed'
            })
            quiz_history_id = result.lastrowid
        
        # 儲存所有題目的用戶答案到 quiz_answers 表
        # 1. 儲存已作答題目（AI評分結果）
        for i, q_data in enumerate(answered_questions):
            question = q_data['question']
            user_answer = q_data['user_answer']
            question_id = question.get('original_exam_id', '')
            question_type = question.get('type', '')
            
            # 獲取AI評分結果
            ai_result = q_data.get('ai_result', {})
            is_correct = ai_result.get('is_correct', False)
            score = ai_result.get('score', 0)
            feedback = ai_result.get('feedback', {})
            
            # 獲取作答時間（秒數）
            answer_time_seconds = q_data.get('answer_time_seconds', 0)
            
            # 處理 Group 題目的答案格式
            if question_type == 'group':
                # Group 題目的答案可能是陣列，需要轉換為字串
                if isinstance(user_answer, list):
                    user_answer_str = json.dumps(user_answer, ensure_ascii=False)
                else:
                    user_answer_str = str(user_answer)
            else:
                user_answer_str = str(user_answer)
            
            # 構建用戶答案資料
            answer_data = {
                'answer': user_answer_str,
                'feedback': feedback  # 使用AI批改的feedback
            }
            
            # 使用新的長答案存儲方法，保持數據完整性
            stored_answer = _store_long_answer(user_answer_str, 'unknown', quiz_history_id, question_id, user_email)
            
            # 插入到 quiz_answers 表，包含feedback和作答時間
            conn.execute(text("""
                INSERT INTO quiz_answers 
                (quiz_history_id, user_email, mongodb_question_id, user_answer, is_correct, score, feedback, answer_time_seconds)
                VALUES (:quiz_history_id, :user_email, :mongodb_question_id, :user_answer, :is_correct, :score, :feedback, :answer_time_seconds)
            """), {
                'quiz_history_id': quiz_history_id,
                'user_email': user_email,
                'mongodb_question_id': question_id,
                'user_answer': stored_answer,  # 使用存儲後的答案引用
                'is_correct': is_correct,
                'score': score,
                'feedback': json.dumps(feedback),  # 將feedback轉換為JSON字符串
                'answer_time_seconds': answer_time_seconds  # 每題作答時間（秒）
            })
        
        # 2. 儲存未作答題目
        for q_data in unanswered_questions:
            i = q_data['index']
            question = q_data['question']
            question_id = question.get('original_exam_id', '')
            
            # 未作答題目：is_correct = False, score = 0
            answer_data = {
                'answer': '',
                'feedback': {}
            }
            
            # 插入到 quiz_answers 表
            conn.execute(text("""
                INSERT INTO quiz_answers 
                (quiz_history_id, user_email, mongodb_question_id, user_answer, is_correct, score, answer_time_seconds)
                VALUES (:quiz_history_id, :user_email, :mongodb_question_id, :user_answer, :is_correct, :score, :answer_time_seconds)
            """), {
                'quiz_history_id': quiz_history_id,
                'user_email': user_email,
                'mongodb_question_id': question_id,
                'user_answer': '',  # 未作答題目答案為空
                'is_correct': False,  # 未作答題目標記為錯誤
                'score': 0,
                'answer_time_seconds': 0
            })
        
        # 保留原有的錯題儲存邏輯（向後兼容）
        if wrong_questions:
            for wrong_q in wrong_questions:
                # 使用新的長答案存儲方法，保持數據完整性
                stored_answer = _store_long_answer(wrong_q['user_answer'], 'unknown', quiz_history_id, 
                                                wrong_q.get('original_exam_id', ''), user_email)
                
                conn.execute(text("""
                    INSERT INTO quiz_errors 
                    (quiz_history_id, user_email, mongodb_question_id, user_answer,
                     score, time_taken)
                    VALUES (:quiz_history_id, :user_email, :mongodb_question_id,
                           :user_answer, :score, :time_taken)
                """), {
                    'quiz_history_id': quiz_history_id,
                    'user_email': user_email,
                    'mongodb_question_id': wrong_q.get('original_exam_id', ''),
                    'user_answer': stored_answer,  # 使用存儲後的答案引用
                    'score': wrong_q.get('score', 0),
                    'time_taken': 0  # 簡化時間處理
                })
        
        conn.commit()
    

    # 更新進度追蹤狀態為完成
    update_progress_status(progress_id, True, 4, "AI批改完成！")
    
    return jsonify({
        'token': refresh_token(token),
        'message': '測驗提交成功',
        'data': {
            'template_id': template_id,  # 返回模板ID
            'quiz_history_id': quiz_history_id,  # 返回測驗歷史記錄ID
            'result_id': f'result_{quiz_history_id}',  # 返回結果ID（用於前端跳轉）
            'progress_id': progress_id,  # 返回進度追蹤ID
            'total_questions': total_questions,
            'answered_questions': answered_count,
            'unanswered_questions': unanswered_count,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'marked_count': 0,  # 暫時設為0，後續可擴展
            'accuracy_rate': round(accuracy_rate, 2),
            'average_score': round(average_score, 2),
            'time_taken': time_taken,
            'total_time': time_taken,  # 添加總時間字段
            'grading_stages': [
                {'stage': 1, 'name': '試卷批改', 'status': 'completed', 'description': '獲取題目數據完成'},
                {'stage': 2, 'name': '計算分數', 'status': 'completed', 'description': '題目分類完成'},
                {'stage': 3, 'name': '評判知識點', 'status': 'completed', 'description': f'AI評分完成，共評分{answered_count}題'},
                {'stage': 4, 'name': '生成學習計畫', 'status': 'completed', 'description': f'統計完成，正確率{accuracy_rate:.1f}%'}
            ],
            'detailed_results': [
                {
                    'question_index': q_data['index'],
                    'question_text': q_data['question'].get('question_text', ''),
                    'user_answer': q_data['user_answer'],
                    'correct_answer': q_data['question'].get('correct_answer', ''),
                    'is_correct': q_data.get('ai_result', {}).get('is_correct', False),
                    'score': q_data.get('ai_result', {}).get('score', 0),
                    'feedback': q_data.get('ai_result', {}).get('feedback', {})
                }
                for q_data in answered_questions
            ]
        }
    })


# 舊的答案截斷方法已移除，現在使用長答案存儲方法保持數據完整性


# 進度追蹤存儲（簡單的內存存儲，生產環境建議使用 Redis）
progress_storage = {}

def update_progress_status(progress_id: str, is_completed: bool, current_stage: int, description: str):
    """更新進度追蹤狀態"""
    progress_storage[progress_id] = {
        'is_completed': is_completed,
        'current_stage': current_stage,
        'stage_description': description,
        'updated_at': time.time()
    }

def get_progress_status(progress_id: str) -> dict:
    """獲取進度追蹤狀態"""
    try:
        # 從進度追蹤存儲中獲取狀態
        return progress_storage.get(progress_id, {
            'current_stage': 1,  # 默認從第一階段開始
            'is_completed': False,
            'stage_description': '正在初始化...'
        })
    except Exception as e:
        print(f"❌ 獲取進度狀態失敗: {e}")
        return None

def _parse_user_answer(user_answer):
    """解析用戶答案，支援多種格式，包括 LONG_ANSWER_ 引用"""
    if isinstance(user_answer, dict):
        return user_answer.get('answer', '')
    elif isinstance(user_answer, str):
        # 處理 LONG_ANSWER_ 引用
        if user_answer.startswith('LONG_ANSWER_'):
            try:
                long_answer_id = int(user_answer.replace('LONG_ANSWER_', ''))
                # 從 long_answers 表查詢完整答案
                with sqldb.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT full_answer FROM long_answers 
                        WHERE id = :long_answer_id
                    """), {
                        'long_answer_id': long_answer_id
                    }).fetchone()
                    
                    if result:
                        return result[0]  # 返回完整的答案內容
                    else:
                        return f"[長答案載入失敗: {user_answer}]"
            except (ValueError, Exception) as e:
                print(f"❌ 解析長答案引用失敗: {e}")
                return f"[長答案解析錯誤: {user_answer}]"
        
        # 處理 JSON 格式
        elif user_answer.startswith('['):
            try:
                return json.loads(user_answer)
            except json.JSONDecodeError:
                return user_answer
    return user_answer

def _store_long_answer(user_answer: any, question_type: str, quiz_history_id: int, question_id: str, user_email: str) -> str:
    """
    存儲長答案到專門的表中，保持數據完整性
    
    參數：
    - user_answer: 原始用戶答案
    - question_type: 題目類型
    - quiz_history_id: 測驗歷史ID
    - question_id: 題目ID
    - user_email: 用戶郵箱
    
    返回：
    - 存儲引用ID或標識符
    """
    try:
        answer_str = str(user_answer)
        
        # 如果答案不長，直接返回
        if len(answer_str) <= 10000:
            return answer_str
        
        # 對於長答案，存儲到專門的表中
        with sqldb.engine.connect() as conn:
            # 創建長答案存儲表（如果不存在）
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS long_answers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    quiz_history_id INT NOT NULL,
                    question_id VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255) NOT NULL,
                    question_type VARCHAR(50) NOT NULL,
                    full_answer LONGTEXT NOT NULL,
                    answer_hash VARCHAR(64) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_quiz_question (quiz_history_id, question_id),
                    INDEX idx_user (user_email)
                )
            """))
            
            # 計算答案的哈希值作為唯一標識
            answer_hash = hashlib.md5(answer_str.encode()).hexdigest()
            
            # 檢查是否已經存儲過相同的答案
            existing = conn.execute(text("""
                SELECT id FROM long_answers 
                WHERE quiz_history_id = :quiz_history_id AND question_id = :question_id
            """), {
                'quiz_history_id': quiz_history_id,
                'question_id': question_id
            }).fetchone()
            
            if existing:
                # 如果已存在，返回引用標識
                return f"LONG_ANSWER_{existing[0]}"
            else:
                # 存儲新的長答案
                result = conn.execute(text("""
                    INSERT INTO long_answers 
                    (quiz_history_id, question_id, user_email, question_type, full_answer, answer_hash)
                    VALUES (:quiz_history_id, :question_id, :user_email, :question_type, :full_answer, :answer_hash)
                """), {
                    'quiz_history_id': quiz_history_id,
                    'question_id': question_id,
                    'user_email': user_email,
                    'question_type': question_type,
                    'full_answer': answer_str,
                    'answer_hash': answer_hash
                })
                
                long_answer_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                conn.commit()
                return f"LONG_ANSWER_{long_answer_id}"
                
    except Exception as e:
        print(f"❌ 存儲長答案失敗: {e}")
        # 如果存儲失敗，返回截斷的答案（但保持數據完整性）
        answer_str = str(user_answer)
        if len(answer_str) > 10000:
            # 返回截斷的答案，但添加錯誤標記
            truncated_answer = answer_str[:9000] + "...[存儲失敗，答案已截斷]"
            print(f"⚠️ 長答案存儲失敗，使用截斷方式: {len(answer_str)} -> {len(truncated_answer)} 字符")
            return truncated_answer
        else:
            # 如果答案不長，直接返回
            return answer_str


@quiz_bp.route('/get-quiz-result/<result_id>', methods=['GET', 'OPTIONS'])
def get_quiz_result(result_id):
    """根據結果ID獲取測驗結果 API - 優化版本"""
    if request.method == 'OPTIONS':
        return jsonify({'token': None, 'success': True}), 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供token'}), 401
    
    token = auth_header.split(" ")[1]
    
    # 從result_id中提取quiz_history_id
    # result_id格式: result_123
    if not result_id.startswith('result_'):
        return jsonify({'token': None, 'message': '無效的結果ID格式'}), 400
    
    try:
        quiz_history_id = int(result_id.split('_')[1])
    except (ValueError, IndexError):
        return jsonify({'token': None, 'message': '無效的結果ID格式'}), 400
    
    # 從SQL獲取測驗結果
    with sqldb.engine.connect() as conn:
        # 獲取測驗歷史記錄
        history_result = conn.execute(text("""
            SELECT qh.id, qh.quiz_template_id, qh.user_email, qh.quiz_type, 
                   qh.total_questions, qh.answered_questions, qh.correct_count, qh.wrong_count,
                   qh.accuracy_rate, qh.average_score, qh.total_time_taken, 
                   qh.submit_time, qh.status, qh.created_at,
                   qt.question_ids, qt.school, qt.department, qt.year
            FROM quiz_history qh
            LEFT JOIN quiz_templates qt ON qh.quiz_template_id = qt.id
            WHERE qh.id = :quiz_history_id
        """), {
            'quiz_history_id': quiz_history_id
        }).fetchone()
        
        if not history_result:
            return jsonify({'token': None, 'message': '測驗結果不存在'}), 404
        

        # 獲取所有題目的用戶答案（從quiz_answers表）
        answers_result = conn.execute(text("""
            SELECT mongodb_question_id, user_answer, is_correct, score, feedback, answer_time_seconds, created_at
            FROM quiz_answers 
            WHERE quiz_history_id = :quiz_history_id
            ORDER BY created_at
        """), {
            'quiz_history_id': quiz_history_id
        }).fetchall()
        

        # 獲取錯題詳情（從quiz_errors表，向後兼容）
        error_result = conn.execute(text("""
            SELECT mongodb_question_id, user_answer, score, time_taken, created_at
            FROM quiz_errors 
            WHERE quiz_history_id = :quiz_history_id
            ORDER BY created_at
        """), {
            'quiz_history_id': quiz_history_id
        }).fetchall()
        

        # 構建答案字典，方便查詢
        answers_dict = {}
        for answer in answers_result:
            answers_dict[str(answer[0])] = {
                'user_answer': json.loads(answer[1]) if answer[1] else '',
                'is_correct': bool(answer[2]),
                'score': float(answer[3]) if answer[3] else 0,
                'feedback': json.loads(answer[4]) if answer[4] else {}, # 將JSON字符串轉換回Python字典
                'answer_time_seconds': answer[5] if answer[5] else 0,
                'answer_time': answer[6].isoformat() if answer[6] else None
            }
        
        # 獲取題目ID列表
        question_ids_raw = history_result[14]
        question_ids = []
        if question_ids_raw:
            try:
                question_ids = json.loads(question_ids_raw)
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失敗: {e}")
                question_ids = []
        
        if not question_ids:
            result_data = {
                'quiz_history_id': history_result[0],
                'quiz_template_id': history_result[1],
                'user_email': history_result[2],
                'quiz_type': history_result[3],
                'total_questions': history_result[4],
                'answered_questions': history_result[5],
                'unanswered_questions': history_result[4] - history_result[5],
                'correct_count': history_result[6],
                'wrong_count': history_result[7],
                'accuracy_rate': float(history_result[8]) if history_result[8] else 0,
                'average_score': float(history_result[9]) if history_result[9] else 0,
                'total_time_taken': history_result[10] if history_result[10] else 0,
                'submit_time': history_result[11].isoformat() if history_result[11] else None,
                'status': history_result[12],
                'created_at': history_result[13].isoformat() if history_result[13] else None,
                'school': history_result[15] if history_result[15] else '',
                'department': history_result[16] if history_result[16] else '',
                'year': history_result[17] if history_result[17] else '',
                'questions': [],
                'errors': []
            }
            
            return jsonify({
                'token': refresh_token(token),
                'success': True,
                'message': '獲取測驗結果成功（僅基本統計）',
                'data': result_data
            }), 200
        
        # 獲取所有題目的詳細資訊
        all_questions = []
        errors = []
        
        for i, question_id in enumerate(question_ids):

            # 從MongoDB獲取題目詳情
            question_detail = {}
            try:
                # 安全地處理 ObjectId 查詢
                if isinstance(question_id, str) and len(question_id) == 24:
                    exam_question = mongo.db.exam.find_one({"_id": ObjectId(question_id)})
                else:
                    exam_question = mongo.db.exam.find_one({"_id": question_id})
                
                if exam_question:
                    # 使用與 create-quiz 相同的題目處理邏輯
                    exam_type = exam_question.get('type', 'single')
                    if exam_type == 'group':
                        # 題組：保留群組題外層資訊，展開子題但一併回傳
                        group_question_text = exam_question.get('group_question_text') or exam_question.get('question_text', '')
                        if not group_question_text:
                            group_question_text = f"題組 {i+1} (無題目文字)"
                        
                        micro_concepts = exam_question.get('micro_concepts', [])
                        key_points = exam_question.get('key-points', '')
                        # 處理 key-points 可能是陣列或字串的情況
                        if isinstance(key_points, list):
                            key_points = ', '.join(key_points) if key_points else ''
                        parent_id = str(exam_question.get('_id', ''))

                        # 構建子題清單
                        sub_qs_raw = exam_question.get('sub_questions', []) or []
                        sub_qs = []
                        for sub in sub_qs_raw:
                            sub_options = sub.get('options', [])
                            if isinstance(sub_options, str):
                                sub_options = [opt.strip() for opt in sub_options.split(',') if opt.strip()]
                            elif not isinstance(sub_options, list):
                                sub_options = []

                            sub_image = sub.get('image_file', '')

                            sub_qs.append({
                                'question_number': sub.get('question_number', ''),
                                'question_text': sub.get('question_text', ''),
                                'options': sub_options,
                                'answer': sub.get('answer', ''),
                                'answer_type': sub.get('answer_type', 'single-choice'),
                                'image_file': sub_image,
                                'detail_answer': sub.get('detail-answer', ''),
                                'key_points': ', '.join(sub.get('key-points', [])) if isinstance(sub.get('key-points', []), list) else sub.get('key-points', ''),
                                'difficulty_level': sub.get('difficulty level', sub.get('difficulty_level', '')),
                                'original_exam_id': parent_id
                            })

                        question_detail = {
                            'type': 'group',
                            'group_question_text': group_question_text,
                            'micro_concepts': micro_concepts,
                            'key_points': key_points,
                            'original_exam_id': parent_id,
                            'sub_questions': sub_qs,
                            'image_file': exam_question.get('image_file', '')
                        }
                    else:
                        # 單題處理
                        question_text = exam_question.get('question_text', '')
                        if not question_text:
                            if exam_question.get('answer'):
                                question_text = f"題目 {i+1}: {exam_question.get('answer', '')[:200]}..."
                            else:
                                question_text = f"題目 {i+1} (無題目文字)"
                        
                        question_detail = {
                            'type': exam_question.get('answer_type', 'single-choice'),
                            'question_text': question_text,
                            'options': exam_question.get('options', []),
                            'correct_answer': exam_question.get('answer', ''),
                            'image_file': exam_question.get('image_file', ''),
                            'key_points': ', '.join(exam_question.get('key-points', [])) if isinstance(exam_question.get('key-points', []), list) else exam_question.get('key-points', ''),
                            'original_exam_id': str(exam_question.get('_id', ''))
                        }
                else:
                    question_detail = {
                        'question_text': f'題目 {i + 1}',
                        'options': [],
                        'correct_answer': '',
                        'image_file': '',
                        'key_points': ''
                    }
            except Exception as e:
                print(f"⚠️ 獲取題目詳情失敗: {e}")
                question_detail = {
                    'question_text': f'題目 {i + 1}',
                    'options': [],
                    'correct_answer': '',
                    'image_file': '',
                    'key_points': ''
                }
            
            # 獲取用戶答案信息
            question_id_str = str(question_id)
            answer_info = answers_dict.get(question_id_str, {})
            
            # 構建題目資訊
            if question_detail.get('type') == 'group':
                # GROUP 題特殊處理
                sub_questions = question_detail.get('sub_questions', [])
                
                # 處理子題答案
                processed_sub_questions = []
                for sub_idx, sub_question in enumerate(sub_questions):
                    # 查找子題的答案（格式：主題ID_sub_子題索引）
                    sub_question_id = f"{question_id_str}_{sub_idx}"
                    sub_answer_info = answers_dict.get(sub_question_id, {})
                    
                    # 構建子題資訊
                    processed_sub_question = {
                        'question_number': sub_question.get('question_number', ''),
                        'question_text': sub_question.get('question_text', ''),
                        'answer_type': sub_question.get('answer_type', 'short-answer'),
                        'options': sub_question.get('options', []),
                        'correct_answer': sub_question.get('answer', ''),
                        'image_file': sub_question.get('image_file', ''),
                        'key_points': sub_question.get('key_points', ''),
                        'difficulty_level': sub_question.get('difficulty_level', ''),
                        'is_correct': sub_answer_info.get('is_correct', False),
                        'user_answer': sub_answer_info.get('user_answer', ''),
                        'score': sub_answer_info.get('score', 0),
                        'answer_time_seconds': sub_answer_info.get('answer_time_seconds', 0),
                        'feedback': sub_answer_info.get('feedback', {})
                    }
                    processed_sub_questions.append(processed_sub_question)
                
                # 處理 Group 題目的用戶答案
                group_user_answer = _parse_user_answer(answer_info.get('user_answer', ''))
                
                question_info = {
                    'question_id': question_id_str,
                    'question_index': i,
                    'type': 'group',
                    'question_text': question_detail.get('group_question_text', ''),  # 添加 question_text 欄位
                    'group_question_text': question_detail.get('group_question_text', ''),
                    'micro_concepts': question_detail.get('micro_concepts', []),
                    'key_points': question_detail.get('key_points', ''),
                    'image_file': question_detail.get('image_file', ''),
                    'sub_questions': processed_sub_questions,
                    'is_correct': answer_info.get('is_correct', False),
                    'is_marked': False,  # 目前沒有標記功能
                    'user_answer': group_user_answer,
                    'score': answer_info.get('score', 0),
                    'answer_time_seconds': answer_info.get('answer_time_seconds', 0),
                    'answer_time': answer_info.get('answer_time')
                }
            else:
                # 單題處理
                single_user_answer = _parse_user_answer(answer_info.get('user_answer', ''))
                
                question_info = {
                    'question_id': question_id_str,
                    'question_index': i,
                    'type': question_detail.get('type', 'single-choice'),
                    'question_text': question_detail.get('question_text', ''),
                    'options': question_detail.get('options', []),
                    'correct_answer': question_detail.get('correct_answer', ''),
                    'image_file': question_detail.get('image_file', ''),
                    'key_points': question_detail.get('key_points', ''),
                    'is_correct': answer_info.get('is_correct', False),
                    'is_marked': False,  # 目前沒有標記功能
                    'user_answer': single_user_answer,
                    'score': answer_info.get('score', 0),
                    'answer_time_seconds': answer_info.get('answer_time_seconds', 0),
                    'answer_time': answer_info.get('answer_time')
                }
            
            # 檢查是否為錯題
            if not answer_info.get('is_correct', False):
                errors.append(question_info)
            
            all_questions.append(question_info)
        
        # 計算統計數據
        total_questions = history_result[4]
        answered_questions = history_result[5]
        correct_count = history_result[6]
        wrong_count = history_result[7]
        unanswered_count = total_questions - answered_questions
        
        result_data = {
            'quiz_history_id': history_result[0],
            'quiz_template_id': history_result[1],
            'user_email': history_result[2],
            'quiz_type': history_result[3],
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'unanswered_questions': unanswered_count,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'accuracy_rate': float(history_result[8]) if history_result[8] else 0,
            'average_score': float(history_result[9]) if history_result[9] else 0,
            'total_time_taken': history_result[10] if history_result[10] else 0,
            'submit_time': history_result[11].isoformat() if history_result[11] else None,
            'status': history_result[12],
            'created_at': history_result[13].isoformat() if history_result[13] else None,
            'school': history_result[15] if history_result[15] else '',
            'department': history_result[16] if history_result[16] else '',
            'year': history_result[17] if history_result[17] else '',
            'questions': all_questions,  # 所有題目的詳細資訊
            'errors': errors  # 錯題列表
        }

        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'message': '獲取測驗結果成功',
            'data': result_data
        }), 200


# 删除 /test-quiz-result API - 与 /get-quiz-result 功能重复

@quiz_bp.route('/create-quiz', methods=['POST', 'OPTIONS'])
def create_quiz():
    """創建測驗 API - 支持用戶填寫學校、科系、年份"""
    if request.method == 'OPTIONS':
        return jsonify({'token': None, 'message': 'CORS preflight'}), 200
    token = request.headers.get('Authorization')
    token = token.split(" ")[1]
    try:
        # 驗證token
        user_email = verify_token(token)

        # 獲取請求參數
        data = request.get_json()
        quiz_type = data.get('type')  # 'knowledge' 或 'pastexam'
        
        
        # 獲取用戶填寫的學校、科系、年份信息
        school = data.get('school', '')
        department = data.get('department', '')
        year = data.get('year', '')
        
        if quiz_type == 'knowledge':
            # 知識點測驗
            topic = data.get('topic')
            difficulty = data.get('difficulty', 'medium')
            count = int(data.get('count', 20))
            
            if not topic:
                return jsonify({'token': None, 'message': '缺少知識點參數'}), 400
            
            # 從MongoDB獲取符合條件的考題
            # 使用正確的欄位名稱：key-points
            query = {"key-points": topic}
            available_exams = list(mongo.db.exam.find(query).limit(count * 2))
            
            if len(available_exams) < count:
                available_exams = list(mongo.db.exam.find({}).limit(count))
            
            selected_exams = random.sample(available_exams, min(count, len(available_exams)))
            quiz_title = f"{topic} - {difficulty} - {count}題"
            
            # 知識點測驗的學校、科系、年份
            if not school:
                school = '知識點測驗'
            if not department:
                department = topic or '通用'
            if not year:
                year = '不限年份'
            
        elif quiz_type == 'pastexam':
            # 考古題測驗
            if not all([school, year, department]):
                return jsonify({'token': None, 'message': '考古題測驗必須填寫學校、年份、系所'}), 400
            
            # 特殊處理 demo 選項
            if school == 'demo' and year == '114' and department == 'demo':
                # 返回固定的 7 題 demo 題目
                demo_question_ids = [
                    "6905deac7292fdbd94102c01",
                    "6905deac7292fdbd94102c02",
                    "6905deac7292fdbd94102c03",
                    "6905deac7292fdbd94102c04",
                    "6905deac7292fdbd94102c05",
                    "6905deac7292fdbd94102c06",
                    "6905deac7292fdbd94102c07"
                ]
                selected_exams = []
                for q_id in demo_question_ids:
                    try:
                        object_id = ObjectId(q_id)
                        question_doc = mongo.db.exam.find_one({"_id": object_id})
                        if question_doc:
                            selected_exams.append(question_doc)
                    except Exception as e:
                        print(f"⚠️ 載入 demo 題目失敗 (ID: {q_id}): {e}")
                        continue
                
                if not selected_exams:
                    return jsonify({'token': None, 'message': '找不到 demo 題目'}), 404
                
                quiz_title = f"Demo - 114年 - Demo"
            else:
                # 從MongoDB獲取符合條件的考古題
                query = {
                    "school": school,
                    "year": year,
                    "department": department
                }
                selected_exams = list(mongo.db.exam.find(query))
                
                if not selected_exams:
                    print(f"❌ 找不到符合條件的考題: {query}")
                    return jsonify({'token': None, 'message': '找不到符合條件的考題'}), 404
                
                quiz_title = f"{school} - {year}年 - {department}"

        else:
            return jsonify({'token': None, 'message': '無效的測驗類型'}), 400
        
        # 轉換為標準化的題目格式
        questions = []
        for i, exam in enumerate(selected_exams):
            # 正確讀取題目類型 - type用來判斷單一/題組，answer_type用來判斷單選/多選
            exam_type = exam.get('type', 'single')  # type: single/group
            answer_type = exam.get('answer_type', 'single-choice')  # answer_type: single-choice/multiple-choice等
            if exam_type == 'group':  # 使用type欄位判斷是否為題組
                # 題組：保留群組題外層資訊，展開子題但一併回傳
                group_question_text = exam.get('group_question_text') or exam.get('question_text', '')
                if not group_question_text:
                    print(f"⚠️ 警告：題組 {i+1} (ID: {exam.get('_id')}) 的 group_question_text 和 question_text 都為空")
                    group_question_text = f"題組 {i+1} (無題目文字)"
                
                micro_concepts = exam.get('micro_concepts', [])
                key_points = exam.get('key-points', '')
                # 處理 key-points 可能是陣列或字串的情況
                if isinstance(key_points, list):
                    key_points = ', '.join(key_points) if key_points else ''
                parent_id = str(exam.get('_id', ''))

                # 構建子題清單
                sub_qs_raw = exam.get('sub_questions', []) or []
                sub_qs = []
                for sub in sub_qs_raw:
                    sub_options = sub.get('options', [])
                    if isinstance(sub_options, str):
                        sub_options = [opt.strip() for opt in sub_options.split(',') if opt.strip()]
                    elif not isinstance(sub_options, list):
                        sub_options = []

                    sub_image = sub.get('image_file', '')
                    # 處理子題圖片 - 轉換為 base64
                    sub_image_data_list = []
                    if sub_image and sub_image not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']:
                        sub_image_filenames = []
                        if isinstance(sub_image, list):
                            sub_image_filenames = [img for img in sub_image if img and img not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']]
                        elif isinstance(sub_image, str):
                            sub_image_filenames = [sub_image]
                        
                        # 將每個圖片檔案轉換為 base64
                        for sub_image_filename in sub_image_filenames:
                            sub_image_base64 = get_image_base64(sub_image_filename)
                            if sub_image_base64:
                                # 判斷圖片格式
                                image_ext = os.path.splitext(sub_image_filename)[1].lower()
                                mime_type = 'image/jpeg'
                                if image_ext in ['.png']:
                                    mime_type = 'image/png'
                                elif image_ext in ['.gif']:
                                    mime_type = 'image/gif'
                                elif image_ext in ['.webp']:
                                    mime_type = 'image/webp'
                                
                                sub_image_data_list.append(f"data:{mime_type};base64,{sub_image_base64}")
                    
                    # 如果只有一張圖片，直接返回字串；多張圖片返回陣列
                    if len(sub_image_data_list) == 1:
                        sub_image_final = sub_image_data_list[0]
                    elif len(sub_image_data_list) > 1:
                        sub_image_final = sub_image_data_list
                    else:
                        sub_image_final = ''

                    # 處理子題的 key-points
                    sub_key_points = sub.get('key-points', '')
                    if isinstance(sub_key_points, list):
                        sub_key_points = ', '.join(sub_key_points) if sub_key_points else ''
                    
                    sub_qs.append({
                        'question_number': sub.get('question_number', ''),
                        'question_text': sub.get('question_text', ''),
                        'options': sub_options,
                        'answer': sub.get('answer', ''),
                        'answer_type': sub.get('answer_type', 'single-choice'),
                        'image_file': sub_image_final,
                        'detail_answer': sub.get('detail-answer', ''),
                        'key_points': sub_key_points,
                        'difficulty_level': sub.get('difficulty level', sub.get('difficulty_level', '')),
                        'original_exam_id': parent_id
                    })

                group_question = {
                    'id': i + 1,
                    'type': 'group',
                    'group_question_text': group_question_text,
                    'micro_concepts': micro_concepts,
                    'key_points': key_points,
                    'original_exam_id': parent_id,
                    'sub_questions': sub_qs
                }

                # 題組外層若也有圖片，轉換為 base64
                group_image_file = exam.get('image_file', '')
                group_image_data_list = []
                if group_image_file and group_image_file not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']:
                    group_image_filenames = []
                    if isinstance(group_image_file, list):
                        group_image_filenames = [img for img in group_image_file if img and img not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']]
                    elif isinstance(group_image_file, str):
                        group_image_filenames = [group_image_file]
                    
                    # 將每個圖片檔案轉換為 base64
                    for group_image_filename in group_image_filenames:
                        group_image_base64 = get_image_base64(group_image_filename)
                        if group_image_base64:
                            # 判斷圖片格式
                            image_ext = os.path.splitext(group_image_filename)[1].lower()
                            mime_type = 'image/jpeg'
                            if image_ext in ['.png']:
                                mime_type = 'image/png'
                            elif image_ext in ['.gif']:
                                mime_type = 'image/gif'
                            elif image_ext in ['.webp']:
                                mime_type = 'image/webp'
                            
                            group_image_data_list.append(f"data:{mime_type};base64,{group_image_base64}")
                    
                    # 如果只有一張圖片，直接返回字串；多張圖片返回陣列
                    if len(group_image_data_list) == 1:
                        group_question['image_file'] = group_image_data_list[0]
                    elif len(group_image_data_list) > 1:
                        group_question['image_file'] = group_image_data_list
                    else:
                        group_question['image_file'] = ''
                else:
                    group_question['image_file'] = ''

                questions.append(group_question)
            else:
                # 單題：保持原有行為
                question_type = answer_type  # 使用answer_type作為question_type
                
                # 調試信息：檢查題目文字
                question_text = exam.get('question_text', '')
                if not question_text:
                    print(f"⚠️ 警告：題目 {i+1} (ID: {exam.get('_id')}) 的 question_text 為空")
                    print(f"   學校: {exam.get('school')}, 科系: {exam.get('department')}, 年份: {exam.get('year')}")
                    print(f"   答案: {exam.get('answer', '')[:100]}...")
                    # 嘗試從其他欄位獲取題目文字
                    if exam.get('answer'):
                        question_text = f"題目 {i+1}: {exam.get('answer', '')[:200]}..."
                    else:
                        question_text = f"題目 {i+1} (無題目文字)"
                
                
                question = {
                    'id': i + 1,
                    'question_text': question_text,
                    'type': question_type,  # 這裡應該是answer_type的值
                    'options': exam.get('options'),
                    'correct_answer': exam.get('answer', ''),
                    'original_exam_id': str(exam.get('_id', '')),
                    'image_file': exam.get('image_file'),
                    'key_points': ', '.join(exam.get('key-points', [])) if isinstance(exam.get('key-points', []), list) else exam.get('key-points', ''),
                    'answer_type': question_type,  # 這裡也使用answer_type
                    'detail_answer': exam.get('detail-answer', '')
                }

                # 處理選項格式
                if isinstance(question['options'], str):
                    question['options'] = [opt.strip() for opt in question['options'].split(',') if opt.strip()]
                elif not isinstance(question['options'], list):
                    question['options'] = []

                # 處理圖片檔案（單題）- 轉換為 base64
                image_file = exam.get('image_file', '')
                image_data_list = []
                if image_file and image_file not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']:
                    image_filenames = []
                    if isinstance(image_file, list):
                        image_filenames = [img for img in image_file if img and img not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']]
                    elif isinstance(image_file, str):
                        image_filenames = [image_file]
                    
                    # 將每個圖片檔案轉換為 base64
                    for image_filename in image_filenames:
                        image_base64 = get_image_base64(image_filename)
                        if image_base64:
                            # 判斷圖片格式
                            image_ext = os.path.splitext(image_filename)[1].lower()
                            mime_type = 'image/jpeg'
                            if image_ext in ['.png']:
                                mime_type = 'image/png'
                            elif image_ext in ['.gif']:
                                mime_type = 'image/gif'
                            elif image_ext in ['.webp']:
                                mime_type = 'image/webp'
                            
                            image_data_list.append(f"data:{mime_type};base64,{image_base64}")
                    
                    # 如果只有一張圖片，直接返回字串；多張圖片返回陣列
                    if len(image_data_list) == 1:
                        question['image_file'] = image_data_list[0]
                    elif len(image_data_list) > 1:
                        question['image_file'] = image_data_list
                    else:
                        question['image_file'] = ''
                else:
                    question['image_file'] = ''

                questions.append(question)
        
        # 生成測驗ID
        quiz_id = str(uuid.uuid4())
        

        # 在SQL中創建quiz_history初始記錄
        try:
            with sqldb.engine.connect() as conn:
                # 檢查並創建 quiz_templates 表
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS quiz_templates (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_email VARCHAR(255) NOT NULL,
                            template_type ENUM('knowledge', 'pastexam') NOT NULL,
                            question_ids JSON NOT NULL,
                            school VARCHAR(100) DEFAULT '',
                            department VARCHAR(100) DEFAULT '',
                            year VARCHAR(20) DEFAULT '',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_user_email (user_email),
                            INDEX idx_template_type (template_type),
                            INDEX idx_school (school),
                            INDEX idx_department (department),
                            INDEX idx_year (year),
                            INDEX idx_created_at (created_at)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """))
                    conn.commit()

                except Exception as e:
                    print(f"⚠️ 創建 quiz_templates 表失敗: {e}")
                
                # 檢查並創建 quiz_history 表
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS quiz_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            quiz_template_id INT NULL,
                            user_email VARCHAR(255) NOT NULL,
                            quiz_type ENUM('knowledge', 'pastexam') NOT NULL,
                            total_questions INT DEFAULT 0,
                            answered_questions INT DEFAULT 0,
                            correct_count INT DEFAULT 0,
                            wrong_count INT DEFAULT 0,
                            accuracy_rate DECIMAL(5,2) DEFAULT 0,
                            average_score DECIMAL(5,2) DEFAULT 0,
                            total_time_taken INT DEFAULT 0,
                            submit_time DATETIME NOT NULL,
                            status ENUM('incomplete', 'completed', 'abandoned') DEFAULT 'incomplete',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (quiz_template_id) REFERENCES quiz_templates(id) ON DELETE SET NULL,
                            INDEX idx_user_email (user_email),
                            INDEX idx_quiz_template_id (quiz_template_id),
                            INDEX idx_submit_time (submit_time)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """))
                    conn.commit()

                except Exception as e:
                    print(f"⚠️ 創建 quiz_history 表失敗: {e}")
                
                # 檢查並創建 quiz_errors 表
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS quiz_errors (
                            error_id INT AUTO_INCREMENT PRIMARY KEY,
                            quiz_history_id INT NOT NULL,
                            user_email VARCHAR(255) NOT NULL,
                            mongodb_question_id VARCHAR(50) NOT NULL,
                            user_answer TEXT,
                            score DECIMAL(5,2) DEFAULT 0,
                            time_taken INT DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (quiz_history_id) REFERENCES quiz_history(id) ON DELETE CASCADE,
                            INDEX idx_user_email (user_email),
                            INDEX idx_mongodb_question_id (mongodb_question_id),
                            INDEX idx_created_at (created_at)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """))
                    conn.commit()

                except Exception as e:
                    print(f"⚠️ 創建 quiz_errors 表失敗: {e}")
                
                # 創建考卷模板
                question_ids = [str(q.get('original_exam_id', '')) for q in questions if q.get('original_exam_id')]
                
                template_result = conn.execute(text("""
                    INSERT INTO quiz_templates 
                    (user_email, template_type, question_ids, school, department, year)
                    VALUES (:user_email, :template_type, :question_ids, :school, :department, :year)
                """), {
                    'user_email': user_email,
                    'template_type': quiz_type,
                    'question_ids': json.dumps(question_ids),
                    'school': school,
                    'department': department,
                    'year': year
                })
                conn.commit()
                
                template_id = template_result.lastrowid

                
                # 創建初始的quiz_history記錄
                conn.execute(text("""
                    INSERT INTO quiz_history 
                    (quiz_template_id, user_email, quiz_type, total_questions, answered_questions, 
                     correct_count, wrong_count, accuracy_rate, average_score, submit_time, status)
                    VALUES (:quiz_template_id, :user_email, :quiz_type, :total_questions, :answered_questions,
                           :correct_count, :wrong_count, :accuracy_rate, :average_score, :submit_time, :status)
                """), {
                    'quiz_template_id': template_id,
                    'user_email': user_email,
                    'quiz_type': quiz_type,
                    'total_questions': len(questions),
                    'answered_questions': 0,
                    'correct_count': 0,
                    'wrong_count': 0,
                    'accuracy_rate': 0,
                    'average_score': 0,
                    'submit_time': datetime.now(),
                    'status': 'incomplete'
                })
                conn.commit()

                
        except Exception as sql_error:
            print(f"⚠️ SQL初始記錄創建失敗: {sql_error}")
            # SQL創建失敗不影響主要功能
        
        return jsonify({
            'token': refresh_token(token),
            'message': '測驗創建成功',
            'quiz_id': quiz_id,
            'template_id': template_id,  # 返回模板ID
            'title': quiz_title,
            'school': school,
            'department': department,
            'year': year,
            'question_count': len(questions),
            'time_limit': 60,
            'questions': questions  # 直接返回题目数据
        }), 200

    except Exception as e:
        print(f"❌ 創建測驗時發生錯誤: {str(e)}")
        return jsonify({'token': None, 'message': f'創建測驗失敗: {str(e)}'}), 500

def get_image_base64(image_filename):
    """讀取圖片檔案並轉換為 base64 編碼"""
    try:
        # 檢查檔案名稱是否為空
        if not image_filename or not image_filename.strip():
            return None
        
        # 取得當前檔案所在目錄，圖片在同層的 picture 資料夾
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(current_dir, 'picture', image_filename)
        
        if os.path.exists(image_path):
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_encoded = base64.b64encode(image_data).decode('utf-8')
                return base64_encoded
        else:
            # print(f"圖片檔案不存在: {image_path}")
            return None
    except Exception as e:
        print(f"讀取圖片時發生錯誤: {str(e)}")
        return None

# 删除 /get-quiz API - 前端不再使用，功能已被 create-quiz 替代

@quiz_bp.route('/get-exam', methods=['POST', 'OPTIONS'])
def get_exam():
    """獲取所有考題數據"""
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供token', 'code': 'NO_TOKEN'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        user_email = decoded_token.get('user')
        
        if not user_email:
            return jsonify({'token': None, 'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({'token': None, 'message': 'Token已過期，請重新登錄', 'code': 'TOKEN_EXPIRED'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'token': None, 'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except Exception as e:
        print(f"驗證token時發生錯誤: {str(e)}")
        return jsonify({'token': None, 'message': '認證失敗', 'code': 'AUTH_FAILED'}), 401
    
    examdata = mongo.db.exam.find()
    exam_list = []
    for exam in examdata:
        exam_dict = {
             'type': exam.get('type'),
                    'school': exam.get('school'),
                    'department': exam.get('department'),
                    'year': exam.get('year'),
                    'question_number': exam.get('question_number'),
                    'question_text': exam.get('question_text'),
                    'options': exam.get('options'),
                    'answer': exam.get('answer'),
                    'answer_type': exam.get('answer_type'),
                    'image_file': exam.get('image_file'),
                    'detail-answer': exam.get('detail-answer'),
                    'key_points': ', '.join(exam.get('key-points', [])) if isinstance(exam.get('key-points', []), list) else exam.get('key-points', ''),
                    'difficulty level': exam.get('difficulty level'),
        }
        
        # 處理圖片檔案
        if exam_dict['image_file']:
            image_data_list = []
            for image_filename in exam_dict['image_file']:
                image_base64 = get_image_base64(image_filename)
                if image_base64:
                    image_data_list.append({
                        'filename': image_filename,
                        'data': image_base64
                    })
            exam_dict['images'] = image_data_list
        
        exam_list.append(exam_dict)
 
    return jsonify({'token': refresh_token(token), 'exams': exam_list}), 200


@quiz_bp.route('/get-exam-filters', methods=['POST', 'OPTIONS'])
def get_exam_filters():
    """獲取考題篩選選項（輕量級，不包含題目內容和圖片）"""
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供token', 'code': 'NO_TOKEN'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        user_email = decoded_token.get('user')
        
        if not user_email:
            return jsonify({'token': None, 'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({'token': None, 'message': 'Token已過期，請重新登錄', 'code': 'TOKEN_EXPIRED'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'token': None, 'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except Exception as e:
        print(f"驗證token時發生錯誤: {str(e)}")
        return jsonify({'token': None, 'message': '認證失敗', 'code': 'AUTH_FAILED'}), 401
    
    try:
        # 只查詢需要的欄位，不包含題目內容和圖片
        examdata = mongo.db.exam.find(
            {},
            {
                'school': 1,
                'department': 1,
                'year': 1,
                'key-points': 1,
                '_id': 0
            }
        )
        
        # 使用集合來去重並收集資料
        schools = set()
        departments = set()
        years = set()
        subjects = set()
        subject_count_map = {}
        
        # 統計每個學校-年度-系所組合的題目數量
        school_year_dept_count = {}
        
        for exam in examdata:
            # 收集學校
            if exam.get('school'):
                schools.add(exam.get('school'))
            
            # 收集系所
            if exam.get('department'):
                departments.add(exam.get('department'))
            
            # 收集年度
            if exam.get('year'):
                years.add(str(exam.get('year')))
            
            # 收集知識點/科目
            key_points = exam.get('key-points', [])
            if isinstance(key_points, list):
                for subject in key_points:
                    if subject and subject != '其他':
                        subjects.add(subject)
                        subject_count_map[subject] = subject_count_map.get(subject, 0) + 1
            elif key_points and key_points != '其他':
                subjects.add(key_points)
                subject_count_map[key_points] = subject_count_map.get(key_points, 0) + 1
            
            # 統計學校-年度-系所組合的題目數量
            school = exam.get('school', '')
            year = str(exam.get('year', ''))
            dept = exam.get('department', '')
            if school and year and dept:
                key = f"{school}|{year}|{dept}"
                school_year_dept_count[key] = school_year_dept_count.get(key, 0) + 1
        
        # 轉換為排序後的列表
        result = {
            'token': refresh_token(token),
            'filters': {
                'schools': sorted(list(schools)),
                'departments': sorted(list(departments)),
                'years': sorted(list(years)),
                'subjects': sorted(list(subjects)),
                'subject_counts': subject_count_map,
                'school_year_dept_counts': school_year_dept_count
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"獲取篩選選項時發生錯誤: {str(e)}")
        return jsonify({'token': refresh_token(token), 'message': '獲取篩選選項失敗', 'error': str(e)}), 500


@quiz_bp.route('/grading-progress/<template_id>', methods=['GET', 'OPTIONS'])
def get_grading_progress(template_id):
    """獲取測驗批改進度 API"""
    if request.method == 'OPTIONS':
        return jsonify({'token': None, 'message': 'CORS preflight'}), 200
    
    try:
        # 驗證用戶身份
        token = request.headers.get('Authorization').split(" ")[1]
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        # 檢查測驗狀態
        with sqldb.engine.connect() as conn:
            template_id_int = int(template_id)
            
            # 檢查是否有完成的測驗記錄
            history_result = conn.execute(text("""
                SELECT id, status, correct_count, wrong_count, accuracy_rate, average_score, total_questions, answered_questions
                FROM quiz_history 
                WHERE quiz_template_id = :template_id AND user_email = :user_email
                ORDER BY created_at DESC LIMIT 1
            """), {
                'template_id': template_id_int,
                'user_email': user_email
            }).fetchone()
            
            if history_result and history_result[1] == 'completed':
                # 測驗已完成，返回完整結果
                total_questions = history_result[6]
                answered_questions = history_result[7]
                unanswered_questions = total_questions - answered_questions
                    
                return jsonify({
                    'token': refresh_token(token),
                    'success': True,
                        'status': 'completed',
                        'data': {
                            'quiz_history_id': history_result[0],
                            'correct_count': history_result[2],
                            'wrong_count': history_result[3],
                            'unanswered_count': unanswered_questions,
                            'accuracy_rate': float(history_result[4]) if history_result[4] else 0,
                            'average_score': float(history_result[5]) if history_result[5] else 0,
                            'grading_stages': [
                                {'stage': 1, 'name': '試卷批改', 'status': 'completed', 'description': '獲取題目數據完成'},
                                {'stage': 2, 'name': '計算分數', 'status': 'completed', 'description': '題目分類完成'},
                                {'stage': 3, 'name': '評判知識點', 'status': 'completed', 'description': 'AI評分完成'},
                                {'stage': 4, 'name': '生成學習計畫', 'status': 'completed', 'description': '統計完成'}
                            ]
                        }
                    })
            else:
                # 測驗進行中，返回進度狀態
                return jsonify({
                    'token': refresh_token(token),
                    'success': True,
                    'status': 'in_progress',
                    'data': {
                        'grading_stages': [
                            {'stage': 1, 'name': '試卷批改', 'status': 'in_progress', 'description': '正在獲取題目數據...'},
                            {'stage': 2, 'name': '計算分數', 'status': 'pending', 'description': '等待開始'},
                            {'stage': 3, 'name': '評判知識點', 'status': 'pending', 'description': '等待開始'},
                            {'stage': 4, 'name': '生成學習計畫', 'status': 'pending', 'description': '等待開始'}
                        ]
                    }
                })
                
    except Exception as e:
        print(f"❌ 獲取批改進度時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取批改進度失敗: {str(e)}'}), 500


@quiz_bp.route('/quiz-progress/<progress_id>', methods=['GET'])
def get_quiz_progress(progress_id):
    """獲取測驗進度 API - 用於前端實時查詢進度"""
    try:

        # 解析progress_id獲取用戶信息
        if not progress_id.startswith('progress_'):
            return jsonify({'error': '無效的進度ID'}), 400
        
        # 模擬進度狀態（實際應該從數據庫獲取）
        progress_data = {
            'progress_id': progress_id,
            'current_stage': 3,  # 當前階段：1=試卷批改, 2=計算分數, 3=評判知識點, 4=生成學習計畫
            'total_stages': 4,
            'stage_name': '評判知識點',
            'stage_description': 'AI正在進行智能評分...',
            'progress_percentage': 75,  # 75%完成
            'is_completed': False,
            'estimated_time_remaining': 30,  # 預計剩餘時間（秒）
            'last_updated': time.time()
        }
        
        return jsonify({
            'success': True,
            'data': progress_data
        })
        
    except Exception as e:
        print(f"❌ 獲取進度失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取進度失敗: {str(e)}'
        }), 500


@quiz_bp.route('/quiz-progress-sse/<progress_id>', methods=['GET'])
def quiz_progress_sse(progress_id):
    """測驗進度 Server-Sent Events API - 實時推送進度更新"""
    def generate_progress_events():
        # 設置SSE headers
        yield 'data: {"type": "connected", "message": "進度追蹤已連接"}\n\n'
        
        # 檢查進度追蹤狀態
        progress_status = get_progress_status(progress_id)
        
        if progress_status and progress_status.get('is_completed'):
            # 如果AI批改已經完成，直接發送完成消息
            completion_data = {
                'type': 'completion',
                'message': 'AI批改完成！',
                'progress_percentage': 100,
                'is_completed': True,
                'timestamp': time.time()
            }
            yield f'data: {json.dumps(completion_data, ensure_ascii=False)}\n\n'
            return
        
        # 如果還沒完成，發送當前進度
        current_stage = progress_status.get('current_stage', 1) if progress_status else 1
        stage_descriptions = {
            1: '正在獲取題目數據...',
            2: '正在分類題目...',
            3: 'AI正在進行智能評分...',
            4: '正在統計結果...'
        }
        
        progress_data = {
            'type': 'progress_update',
            'current_stage': current_stage,
            'stage_description': stage_descriptions.get(current_stage, '處理中...'),
            'progress_percentage': (current_stage / 4) * 100,
            'is_completed': False,
            'timestamp': time.time()
        }
        
        yield f'data: {json.dumps(progress_data, ensure_ascii=False)}\n\n'
        
        # 等待一下，然後檢查是否完成
        time.sleep(1)
        
        # 再次檢查完成狀態
        progress_status = get_progress_status(progress_id)
        if progress_status and progress_status.get('is_completed'):
            completion_data = {
                'type': 'completion',
                'message': 'AI批改完成！',
                'progress_percentage': 100,
                'is_completed': True,
                'timestamp': time.time()
            }
            yield f'data: {json.dumps(completion_data, ensure_ascii=False)}\n\n'
    # 設置SSE響應headers
    response = Response(
        generate_progress_events(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )
    
    return response

@quiz_bp.route('/get-long-answer/<answer_id>', methods=['GET'])
def get_long_answer(answer_id: str):

        # 驗證用戶身份
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': '缺少授權token'}), 401
    
    user_email = verify_token(token.split(" ")[1])
    if not user_email:
        return jsonify({'error': '無效的token'}), 401
    
    # 解析答案ID
    if not answer_id.startswith('LONG_ANSWER_'):
        return jsonify({'error': '無效的答案ID格式'}), 400
    
    long_answer_id = int(answer_id.replace('LONG_ANSWER_', ''))
    
    # 從數據庫獲取長答案
    with sqldb.engine.connect() as conn:
        result = conn.execute(text("""
            SELECT la.full_answer, la.question_type, la.created_at,
                    qh.template_id, qh.user_email
            FROM long_answers la
            JOIN quiz_history qh ON la.quiz_history_id = qh.id
            WHERE la.id = :long_answer_id
        """), {
            'long_answer_id': long_answer_id
        }).fetchone()
        
        if not result:
            return jsonify({'error': '答案不存在'}), 404
        
        # 驗證用戶權限（只能查看自己的答案）
        if result.user_email != user_email:
            return jsonify({'error': '無權限查看此答案'}), 403
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'data': {
                'full_answer': result.full_answer,
                'question_type': result.question_type,
                'created_at': result.created_at.isoformat() if result.created_at else None,
                'template_id': result.template_id
            }
        })

@quiz_bp.route('/get-quiz-from-database', methods=['POST', 'OPTIONS'])
def get_quiz_from_database_endpoint():

    if request.method == 'OPTIONS':
        return jsonify({'token': None, 'success': True}), 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供token'}), 401
    
    token = auth_header.split(" ")[1]
    data = request.get_json()
    quiz_ids = data.get('quiz_ids', [])
    
    if not quiz_ids:
        return jsonify({
            'success': False,
            'message': '缺少考卷ID'
        }), 400
    
    # 調用獲取考卷數據函數
    result = get_quiz_from_database(quiz_ids)
    
    return jsonify({'token': refresh_token(token), 'data': result})

@quiz_bp.route('/get-quiz/<quiz_id>', methods=['GET', 'OPTIONS'])
def get_quiz(quiz_id):
    """獲取單個測驗數據"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 204
    
    try:
        logger.info(f"收到獲取測驗請求: {quiz_id}")
        
        # 直接調用get_quiz_from_database函數
        result = get_quiz_from_database([quiz_id])
        
        logger.info(f"get_quiz_from_database結果: {result.get('success', False)}")
        
        if result.get('success'):
            data = result.get('data', {})
            questions = data.get('questions', [])
            logger.info(f"找到測驗，題目數量: {len(questions)}")
            
            return jsonify({
                'success': True,
                'data': {
                    'quiz_id': quiz_id,
                    'template_id': quiz_id,
                    'title': data.get('quiz_info', {}).get('title', ''),
                    'questions': questions,
                    'time_limit': data.get('time_limit', 60),
                    'total_questions': len(questions),
                    'quiz_info': data.get('quiz_info', {})
                }
            })
        else:
            logger.warning(f"找不到測驗: {result.get('message', '未知錯誤')}")
            return jsonify({
                'success': False,
                'error': result.get('message', '找不到測驗')
            }), 404
            
    except Exception as e:
        logger.error(f"獲取測驗失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取測驗失敗: {str(e)}'
        }), 500
