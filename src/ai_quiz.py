from flask import jsonify, request, Blueprint, current_app
from accessories import mongo
from src.api import verify_token
import json
from datetime import datetime
from bson.objectid import ObjectId
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
from src.ai_teacher import get_quiz_from_database
import time
import hashlib
import json
import logging
from typing import List


# 創建 AI 測驗藍圖
ai_quiz_bp = Blueprint('ai_quiz', __name__)


logger = logging.getLogger(__name__)


@ai_quiz_bp.route('/submit-quiz', methods=['POST', 'OPTIONS'])
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
    if not template_id:
        return jsonify({'success': False, 'message': '缺少考卷模板ID'}), 400
    progress_id = f"progress_{user_email}_{int(time.time())}"
    # 階段1: 試卷批改 - 獲取題目數據
    # 更新進度狀態為第1階段
    update_progress_status(progress_id, False, 1, "正在獲取題目數據...")
    with sqldb.engine.connect() as conn:
        # 檢查是否為AI模板ID格式
        if isinstance(template_id, str) and template_id.startswith('ai_template_'):
            # 如果是AI模板，嘗試從前端發送的題目數據中獲取信息
            if frontend_questions and len(frontend_questions) > 0:
                print("✅ 使用AI模板，從前端題目數據獲取信息")
                # 創建一個模擬的模板對象
                template = type('Template', (), {
                    'question_ids': json.dumps([q.get('original_exam_id', '') for q in frontend_questions if q.get('original_exam_id')]),
                    'template_type': 'knowledge'  # 使用knowledge類型，避免資料庫錯誤
                })()
                question_ids = [q.get('original_exam_id', '') for q in frontend_questions if q.get('original_exam_id')]
                total_questions = len(frontend_questions)
                quiz_type = 'knowledge'  # 使用現有的類型，避免資料庫錯誤
            else:
                return jsonify({
                    'success': False,
                    'message': 'AI模板需要前端題目數據'
                }), 400
        else:
            # 傳統數字ID模板
            try:
                template_id_int = int(template_id)
                template = conn.execute(text("""
                    SELECT * FROM quiz_templates WHERE id = :template_id
                """), {'template_id': template_id_int}).fetchone()
                
                if not template:
                    return jsonify({
                        'success': False,
                        'message': '考卷模板不存在'
                    }), 404
                
                # 從模板獲取題目ID列表
                question_ids = json.loads(template.question_ids)
                total_questions = len(question_ids)
                quiz_type = 'knowledge'  # 強制使用knowledge類型，避免資料庫錯誤
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': '無效的模板ID格式'
                }), 400
        
        # 從模板獲取題目數量
        
        # 優先使用前端發送的題目數據，如果沒有則從MongoDB獲取
        if frontend_questions and len(frontend_questions) > 0:
            print("✅ 使用前端發送的題目數據")
            questions = frontend_questions
        else:
            print("🔄 從MongoDB獲取題目數據")
            # 從MongoDB exam集合獲取題目詳情
            questions = []
            for i, question_id in enumerate(question_ids):
                # 嘗試使用ObjectId查詢
                exam_question = mongo.db.exam.find_one({"_id": ObjectId(question_id)})
                if not exam_question:
                    # 如果ObjectId查詢失敗，嘗試直接查詢
                    exam_question = mongo.db.exam.find_one({"_id": question_id})
                
                if exam_question:
                    # 正確讀取題目類型
                    exam_type = exam_question.get('type', 'single')
                    if exam_type == 'group':
                        # 如果是題組，讀取子題目的answer_type
                        sub_questions = exam_question.get('sub_questions', [])
                        if sub_questions:
                            # 使用第一個子題目的類型
                            question_type = sub_questions[0].get('answer_type', 'single-choice')
                        else:
                            question_type = 'single-choice'
                    else:
                        # 如果是單題，直接讀取answer_type
                        question_type = exam_question.get('answer_type', 'single-choice')
                    
                    question = {
                        'id': i + 1,
                        'question_text': exam_question.get('question_text', ''),
                        'type': question_type,  # 使用正確的題目類型
                        'options': exam_question.get('options', []),
                        'correct_answer': exam_question.get('answer', ''),
                        'original_exam_id': str(exam_question.get('_id', '')),
                        'image_file': exam_question.get('image_file', ''),
                        'key_points': exam_question.get('key-points', '')
                    }
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
    print("🔄 階段2: 計算分數 - 分類題目")
    
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
        
        if user_answer:  # 只處理有答案的題目
            # 獲取作答時間（秒數）
            answer_time_seconds = question_answer_times.get(str(i), 0)
            
            # 調試日誌
            print(f"🔍 Debug: 題目 {i} - answer_time_seconds: {answer_time_seconds}")
            
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
                'question_type': question.get('type', '')
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
            ai_questions_data.append({
                'question_id': question.get('original_exam_id', ''),
                'user_answer': user_answer,  # 使用原始完整答案
                'question_type': question_type,
                'question_text': question.get('question_text', ''),
                'options': question.get('options', []),
                'correct_answer': question.get('correct_answer', ''),
                'key_points': question.get('key_points', '')
            })
        
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
                wrong_questions.append({
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
                })
            
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
    
    # 啟用 SQL 資料庫操作，建立與MongoDB的關聯
    # 更新或創建SQL記錄
    with sqldb.engine.connect() as conn:
        # 根據模板類型決定quiz_template_id
        if isinstance(template_id, str) and template_id.startswith('ai_template_'):
            quiz_template_id = None  # AI模板不需要SQL模板ID
        else:
            quiz_template_id = template_id_int  # 傳統模板使用數字ID
        
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
            
            # 獲取AI評分結果
            ai_result = q_data.get('ai_result', {})
            is_correct = ai_result.get('is_correct', False)
            score = ai_result.get('score', 0)
            feedback = ai_result.get('feedback', {})
            
            # 獲取作答時間（秒數）
            answer_time_seconds = q_data.get('answer_time_seconds', 0)
            
            # 調試日誌
            print(f"🔍 Debug: 保存題目 {i} - answer_time_seconds: {answer_time_seconds}")
            
            # 構建用戶答案資料
            answer_data = {
                'answer': user_answer,
                'feedback': feedback  # 使用AI批改的feedback
            }
            
            # 使用新的長答案存儲方法，保持數據完整性
            stored_answer = _store_long_answer(user_answer, 'unknown', quiz_history_id, question_id, user_email)
            
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
        'success': True,
        'message': '測驗提交成功',
        'data': {
            'template_id': template_id,  # 返回模板ID
            'quiz_history_id': f'quiz_history_{template_id}',  # 返回測驗歷史記錄ID（使用模板ID）
            'result_id': f'result_{template_id}',  # 返回結果ID（用於前端跳轉）
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
        
        # 啟用 SQL 操作，存儲長答案到專門的表中
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


@ai_quiz_bp.route('/get-drawing-answer/<quiz_history_id>/<question_id>', methods=['GET', 'OPTIONS'])
def get_drawing_answer(quiz_history_id, question_id):
    """根據測驗歷史ID和題目ID獲取繪圖答案"""
    try:
        # 處理CORS預檢請求
        if request.method == 'OPTIONS':
            return '', 200
        
        with sqldb.engine.connect() as conn:
            # 首先從 quiz_answers 表查詢
            answer_result = conn.execute(text("""
                SELECT user_answer FROM quiz_answers 
                WHERE quiz_history_id = :quiz_history_id AND mongodb_question_id = :question_id
            """), {
                'quiz_history_id': int(quiz_history_id),
                'question_id': question_id
            }).fetchone()
            
            if answer_result:
                user_answer = answer_result[0]
                
                # 檢查是否為長答案引用
                if isinstance(user_answer, str) and user_answer.startswith('LONG_ANSWER_'):
                    # 從 long_answers 表查詢完整答案
                    long_answer_id = user_answer.replace('LONG_ANSWER_', '')
                    long_answer_result = conn.execute(text("""
                        SELECT full_answer FROM long_answers 
                        WHERE id = :long_answer_id
                    """), {
                        'long_answer_id': int(long_answer_id)
                    }).fetchone()
                    
                    if long_answer_result:
                        return jsonify({
                            'success': True,
                            'drawing_answer': long_answer_result[0],
                            'source': 'long_answers_table'
                        })
                
                # 直接返回答案
                return jsonify({
                    'success': True,
                    'drawing_answer': user_answer,
                    'source': 'quiz_answers_table'
                })
            
            return jsonify({
                'success': False,
                'message': '找不到繪圖答案'
            }), 404
            
    except Exception as e:
        print(f"❌ 查詢繪圖答案失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'查詢失敗: {str(e)}'
        }), 500

@ai_quiz_bp.route('/get-quiz-result/<result_id>', methods=['GET', 'OPTIONS'])
def get_quiz_result(result_id):
    """根據結果ID獲取測驗結果 API - 優化版本"""
    if request.method == 'OPTIONS':
        return jsonify({'token': None, 'success': True}), 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供token'}), 401
    
    token = auth_header.split(" ")[1]
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
                    question_detail = {
                        'question_text': exam_question.get('question_text', ''),
                        'options': exam_question.get('options', []),
                        'correct_answer': exam_question.get('answer', ''),
                        'image_file': exam_question.get('image_file', ''),
                        'key_points': exam_question.get('key-points', '')
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
            question_info = {
                'question_id': question_id_str,
                'question_index': i,
                'question_text': question_detail.get('question_text', ''),
                'options': question_detail.get('options', []),
                'correct_answer': question_detail.get('correct_answer', ''),
                'image_file': question_detail.get('image_file', ''),
                'key_points': question_detail.get('key_points', ''),
                'is_correct': answer_info.get('is_correct', False),
                'is_marked': False,  # 目前沒有標記功能
                'user_answer': answer_info.get('user_answer', {}).get('answer', ''),
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

@ai_quiz_bp.route('/create-quiz', methods=['POST', 'OPTIONS'])
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
                return jsonify({'message': '缺少知識點參數'}), 400
            
            # 從MongoDB獲取符合條件的考題
            query = {"主要學科": topic}
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
                return jsonify({'message': '考古題測驗必須填寫學校、年份、系所'}), 400
            

            # 從MongoDB獲取符合條件的考古題
            query = {
                "school": school,
                "year": year,
                "department": department
            }
            selected_exams = list(mongo.db.exam.find(query))
            
            if not selected_exams:
                print(f"❌ 找不到符合條件的考題: {query}")
                return jsonify({'message': '找不到符合條件的考題'}), 404
            
            quiz_title = f"{school} - {year}年 - {department}"

        else:
            return jsonify({'message': '無效的測驗類型'}), 400
        
        # 轉換為標準化的題目格式
        questions = []
        for i, exam in enumerate(selected_exams):
            # 正確讀取題目類型
            exam_type = exam.get('type', 'single')
            if exam_type == 'group':
                # 如果是題組，讀取子題目的answer_type
                sub_questions = exam.get('sub_questions', [])
                if sub_questions:
                    # 使用第一個子題目的類型
                    question_type = sub_questions[0].get('answer_type', 'single-choice')
                else:
                    question_type = 'single-choice'
            else:
                # 如果是單題，直接讀取answer_type
                question_type = exam.get('answer_type', 'single-choice')
            
            question = {
                'id': i + 1,
                'question_text': exam.get('question_text', ''),
                'type': question_type,  # 使用正確的題目類型
                'options': exam.get('options'),
                'correct_answer': exam.get('answer', ''),
                'original_exam_id': str(exam.get('_id', '')),
                'image_file': exam.get('image_file'),
                'key_points': exam.get('key-points', ''),
                'answer_type': question_type,  # 添加答案類型
                'detail_answer': exam.get('detail-answer', '')  # 添加詳解
            }
            
            # 處理選項格式
            if isinstance(question['options'], str):
                question['options'] = [opt.strip() for opt in question['options'].split(',') if opt.strip()]
            elif not isinstance(question['options'], list):
                question['options'] = []
            
            # 處理圖片檔案
            image_file = exam.get('image_file', '')
            image_filename = ''  # 初始化變數
            
            if image_file and image_file not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']:
                # 處理圖片文件列表
                if isinstance(image_file, list) and len(image_file) > 0:
                    question['image_file'] = image_file[0]  # 取第一張圖片
                elif isinstance(image_file, str):
                    # 如果是字符串，直接使用
                    image_filename = image_file
                else:
                    # 其他情況，設為空字符串
                    image_filename = ''
                
                # 檢查圖片檔案是否存在
                if image_filename:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    image_path = os.path.join(current_dir, 'picture', image_filename)
                    if os.path.exists(image_path):
                        question['image_file'] = image_filename
                    else:
                        question['image_file'] = ''
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
                            quiz_type VARCHAR(50) NOT NULL,
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
        return jsonify({'message': f'創建測驗失敗: {str(e)}'}), 500

def get_image_base64(image_filename):
    """讀取圖片檔案並轉換為 base64 編碼"""
    try:
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

@ai_quiz_bp.route('/get-exam', methods=['POST', 'OPTIONS'])
def get_exam():
    """獲取所有考題數據"""
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return jsonify({'message': '未提供token', 'code': 'NO_TOKEN'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        user_email = decoded_token.get('user')
        
        if not user_email:
            return jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token已過期，請重新登錄', 'code': 'TOKEN_EXPIRED'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except Exception as e:
        print(f"驗證token時發生錯誤: {str(e)}")
        return jsonify({'message': '認證失敗', 'code': 'AUTH_FAILED'}), 401
    
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
                    'key_points': exam.get('key-points'),
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
 
    return jsonify({'exams': exam_list}), 200


@ai_quiz_bp.route('/grading-progress/<template_id>', methods=['GET', 'OPTIONS'])
def get_grading_progress(template_id):
    """獲取測驗批改進度 API"""
    if request.method == 'OPTIONS':
        return jsonify({'token': None, 'success': True}), 204
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'token': None, 'message': '未提供token'}), 401
    
    token = auth_header.split(" ")[1]
    
    try:
        user_email = get_user_info(token, 'email')
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        # 檢查測驗狀態
        # 檢查是否為AI模板ID格式
        if isinstance(template_id, str) and template_id.startswith('ai_template_'):
            # AI模板無法從SQL資料庫查詢，返回進行中狀態
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
        
        # 傳統數字ID模板
        try:
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
                    
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': '無效的模板ID格式'
            }), 400
                
    except Exception as e:
        print(f"❌ 獲取批改進度時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取批改進度失敗: {str(e)}'}), 500


@ai_quiz_bp.route('/quiz-progress/<progress_id>', methods=['GET'])
def get_quiz_progress(progress_id):
    """獲取測驗進度 API - 用於前端實時查詢進度"""
    try:
        # 這裡應該從數據庫或緩存中獲取實際進度
        # 目前先返回模擬進度，後續可以實現真實的進度追蹤
        
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


@ai_quiz_bp.route('/quiz-progress-sse/<progress_id>', methods=['GET'])
def quiz_progress_sse(progress_id):
    """測驗進度 Server-Sent Events API - 實時推送進度更新"""
    def generate_progress_events():
        """生成進度事件流"""
        try:
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
                    
        except Exception as e:
            error_data = {
                'type': 'error',
                'message': f'進度追蹤錯誤: {str(e)}',
                'timestamp': time.time()
            }
            yield f'data: {json.dumps(error_data, ensure_ascii=False)}\n\n'
    
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

@ai_quiz_bp.route('/get-long-answer/<answer_id>', methods=['GET'])
def get_long_answer(answer_id: str):
    """獲取長答案的完整內容"""
    try:
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
            
    except Exception as e:
        print(f"❌ 獲取長答案失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取長答案失敗: {str(e)}'
        }), 500

@ai_quiz_bp.route('/get-quiz-from-database', methods=['POST', 'OPTIONS'])
def get_quiz_from_database_endpoint():
    """從資料庫獲取考卷數據"""
    try:
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
        
        # 直接返回結果，因為 result 已經包含了 success 和 data 字段
        return jsonify({
            'token': refresh_token(token),
            'success': result.get('success', False),
            'data': result.get('data'),
            'message': result.get('message', '')
        })
        
    except Exception as e:
        logger.error(f"❌ 獲取考卷數據失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取考卷數據失敗：{str(e)}'
        }), 500

@ai_quiz_bp.route('/get-latest-quiz', methods=['GET', 'OPTIONS'])
def get_latest_quiz():
    """從資料庫獲取最新的考卷數據"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True}), 204
        
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'token': None, 'message': '未提供token'}), 401
        
        token = auth_header.split(" ")[1]
        
        # 從 MongoDB 獲取最新考卷數據
        if mongo is None or mongo.db is None:
            return jsonify({'success': False, 'error': '資料庫連接不可用'}), 500
        
        # 查詢最新的考卷數據
        questions_collection = mongo.db.questions
        
        # 按創建時間降序排列，獲取最新的考卷
        latest_questions = list(questions_collection.find().sort('created_at', -1).limit(10))
        
        if not latest_questions:
            return jsonify({'success': False, 'error': '資料庫中沒有考卷數據'}), 404
        
        # 按 quiz_id 分組
        quiz_groups = {}
        for question in latest_questions:
            quiz_id = question.get('quiz_id', 'unknown')
            if quiz_id not in quiz_groups:
                quiz_groups[quiz_id] = []
            quiz_groups[quiz_id].append(question)
        
        # 獲取題目最多的考卷（通常是最完整的）
        latest_quiz_id = max(quiz_groups.keys(), key=lambda k: len(quiz_groups[k]))
        questions = quiz_groups[latest_quiz_id]
        
        # 構建考卷數據
        quiz_info = {
            'quiz_id': latest_quiz_id,
            'template_id': f"template_{latest_quiz_id}",
            'title': f"AI生成測驗 - {latest_quiz_id}",
            'topic': questions[0].get('topic', '未知'),
            'difficulty': questions[0].get('difficulty', 'medium'),
            'question_count': len(questions),
            'time_limit': 30,  # 預設30分鐘
            'total_score': len(questions) * 10  # 預設每題10分
        }
        
        quiz_data = {
            'quiz_id': latest_quiz_id,
            'template_id': quiz_info['template_id'],
            'quiz_info': quiz_info,
            'questions': questions
        }
        
        logger.info(f"✅ 成功獲取最新考卷: {latest_quiz_id}, 題目數量: {len(questions)}")
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'data': quiz_data
        })
        
    except Exception as e:
        logger.error(f"❌ 獲取最新考卷數據失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取最新考卷數據失敗：{str(e)}'
        }), 500

@ai_quiz_bp.route('/get-user-submissions-analysis', methods=['POST', 'OPTIONS'])
def get_user_submissions_analysis():
    """獲取用戶提交分析數據 - 使用SQL表結構"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True})
        
        # 驗證用戶身份
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少授權token'}), 401
        
        user_email = verify_token(token.split(" ")[1])
        if not user_email:
            return jsonify({'error': '無效的token'}), 401
        
        print(f"🔍 開始獲取用戶 {user_email} 的提交分析數據")
        
        # 從SQL資料庫獲取用戶的測驗歷史記錄
        with sqldb.engine.connect() as conn:
            # 獲取用戶的所有測驗記錄
            history_results = conn.execute(text("""
                SELECT id, quiz_template_id, quiz_type, total_questions, answered_questions,
                       correct_count, wrong_count, accuracy_rate, average_score, 
                       total_time_taken, submit_time, status, created_at
                FROM quiz_history 
                WHERE user_email = :user_email
                ORDER BY created_at DESC
            """), {
                'user_email': user_email
            }).fetchall()
            
            print(f"🔍 從SQL找到 {len(history_results)} 條測驗記錄")
            
            # 處理每條測驗記錄
            processed_submissions = []
            for history_record in history_results:
                quiz_history_id = history_record[0]
                quiz_template_id = history_record[1]
                quiz_type = history_record[2]
                total_questions = history_record[3]
                answered_questions = history_record[4]
                correct_count = history_record[5]
                wrong_count = history_record[6]
                accuracy_rate = float(history_record[7]) if history_record[7] else 0
                average_score = float(history_record[8]) if history_record[8] else 0
                total_time_taken = history_record[9] if history_record[9] else 0
                submit_time = history_record[10]
                status = history_record[11]
                created_at = history_record[12]
                
                # 獲取該測驗的詳細答案信息
                answers_result = conn.execute(text("""
                    SELECT mongodb_question_id, user_answer, is_correct, score, 
                           feedback, answer_time_seconds, created_at
                    FROM quiz_answers 
                    WHERE quiz_history_id = :quiz_history_id
                    ORDER BY created_at
                """), {
                    'quiz_history_id': quiz_history_id
                }).fetchall()
                
                # 處理答案數據
                answers = []
                for answer_record in answers_result:
                    mongodb_question_id = answer_record[0]
                    user_answer = answer_record[1]
                    is_correct = answer_record[2]
                    score = float(answer_record[3]) if answer_record[3] else 0
                    feedback = json.loads(answer_record[4]) if answer_record[4] else {}
                    answer_time_seconds = answer_record[5] if answer_record[5] else 0
                    answer_created_at = answer_record[6]
                    
                    # 嘗試從MongoDB獲取題目詳情
                    question_detail = {}
                    try:
                        if mongodb_question_id and len(mongodb_question_id) == 24:
                            exam_question = mongo.db.exam.find_one({"_id": ObjectId(mongodb_question_id)})
                        else:
                            exam_question = mongo.db.exam.find_one({"_id": mongodb_question_id})
                        
                        if exam_question:
                            question_detail = {
                                'question_text': exam_question.get('question_text', ''),
                                'topic': exam_question.get('主要學科', 'unknown'),
                                'chapter': exam_question.get('章節', 'unknown'),
                                'options': exam_question.get('options', []),
                                'correct_answer': exam_question.get('answer', ''),
                                'image_file': exam_question.get('image_file', '')
                            }
                    except Exception as e:
                        print(f"⚠️ 獲取題目詳情失敗: {e}")
                        question_detail = {
                            'question_text': f'題目 {mongodb_question_id}',
                            'topic': 'unknown',
                            'chapter': 'unknown',
                            'options': [],
                            'correct_answer': '',
                            'image_file': ''
                        }
                    
                    # 構建答案對象
                    answer_obj = {
                        'question_id': mongodb_question_id,
                        'question_text': question_detail.get('question_text', ''),
                        'topic': question_detail.get('topic', 'unknown'),
                        'chapter': question_detail.get('chapter', 'unknown'),
                        'user_answer': user_answer,
                        'is_correct': is_correct,
                        'score': score,
                        'feedback': feedback,
                        'answer_time_seconds': answer_time_seconds,
                        'answer_time': answer_created_at.isoformat() if answer_created_at else None,
                        'options': question_detail.get('options', []),
                        'correct_answer': question_detail.get('correct_answer', ''),
                        'image_file': question_detail.get('image_file', '')
                    }
                    answers.append(answer_obj)
                
                # 構建提交記錄對象
                processed_submission = {
                    'submission_id': f"quiz_{quiz_history_id}",
                    'quiz_history_id': quiz_history_id,
                    'quiz_template_id': quiz_template_id,
                    'quiz_type': quiz_type,
                    'submit_time': submit_time.isoformat() if submit_time else None,
                    'created_at': created_at.isoformat() if created_at else None,
                    'total_questions': total_questions,
                    'answered_questions': answered_questions,
                    'unanswered_questions': total_questions - answered_questions,
                    'correct_count': correct_count,
                    'wrong_count': wrong_count,
                    'accuracy_rate': accuracy_rate,
                    'average_score': average_score,
                    'total_time_taken': total_time_taken,
                    'status': status,
                    'answers': answers
                }
                
                processed_submissions.append(processed_submission)
                
                print(f"🔍 處理測驗記錄 {quiz_history_id}: {quiz_type}, 正確率: {accuracy_rate:.1f}%")
        
        print(f"✅ 成功處理 {len(processed_submissions)} 條提交記錄")
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'submissions': processed_submissions,
            'total_submissions': len(processed_submissions)
        })
        
    except Exception as e:
        print(f"❌ 獲取用戶提交分析失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取用戶提交分析失敗：{str(e)}'
        }), 500


@ai_quiz_bp.route('/generate-guided-learning-session', methods=['POST', 'OPTIONS'])
def generate_guided_learning_session():
    """生成AI引導學習會話 API"""
    print(f"🚀 進入 generate-guided-learning-session 函數")
    print(f"🔍 請求方法: {request.method}")
    
    if request.method == 'OPTIONS':
        print(f"✅ 處理 OPTIONS 請求，返回 CORS 預檢響應")
        return jsonify({'token': None, 'message': 'CORS preflight'}), 200
    
    try:
        print(f"🔍 開始處理 POST 請求")
        
        # 驗證用戶身份
        token = request.headers.get('Authorization')
        print(f"🔍 Authorization header: {token}")
        
        if not token:
            print(f"❌ 缺少授權token")
            return jsonify({'error': '缺少授權token'}), 401
        
        user_email = verify_token(token.split(" ")[1])
        print(f"🔍 驗證後的 user_email: {user_email}")
        
        if not user_email:
            print(f"❌ 無效的token")
            return jsonify({'error': '無效的token'}), 401
        
        # 獲取請求數據
        data = request.get_json()
        print(f"🔍 請求數據: {data}")
        
        submission_id = data.get('question_id')  # 實際上是 submission_id
        session_type = data.get('session_type', 'general')  # general, mistake_review, concept_explanation
        
        print(f"🔍 提取的 submission_id: {submission_id}")
        print(f"🔍 提取的 session_type: {session_type}")
        
        if not submission_id:
            print(f"❌ 缺少提交記錄ID")
            return jsonify({
                'success': False,
                'message': '缺少提交記錄ID'
            }), 400
        
        print(f"🔍 開始查找 submission_id: {submission_id}")
        
        # 檢查 submission_id 格式，支援 AI 測驗的 MongoDB ObjectId
        if submission_id.startswith('quiz_'):
            # 如果是 quiz_ 格式，提取 quiz_history_id (傳統測驗)
            try:
                quiz_history_id = int(submission_id.replace('quiz_', ''))
                print(f"🔍 提取的 quiz_history_id: {quiz_history_id}")
                is_ai_quiz = False
            except ValueError:
                print(f"❌ 無效的 quiz_history_id 格式: {submission_id}")
                return jsonify({
                    'success': False,
                    'message': f'無效的提交記錄ID格式: {submission_id}'
                }), 400
        elif len(submission_id) == 24 and submission_id.isalnum():
            # 如果是 24 位十六進制字符串，視為 MongoDB ObjectId (AI 測驗)
            print(f"🔍 檢測到 MongoDB ObjectId 格式: {submission_id}")
            is_ai_quiz = True
        else:
            # 嘗試直接作為 quiz_history_id 使用 (傳統測驗)
            try:
                quiz_history_id = int(submission_id)
                print(f"🔍 直接使用 quiz_history_id: {quiz_history_id}")
                is_ai_quiz = False
            except ValueError:
                print(f"❌ 無效的提交記錄ID格式: {submission_id}")
                return jsonify({
                    'success': False,
                    'message': f'無效的提交記錄ID格式: {submission_id}'
                }), 400
        
        # 根據測驗類型選擇不同的數據源
        if is_ai_quiz:
            # AI 測驗：從 MongoDB 獲取提交記錄
            print(f"🔍 從 MongoDB 查詢 AI 測驗提交記錄: {submission_id}")
            
            if mongo is None or mongo.db is None:
                print(f"❌ MongoDB 連接不可用")
                return jsonify({
                    'success': False,
                    'message': '資料庫連接不可用'
                }), 500
            
            # 從 submissions 集合獲取提交記錄
            submission_doc = mongo.db.submissions.find_one({"_id": ObjectId(submission_id)})
            if not submission_doc:
                print(f"⚠️ 找不到 AI 測驗提交記錄: {submission_id}")
                return jsonify({
                    'success': False,
                    'message': f'測驗記錄不存在，ID: {submission_id}'
                }), 404
            
            print(f"✅ 找到 AI 測驗提交記錄: {submission_doc.get('quiz_id', 'Unknown')}")
            
            # 從考卷獲取題目詳情
            quiz_id = submission_doc.get('quiz_id')
            quiz_doc = mongo.db.exam.find_one({"_id": quiz_id})
            if not quiz_doc:
                print(f"❌ 找不到對應的考卷: {quiz_id}")
                return jsonify({
                    'success': False,
                    'message': '找不到對應的考卷'
                }), 404
            
            questions = quiz_doc.get('questions', [])
            answers = submission_doc.get('answers', {})
            
            # 構建答案數據
            answer_objects = []
            for i, question in enumerate(questions):
                user_answer = answers.get(str(i), '')
                correct_answer = question.get('correct_answer', '')
                is_correct = user_answer == correct_answer
                
                answer_obj = {
                    'question_id': f"q_{i}",
                    'question_text': question.get('question_text', ''),
                    'topic': question.get('topic', 'unknown'),
                    'chapter': question.get('chapter', 'unknown'),
                    'user_answer': user_answer,
                    'is_correct': is_correct,
                    'score': 10 if is_correct else 0,
                    'feedback': {},
                    'answer_time_seconds': 0,
                    'answer_time': submission_doc.get('submitted_at'),
                    'options': question.get('options', []),
                    'correct_answer': correct_answer,
                    'image_file': question.get('image_file', '')
                }
                answer_objects.append(answer_obj)
            
            print(f"✅ 成功處理 {len(answer_objects)} 個 AI 測驗答案")
            
        else:
            # 傳統測驗：從 SQL 資料庫獲取測驗記錄
            print(f"🔍 從SQL資料庫查詢 quiz_history_id: {quiz_history_id}")
            
            with sqldb.engine.connect() as conn:
                # 獲取測驗歷史記錄
                history_result = conn.execute(text("""
                    SELECT id, quiz_template_id, quiz_type, total_questions, answered_questions,
                           correct_count, wrong_count, accuracy_rate, average_score, 
                           total_time_taken, submit_time, status, created_at
                    FROM quiz_history 
                    WHERE id = :quiz_history_id AND user_email = :user_email
                """), {
                    'quiz_history_id': quiz_history_id,
                    'user_email': user_email
                }).fetchone()
            
            if not history_result:
                print(f"⚠️ 找不到測驗記錄，quiz_history_id: {quiz_history_id}, user_email: {user_email}")
                return jsonify({
                    'success': False,
                    'message': f'測驗記錄不存在，ID: {submission_id}'
                }), 404
            
            print(f"✅ 找到測驗記錄: {history_result[2]} (類型: {history_result[2]})")
            
            # 獲取該測驗的詳細答案信息
            answers_result = conn.execute(text("""
                SELECT mongodb_question_id, user_answer, is_correct, score, 
                       feedback, answer_time_seconds, created_at
                FROM quiz_answers 
                WHERE quiz_history_id = :quiz_history_id
                ORDER BY created_at
            """), {
                'quiz_history_id': quiz_history_id
            }).fetchall()
            
            print(f"🔍 找到 {len(answers_result)} 個答案記錄")
            
            if not answers_result:
                print(f"❌ 測驗記錄中沒有答案數據")
                return jsonify({
                    'success': False,
                    'message': '測驗記錄中沒有答案數據'
                }), 400
            
            # 處理答案數據，獲取題目詳情
            answers = []
            for answer_record in answers_result:
                mongodb_question_id = answer_record[0]
                user_answer = answer_record[1]
                is_correct = answer_record[2]
                score = float(answer_record[3]) if answer_record[3] else 0
                feedback = json.loads(answer_record[4]) if answer_record[4] else {}
                answer_time_seconds = answer_record[5] if answer_record[5] else 0
                answer_created_at = answer_record[6]
                
                # 從MongoDB獲取題目詳情
                question_detail = {}
                try:
                    if mongodb_question_id and len(mongodb_question_id) == 24:
                        exam_question = mongo.db.exam.find_one({"_id": ObjectId(mongodb_question_id)})
                    else:
                        exam_question = mongo.db.exam.find_one({"_id": mongodb_question_id})
                    
                    if exam_question:
                        question_detail = {
                            'question_text': exam_question.get('question_text', ''),
                            'topic': exam_question.get('主要學科', 'unknown'),
                            'chapter': exam_question.get('章節', 'unknown'),
                            'options': exam_question.get('options', []),
                            'correct_answer': exam_question.get('answer', ''),
                            'image_file': exam_question.get('image_file', '')
                        }
                except Exception as e:
                    print(f"⚠️ 獲取題目詳情失敗: {e}")
                    question_detail = {
                        'question_text': f'題目 {mongodb_question_id}',
                        'topic': 'unknown',
                        'chapter': 'unknown',
                        'options': [],
                        'correct_answer': '',
                        'image_file': ''
                    }
                
                # 構建答案對象
                answer_obj = {
                    'question_id': mongodb_question_id,
                    'question_text': question_detail.get('question_text', ''),
                    'topic': question_detail.get('topic', 'unknown'),
                    'chapter': question_detail.get('chapter', 'unknown'),
                    'user_answer': user_answer,
                    'is_correct': is_correct,
                    'score': score,
                    'feedback': feedback,
                    'answer_time_seconds': answer_time_seconds,
                    'answer_time': answer_created_at.isoformat() if answer_created_at else None,
                    'options': question_detail.get('options', []),
                    'correct_answer': question_detail.get('correct_answer', ''),
                    'image_file': question_detail.get('image_file', '')
                }
                answers.append(answer_obj)
            
            print(f"✅ 成功處理 {len(answer_objects)} 個傳統測驗答案")
            
            # 將傳統測驗的答案轉換為統一格式
            answer_objects = []
            for answer_record in answers_result:
                mongodb_question_id = answer_record[0]
                user_answer = answer_record[1]
                is_correct = answer_record[2]
                score = float(answer_record[3]) if answer_record[3] else 0
                feedback = json.loads(answer_record[4]) if answer_record[4] else {}
                answer_time_seconds = answer_record[5] if answer_record[5] else 0
                answer_created_at = answer_record[6]
                
                # 從MongoDB獲取題目詳情
                question_detail = {}
                try:
                    if mongodb_question_id and len(mongodb_question_id) == 24:
                        exam_question = mongo.db.exam.find_one({"_id": ObjectId(mongodb_question_id)})
                    else:
                        exam_question = mongo.db.exam.find_one({"_id": mongodb_question_id})
                    
                    if exam_question:
                        question_detail = {
                            'question_text': exam_question.get('question_text', ''),
                            'topic': exam_question.get('主要學科', 'unknown'),
                            'chapter': exam_question.get('章節', 'unknown'),
                            'options': exam_question.get('options', []),
                            'correct_answer': exam_question.get('answer', ''),
                            'image_file': exam_question.get('image_file', '')
                        }
                except Exception as e:
                    print(f"⚠️ 獲取題目詳情失敗: {e}")
                    question_detail = {
                        'question_text': f'題目 {mongodb_question_id}',
                        'topic': 'unknown',
                        'chapter': 'unknown',
                        'options': [],
                        'correct_answer': '',
                        'image_file': ''
                    }
                
                # 構建答案對象
                answer_obj = {
                    'question_id': mongodb_question_id,
                    'question_text': question_detail.get('question_text', ''),
                    'topic': question_detail.get('topic', 'unknown'),
                    'chapter': question_detail.get('chapter', 'unknown'),
                    'user_answer': user_answer,
                    'is_correct': is_correct,
                    'score': score,
                    'feedback': feedback,
                    'answer_time_seconds': answer_time_seconds,
                    'answer_time': answer_created_at.isoformat() if answer_created_at else None,
                    'options': question_detail.get('options', []),
                    'correct_answer': question_detail.get('correct_answer', ''),
                    'image_file': question_detail.get('image_file', '')
                }
                answer_objects.append(answer_obj)
        
        # 使用第一個題目作為學習會話的基礎
        if answer_objects:
            first_answer = answer_objects[0]
            print(f"🔍 第一個答案的結構: {first_answer}")
            
            question_text = first_answer.get('question_text', '')
            question_topic = first_answer.get('topic', 'unknown')
            question_chapter = first_answer.get('chapter', 'unknown')
            
            print(f"🔍 提取的題目信息:")
            print(f"  - question_text: {question_text}")
            print(f"  - question_topic: {question_topic}")
            print(f"  - question_chapter: {question_chapter}")
        else:
            print(f"❌ 沒有可用的答案數據")
            return jsonify({
                'success': False,
                'message': '沒有可用的答案數據'
            }), 400
        
        # 生成學習會話ID
        session_id = f"session_{user_email}_{int(time.time())}"
        
        # 根據會話類型生成不同的學習內容
        if session_type == 'mistake_review':
            # 錯題複習模式
            session_data = {
                'session_id': session_id,
                'user_email': user_email,
                'submission_id': submission_id,
                'session_type': session_type,
                'title': f'錯題複習：{question_text[:50] if question_text else "題目"}...',
                'description': f'針對您的{question_topic}科目{question_chapter}章節的錯題進行深入分析和學習',
                'learning_objectives': [
                    '理解題目核心概念',
                    '掌握正確解題思路',
                    '避免常見錯誤'
                ],
                'topic': question_topic,
                'chapter': question_chapter,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
        else:
            # 一般學習模式
            session_data = {
                'session_id': session_id,
                'user_email': user_email,
                'submission_id': submission_id,
                'session_type': session_type,
                'title': f'概念學習：{question_text[:50] if question_text else "題目"}...',
                'description': f'深入學習{question_topic}科目{question_chapter}章節的相關知識點',
                'learning_objectives': [
                    '掌握核心概念',
                    '理解解題方法',
                    '擴展相關知識'
                ],
                'topic': question_topic,
                'chapter': question_chapter,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'session_data': session_data
        }), 200
        
    except Exception as e:
        print(f"❌ 生成學習會話失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'生成學習會話失敗：{str(e)}'
        }), 500

@ai_quiz_bp.route('/get-user-errors-mongo', methods=['POST', 'OPTIONS'])
def get_user_errors_mongo():
    """從 MongoDB error_questions 集合獲取用戶錯題"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True})
        
        # 驗證用戶身份
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少授權token'}), 401
        
        user_email = verify_token(token.split(" ")[1])
        if not user_email:
            return jsonify({'error': '無效的token'}), 401
        
        # 從 MongoDB error_questions 集合獲取用戶錯題
        error_questions = list(mongo.db.error_questions.find(
            {'user_email': user_email},
            {'_id': 0}  # 排除 _id 字段
        ).sort('timestamp', -1))  # 按時間倒序排列
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'error_questions': error_questions,
            'total_errors': len(error_questions)
        })
        
    except Exception as e:
        print(f"❌ 獲取用戶錯題失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取用戶錯題失敗：{str(e)}'
        }), 500

@ai_quiz_bp.route('/generate-content-based-quiz', methods=['POST', 'OPTIONS'])
def generate_content_based_quiz():
    """基於內容生成考卷 API"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True}), 204
        
        # 驗證用戶身份
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少授權token'}), 401
        
        user_email = verify_token(token.split(" ")[1])
        if not user_email:
            return jsonify({'error': '無效的token'}), 401
        
        # 獲取請求數據
        data = request.get_json()
        content = data.get('content', '')
        difficulty = data.get('difficulty', 'medium')
        question_count = data.get('question_count', 1)
        question_types = data.get('question_types', ['single-choice', 'multiple-choice'])
        
        if not content:
            return jsonify({
                'success': False,
                'message': '缺少內容參數'
            }), 400
        
        print(f"🎯 開始基於內容生成考卷，用戶: {user_email}, 內容長度: {len(content)}")
        
        # 調用基於內容的考卷生成
        from src.quiz_generator import execute_content_based_quiz_generation
        
        # 構建完整的內容字符串
        full_content = f"根據以下內容生成一道題目：{content}"
        
        # 生成考卷
        result = execute_content_based_quiz_generation(full_content)
        
        # 解析結果中的考卷ID
        import re
        quiz_id_match = re.search(r'考卷ID: `([^`]+)`', result)
        quiz_id = quiz_id_match.group(1) if quiz_id_match else f"content_based_{int(time.time())}"
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'message': '基於內容的考卷生成成功',
            'quiz_id': quiz_id,
            'result': result
        }), 200
        
    except Exception as e:
        print(f"❌ 基於內容的考卷生成失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'基於內容的考卷生成失敗：{str(e)}'
        }), 500

@ai_quiz_bp.route('/submit-ai-quiz', methods=['POST', 'OPTIONS'])
def submit_ai_quiz():
    """提交 AI 生成的測驗答案 - 帶進度追蹤版本"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'token': None, 'success': True}), 200
        
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'token': None, 'message': '未提供token'}), 401
        
        token = auth_header.split(" ")[1]
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'token': None, 'message': '無效的token'}), 401
            
        data = request.get_json()
        
        # 提取提交數據
        quiz_id = data.get('quiz_id')
        template_id = data.get('template_id')
        answers = data.get('answers', {})
        question_answer_times = data.get('question_answer_times', {})
        time_taken = data.get('time_taken', 0)
        frontend_questions = data.get('questions', [])
        
        if not quiz_id or not template_id:
            return jsonify({
                'success': False,
                'message': '缺少必要的測驗參數'
            }), 400
        
        # 生成唯一的進度追蹤ID
        progress_id = f"ai_progress_{user_email}_{int(time.time())}"
        
        # 階段1: 獲取題目數據
        update_progress_status(progress_id, False, 1, "正在獲取AI測驗題目數據...")
        
        # 從 MongoDB 獲取考卷數據
        if mongo is None or mongo.db is None:
            return jsonify({'success': False, 'error': '資料庫連接不可用'}), 500
        
        quiz_doc = mongo.db.exam.find_one({"_id": quiz_id})
        if not quiz_doc:
            return jsonify({'success': False, 'error': '找不到考卷'}), 404
        
        # 優先使用前端發送的題目數據，如果沒有則從MongoDB獲取
        if frontend_questions and len(frontend_questions) > 0:
            print("✅ AI測驗：使用前端發送的題目數據")
            questions = frontend_questions
        else:
            print("🔄 AI測驗：從MongoDB獲取題目數據")
            questions = quiz_doc.get('questions', [])
            
        if not questions:
            return jsonify({'success': False, 'error': '考卷中沒有題目'}), 400
        
        total_questions = len(questions)
        
        # 階段2: 分類題目
        update_progress_status(progress_id, False, 2, "正在分類AI測驗題目...")
        
        # 分類已作答和未作答題目
        answered_questions = []
        unanswered_questions = []
        correct_count = 0
        wrong_count = 0
        total_score = 0
        wrong_questions = []
        
        for i, question in enumerate(questions):
            user_answer = answers.get(str(i), '')
            question_type = question.get('type', 'single-choice')
            
            # 檢查是否有有效答案
            has_valid_answer = False
            if user_answer is not None and user_answer != '':
                has_valid_answer = True
            
            if has_valid_answer:
                # 已作答題目：收集到已作答列表
                answered_questions.append({
                    'index': i,
                    'question': question,
                    'user_answer': user_answer,
                    'question_type': question_type
                })
            else:
                # 未作答題目：收集到未作答列表
                unanswered_questions.append({
                    'index': i,
                    'question': question,
                    'user_answer': '',
                    'question_type': question_type
                })
        
        # 階段3: AI智能評分
        update_progress_status(progress_id, False, 3, "AI正在進行智能評分...")
        
        # 批量AI評分所有已作答題目
        if answered_questions:
            # 準備AI評分數據
            ai_questions_data = []
            for q_data in answered_questions:
                question = q_data['question']
                user_answer = q_data['user_answer']
                question_type = question.get('type', '')
                
                ai_questions_data.append({
                    'question_id': question.get('original_exam_id', ''),
                    'user_answer': user_answer,
                    'question_type': question_type,
                    'question_text': question.get('question_text', ''),
                    'options': question.get('options', []),
                    'correct_answer': question.get('correct_answer', ''),
                    'key_points': question.get('key_points', '')
                })
            
            # 使用AI批改模組進行批量評分
            from src.grade_answer import batch_grade_ai_questions
            ai_results = batch_grade_ai_questions(ai_questions_data)
            
            # 處理AI評分結果
            for i, result in enumerate(ai_results):
                q_data = answered_questions[i]
                question = q_data['question']
                
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
                    wrong_questions.append({
                        'question_id': question.get('id', q_data['index'] + 1),
                        'question_text': question.get('question_text', ''),
                        'question_type': question.get('type', ''),
                        'user_answer': q_data['user_answer'],
                        'correct_answer': question.get('correct_answer', ''),
                        'options': question.get('options', []),
                        'image_file': question.get('image_file', ''),
                        'original_exam_id': question.get('original_exam_id', ''),
                        'question_index': q_data['index'],
                        'score': score,
                        'feedback': feedback
                    })
                
                # 保存AI評分結果到 answered_questions 中，供後續使用
                q_data['ai_result'] = {
                    'is_correct': is_correct,
                    'score': score,
                    'feedback': feedback
                }
        
        # 階段4: 統計結果
        update_progress_status(progress_id, False, 4, "正在統計AI測驗結果...")
        
        # 計算統計數據
        answered_count = len(answered_questions)
        unanswered_count = len(unanswered_questions)
        accuracy_rate = (correct_count / total_questions * 100) if total_questions > 0 else 0
        average_score = (total_score / answered_count) if answered_count > 0 else 0
        
        # 簡化版本：直接保存到 MongoDB，避免 SQL 資料庫問題
        submission_data = {
            'quiz_id': quiz_id,
            'template_id': template_id,
            'user_email': user_email,
            'answers': answers,
            'question_answer_times': question_answer_times,
            'time_taken': time_taken,
            'score': accuracy_rate,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'total_questions': total_questions,
            'answered_count': answered_count,
            'unanswered_count': unanswered_count,
            'accuracy_rate': accuracy_rate,
            'average_score': average_score,
            'wrong_questions': wrong_questions,
            'submitted_at': datetime.now().isoformat(),
            'quiz_type': 'ai_generated',
            'progress_id': progress_id
        }
        
        # 保存到 submissions 集合
        result = mongo.db.submissions.insert_one(submission_data)
        submission_id = str(result.inserted_id)
        
        # 生成結果ID
        result_id = f"ai_result_{submission_id}"
        quiz_history_id = f"quiz_history_{submission_id}"
        
        # 更新進度追蹤狀態為完成
        update_progress_status(progress_id, True, 4, "AI測驗批改完成！")
        
        return jsonify({
            'token': refresh_token(token),
            'success': True,
            'message': 'AI測驗提交成功',
            'data': {
                'submission_id': submission_id,
                'quiz_history_id': quiz_history_id,  # 返回測驗歷史記錄ID
                'result_id': result_id,
                'progress_id': progress_id,  # 返回進度追蹤ID
                'template_id': template_id,  # 返回模板ID
                'quiz_id': quiz_id,
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
                    {'stage': 1, 'name': '試卷批改', 'status': 'completed', 'description': '獲取AI測驗題目數據完成'},
                    {'stage': 2, 'name': '計算分數', 'status': 'completed', 'description': 'AI測驗題目分類完成'},
                    {'stage': 3, 'name': '評判知識點', 'status': 'completed', 'description': f'AI智能評分完成，共評分{answered_count}題'},
                    {'stage': 4, 'name': '生成學習計畫', 'status': 'completed', 'description': f'AI測驗統計完成，正確率{accuracy_rate:.1f}%'}
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
        
    except Exception as e:
        logger.error(f"❌ AI測驗提交失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'AI測驗提交失敗：{str(e)}'
        }), 500