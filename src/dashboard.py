from werkzeug.security import generate_password_hash
from flask_mail import Message
from flask import jsonify, request, redirect, url_for, Blueprint, current_app
import uuid
from accessories import mail, redis_client, mongo, save_json_to_mongo
from src.api import get_user_info, verify_token
from bson.objectid import ObjectId
import jwt
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/get-user-name', methods=['POST', 'OPTIONS'])
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
    user_name = get_user_info(token, 'name')
    return jsonify({'name': user_name}), 200

@dashboard_bp.route('/get-exam', methods=['POST', 'OPTIONS'])
def get_exam():
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
    
    examdata = mongo.db.exam.find()
    exam_list = []
    for exam in examdata:
        exam_dict = {
            'id': str(exam['_id']),
            'school': exam['school'],
            'department': exam['department'],
            'year': exam['year'],
            'question_number': exam['question_number'],
            'question_text': exam['question_text'],
            'type': exam['type'],
            'predicted_category': exam['predicted_category']
        }
        exam_list.append(exam_dict)
    

    if not auth_header:
        return jsonify({'message': '未提供token'}), 401
    token = auth_header.split(" ")[1]
 
    return jsonify({'exams': exam_list}), 200

@dashboard_bp.route('/get-exam-to-object', methods=['POST', 'OPTIONS'])
def get_exam_to_object():
    if request.method == 'OPTIONS':
        return '', 204
    auth_header = request.headers.get('Authorization')
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
            'id': str(exam['_id']),
            'school': exam['school'],
            'department': exam['department'],
            'year': exam['year'],
            'question_number': exam['question_number'],
            'question_text': exam['question_text'],
            'type': exam['type'],
            'predicted_category': exam['predicted_category'],
            'options': exam.get('options', []),
            'image_file': exam.get('image_file', []),
            'image_regions': exam.get('image_regions', [])
        }
        exam_list.append(exam_dict)

    return jsonify({'exams': exam_list}), 200

@dashboard_bp.route('/submit-answers', methods=['POST', 'OPTIONS'])
def submit_answers():
    if request.method == 'OPTIONS':
        return '', 204

    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1]
     
    try:
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        user_email = decoded_token['user']
        user = mongo.db.students.find_one({"email": user_email})
        user_name = get_user_info(token, 'name')
    except:
        return jsonify({'message': '無效的token'}), 401

    answers = request.json.get('answers')
    print("收到的答案資料:", answers)
    
    if not answers or len(answers) == 0:
        return jsonify({'message': '沒有收到答案資料'}), 400
  
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    submission_id = str(uuid.uuid4())
    
 
    school = answers[0].get('school', '') if answers else ''
    year = answers[0].get('year', '') if answers else ''
    subject = answers[0].get('subject', '') if answers else ''
    department = answers[0].get('department', '') if answers else ''
    
    
    answer_stats = {}
    for answer in answers:
        answer_type = answer.get('type', 'unknown')
        if answer_type not in answer_stats:
            answer_stats[answer_type] = 0
        answer_stats[answer_type] += 1
    
    # 整合的答案文件結構
    integrated_submission = {
        'submission_id': submission_id,
        'user_name': user_name,
        'user_email': user_email,
        'submit_time': current_time,
        'school': school,
        'department': department,
        'year': year,
        'subject': subject,
        'answer_summary': {
            'total_questions': len(answers),
            'answer_stats': answer_stats
        },
        'answers': answers,
        'status': 'submitted'
    }
    
  
    try:
        result = mongo.db.user_answer.insert_one(integrated_submission)
        print(f"成功提交答案，submission_id: {submission_id}")
        
        return jsonify({
            'message': '答案提交成功',
            'submission_id': submission_id,
            'total_questions': len(answers)
        }), 200
        
    except Exception as e:
        print(f"提交答案時發生錯誤: {str(e)}")
        return jsonify({'message': '答案提交失敗'}), 500

