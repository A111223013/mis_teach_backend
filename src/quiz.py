from flask import jsonify, request, Blueprint, current_app
import uuid
from accessories import mongo, sqldb
from src.api import get_user_info, verify_token
import jwt
from datetime import datetime
import random
import base64
import os

quiz_bp = Blueprint('quiz', __name__)

def init_quiz_tables():
    """初始化測驗相關的SQL表格"""
    try:
        with current_app.app_context():
            # 創建quiz_history表
            sqldb.engine.execute("""
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
                )
            """)
            
            # 創建quiz_errors表
            sqldb.engine.execute("""
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
                )
            """)
            
            print("✅ Quiz SQL tables initialized successfully")
            return True
    except Exception as e:
        print(f"❌ Failed to initialize quiz tables: {e}")
        return False

def verify_token():
    """驗證JWT token"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return None, jsonify({'message': '未提供token', 'code': 'NO_TOKEN'}), 401
    
    try:
        token = auth_header.split(" ")[1]
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        user_email = decoded_token.get('user')
        
        if not user_email:
            return None, jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
            
        return user_email, None, None
        
    except jwt.ExpiredSignatureError:
        return None, jsonify({'message': 'Token已過期，請重新登錄', 'code': 'TOKEN_EXPIRED'}), 401
    except jwt.InvalidTokenError:
        return None, jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
    except Exception as e:
        print(f"驗證token時發生錯誤: {str(e)}")
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
            print(f"圖片檔案不存在: {image_path}")
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
                'image_file': exam.get('image_file')
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
                    question['image_file'] = image_file[0]  # 取第一張圖片
                elif isinstance(image_file, str):
                    question['image_file'] = image_file
                
                if question['image_file']:
                    print(f"🖼️ 題目 {i+1} 包含圖片: {question['image_file']}")
            
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
                    'image_file': ''
                }
                
                # 處理圖片文件
                image_file = question.get('image_file', '')
                if image_file and image_file not in ['沒有圖片', '不需要圖片', '不須圖片', '不須照片', '沒有考卷', '']:
                    processed_question['image_file'] = image_file
                    print(f"🖼️ 題目 {i+1} 包含圖片: {image_file}")
                
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
    """提交測驗答案 API"""
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
        
        if not answers:
            print("Debug: answers缺失")
            return jsonify({'message': '缺少答案數據'}), 400
        
        # 獲取用戶信息
        user_info = get_user_info(request.headers.get('Authorization'), 'name')
        print(f"Debug: 取得用戶資訊 user_info={user_info}")
        if not user_info:
            print("Debug: 用戶不存在")
            return jsonify({'message': '用戶不存在'}), 404
        
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
        correct_count = 0
        wrong_questions = []
        scored_answers = {}
        
        # 逐題評分
        for question_index_str, user_answer in answers.items():
            print(f"Debug: 處理題目 question_index_str={question_index_str}, user_answer={user_answer}")
            question_index = int(question_index_str)
            
            if question_index < len(questions):
                question = questions[question_index]
                question_id = question.get('id', question_index + 1)
                correct_answer = question.get('correct_answer')
                question_type = question.get('type', 'single-choice')
                print(f"Debug: 題目內容 question_id={question_id}, correct_answer={correct_answer}, question_type={question_type}")
                
                # 評判正確性
                is_correct = False
                
                if correct_answer:
                    if question_type == 'single-choice':
                        is_correct = user_answer == correct_answer
                    elif question_type == 'multiple-choice':
                        if isinstance(user_answer, list) and isinstance(correct_answer, list):
                            is_correct = sorted(user_answer) == sorted(correct_answer)
                    elif question_type == 'true-false':
                        is_correct = (user_answer == correct_answer or 
                                    (user_answer == True and correct_answer in ['是', 'True', True]) or
                                    (user_answer == False and correct_answer in ['否', 'False', False]))
                    elif question_type in ['fill-in-the-blank', 'short-answer', 'long-answer']:
                        user_text = str(user_answer).strip().lower()
                        correct_text = str(correct_answer).strip().lower()
                        is_correct = user_text == correct_text or user_text in correct_text or correct_text in user_text
                print(f"Debug: is_correct={is_correct}")
                
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
                    # 收集錯題信息
                    wrong_questions.append({
                        'question_id': question_id,
                        'question_text': question.get('question_text', ''),
                        'question_type': question_type,
                        'user_answer': user_answer,
                        'correct_answer': correct_answer,
                        'options': question.get('options', []),
                        'image_file': question.get('image_file', ''),
                        'original_exam_id': question.get('original_exam_id', ''),
                        'question_index': question_index
                    })
                    print(f"Debug: 錯題收集 question_id={question_id}")
        
        # 計算統計數據
        answered_count = len(answers)
        accuracy_rate = (correct_count / answered_count * 100) if answered_count > 0 else 0
        average_score = (correct_count / answered_count * 100) if answered_count > 0 else 0
        print(f"Debug: 統計 answered_count={answered_count}, correct_count={correct_count}, accuracy_rate={accuracy_rate}, average_score={average_score}")
        
        # 生成提交ID
        submission_id = str(uuid.uuid4())
        print(f"Debug: 產生submission_id={submission_id}")
        
        # 準備保存到MongoDB的數據
        submission_data = {
            'submission_id': submission_id,
            'quiz_id': quiz_id,
            'user_email': user_email,
            'user_name': user_info,
            'quiz_title': quiz_data.get('title', ''),
            'quiz_type': quiz_data.get('type', 'unknown'),
            'quiz_metadata': quiz_data.get('metadata', {}),
            'answers': answers,
            'scored_answers': scored_answers,
            'time_taken': time_taken,
            'submit_time': datetime.now().isoformat(),
            'status': 'completed',
            'statistics': {
                'total_questions': total_questions,
                'answered_questions': answered_count,
                'correct_count': correct_count,
                'wrong_count': len(wrong_questions),
                'accuracy_rate': round(accuracy_rate, 2),
                'average_score': round(average_score, 2)
            },
            'wrong_questions': wrong_questions,
            'type': 'quiz_submission'
        }
        print(f"Debug: 準備存入MongoDB的資料 submission_data={submission_data}")
        
        # 保存到MongoDB
        try:
            result = mongo.db.submissions.insert_one(submission_data)
            print(f"Debug: MongoDB insert result={result.inserted_id}")
            if result.inserted_id:
                print(f"測驗提交成功保存到MongoDB，ID: {submission_id}")
                
                # 同時保存到SQL數據庫
                try:
                    # 獲取quiz metadata
                    metadata = quiz_data.get('metadata', {})
                    print(f"Debug: SQL metadata={metadata}")
                    
                    # 插入quiz_history記錄
                    quiz_history_sql = """
                        INSERT INTO quiz_history (
                            quiz_id, user_email, user_name, quiz_title, quiz_type,
                            school, department, year, subject, total_questions,
                            answered_questions, correct_count, wrong_count,
                            accuracy_rate, average_score, time_taken, submit_time, status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    
                    with sqldb.engine.connect() as conn:
                        # 插入quiz_history
                        print("Debug: 開始插入quiz_history")
                        result_sql = conn.execute(quiz_history_sql, (
                            quiz_id, user_email, user_info, quiz_data.get('title', ''),
                            quiz_data.get('type', 'unknown'),
                            metadata.get('school', ''), metadata.get('department', ''),
                            metadata.get('year', ''), metadata.get('topic', ''),
                            total_questions, answered_count, correct_count, len(wrong_questions),
                            round(accuracy_rate, 2), round(average_score, 2),
                            time_taken, datetime.now(), 'completed'
                        ))
                        print(f"Debug: quiz_history插入完成，lastrowid={result_sql.lastrowid}")
                        
                        # 獲取插入的quiz_history_id
                        quiz_history_id = result_sql.lastrowid
                        
                        # 插入錯題記錄到quiz_errors
                        if wrong_questions:
                            error_sql = """
                                INSERT INTO quiz_errors (
                                    quiz_history_id, user_email, question_id, question_text,
                                    question_type, user_answer, correct_answer, mistake_content,
                                    question_options, image_file, original_exam_id,
                                    question_index, error_time
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """
                            print(f"Debug: 準備插入錯題數量={len(wrong_questions)}")
                            for wrong_q in wrong_questions:
                                mistake_content = f"用戶回答：{wrong_q['user_answer']}，正確答案：{wrong_q['correct_answer']}"
                                import json
                                options_json = json.dumps(wrong_q.get('options', []), ensure_ascii=False)
                                print(f"Debug: 插入錯題 question_id={wrong_q['question_id']}, mistake_content={mistake_content}")
                                
                                conn.execute(error_sql, (
                                    quiz_history_id, user_email, str(wrong_q['question_id']),
                                    wrong_q['question_text'], wrong_q['question_type'],
                                    str(wrong_q['user_answer']), str(wrong_q['correct_answer']),
                                    mistake_content, options_json, wrong_q.get('image_file', ''),
                                    wrong_q.get('original_exam_id', ''), wrong_q['question_index'],
                                    datetime.now()
                                ))
                        
                        print(f"✅ 測驗記錄成功保存到SQL數據庫，quiz_history_id: {quiz_history_id}")
                    
                except Exception as sql_error:
                    print(f"⚠️ SQL數據庫保存失敗，但MongoDB保存成功: {str(sql_error)}")
                    # SQL保存失敗不影響主要功能，繼續返回成功
                
                print(f"評分統計: 總題數 {total_questions}, 作答 {answered_count}, 正確 {correct_count}, 正確率 {accuracy_rate:.2f}%")
                
                return jsonify({
                    'message': '測驗提交成功',
                    'submission_id': submission_id,
                    'status': 'success',
                    'statistics': {
                        'total_questions': total_questions,
                        'answered_questions': answered_count,
                        'correct_count': correct_count,
                        'wrong_count': len(wrong_questions),
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
        return jsonify({'message': f'提交測驗失敗: {str(e)}'}), 500 