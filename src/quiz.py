from flask import jsonify, request, Blueprint, current_app
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
from src.grade_answer_simple import grade_single_answer, batch_grade_ai_questions
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
            
            print("✅ Quiz SQL tables initialized successfully (final optimized)")
            return True
    except Exception as e:
        print(f"❌ Failed to initialize quiz tables: {e}")
        return False



@quiz_bp.route('/submit-quiz', methods=['POST', 'OPTIONS'])
def submit_quiz():
    """提交測驗 API - 處理前端發送的答案數據"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    token = request.headers.get('Authorization')
    token = token.split(" ")[1]
    try:
        # 驗證token
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        data = request.get_json()
        template_id = data.get('template_id')  # 改為 template_id
        answers = data.get('answers', {})
        time_taken = data.get('time_taken', 0)
        
        if not template_id:
            return jsonify({
                'success': False,
                'message': '缺少考卷模板ID'
            }), 400
        
        print(f"Debug: 收到測驗提交請求，template_id: {template_id}, 答案數量: {len(answers)}")
        
        # 從SQL獲取模板信息
        try:
            with sqldb.engine.connect() as conn:
                # 嘗試將 template_id 轉換為數字，如果失敗則使用字符串查詢
                try:
                    template_id_int = int(template_id)
                    template = conn.execute(text("""
                        SELECT * FROM quiz_templates WHERE id = :template_id
                    """), {'template_id': template_id_int}).fetchone()
                except ValueError:
                    # 如果轉換失敗，嘗試使用字符串查詢
                    template = conn.execute(text("""
                        SELECT * FROM quiz_templates WHERE id = :template_id
                    """), {'template_id': template_id}).fetchone()
                
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
                    try:
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
                            
                    except Exception as e:
                        print(f"⚠️ 處理題目 {question_id} 時出錯: {e}")
                        # 創建一個錯誤的題目記錄
                        question = {
                            'id': i + 1,
                            'question_text': f'題目 {i + 1} (錯誤: {question_id})',
                            'type': 'single-choice',
                            'options': [],
                            'correct_answer': '',
                            'original_exam_id': question_id,
                            'image_file': '',
                            'key_points': ''
                        }
                        questions.append(question)
                
                print(f"Debug: 成功獲取 {len(questions)} 道題目詳情")
                
        except Exception as e:
            print(f"❌ 獲取題目數據失敗: {e}")
            return jsonify({
                'success': False,
                'message': f'獲取題目數據失敗: {str(e)}'
            }), 500
        
        # 評分和分析
        correct_count = 0
        wrong_count = 0
        total_score = 0
        wrong_questions = []
        unanswered_count = 0
        
        # 分類題目：固定答案題型和AI評分題型
        fixed_answer_questions = []  # 單選題、多選題、是非題、填空題
        ai_grading_questions = []    # 簡答題、申論題
        
        for i in range(total_questions):
            question = questions[i]
            question_type = question.get('type', '')
            user_answer = answers.get(str(i))
            
            # 檢查題目狀態 - 更寬鬆的檢查
            if (user_answer is None or 
                user_answer == "" or 
                user_answer == "null" or 
                user_answer == "undefined" or
                (isinstance(user_answer, str) and user_answer.strip() == "")):
                unanswered_count += 1
                print(f"Debug: 題目 {i} 未作答 (答案: {user_answer})")
                continue
            
            print(f"Debug: 題目 {i} 已作答 (答案: {user_answer})")
            
            # 分類題目 - 根據 answer_type 進行分類
            if question_type in ['single-choice', 'multiple-choice', 'true-false', 'fill-in-the-blank']:
                # 固定答案題型，直接評分
                fixed_answer_questions.append({
                    'index': i,
                    'question': question,
                    'user_answer': user_answer
                })
                print(f"Debug: 題目 {i} 分類為固定答案題型: {question_type}")
            else:
                # AI評分題型，收集起來批量處理
                ai_grading_questions.append({
                    'index': i,
                    'question_id': question.get('original_exam_id', ''),
                    'user_answer': user_answer,
                    'question_type': question_type
                })
                print(f"Debug: 題目 {i} 分類為AI評分題型: {question_type}")
        
        print(f"Debug: 固定答案題型: {len(fixed_answer_questions)} 題")
        print(f"Debug: AI評分題型: {len(ai_grading_questions)} 題")
        
        # 1. 處理固定答案題型
        for q_data in fixed_answer_questions:
            i = q_data['index']
            question = q_data['question']
            user_answer = q_data['user_answer']
            question_id = question.get('original_exam_id', '')
            question_type = question.get('type', '')
            
            print(f"Debug: 評分固定答案題目 {i}, 類型: {question_type}")
            
            # 使用AI批改模組進行評分
            try:
                is_correct, score, feedback = grade_single_answer(question_id, user_answer, question_type)
                
                # 構建完整的答案信息
                answer_info = {
                    'question_id': question.get('id', i + 1),
                    'question_text': question.get('question_text', ''),
                    'question_type': question_type,
                    'user_answer': user_answer,
                    'correct_answer': question.get('correct_answer', ''),
                    'options': question.get('options', []),
                    'image_file': question.get('image_file', ''),
                    'original_exam_id': question.get('original_exam_id', ''),
                    'question_index': i,
                    'score': score,
                    'feedback': feedback
                }
            
                if is_correct:
                    correct_count += 1
                    total_score += score
                    print(f"Debug: 題目 {i} 正確，分數: {score}")
                else:
                    wrong_count += 1
                    print(f"Debug: 題目 {i} 錯誤，分數: {score}")
                    # 收集錯題信息
                    wrong_questions.append(answer_info)
                        
            except Exception as e:
                print(f"Debug: 題目 {i} 評分失敗: {e}")
                wrong_count += 1
                # 評分失敗也算錯題
                wrong_questions.append({
                    'question_id': question.get('id', i + 1),
                    'question_text': question.get('question_text', ''),
                    'question_type': question_type,
                    'user_answer': user_answer,
                    'correct_answer': question.get('correct_answer', ''),
                    'options': question.get('options', []),
                    'image_file': question.get('image_file', ''),
                    'original_exam_id': question.get('original_exam_id', ''),
                    'question_index': i,
                    'score': 0,
                    'feedback': {'error': f'評分失敗: {str(e)}'}
                })
        
        # 2. 批量處理AI評分題型
        if ai_grading_questions:
            print(f"Debug: 開始批量AI評分 {len(ai_grading_questions)} 題")
            
            try:
                # 使用同步批量AI批改
                ai_results = batch_grade_ai_questions(ai_grading_questions)
                
                # 處理AI評分結果
                for result in ai_results:
                    question_index = None
                    # 找到對應的題目索引
                    for q_data in ai_grading_questions:
                        if q_data['question_id'] == result['question_id']:
                            question_index = q_data['index']
                            break
                    
                    if question_index is not None:
                        question = questions[question_index]
                        is_correct = result['is_correct']
                        score = result['score']
                        
                        if is_correct:
                            correct_count += 1
                            total_score += score
                            print(f"Debug: AI評分題目 {question_index} 正確，分數: {score}")
                        else:
                            wrong_count += 1
                            print(f"Debug: AI評分題目 {question_index} 錯誤，分數: {score}")
                            # 收集錯題信息
                            wrong_questions.append({
                                'question_id': question.get('id', question_index + 1),
                                'question_text': question.get('question_text', ''),
                                'question_type': question.get('type', ''),
                                'user_answer': result['feedback'].get('user_answer', ''),
                                'correct_answer': result['feedback'].get('reference_answer', ''),
                                'options': question.get('options', []),
                                'image_file': question.get('image_file', ''),
                                'original_exam_id': question.get('original_exam_id', ''),
                                'question_index': question_index,
                                'score': score,
                                'feedback': result['feedback']
                            })
                
                print(f"Debug: AI批量評分完成")
                
            except Exception as e:
                print(f"Debug: AI批量評分失敗: {e}")
                # 如果AI批量評分失敗，回退到逐題評分
                for q_data in ai_grading_questions:
                    i = q_data['index']
                    question = questions[i]
                    user_answer = q_data['user_answer']
                    question_id = q_data['question_id']
                    question_type = q_data['question_type']
                    
                    print(f"Debug: 回退評分AI題目 {i}")
                    
                    try:
                        is_correct, score, feedback = grade_single_answer(question_id, user_answer, question_type)
                        
                        if is_correct:
                            correct_count += 1
                            total_score += score
                            print(f"Debug: 回退評分題目 {i} 正確，分數: {score}")
                        else:
                            wrong_count += 1
                            print(f"Debug: 回退評分題目 {i} 錯誤，分數: {score}")
                            wrong_questions.append({
                                'question_id': question.get('id', i + 1),
                                'question_text': question.get('question_text', ''),
                                'question_type': question_type,
                                'user_answer': user_answer,
                                'correct_answer': question.get('correct_answer', ''),
                                'options': question.get('options', []),
                                'image_file': question.get('image_file', ''),
                                'original_exam_id': question.get('original_exam_id', ''),
                                'question_index': i,
                                'score': score,
                                'feedback': feedback
                            })
                    except Exception as fallback_error:
                        print(f"Debug: 回退評分也失敗: {fallback_error}")
                        wrong_count += 1
                        wrong_questions.append({
                            'question_id': question.get('id', i + 1),
                            'question_text': question.get('question_text', ''),
                            'question_type': question_type,
                            'user_answer': user_answer,
                            'correct_answer': question.get('correct_answer', ''),
                            'options': question.get('options', []),
                            'image_file': question.get('image_file', ''),
                            'original_exam_id': question.get('original_exam_id', ''),
                            'question_index': i,
                            'score': 0,
                            'feedback': {'error': f'評分失敗: {str(fallback_error)}'}
                        })
        else:
            print(f"Debug: 沒有AI評分題型")
        
        # 計算統計數據
        answered_questions = correct_count + wrong_count
        total_questions_processed = answered_questions + unanswered_count
        
        # 驗證題目數量一致性
        if total_questions_processed != total_questions:
            print(f"⚠️ 題目數量不一致: 處理的({total_questions_processed}) != 總題數({total_questions})")
            # 調整未答題數量
            unanswered_count = total_questions - answered_questions
        
        # 確保未答題數不會為負數
        if unanswered_count < 0:
            print(f"⚠️ 未答題數為負數({unanswered_count})，調整為0")
            unanswered_count = 0
        
        print(f"Debug: 統計數據 - 總題數: {total_questions}, 已答: {answered_questions}, 未答: {unanswered_count}")
        print(f"Debug: 統計數據 - 正確: {correct_count}, 錯誤: {wrong_count}, 總分: {total_score}")
        
        accuracy_rate = (correct_count / total_questions * 100) if total_questions > 0 else 0
        average_score = (total_score / total_questions) if total_questions > 0 else 0
        
        print(f"Debug: 評分完成 - 總題數: {total_questions}, 已作答: {answered_questions}, 未作答: {unanswered_count}")
        print(f"Debug: 正確: {correct_count}, 錯誤: {wrong_count}, 正確率: {accuracy_rate:.2f}%")
        print(f"Debug: 答案對象詳情: {answers}")
        print(f"Debug: 錯題列表: {wrong_questions}")
        
        # 更新或創建SQL記錄
        with sqldb.engine.connect() as conn:
            # 使用從測驗數據獲取的類型
            quiz_template_id = None  # 暫時設為 None，因為我們直接從 MongoDB 獲取題目
            
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
                    'answered_questions': answered_questions,
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
                    'answered_questions': answered_questions,
                    'correct_count': correct_count,
                    'wrong_count': wrong_count,
                    'accuracy_rate': round(accuracy_rate, 2),
                    'average_score': round(average_score, 2),
                    'total_time_taken': time_taken,
                    'submit_time': datetime.now(),
                    'status': 'completed'
                })
                quiz_history_id = result.lastrowid
            
            # 添加錯題到quiz_errors
            if wrong_questions:
                for wrong_q in wrong_questions:
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
                        'user_answer': json.dumps({
                            'answer': wrong_q['user_answer'],
                            'feedback': wrong_q.get('feedback', {})
                        }, ensure_ascii=False),
                        'score': wrong_q.get('score', 0),
                        'time_taken': 0  # 簡化時間處理
                    })
            
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': '測驗提交成功',
            'data': {
                'template_id': template_id,  # 返回模板ID
                'quiz_history_id': quiz_history_id,  # 返回測驗歷史記錄ID
                'result_id': f'result_{quiz_history_id}',  # 返回結果ID（用於前端跳轉）
                'total_questions': total_questions,
                'answered_questions': answered_questions,
                'unanswered_questions': unanswered_count,
                'correct_count': correct_count,
                'wrong_count': wrong_count,
                'marked_count': 0,  # 暫時設為0，後續可擴展
                'accuracy_rate': round(accuracy_rate, 2),
                'average_score': round(average_score, 2),
                'time_taken': time_taken,
                'total_time': time_taken  # 添加總時間字段
            }
        })
        
    except Exception as e:
        print(f"提交測驗時發生錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'提交測驗失敗: {str(e)}'
        }), 500

# 删除 grade_question 函数 - 未使用，已被 grade_answer_simple 模块替代


@quiz_bp.route('/get-quiz-result/<result_id>', methods=['GET', 'OPTIONS'])
def get_quiz_result(result_id):
    """根據結果ID獲取測驗結果 API - 優化版本"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
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
        try:
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
                print(f"📊 測驗記錄詳細:")
                print(f"  - ID: {history_result[0]}")
                print(f"  - 模板ID: {history_result[1]}")
                print(f"  - 用戶: {history_result[2]}")
                print(f"  - 類型: {history_result[3]}")
                print(f"  - 總題數: {history_result[4]}")
                print(f"  - 已答題數: {history_result[5]}")
                print(f"  - 正確數: {history_result[6]}")
                print(f"  - 錯誤數: {history_result[7]}")
                print(f"  - 題目ID列表欄位: {history_result[14]}")
                print(f"  - 題目ID列表類型: {type(history_result[14])}")
                
                # 獲取錯題詳情
                error_result = conn.execute(text("""
                    SELECT mongodb_question_id, user_answer, score, time_taken, created_at
                    FROM quiz_errors 
                    WHERE quiz_history_id = :quiz_history_id
                    ORDER BY created_at
                """), {
                    'quiz_history_id': quiz_history_id
                }).fetchall()
                
                print(f"❌ 錯題記錄數量: {len(error_result)}")
                if error_result:
                    print(f"❌ 錯題記錄詳情: {error_result}")
                
                # 獲取完整題目列表和用戶答案
                question_ids_raw = history_result[14]
                print(f"📋 原始題目ID欄位: {question_ids_raw}")
                print(f"📋 原始題目ID欄位類型: {type(question_ids_raw)}")
                print(f"📋 原始題目ID欄位是否為None: {question_ids_raw is None}")
                print(f"📋 原始題目ID欄位是否為空字串: {question_ids_raw == ''}")
                
                question_ids = []
                if question_ids_raw:
                    try:
                        question_ids = json.loads(question_ids_raw)
                        print(f"📋 解析後題目ID列表: {question_ids}")
                        print(f"📋 題目ID列表類型: {type(question_ids)}")
                        print(f"📋 題目ID列表長度: {len(question_ids) if isinstance(question_ids, list) else 'N/A'}")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON解析失敗: {e}")
                        print(f"❌ 原始內容: {question_ids_raw}")
                else:
                    print(f"⚠️ 題目ID欄位為空或None")
                
                # 直接檢查資料庫中的原始值
                print(f"\n🔍 直接檢查資料庫原始值:")
                template_check = conn.execute(text("""
                    SELECT question_ids FROM quiz_templates WHERE id = :template_id
                """), {
                    'template_id': history_result[1]
                }).fetchone()
                
                if template_check:
                    print(f"  - 模板 {history_result[1]} 的 question_ids: {template_check[0]}")
                    print(f"  - 類型: {type(template_check[0])}")
                    if template_check[0]:
                        try:
                            parsed_check = json.loads(template_check[0])
                            print(f"  - 解析後: {parsed_check}")
                            print(f"  - 長度: {len(parsed_check) if isinstance(parsed_check, list) else 'N/A'}")
                        except:
                            print(f"  - JSON 解析失敗")
                else:
                    print(f"  - 找不到模板 {history_result[1]}")
                
                if not question_ids:
                    print(f"⚠️ 沒有題目ID，直接返回基本統計")
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
                        'questions': [],  # 空陣列
                        'errors': []      # 空陣列
                    }
                    
                    print(f"✅ 返回基本統計資料，沒有題目詳情")
                    return jsonify({
                        'success': True,
                        'message': '獲取測驗結果成功（僅基本統計）',
                        'data': result_data
                    }), 200
                
                # 創建錯題字典，方便查詢
                error_dict = {}
                for error in error_result:
                    error_dict[str(error[0])] = {
                        'user_answer': json.loads(error[1]) if error[1] else '',
                        'score': float(error[2]) if error[2] else 0,
                        'time_taken': error[3] if error[3] else 0,
                        'answer_time': error[4].isoformat() if error[4] else None
                    }
                
                # 獲取所有題目的詳細資訊
                all_questions = []
                for i, question_id in enumerate(question_ids):
                    print(f"🔍 處理題目 {i + 1}: {question_id}")
                    
                    # 從MongoDB獲取題目詳情
                    question_detail = {}
                    try:
                        # 安全地處理 ObjectId 查詢
                        try:
                            if isinstance(question_id, str) and len(question_id) == 24:
                                exam_question = mongo.db.exam.find_one({"_id": ObjectId(question_id)})
                            else:
                                exam_question = mongo.db.exam.find_one({"_id": question_id})
                        except Exception as oid_error:
                            print(f"⚠️ ObjectId 轉換失敗: {oid_error}")
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
                    
                    # 檢查是否為錯題
                    question_id_str = str(question_id)
                    is_error = question_id_str in error_dict
                    
                    # 構建題目資訊
                    question_info = {
                        'question_id': question_id_str,
                        'question_index': i,
                        'question_text': question_detail.get('question_text', ''),
                        'options': question_detail.get('options', []),
                        'correct_answer': question_detail.get('correct_answer', ''),
                        'image_file': question_detail.get('image_file', ''),
                        'key_points': question_detail.get('key_points', ''),
                        'is_correct': not is_error,
                        'is_marked': False  # 目前沒有標記功能
                    }
                    
                    if is_error:
                        # 錯題：使用用戶的錯誤答案
                        error_info = error_dict[question_id_str]
                        question_info.update({
                            'user_answer': error_info['user_answer'],
                            'time_taken': error_info['time_taken'],
                            'answer_time': error_info['answer_time']
                        })
                    else:
                        # 非錯題：user_answer為空字串（表示未作答或正確作答）
                        question_info.update({
                            'user_answer': '',
                            'time_taken': 0,
                            'answer_time': None
                        })
                    
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
                    'errors': [q for q in all_questions if not q['is_correct']]  # 錯題列表
                }
                
                print(f"✅ 成功獲取測驗結果，包含 {len(all_questions)} 道題目，其中 {wrong_count} 道錯題")
                
                return jsonify({
                    'success': True,
                    'message': '獲取測驗結果成功',
                    'data': result_data
                }), 200
                
        except Exception as db_error:
            print(f"❌ 數據庫查詢錯誤: {str(db_error)}")
            return jsonify({'message': f'獲取測驗結果失敗: {str(db_error)}'}), 500
        
    except Exception as e:
        print(f"❌ 獲取測驗結果時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取測驗結果失敗: {str(e)}'}), 500


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

# 删除 /get-exam-to-object API - 与 /get-exam 功能重复