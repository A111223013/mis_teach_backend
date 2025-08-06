from flask import jsonify, request, Blueprint, current_app
import uuid
from accessories import mongo, sqldb, redis_client
from src.api import get_user_info, verify_token
import jwt
from datetime import datetime
import random
import base64
import os
import json

quiz_bp = Blueprint('quiz', __name__)

def init_quiz_tables():
    """初始化測驗相關的SQL表格"""
    try:
        with current_app.app_context():
            # 創建quiz_history表 - 存儲測驗提交記錄
            with sqldb.engine.connect() as conn:
                conn.execute(sqldb.text("""
                    CREATE TABLE IF NOT EXISTS quiz_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        quiz_id VARCHAR(36) NOT NULL,
                        user_email VARCHAR(255) NOT NULL,
                        user_name VARCHAR(255),
                        quiz_title VARCHAR(500),
                        quiz_type ENUM('knowledge', 'pastexam') NOT NULL,
                        school VARCHAR(255),
                        department VARCHAR(255),
                        year VARCHAR(10),
                        subject VARCHAR(255),
                        total_questions INT DEFAULT 0,
                        answered_questions INT DEFAULT 0,
                        correct_count INT DEFAULT 0,
                        wrong_count INT DEFAULT 0,
                        accuracy_rate DECIMAL(5,2) DEFAULT 0,
                        average_score DECIMAL(5,2) DEFAULT 0,
                        time_taken INT DEFAULT 0,
                        submit_time DATETIME NOT NULL,
                        status ENUM('completed', 'incomplete', 'abandoned') DEFAULT 'completed',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_email (user_email),
                        INDEX idx_quiz_id (quiz_id),
                        INDEX idx_submit_time (submit_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            
            # 創建quiz_errors表 - 存儲考生錯題
            with sqldb.engine.connect() as conn:
                conn.execute(sqldb.text("""
                    CREATE TABLE IF NOT EXISTS quiz_errors (
                        error_id INT AUTO_INCREMENT PRIMARY KEY,
                        quiz_history_id INT NOT NULL,
                        user_email VARCHAR(255) NOT NULL,
                        question_id VARCHAR(50),
                        question_text TEXT,
                        question_type VARCHAR(50),
                        user_answer TEXT,
                        correct_answer TEXT,
                        mistake_content TEXT,
                        question_options JSON,
                        image_file VARCHAR(255),
                        original_exam_id VARCHAR(50),
                        question_index INT,
                        error_time DATETIME NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (quiz_history_id) REFERENCES quiz_history(id) ON DELETE CASCADE,
                        INDEX idx_user_email (user_email),
                        INDEX idx_question_id (question_id),
                        INDEX idx_error_time (error_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            
            print("✅ Quiz SQL tables initialized successfully")
            return True
    except Exception as e:
        print(f"❌ Failed to initialize quiz tables: {e}")
        return False

def verify_token():
    """驗證JWT token"""
    auth_header = request.headers.get('Authorization')
    
    print(f"Debug: Authorization header = {auth_header}")
    
    if not auth_header:
        print("Debug: 未提供 Authorization header")
        return None, jsonify({'message': '未提供token', 'code': 'NO_TOKEN'}), 401
    
    try:
        # 檢查 header 格式
        if not auth_header.startswith('Bearer '):
            print(f"Debug: Authorization header 格式錯誤，期望 'Bearer token'，實際: {auth_header}")
            return None, jsonify({'message': 'Authorization header 格式錯誤', 'code': 'INVALID_HEADER'}), 401
        
        token = auth_header.split(" ")[1]
        print(f"Debug: 提取的 token = {token[:20]}...")  # 只顯示前20個字符
        
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        print(f"Debug: 解碼後的 token payload = {decoded_token}")
        
        user_email = decoded_token.get('user')
        print(f"Debug: 提取的 user_email = {user_email}")
        
        if not user_email:
            print("Debug: token 中沒有 user 欄位")
            return None, jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
            
        return user_email, None, None
        
    except jwt.ExpiredSignatureError:
        print("Debug: Token 已過期")
        return None, jsonify({'message': 'Token已過期，請重新登錄', 'code': 'TOKEN_EXPIRED'}), 401
    except jwt.InvalidTokenError as e:
        print(f"Debug: 無效的 token: {e}")
        return None, jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except Exception as e:
        print(f"Debug: 驗證token時發生錯誤: {str(e)}")
        return None, jsonify({'message': '認證失敗', 'code': 'AUTH_FAILED'}), 401

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

# 移動自dashboard.py的考題查詢函數
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

@quiz_bp.route('/get-exam-to-object', methods=['POST', 'OPTIONS'])
def get_exam_to_object():
    """根據條件查詢考題數據"""
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return jsonify({'message': '未提供token'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        user_email = decoded_token.get('user')
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    
    school = request.json.get('school')
    year = request.json.get('year')
    subject = request.json.get('subject')

    # 計算有效查詢條件的數量
    valid_conditions = sum(1 for x in [school, year, subject] if x)

    # 建立查詢條件
    query = {}
    if school:
        query['school'] = school
    if year:
        query['year'] = year
    if subject:
        query['predicted_category'] = subject

    if valid_conditions == 0:
        examdata = mongo.db.exam.find()
    elif valid_conditions == 1:
        examdata = mongo.db.exam.find(query)
    else:
        examdata = mongo.db.exam.find(query)
        
    exam_list = []
    for exam in examdata:
        exam_dict = {
            'school': exam.get('school', ''),
            'department': exam.get('department', ''),
            'year': exam.get('year', ''),
            'question_number': exam.get('question_number', ''),
            'question_text': exam.get('question_text', ''),
            'type': exam.get('type', ''),
            'subject': exam.get('主要學科', ''),
            'options': exam.get('options', []),
            'textbook_source': exam.get('教科書來源', ''),
            'textbook_chapter': exam.get('教科書章節', ''),
            'exam_unit': exam.get('考點單元', ''),
            'related_concepts': exam.get('相關概念', []),
            'analysis_description': exam.get('分析說明', ''),
            'image_file': exam.get('image_file', []),
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

@quiz_bp.route('/create-quiz', methods=['POST', 'OPTIONS'])
def create_quiz():
    """創建測驗 API"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code

        # 獲取請求參數
        data = request.get_json()
        quiz_type = data.get('type')  # 'knowledge' 或 'pastexam'
        
        print(f"📝 用戶 {user_email} 請求創建 {quiz_type} 測驗")
        
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
            
        elif quiz_type == 'pastexam':
            # 考古題測驗
            school = data.get('school')
            year = data.get('year')
            department = data.get('department')
            
            if not all([school, year, department]):
                return jsonify({'message': '缺少學校、年度或系所參數'}), 400
            
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
            question = {
                'id': i + 1,
                'question_text': exam.get('question_text', ''),
                'type': exam.get('answer_type'),
                'options': exam.get('options'),
                'correct_answer': exam.get('answer', ''),
                'original_exam_id': str(exam.get('_id', '')),
                'image_file': exam.get('image_file'),
                'key_points': exam.get('key-points', '')
            }
            
            # 處理選項格式
            if isinstance(question['options'], str):
                question['options'] = [opt.strip() for opt in question['options'].split(',') if opt.strip()]
            elif not isinstance(question['options'], list):
                question['options'] = []
            
            # 處理圖片檔案
            image_file = exam.get('image_file', '')
            if image_file and image_file not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']:
                # 處理圖片文件列表
                if isinstance(image_file, list) and len(image_file) > 0:
                    # 如果是列表，取第一個檔案名
                    image_filename = image_file[0]
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
                        print(f"🖼️ 題目 {i+1} 包含圖片: {image_filename}")
                    else:
                        # 圖片檔案不存在，不設定 image_file
                        print(f"⚠️ 題目 {i+1} 圖片檔案不存在: {image_filename}")
                        question['image_file'] = ''
                else:
                    question['image_file'] = ''
            else:
                question['image_file'] = ''
            
            questions.append(question)
        
        # 生成測驗ID
        quiz_id = str(uuid.uuid4())
        
        # 準備測驗數據
        quiz_data = {
            'quiz_id': quiz_id,
            'title': quiz_title,
            'type': quiz_type,
            'creator_email': user_email,
            'create_time': datetime.now().isoformat(),
            'time_limit': 60,
            'questions': questions,
            'metadata': {
                'topic': data.get('topic'),
                'difficulty': data.get('difficulty'),
                'school': data.get('school'),
                'year': data.get('year'),
                'department': data.get('department'),
                'question_count': len(questions)
            }
        }
        
        # 保存到MongoDB
        try:
            result = mongo.db.quizzes.insert_one(quiz_data)
            if result.inserted_id:
                print(f"✅ 測驗創建成功，ID: {quiz_id}, 包含 {len(questions)} 道題目")
                
                return jsonify({
                    'message': '測驗創建成功',
                    'quiz_id': quiz_id,
                    'title': quiz_title,
                    'question_count': len(questions),
                    'time_limit': 60
                }), 200
            else:
                return jsonify({'message': '測驗創建失敗'}), 500
                
        except Exception as db_error:
            print(f"❌ 數據庫保存錯誤: {str(db_error)}")
            return jsonify({'message': f'創建失敗: {str(db_error)}'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 創建測驗時發生錯誤: {str(e)}")
        return jsonify({'message': f'創建測驗失敗: {str(e)}'}), 500


@quiz_bp.route('/get-quiz', methods=['POST', 'OPTIONS'])
def get_quiz():
    """獲取測驗詳情 API"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        # 獲取請求參數
        data = request.get_json()
        quiz_id = data.get('quiz_id')
        
        if not quiz_id:
            return jsonify({'message': '缺少 quiz_id 參數'}), 400
        
        print(f"📝 正在查詢測驗 ID: {quiz_id}")
        
        # 從MongoDB獲取測驗數據
        try:
            quiz_data = mongo.db.quizzes.find_one({'quiz_id': quiz_id})
            
            if not quiz_data:
                print(f"❌ 測驗不存在: {quiz_id}")
                return jsonify({'message': f'測驗 {quiz_id} 不存在'}), 404
            
            # 移除MongoDB的_id字段
            quiz_data.pop('_id', None)
            
            # 處理questions格式並加入圖片
            questions = quiz_data.get('questions', [])
            processed_questions = []
            
            for i, question in enumerate(questions):
                processed_question = {
                    'id': question.get('id', i + 1),
                    'question_text': question.get('question_text', ''),
                    'type': question.get('type', 'single-choice'),
                    'options': question.get('options', []),
                    'correct_answer': question.get('correct_answer', ''),
                    'original_exam_id': question.get('original_exam_id', ''),
                    'image_file': '',
                    'key_points': question.get('key_points', '')
                }
                
                # 處理圖片文件
                image_file = question.get('image_file', '')
                if image_file and image_file not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']:
                    # 處理圖片文件列表
                    if isinstance(image_file, list) and len(image_file) > 0:
                        # 如果是列表，取第一個檔案名
                        image_filename = image_file[0]
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
                            processed_question['image_file'] = image_filename
                            print(f"🖼️ 題目 {i+1} 包含圖片: {image_filename}")
                        else:
                            # 圖片檔案不存在，不設定 image_file
                            print(f"⚠️ 題目 {i+1} 圖片檔案不存在: {image_filename}")
                            processed_question['image_file'] = ''
                    else:
                        processed_question['image_file'] = ''
                else:
                    processed_question['image_file'] = ''
                
                # 確保選項是列表格式
                if isinstance(processed_question['options'], str):
                    processed_question['options'] = [opt.strip() for opt in processed_question['options'].split(',') if opt.strip()]
                elif not isinstance(processed_question['options'], list):
                    processed_question['options'] = []
                
                processed_questions.append(processed_question)
            
            print(f"✅ 成功處理測驗 {quiz_id}，包含 {len(processed_questions)} 道題目")
            
            return jsonify({
                'message': '獲取測驗成功',
                'quiz_id': quiz_data['quiz_id'],
                'title': quiz_data['title'],
                'time_limit': quiz_data.get('time_limit', 60),
                'questions': processed_questions,
                'metadata': quiz_data.get('metadata', {})
            }), 200
            
        except Exception as db_error:
            print(f"❌ 數據庫查詢錯誤: {str(db_error)}")
            return jsonify({'message': f'獲取測驗失敗: {str(db_error)}'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 獲取測驗時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取測驗失敗: {str(e)}'}), 500


@quiz_bp.route('/submit-quiz', methods=['POST', 'OPTIONS'])
def submit_quiz():
    """提交測驗答案 API - 完整流程"""
    if request.method == 'OPTIONS':
        print("Debug: 收到OPTIONS請求，回應CORS preflight")
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        # 獲取請求參數
        data = request.get_json()
        print(f"Debug: 請求資料 data={data}")
        quiz_id = data.get('quiz_id')
        answers = data.get('answers', {})
        time_taken = data.get('time_taken', 0)
        print(f"Debug: quiz_id={quiz_id}, answers={answers}, time_taken={time_taken}")
        
        if not quiz_id:
            print("Debug: quiz_id缺失")
            return jsonify({'message': '缺少 quiz_id 參數'}), 400
        
        # 獲取測驗信息
        quiz_data = mongo.db.quizzes.find_one({'quiz_id': quiz_id})
        print(f"Debug: 取得quiz_data={quiz_data}")
        if not quiz_data:
            print("Debug: 測驗不存在")
            return jsonify({'message': '測驗不存在'}), 404
        
        # 評分和分析
        questions = quiz_data.get('questions', [])
        total_questions = len(questions)
        print(f"Debug: 取得questions數量={total_questions}")
        
        # 添加題目數據調試信息
        print(f"Debug: 前3題的數據結構:")
        for i, q in enumerate(questions[:3]):
            print(f"  題目{i+1}: id={q.get('id')}, type={q.get('type')}, correct_answer={q.get('correct_answer')}")
        
        correct_count = 0
        wrong_questions = []
        scored_answers = {}
        
        # 逐題評分 - 對照exam中的answer
        for question_index_str, user_answer in answers.items():
            print(f"Debug: 處理題目 question_index_str={question_index_str}, user_answer={user_answer}")
            question_index = int(question_index_str)
            
            if question_index < len(questions):
                question = questions[question_index]
                question_id = question.get('id', question_index + 1)
                correct_answer = question.get('correct_answer')
                question_type = question.get('type', 'single-choice')
                original_exam_id = question.get('original_exam_id', '')
                
                print(f"Debug: 題目內容 question_id={question_id}, correct_answer={correct_answer}, question_type={question_type}")
                print(f"Debug: 用戶答案類型: {type(user_answer)}, 正確答案類型: {type(correct_answer)}")
                
                # 評判正確性 - 對照exam中的answer
                is_correct = False
                
                if correct_answer:
                    if question_type == 'single-choice':
                        is_correct = user_answer == correct_answer
                        print(f"Debug: 單選題比較 - 用戶: '{user_answer}' vs 正確: '{correct_answer}' = {is_correct}")
                    elif question_type == 'multiple-choice':
                        if isinstance(user_answer, list) and isinstance(correct_answer, list):
                            is_correct = sorted(user_answer) == sorted(correct_answer)
                        print(f"Debug: 多選題比較 - 用戶: {user_answer} vs 正確: {correct_answer} = {is_correct}")
                    elif question_type == 'true-false':
                        is_correct = (user_answer == correct_answer or 
                                    (user_answer == True and correct_answer in ['是', 'True', True]) or
                                    (user_answer == False and correct_answer in ['否', 'False', False]))
                        print(f"Debug: 是非題比較 - 用戶: {user_answer} vs 正確: {correct_answer} = {is_correct}")
                    elif question_type in ['fill-in-the-blank', 'short-answer', 'long-answer']:
                        user_text = str(user_answer).strip().lower()
                        correct_text = str(correct_answer).strip().lower()
                        
                        # 直接比較答案，不檢查測試答案
                        if user_text == correct_text:
                            is_correct = True
                        elif len(user_text) > 3 and len(correct_text) > 3:
                            # 對於較長的答案，檢查關鍵詞匹配
                            user_words = set(user_text.split())
                            correct_words = set(correct_text.split())
                            if len(user_words.intersection(correct_words)) >= min(len(user_words), len(correct_words)) * 0.7:
                                is_correct = True
                        elif len(user_text) <= 3 and len(correct_text) <= 3:
                            # 對於短答案，允許部分匹配
                            if user_text in correct_text or correct_text in user_text:
                                is_correct = True
                        
                        print(f"Debug: 文字題比較 - 用戶答案: '{user_text}', 正確答案: '{correct_text}', 是否正確: {is_correct}")
                else:
                    print(f"Debug: 題目 {question_index} 沒有正確答案")
                
                print(f"Debug: 最終評分結果 - 題目 {question_index}: is_correct={is_correct}")
                
                # 記錄評分結果
                scored_answers[question_index_str] = {
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'is_correct': is_correct,
                    'question_text': question.get('question_text', ''),
                    'question_type': question_type,
                    'options': question.get('options', []),
                    'image_file': question.get('image_file', ''),
                    'score': 1 if is_correct else 0
                }
                
                if is_correct:
                    correct_count += 1
                else:
                    # 收集錯題信息 - 準備保存到error_questions
                    wrong_questions.append({
                        'question_id': question_id,
                        'question_text': question.get('question_text', ''),
                        'question_type': question_type,
                        'user_answer': user_answer,
                        'correct_answer': correct_answer,
                        'options': question.get('options', []),
                        'image_file': question.get('image_file', ''),
                        'original_exam_id': original_exam_id,
                        'question_index': question_index
                    })
                    print(f"Debug: 錯題收集 question_id={question_id}")
        
        # 確保所有題目都被記錄到submissions中，未作答的題目記錄為空字串
        for i in range(total_questions):
            question_index_str = str(i)
            if question_index_str not in scored_answers:
                # 未作答的題目，記錄為空字串
                question = questions[i]
                scored_answers[question_index_str] = {
                    'user_answer': '',
                    'correct_answer': question.get('correct_answer', ''),
                    'is_correct': False,
                    'question_text': question.get('question_text', ''),
                    'question_type': question.get('type', 'single-choice'),
                    'options': question.get('options', []),
                    'image_file': question.get('image_file', ''),
                    'score': 0
                }
                print(f"Debug: 記錄未作答題目 {i}: 空字串")
        
        # 計算統計數據
        # 計算實際有答案的題目數量（不包括空字串）
        answered_count = sum(1 for answer_data in scored_answers.values() 
                           if answer_data['user_answer'] and str(answer_data['user_answer']).strip() != '')
        correct_count = sum(1 for answer_data in scored_answers.values() if answer_data['is_correct'])
        wrong_count = sum(1 for answer_data in scored_answers.values() 
                         if answer_data['user_answer'] and str(answer_data['user_answer']).strip() != '' and not answer_data['is_correct'])
        unanswered_count = total_questions - answered_count
        
        # 驗證統計數據的一致性
        if correct_count + wrong_count != answered_count:
            print(f"⚠️ 統計數據不一致: 正確({correct_count}) + 錯誤({wrong_count}) != 作答({answered_count})")
            # 重新計算錯誤題數
            wrong_count = answered_count - correct_count
            print(f"修正後錯誤題數: {wrong_count}")
        
        # 添加詳細的統計調試信息
        print(f"Debug: 詳細統計信息:")
        print(f"  - 總題數: {total_questions}")
        print(f"  - 已作答題數: {answered_count}")
        print(f"  - 正確題數: {correct_count}")
        print(f"  - 錯誤題數: {wrong_count}")
        print(f"  - 未答題數: {unanswered_count}")
        print(f"  - 作答題目索引: {list(answers.keys())}")
        print(f"  - 錯題列表長度: {len(wrong_questions)}")
        
        # 檢查每個題目的狀態
        for i in range(total_questions):
            question_index_str = str(i)
            answer_data = scored_answers.get(question_index_str, {})
            user_answer = answer_data.get('user_answer', '')
            is_correct = answer_data.get('is_correct', False)
            has_answer = user_answer and str(user_answer).strip() != ''
            status = '已作答' if has_answer else '未作答'
            correctness = '正確' if is_correct else '錯誤' if has_answer else '未作答'
            print(f"  - 題目 {i}: {status} ({correctness}) - 答案: '{user_answer}'")
        
        accuracy_rate = (correct_count / total_questions * 100) if total_questions > 0 else 0
        average_score = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        print(f"Debug: 統計計算 - 總題數: {total_questions}, 作答: {answered_count}, 正確: {correct_count}, 錯誤: {wrong_count}, 未答: {unanswered_count}")
        
        # 生成提交ID
        submission_id = str(uuid.uuid4())
        print(f"Debug: 產生submission_id={submission_id}")
        
        # 獲取用戶信息
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            user_info = get_user_info(token, 'name')
        else:
            print("Debug: Authorization header 格式錯誤")
            return jsonify({'message': 'Authorization header 格式錯誤'}), 401
        
        print(f"Debug: 取得用戶資訊 user_info={user_info}")
        if not user_info:
            print("Debug: 用戶不存在")
            return jsonify({'message': '用戶不存在'}), 404
        
        # 準備提交記錄 - 保存整張考卷到submissions
        print(user_info)
        submission_data = {
            'submission_id': submission_id,
            'quiz_id': quiz_id,
            'user_email': user_email,
            'user_name': user_info,
            'quiz_title': quiz_data.get('title', ''),
            'quiz_type': quiz_data.get('type', 'unknown'),
            'submit_time': datetime.now().isoformat(),
            'time_taken': time_taken,
            'total_questions': total_questions,
            'answered_questions': answered_count,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'unanswered_count': unanswered_count,
            'accuracy_rate': round(accuracy_rate, 2),
            'score': round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0,
            'answers': scored_answers,  # 整張考卷的所有答案
            'wrong_questions': wrong_questions,
            'metadata': quiz_data.get('metadata', {})
        }
        print(f"Debug: 準備存入MongoDB的資料 submission_data={submission_data}")
        
        # 保存到MongoDB - submissions集合（整張考卷）
        try:
            result = mongo.db.submissions.insert_one(submission_data)
            print(f"Debug: MongoDB insert result={result.inserted_id}")
            if result.inserted_id:
                print(f"✅ 整張考卷成功保存到MongoDB submissions，ID: {submission_id}")
                
                # 同時保存錯題到 error_questions 集合
                if wrong_questions:
                    print(f"📝 開始保存錯題到 error_questions 集合，數量: {len(wrong_questions)}")
                    error_records = []
                    
                    for wrong_q in wrong_questions:
                        error_record = {
                            'error_id': str(uuid.uuid4()),
                            'submission_id': submission_id,
                            'quiz_id': quiz_id,
                            'user_email': user_email,
                            'question_id': wrong_q['question_id'],
                            'question_text': wrong_q['question_text'],
                            'question_type': wrong_q['question_type'],
                            'user_answer': wrong_q['user_answer'],
                            'correct_answer': wrong_q['correct_answer'],
                            'options': wrong_q.get('options', []),
                            'image_file': wrong_q.get('image_file', ''),
                            'original_exam_id': wrong_q.get('original_exam_id', ''),
                            'question_index': wrong_q['question_index'],
                            'error_time': datetime.now().isoformat(),
                            'quiz_title': quiz_data.get('title', ''),
                            'quiz_type': quiz_data.get('type', 'unknown'),
                            'metadata': quiz_data.get('metadata', {})
                        }
                        error_records.append(error_record)
                        print(f"📝 準備錯題記錄: {error_record['error_id']}")
                    
                    # 批量插入錯題記錄
                    if error_records:
                        error_result = mongo.db.error_questions.insert_many(error_records)
                        print(f"✅ 錯題記錄成功保存到 error_questions 集合，數量: {len(error_result.inserted_ids)}")
                
                # 可選：同時保存錯題到 Redis 快取（用於鞏固錯題）
                try:
                    print(f"🔍 開始保存錯題到 Redis，用戶: {user_email}，錯題數量: {len(wrong_questions)}")
                    
                    # 使用 FlaskRedis
                    r = redis_client
                    print("✅ Redis 連接創建成功")
                    
                    # 為用戶創建錯題快取 key
                    user_error_key = f"user_errors:{user_email}"
                    print(f"🔍 用戶錯題 key: {user_error_key}")
                    
                    # 獲取現有的錯題數據
                    existing_errors = r.get(user_error_key)
                    if existing_errors:
                        # 處理bytes到string的轉換
                        if isinstance(existing_errors, bytes):
                            existing_errors = existing_errors.decode('utf-8')
                        error_list = json.loads(existing_errors)
                        print(f"📊 找到現有錯題數據，數量: {len(error_list)}")
                    else:
                        error_list = []
                        print("📊 沒有現有錯題數據，創建新列表")
                    
                    # 添加新的錯題
                    for i, wrong_q in enumerate(wrong_questions):
                        error_item = {
                            'error_id': str(uuid.uuid4()),
                            'submission_id': submission_id,
                            'quiz_id': quiz_id,
                            'quiz_title': quiz_data.get('title', ''),
                            'question_id': wrong_q['question_id'],
                            'question_text': wrong_q['question_text'],
                            'question_type': wrong_q['question_type'],
                            'user_answer': wrong_q['user_answer'],
                            'correct_answer': wrong_q['correct_answer'],
                            'options': wrong_q.get('options', []),
                            'image_file': wrong_q.get('image_file', ''),
                            'original_exam_id': wrong_q.get('original_exam_id', ''),
                            'question_index': wrong_q['question_index'],
                            'error_time': datetime.now().isoformat()
                        }
                        error_list.append(error_item)
                        print(f"📝 添加錯題 {i+1}: {wrong_q['question_id']}")
                    
                    # 保存到 Redis，設置 24 小時過期
                    json_data = json.dumps(error_list, ensure_ascii=False)
                    print(f"📊 準備保存到 Redis 的數據長度: {len(json_data)}")
                    r.setex(user_error_key, 86400, json_data)
                    print(f"✅ 錯題數據已保存到 Redis 快取，用戶: {user_email}，錯題數量: {len(error_list)}")
                    
                    # 驗證保存是否成功
                    verification_data = r.get(user_error_key)
                    if verification_data:
                        print("✅ Redis 保存驗證成功")
                    else:
                        print("❌ Redis 保存驗證失敗")
                    
                except Exception as redis_error:
                    print(f"⚠️ Redis 快取保存失敗: {str(redis_error)}")
                    print(f"⚠️ Redis 錯誤類型: {type(redis_error).__name__}")
                    import traceback
                    print(f"⚠️ Redis 錯誤堆疊: {traceback.format_exc()}")
                    # Redis 保存失敗不影響主要功能
                
                print(f"評分統計: 總題數 {total_questions}, 作答 {answered_count}, 正確 {correct_count}, 正確率 {accuracy_rate:.2f}%")
                
                return jsonify({
                    'message': '測驗提交成功',
                    'submission_id': submission_id,
                    'status': 'success',
                    'statistics': {
                        'total_questions': total_questions,
                        'answered_questions': answered_count,
                        'correct_count': correct_count,
                        'wrong_count': wrong_count,
                        'unanswered_count': unanswered_count,
                        'accuracy_rate': round(accuracy_rate, 2),
                        'average_score': round(average_score, 2)
                    },
                    'wrong_questions_count': len(wrong_questions),
                    'quiz_completed': True
                }), 200
            else:
                print("Debug: MongoDB插入失敗")
                return jsonify({'message': '保存失敗'}), 500
                
        except Exception as db_error:
            print(f"數據庫保存錯誤: {str(db_error)}")
            return jsonify({'message': f'保存失敗: {str(db_error)}'}), 500
        
    except jwt.InvalidTokenError:
        print("Debug: jwt.InvalidTokenError 無效的token")
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"提交測驗時發生錯誤: {str(e)}")
        print(f"錯誤類型: {type(e).__name__}")
        import traceback
        print(f"錯誤堆疊: {traceback.format_exc()}")
        return jsonify({'message': f'提交測驗失敗: {str(e)}'}), 500 

@quiz_bp.route('/get-user-errors', methods=['POST', 'OPTIONS'])
def get_user_errors():
    """獲取用戶錯題數據 API"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        # 獲取請求參數
        data = request.get_json()
        submission_id = data.get('submission_id')
        
        if not submission_id:
            return jsonify({'message': '缺少 submission_id 參數'}), 400
        
        print(f"📝 正在查詢測驗結果 ID: {submission_id}")
        
        # 從MongoDB獲取測驗結果
        try:
            submission_data = mongo.db.submissions.find_one({'submission_id': submission_id})
            
            if not submission_data:
                print(f"❌ 測驗結果不存在: {submission_id}")
                return jsonify({'message': f'測驗結果 {submission_id} 不存在'}), 404
            
            # 提取錯題數據
            wrong_questions = submission_data.get('wrong_questions', [])
            statistics = {
                'total_questions': submission_data.get('total_questions', 0),
                'answered_questions': len(submission_data.get('answers', {})),
                'correct_count': submission_data.get('correct_count', 0),
                'wrong_count': len(wrong_questions),
                'accuracy_rate': submission_data.get('score', 0),
                'time_taken': submission_data.get('time_taken', 0)
            }
            
            print(f"✅ 成功獲取測驗結果 {submission_id}，包含 {len(wrong_questions)} 道錯題")
            
            return jsonify({
                'message': '獲取錯題數據成功',
                'submission_id': submission_id,
                'quiz_title': submission_data.get('quiz_title', ''),
                'statistics': statistics,
                'wrong_questions': wrong_questions
            }), 200
            
        except Exception as db_error:
            print(f"❌ 數據庫查詢錯誤: {str(db_error)}")
            return jsonify({'message': f'獲取錯題數據失敗: {str(db_error)}'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 獲取錯題數據時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取錯題數據失敗: {str(e)}'}), 500 

@quiz_bp.route('/get-user-errors-redis', methods=['POST', 'OPTIONS'])
def get_user_errors_redis():
    """從 Redis 獲取用戶錯題數據 API"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        print(f"📝 正在從 Redis 查詢用戶錯題: {user_email}")
        
        # 從 Redis 獲取錯題數據
        try:
            # 創建 Redis 連接
            r = redis_client
            
            user_error_key = f"user_errors:{user_email}"
            error_data = r.get(user_error_key)
            
            if error_data:
                error_list = json.loads(error_data)
                print(f"✅ 成功從 Redis 獲取錯題數據，用戶: {user_email}，錯題數量: {len(error_list)}")
                
                return jsonify({
                    'message': '獲取錯題數據成功',
                    'user_email': user_email,
                    'error_count': len(error_list),
                    'errors': error_list
                }), 200
            else:
                print(f"📝 用戶 {user_email} 在 Redis 中沒有錯題數據")
                return jsonify({
                    'message': '沒有找到錯題數據',
                    'user_email': user_email,
                    'error_count': 0,
                    'errors': []
                }), 200
            
        except Exception as redis_error:
            print(f"❌ Redis 查詢錯誤: {str(redis_error)}")
            return jsonify({'message': f'獲取錯題數據失敗: {str(redis_error)}'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 獲取錯題數據時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取錯題數據失敗: {str(e)}'}), 500 

@quiz_bp.route('/get-user-errors-mongo', methods=['POST', 'OPTIONS'])
def get_user_errors_mongo():
    """從 MongoDB error_questions 集合獲取用戶錯題數據 API"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        print(f"📝 正在從 MongoDB error_questions 查詢用戶錯題: {user_email}")
        
        # 從 MongoDB error_questions 集合獲取錯題數據
        try:
            # 查詢用戶的所有錯題記錄
            error_records = list(mongo.db.error_questions.find(
                {'user_email': user_email},
                {'_id': 0}  # 排除MongoDB的_id字段
            ).sort('error_time', -1))  # 按時間倒序排列
            
            print(f"✅ 成功從 MongoDB error_questions 獲取錯題數據，用戶: {user_email}，錯題數量: {len(error_records)}")
            
            return jsonify({
                'message': '獲取錯題數據成功',
                'user_email': user_email,
                'error_count': len(error_records),
                'errors': error_records
            }), 200
            
        except Exception as mongo_error:
            print(f"❌ MongoDB 查詢錯誤: {str(mongo_error)}")
            return jsonify({'message': f'獲取錯題數據失敗: {str(mongo_error)}'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 獲取錯題數據時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取錯題數據失敗: {str(e)}'}), 500 

@quiz_bp.route('/get-user-submissions-analysis', methods=['POST', 'OPTIONS'])
def get_user_submissions_analysis():
    """從 MongoDB submissions 集合獲取用戶完整測驗數據進行分析"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        print(f"📝 正在從 MongoDB submissions 查詢用戶測驗數據: {user_email}")
        
        # 從 MongoDB submissions 集合獲取用戶的所有測驗記錄
        try:
            # 查詢用戶的所有提交記錄
            submissions = list(mongo.db.submissions.find(
                {'user_email': user_email},
                {'_id': 0}  # 排除MongoDB的_id字段
            ).sort('submit_time', -1))  # 按時間倒序排列
            
            print(f"✅ 成功從 MongoDB submissions 獲取測驗數據，用戶: {user_email}，測驗數量: {len(submissions)}")
            
            # 統計數據
            total_submissions = len(submissions)
            total_questions = sum(sub.get('total_questions', 0) for sub in submissions)
            total_correct = sum(sub.get('correct_count', 0) for sub in submissions)
            total_wrong = sum(sub.get('wrong_count', 0) for sub in submissions)
            total_unanswered = sum(sub.get('unanswered_count', 0) for sub in submissions)
            
            return jsonify({
                'message': '獲取測驗數據成功',
                'user_email': user_email,
                'statistics': {
                    'total_submissions': total_submissions,
                    'total_questions': total_questions,
                    'total_correct': total_correct,
                    'total_wrong': total_wrong,
                    'total_unanswered': total_unanswered,
                    'overall_accuracy': round((total_correct / total_questions * 100), 2) if total_questions > 0 else 0
                },
                'submissions': submissions
            }), 200
            
        except Exception as mongo_error:
            print(f"❌ MongoDB 查詢錯誤: {str(mongo_error)}")
            return jsonify({'message': f'獲取測驗數據失敗: {str(mongo_error)}'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 獲取測驗數據時發生錯誤: {str(e)}")
        return jsonify({'message': f'獲取測驗數據失敗: {str(e)}'}), 500 

@quiz_bp.route('/view-quiz-result', methods=['POST', 'OPTIONS'])
def view_quiz_result():
    """檢視測驗結果 API - 從submissions載入數據並統計"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        # 獲取請求參數
        data = request.get_json()
        submission_id = data.get('submission_id')
        
        if not submission_id:
            return jsonify({'message': '缺少 submission_id 參數'}), 400
        
        print(f"📝 正在檢視測驗結果 ID: {submission_id}")
        
        # 從MongoDB獲取測驗結果
        try:
            submission_data = mongo.db.submissions.find_one({'submission_id': submission_id})
            
            if not submission_data:
                print(f"❌ 測驗結果不存在: {submission_id}")
                return jsonify({'message': f'測驗結果 {submission_id} 不存在'}), 404
            
            # 從submissions中提取數據並統計
            answers = submission_data.get('answers', {})
            total_questions = submission_data.get('total_questions', 0)
            
            # 統計各種題目狀態
            correct_questions = []
            wrong_questions = []
            unanswered_questions = []
            
            for question_index_str, answer_data in answers.items():
                question_index = int(question_index_str)
                user_answer = answer_data.get('user_answer', '')
                is_correct = answer_data.get('is_correct', False)
                has_answer = user_answer and str(user_answer).strip() != ''
                
                question_info = {
                    'question_index': question_index,
                    'question_text': answer_data.get('question_text', ''),
                    'question_type': answer_data.get('question_type', ''),
                    'user_answer': user_answer,
                    'correct_answer': answer_data.get('correct_answer', ''),
                    'options': answer_data.get('options', []),
                    'image_file': answer_data.get('image_file', ''),
                    'is_correct': is_correct
                }
                
                if has_answer:
                    if is_correct:
                        correct_questions.append(question_info)
                    else:
                        wrong_questions.append(question_info)
                else:
                    unanswered_questions.append(question_info)
            
            # 統計數據
            statistics = {
                'total_questions': total_questions,
                'correct_count': len(correct_questions),
                'wrong_count': len(wrong_questions),
                'unanswered_count': len(unanswered_questions),
                'answered_count': len(correct_questions) + len(wrong_questions),
                'accuracy_rate': submission_data.get('accuracy_rate', 0),
                'score': submission_data.get('score', 0),
                'time_taken': submission_data.get('time_taken', 0)
            }
            
            print(f"✅ 成功檢視測驗結果 {submission_id}")
            print(f"📊 統計: 總題數={total_questions}, 正確={len(correct_questions)}, 錯誤={len(wrong_questions)}, 未答={len(unanswered_questions)}")
            
            return jsonify({
                'message': '檢視測驗結果成功',
                'submission_id': submission_id,
                'quiz_title': submission_data.get('quiz_title', ''),
                'quiz_type': submission_data.get('quiz_type', ''),
                'submit_time': submission_data.get('submit_time', ''),
                'statistics': statistics,
                'correct_questions': correct_questions,
                'wrong_questions': wrong_questions,
                'unanswered_questions': unanswered_questions,
                'all_questions': list(answers.values())  # 所有題目的完整數據
            }), 200
            
        except Exception as db_error:
            print(f"❌ 數據庫查詢錯誤: {str(db_error)}")
            return jsonify({'message': f'檢視測驗結果失敗: {str(db_error)}'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 檢視測驗結果時發生錯誤: {str(e)}")
        return jsonify({'message': f'檢視測驗結果失敗: {str(e)}'}), 500 

@quiz_bp.route('/consolidate-errors', methods=['POST', 'OPTIONS'])
def consolidate_errors():
    """鞏固錯題 API - 支持兩種方式載入錯題"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證token
        user_email, error_response, status_code = verify_token()
        if error_response:
            return error_response, status_code
        
        if not user_email:
            return jsonify({'message': '無效的token'}), 401
        
        # 獲取請求參數
        data = request.get_json()
        source = data.get('source', 'error_questions')  # 'error_questions' 或 'redis'
        submission_id = data.get('submission_id')  # 可選，用於指定特定測驗的錯題
        
        print(f"📝 開始鞏固錯題，用戶: {user_email}，來源: {source}")
        
        error_questions = []
        
        if source == 'error_questions':
            # 方式1：從 MongoDB error_questions 集合載入
            try:
                query = {'user_email': user_email}
                if submission_id:
                    query['submission_id'] = submission_id
                
                error_records = list(mongo.db.error_questions.find(
                    query,
                    {'_id': 0}  # 排除MongoDB的_id字段
                ).sort('error_time', -1))  # 按時間倒序排列
                
                print(f"✅ 從 error_questions 載入錯題，數量: {len(error_records)}")
                
                # 轉換為統一格式
                for record in error_records:
                    error_questions.append({
                        'error_id': record.get('error_id'),
                        'question_id': record.get('question_id'),
                        'question_text': record.get('question_text', ''),
                        'question_type': record.get('question_type', ''),
                        'user_answer': record.get('user_answer', ''),
                        'correct_answer': record.get('correct_answer', ''),
                        'options': record.get('options', []),
                        'image_file': record.get('image_file', ''),
                        'original_exam_id': record.get('original_exam_id', ''),
                        'question_index': record.get('question_index', 0),
                        'error_time': record.get('error_time', ''),
                        'quiz_title': record.get('quiz_title', ''),
                        'quiz_type': record.get('quiz_type', ''),
                        'source': 'error_questions'
                    })
                
            except Exception as mongo_error:
                print(f"❌ MongoDB error_questions 查詢錯誤: {str(mongo_error)}")
                return jsonify({'message': f'載入錯題失敗: {str(mongo_error)}'}), 500
                
        elif source == 'redis':
            # 方式2：從 Redis 快取載入
            try:
                r = redis_client
                user_error_key = f"user_errors:{user_email}"
                error_data = r.get(user_error_key)
                
                if error_data:
                    # 處理bytes到string的轉換
                    if isinstance(error_data, bytes):
                        error_data = error_data.decode('utf-8')
                    
                    error_list = json.loads(error_data)
                    print(f"✅ 從 Redis 載入錯題，數量: {len(error_list)}")
                    
                    # 轉換為統一格式
                    for record in error_list:
                        error_questions.append({
                            'error_id': record.get('error_id'),
                            'question_id': record.get('question_id'),
                            'question_text': record.get('question_text', ''),
                            'question_type': record.get('question_type', ''),
                            'user_answer': record.get('user_answer', ''),
                            'correct_answer': record.get('correct_answer', ''),
                            'options': record.get('options', []),
                            'image_file': record.get('image_file', ''),
                            'original_exam_id': record.get('original_exam_id', ''),
                            'question_index': record.get('question_index', 0),
                            'error_time': record.get('error_time', ''),
                            'quiz_title': record.get('quiz_title', ''),
                            'quiz_type': record.get('quiz_type', ''),
                            'source': 'redis'
                        })
                else:
                    print(f"📝 用戶 {user_email} 在 Redis 中沒有錯題數據")
                    
            except Exception as redis_error:
                print(f"❌ Redis 查詢錯誤: {str(redis_error)}")
                return jsonify({'message': f'載入錯題失敗: {str(redis_error)}'}), 500
        else:
            return jsonify({'message': '無效的來源參數'}), 400
        
        # 統計錯題數據
        statistics = {
            'total_errors': len(error_questions),
            'source': source,
            'user_email': user_email
        }
        
        # 按題目類型分組
        type_groups = {}
        for error in error_questions:
            question_type = error.get('question_type', 'unknown')
            if question_type not in type_groups:
                type_groups[question_type] = []
            type_groups[question_type].append(error)
        
        statistics['type_groups'] = {k: len(v) for k, v in type_groups.items()}
        
        print(f"✅ 鞏固錯題準備完成，總錯題數: {len(error_questions)}")
        
        return jsonify({
            'message': '鞏固錯題載入成功',
            'source': source,
            'statistics': statistics,
            'error_questions': error_questions,
            'type_groups': type_groups
        }), 200
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"❌ 鞏固錯題時發生錯誤: {str(e)}")
        return jsonify({'message': f'鞏固錯題失敗: {str(e)}'}), 500 