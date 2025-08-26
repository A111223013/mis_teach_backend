from flask import jsonify, request, Blueprint, current_app, Response
import uuid
from accessories import mongo, sqldb
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
quiz_bp = Blueprint('quiz', __name__)






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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (quiz_history_id) REFERENCES quiz_history(id) ON DELETE CASCADE,
                        INDEX idx_quiz_history_id (quiz_history_id),
                        INDEX idx_user_email (user_email),
                        INDEX idx_mongodb_question_id (mongodb_question_id),
                        INDEX idx_is_correct (is_correct),
                        INDEX idx_created_at (created_at)
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
            
            print("✅ Quiz SQL tables initialized successfully (final optimized)")
            return True
    except Exception as e:
        print(f"❌ Failed to initialize quiz tables: {e}")
        return False



@quiz_bp.route('/submit-quiz', methods=['POST', 'OPTIONS'])
def submit_quiz():
    """提交測驗 API - 全AI評分版本"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    # 驗證用戶身份
    token = request.headers.get('Authorization').split(" ")[1]
    user_email = verify_token(token)
    if not user_email:
        return jsonify({'message': '無效的token'}), 401
    
    # 獲取請求數據
    data = request.get_json()
    template_id = data.get('template_id')
    answers = data.get('answers', {})
    time_taken = data.get('time_taken', 0)
    questions_data = data.get('questions', [])  # 新增：接收前端傳遞的完整題目數據
    
    if not template_id:
        return jsonify({
            'success': False,
            'message': '缺少考卷模板ID'
        }), 400
    
    print(f"Debug: 收到測驗提交請求，template_id: {template_id}, 答案數量: {len(answers)}")
    
    # 生成唯一的進度追蹤ID
    progress_id = f"progress_{user_email}_{int(time.time())}"
    
    # 階段1: 試卷批改 - 獲取題目數據
    print("🔄 階段1: 試卷批改 - 獲取題目數據")
    
    # 檢查是否有前端傳遞的完整題目數據
    if questions_data and len(questions_data) > 0:
        print("✅ 使用前端傳遞的完整題目數據")
        questions = questions_data
        total_questions = len(questions)
        quiz_type = 'knowledge'  # AI生成的考卷類型，使用 knowledge 類型
        
        # 處理template_id - AI生成的考卷使用字符串格式  ##這裡到時候要改成 另種編碼 以區別
        
        if template_id.startswith('ai_template_'):
            template_id_int = None  # AI生成的考卷不需要template_id_int
        else:
            try:
                template_id_int = int(template_id)
            except ValueError:
                template_id_int = None
        
        # 確保題目格式正確
        for i, question in enumerate(questions):
            if 'id' not in question:
                question['id'] = i + 1
            if 'type' not in question:
                question['type'] = 'single-choice'
        
        print(f"Debug: 使用前端題目數據，共 {total_questions} 道題目")
        
    else:
        print("⚠️ 沒有前端題目數據，嘗試從資料庫讀取")
        # 從SQL獲取模板信息
        with sqldb.engine.connect() as conn:
            # 處理template_id - 確保是整數
            try:
                template_id_int = int(template_id)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'無效的template_id格式: {template_id}'
                }), 400
            
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
            quiz_type = template.template_type
            
            print(f"Debug: 從模板獲取到 {total_questions} 道題目")
            
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
            
            print(f"Debug: 成功獲取 {len(questions)} 道題目詳情")
    
    # 階段2: 計算分數 - 分類題目
    print("🔄 階段2: 計算分數 - 分類題目")
    
    # 評分和分析 - 全AI評分邏輯
    correct_count = 0
    wrong_count = 0
    total_score = 0
    wrong_questions = []
    unanswered_count = 0
    
    # 分類題目：已作答題目和未作答題目（所有已作答題目都使用AI評分）
    answered_questions = []  # 已作答題目（所有類型都使用AI評分）
    unanswered_questions = []    # 未作答題目
    
    for i in range(total_questions):
        question = questions[i]
        question_type = question.get('type', '')
        user_answer = answers.get(str(i))
        
        # 檢查題目狀態 - 判斷是否已作答
        if (user_answer is None or 
            user_answer == "" or 
            user_answer == "null" or 
            user_answer == "undefined" or
            (isinstance(user_answer, str) and user_answer.strip() == "")):
            # 未作答題目：收集到未作答列表
            unanswered_count += 1
            unanswered_questions.append({
                'index': i,
                'question': question,
                'user_answer': '',
                'question_type': question_type
            })
            print(f"Debug: 題目 {i} 未作答 (答案: {user_answer})")
        else:
            # 已作答題目：收集到已作答列表（所有類型都使用AI評分）
            answered_questions.append({
                'index': i,
                'question': question,
                'user_answer': user_answer,
                'question_type': question_type
            })
            print(f"Debug: 題目 {i} 已作答 (答案: {user_answer})")
    
    print(f"Debug: 已作答題目: {len(answered_questions)} 題")
    print(f"Debug: 未作答題目: {len(unanswered_questions)} 題")
    
    # 階段3: 評判知識點 - AI評分
    print("🔄 階段3: 評判知識點 - AI評分")
    
    # 批量AI評分所有已作答題目
    if answered_questions:
        print(f"Debug: 開始批量AI評分 {len(answered_questions)} 題")
        
        # 準備AI評分數據
        ai_questions_data = []
        for q_data in answered_questions:
            question = q_data['question']
            user_answer = q_data['user_answer']
            question_type = q_data['question_type']
            
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
                print(f"Debug: AI評分題目 {i} 正確，分數: {score}")
            else:
                wrong_count += 1
                print(f"Debug: AI評分題目 {i} 錯誤，分數: {score}")
                # 收集錯題信息
                wrong_questions.append({
                    'question_id': question.get('id', q_data['index'] + 1),
                    'question_text': question.get('question_text', ''),
                    'question_type': q_data['question_type'],
                    'user_answer': q_data['user_answer'],
                    'correct_answer': question.get('correct_answer', ''),
                    'options': question.get('options', []),
                    'image_file': question.get('image_file', ''),
                    'original_exam_id': question.get('original_exam_id', ''),
                    'question_index': q_data['index'],
                    'score': score,
                    'feedback': feedback
                })
        
        print(f"Debug: AI批量評分完成")
    else:
        print(f"Debug: 沒有已作答題目")
    
    # 階段4: 生成學習計畫 - 統計和儲存
    print("🔄 階段4: 生成學習計畫 - 統計和儲存")
    
    # 計算統計數據
    answered_count = len(answered_questions)
    unanswered_count = len(unanswered_questions)
    
    # 調試：打印詳細統計信息
    print(f"Debug: 詳細統計 - 總題數: {total_questions}")
    print(f"Debug: 詳細統計 - 已作答題目: {answered_count}")
    print(f"Debug: 詳細統計 - 未作答題目: {unanswered_count}")
    print(f"Debug: 詳細統計 - 正確題目: {correct_count}")
    print(f"Debug: 詳細統計 - 錯誤題目: {wrong_count}")
    
    # 驗證統計數據一致性（但不強制覆蓋）
    if answered_count + unanswered_count != total_questions:
        print(f"⚠️ 統計數據不一致: 已答({answered_count}) + 未答({unanswered_count}) != 總題數({total_questions})")
        print(f"⚠️ 保持原始統計數據，不強制覆蓋")
    
    accuracy_rate = (correct_count / total_questions * 100) if total_questions > 0 else 0
    average_score = (total_score / answered_count) if answered_count > 0 else 0
    
    print(f"Debug: 評分完成 - 總題數: {total_questions}, 已作答: {answered_count}, 未作答: {unanswered_count}")
    print(f"Debug: 正確: {correct_count}, 錯誤: {wrong_count}, 正確率: {accuracy_rate:.2f}%")
    
    # 更新或創建SQL記錄
    with sqldb.engine.connect() as conn:
        # 使用從測驗數據獲取的類型
        # 對於AI生成的考卷，template_id_int可能為None，使用原始template_id
        quiz_template_id = template_id_int if template_id_int is not None else template_id
        
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
            result = conn.execute(text("""
                INSERT INTO quiz_history 
                (quiz_template_id, user_email, quiz_type, total_questions, answered_questions,
                 correct_count, wrong_count, accuracy_rate, average_score, total_time_taken, submit_time, status)
                VALUES (:quiz_template_id, :user_email, :quiz_type, :total_questions, :answered_questions,
                       :correct_count, :wrong_count, :accuracy_rate, :average_score, :total_time_taken, :submit_time, :status)
            """), {
                'quiz_template_id': quiz_template_id,
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
        for q_data in answered_questions:
            i = q_data['index']
            question = q_data['question']
            user_answer = q_data['user_answer']
            question_id = question.get('original_exam_id', '')
            
            # 檢查是否為錯題
            is_wrong = any(wrong_q.get('original_exam_id') == question_id for wrong_q in wrong_questions)
            is_correct = not is_wrong
            
            # 構建用戶答案資料
            answer_data = {
                'answer': user_answer,
                'feedback': {}  # 答對的題目沒有 feedback
            }
            
            # 如果是錯題，添加 feedback
            if is_wrong:
                wrong_q = next((wq for wq in wrong_questions if wq.get('original_exam_id') == question_id), None)
                if wrong_q:
                    answer_data['feedback'] = wrong_q.get('feedback', {})
            
            score = 0 if is_wrong else 100
            
            # 使用新的長答案存儲方法，保持數據完整性
            stored_answer = _store_long_answer(user_answer, 'unknown', quiz_history_id, question_id, user_email)
            
            # 插入到 quiz_answers 表
            conn.execute(text("""
                INSERT INTO quiz_answers 
                (quiz_history_id, user_email, mongodb_question_id, user_answer, is_correct, score)
                VALUES (:quiz_history_id, :user_email, :mongodb_question_id, :user_answer, :is_correct, :score)
            """), {
                'quiz_history_id': quiz_history_id,
                'user_email': user_email,
                'mongodb_question_id': question_id,
                'user_answer': stored_answer,  # 使用存儲後的答案引用
                'is_correct': is_correct,
                'score': score
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
                (quiz_history_id, user_email, mongodb_question_id, user_answer, is_correct, score)
                VALUES (:quiz_history_id, :user_email, :mongodb_question_id, :user_answer, :is_correct, :score)
            """), {
                'quiz_history_id': quiz_history_id,
                'user_email': user_email,
                'mongodb_question_id': question_id,
                'user_answer': '',  # 未作答題目答案為空
                'is_correct': False,  # 未作答題目標記為錯誤
                'score': 0
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
    
    print("✅ 測驗批改完成！")
    
    return jsonify({
        'success': True,
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
            ]
        }
    })


# 舊的答案截斷方法已移除，現在使用長答案存儲方法保持數據完整性


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
                
                print(f"✅ 長答案已存儲到 long_answers 表，ID: {long_answer_id}")
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
        return jsonify({'message': 'CORS preflight'}), 200
    
    # 從result_id中提取quiz_history_id
    # result_id格式: result_123
    if not result_id.startswith('result_'):
        return jsonify({'message': '無效的結果ID格式'}), 400
    
    try:
        quiz_history_id = int(result_id.split('_')[1])
    except (ValueError, IndexError):
        return jsonify({'message': '無效的結果ID格式'}), 400
    
    print(f"📝 正在查詢測驗結果，quiz_history_id: {quiz_history_id}")
    
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
            return jsonify({'message': '測驗結果不存在'}), 404
        
        print(f"📊 測驗記錄: {history_result}")
        
        # 獲取所有題目的用戶答案（從quiz_answers表）
        answers_result = conn.execute(text("""
            SELECT mongodb_question_id, user_answer, is_correct, score, created_at
            FROM quiz_answers 
            WHERE quiz_history_id = :quiz_history_id
            ORDER BY created_at
        """), {
            'quiz_history_id': quiz_history_id
        }).fetchall()
        
        print(f"📝 用戶答案記錄數量: {len(answers_result)}")
        
        # 獲取錯題詳情（從quiz_errors表，向後兼容）
        error_result = conn.execute(text("""
            SELECT mongodb_question_id, user_answer, score, time_taken, created_at
            FROM quiz_errors 
            WHERE quiz_history_id = :quiz_history_id
            ORDER BY created_at
        """), {
            'quiz_history_id': quiz_history_id
        }).fetchall()
        
        print(f"❌ 錯題記錄數量: {len(error_result)}")
        
        # 構建答案字典，方便查詢
        answers_dict = {}
        for answer in answers_result:
            answers_dict[str(answer[0])] = {
                'user_answer': json.loads(answer[1]) if answer[1] else '',
                'is_correct': bool(answer[2]),
                'score': float(answer[3]) if answer[3] else 0,
                'answer_time': answer[4].isoformat() if answer[4] else None
            }
        
        # 獲取題目ID列表
        question_ids_raw = history_result[14]
        question_ids = []
        if question_ids_raw:
            try:
                question_ids = json.loads(question_ids_raw)
                print(f"📋 題目ID列表: {len(question_ids)} 題")
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失敗: {e}")
                question_ids = []
        
        if not question_ids:
            print(f"⚠️ 沒有題目ID，返回基本統計")
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
                'success': True,
                'message': '獲取測驗結果成功（僅基本統計）',
                'data': result_data
            }), 200
        
        # 獲取所有題目的詳細資訊
        all_questions = []
        errors = []
        
        for i, question_id in enumerate(question_ids):
            print(f"🔍 處理題目 {i + 1}: {question_id}")
            
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
                    print(f"✅ 題目詳情獲取成功: {question_detail.get('question_text', '')[:50]}...")
                else:
                    print(f"⚠️ 找不到題目: {question_id}")
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
        
        print(f"✅ 成功獲取測驗結果，包含 {len(all_questions)} 道題目，其中 {len(errors)} 道錯題")
        
        return jsonify({
            'success': True,
            'message': '獲取測驗結果成功',
            'data': result_data
        }), 200


# 删除 /test-quiz-result API - 与 /get-quiz-result 功能重复

@quiz_bp.route('/create-quiz', methods=['POST', 'OPTIONS'])
def create_quiz():
    """創建測驗 API - 支持用戶填寫學校、科系、年份"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    token = request.headers.get('Authorization')
    token = token.split(" ")[1]
    try:
        # 驗證token
        user_email = verify_token(token)

        # 獲取請求參數
        data = request.get_json()
        quiz_type = data.get('type')  # 'knowledge' 或 'pastexam'
        
        print(f"📝 用戶 {user_email} 請求創建 {quiz_type} 測驗")
        
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
            
            print(f"🏫 查詢考古題: {school} - {year}年 - {department}")
            
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
            print(f"✅ 找到 {len(selected_exams)} 道考古題")
            
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
        
        print(f"✅ 測驗準備完成，ID: {quiz_id}, 包含 {len(questions)} 道題目")
        
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
                    print("✅ 自動創建 quiz_templates 表成功")
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
                    print("✅ 自動創建 quiz_history 表成功")
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
                    print("✅ 自動創建 quiz_errors 表成功")
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
                print(f"✅ 創建考卷模板成功，ID: {template_id}")
                
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
                print(f"✅ 在SQL中創建quiz_history初始記錄，關聯模板ID: {template_id}")
                
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

@quiz_bp.route('/get-exam', methods=['POST', 'OPTIONS'])
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


@quiz_bp.route('/grading-progress/<template_id>', methods=['GET', 'OPTIONS'])
def get_grading_progress(template_id):
    """獲取測驗批改進度 API"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證用戶身份
        token = request.headers.get('Authorization').split(" ")[1]
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        # 檢查測驗狀態
        with sqldb.engine.connect() as conn:
            # 處理template_id - 對於AI生成的考卷，直接使用字符串
            if template_id.startswith('ai_template_'):
                template_id_for_query = template_id
            else:
                try:
                    template_id_int = int(template_id)
                    template_id_for_query = template_id_int
                except ValueError:
                    return jsonify({'message': f'無效的template_id格式: {template_id}'}), 400
            
            # 檢查是否有完成的測驗記錄
            history_result = conn.execute(text("""
                SELECT id, status, correct_count, wrong_count, accuracy_rate, average_score, total_questions, answered_questions
                FROM quiz_history 
                WHERE quiz_template_id = :template_id AND user_email = :user_email
                ORDER BY created_at DESC LIMIT 1
            """), {
                'template_id': template_id_for_query,
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
                
    except Exception as e:
        print(f"❌ 獲取批改進度時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取批改進度失敗: {str(e)}'}), 500


@quiz_bp.route('/quiz-progress/<progress_id>', methods=['GET'])
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


@quiz_bp.route('/quiz-progress-sse/<progress_id>', methods=['GET'])
def quiz_progress_sse(progress_id):
    """測驗進度 Server-Sent Events API - 實時推送進度更新"""
    def generate_progress_events():
        """生成進度事件流"""
        try:
            # 設置SSE headers
            yield 'data: {"type": "connected", "message": "進度追蹤已連接"}\n\n'
            
            # 基於真實的AI批改進度，而不是模擬
            stages = [
                {'stage': 1, 'name': '試卷批改', 'description': '正在獲取題目數據...'},
                {'stage': 2, 'name': '計算分數', 'description': '正在分類題目...'},
                {'stage': 3, 'name': '評判知識點', 'description': 'AI正在進行智能評分...'},
                {'stage': 4, 'name': '生成學習計畫', 'description': '正在統計結果...'}
            ]
            
            # 快速發送進度更新，因為AI批改已經完成
            for i, stage in enumerate(stages):
                progress_data = {
                    'type': 'progress_update',
                    'current_stage': stage['stage'],
                    'stage_name': stage['name'],
                    'stage_description': stage['description'],
                    'progress_percentage': (stage['stage'] / len(stages)) * 100,
                    'is_completed': stage['stage'] == len(stages),
                    'timestamp': time.time()
                }
                
                yield f'data: {json.dumps(progress_data, ensure_ascii=False)}\n\n'
                
                # 快速更新，每0.5秒一個階段
                time.sleep(0.5)
                
                # 如果是最後一個階段，發送完成事件
                if stage['stage'] == len(stages):
                    completion_data = {
                        'type': 'completion',
                        'message': 'AI批改完成！',
                        'progress_percentage': 100,
                        'is_completed': True,
                        'timestamp': time.time()
                    }
                    yield f'data: {json.dumps(completion_data, ensure_ascii=False)}\n\n'
                    break
                    
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

@quiz_bp.route('/get-long-answer/<answer_id>', methods=['GET'])
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