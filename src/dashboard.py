from werkzeug.security import generate_password_hash
from flask_mail import Message
from flask import jsonify, request, redirect, url_for, Blueprint, current_app
import uuid
from accessories import mail, redis_client, mongo, save_json_to_mongo
from src.api import get_user_info, verify_token
from bson.objectid import ObjectId

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

    answers = request.json.get('answers')
    print(answers)
    for answer in answers:
        print(answer)
        mongo.db.user_answer.insert_one(answer)
        
    return jsonify({'message': '答案提交成功'}), 200

