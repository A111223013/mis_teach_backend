from werkzeug.security import generate_password_hash
from flask_mail import Message
from flask import jsonify, request, redirect, url_for, Blueprint, current_app
import uuid
from accessories import mail, redis_client, mongo, save_json_to_mongo
from src.api import get_user_info, verify_token
from bson.objectid import ObjectId
import jwt
from datetime import datetime
import os
import base64
import google.generativeai as genai
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import random
import re

dashboard_bp = Blueprint('dashboard', __name__)

# 配置多個 Gemini API Keys
API_KEYS = [
    "AIzaSyBfWLmPH5Z926UYLqotbwgQVmNondhUnsc",
    "AIzaSyBiJ7OJy-4ClQHW2ARGZ6200sQEe7HWoZ4",
    "AIzaSyBCFEh9O0WiGvlE5IXDEnx0tN_4Y_uxx3s",
    "AIzaSyB9RGnWIR_S73P2yv1OHA3ysygTNWXYBt4",
    "AIzaSyDLUJfWhn4OBs3M00qrfGqnYwHTQJZ3yt4",
    "AIzaSyA1SmwUEyBgMZrNByzIRW_8BI6sKYHA758",
    "AIzaSyCHbkAjiy2O6syJDU5g1GqmMjjS9rjwRAs",
    "AIzaSyAwJ_e-baluaPPe4NHU-GWR0vf6FXD-BG8"
]

def create_gemini_model(api_key):
    """為指定的API key創建Gemini模型"""
    try:    
        genai.configure(api_key=api_key)
        # 使用正確的模型名稱
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 測試API是否工作
        try:
            test_response = model.generate_content(
                "測試",
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 10,
                    'candidate_count': 1
                }
            )
            if test_response and hasattr(test_response, 'text'):
                print(f"✅ API Key 測試成功: {api_key[:8]}...")
                return model
            else:
                print(f"❌ API Key 測試失敗 (無回應): {api_key[:8]}...")
                return None
        except Exception as test_error:
            print(f"❌ API Key 測試失敗: {api_key[:8]}... - {str(test_error)}")
            return None
            
    except Exception as e:
        print(f"❌ API Key 初始化失敗: {api_key[:8]}... - {e}")
        return None

def init_gemini():
    """初始化主要的Gemini API（向後兼容）"""
    try:
        api_key = API_KEYS[0]  # 使用第一個API key
        genai.configure(api_key=api_key)
        # 使用正確的模型名稱
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini API 初始化成功")
        return model
    except Exception as e:
        print(f"❌ Gemini API 初始化失敗: {e}")
        return None

def grade_answer_with_gemini(model, user_answer, correct_answer, question_text, question_type):
    """使用Gemini AI來評分答案"""
    try:
        # 注意：空答案已經在submit_answers中被過濾掉，這裡不會收到空答案
        
        # 處理"不會"、"不知道"等無效回答
        invalid_answers = ['不會', '不知道', '不清楚', '不懂', '沒有', '無', '？', '?', 'idk', "i don't know", 'no idea']
        if user_answer.strip().lower() in [ans.lower() for ans in invalid_answers]:
            return {
                'score': 0,
                'is_correct': False,
                'feedback': '學生表示不會或不知道，給予0分',
                'grading_type': 'invalid_answer',
                'accuracy_percentage': 0,
                'key_elements_coverage': 0,
                'key_elements_in_standard': [],
                'key_elements_covered': [],
                'missing_key_elements': [],
                'accuracy_issues': ['學生表示不會或不知道']
            }
            
        if question_type == "single-choice" or question_type == "multiple-choice":
            # 選擇題比較邏輯改進
            def extract_option_letter(answer_text):
                """從答案中提取選項字母 (a, b, c, d等)"""
                if not answer_text:
                    return ""
                answer_text = answer_text.strip().lower()
                
                # 如果答案只是單個字母
                if len(answer_text) == 1 and answer_text in 'abcdefghijklmnopqrstuvwxyz':
                    return answer_text
                
                # 如果答案是 "a.", "b)", "(c)", "d. 內容" 等格式
                match = re.match(r'^[(\[]?([a-z])[.\])]?', answer_text)
                if match:
                    return match.group(1)
                
                # 如果找不到字母，返回原始答案（去除空白並轉小寫）
                return answer_text
            
            user_option = extract_option_letter(user_answer)
            correct_option = extract_option_letter(correct_answer)
            
            is_correct = user_option == correct_option
            score = 100 if is_correct else 0
            feedback = "正確答案" if is_correct else f"錯誤。正確答案是：{correct_answer}"
            
            return {
                'score': score,
                'is_correct': is_correct,
                'feedback': feedback,
                'grading_type': 'automatic'
            }
        
        elif question_type == "true-false":
            # 是非題處理
            user_ans = user_answer.strip().lower()
            correct_ans = correct_answer.strip().lower()
            
            # 處理中文答案
            if user_ans in ['是', 'true', 't', '對', '正確'] and correct_ans in ['是', 'true', 't', '對', '正確']:
                is_correct = True
            elif user_ans in ['否', 'false', 'f', '錯', '錯誤'] and correct_ans in ['否', 'false', 'f', '錯', '錯誤']:
                is_correct = True
            else:
                is_correct = False
                
            score = 100 if is_correct else 0
            feedback = "正確答案" if is_correct else f"錯誤。正確答案是：{correct_answer}"
            
            return {
                'score': score,
                'is_correct': is_correct,
                'feedback': feedback,
                'grading_type': 'automatic'
            }
            
        else:
            # 問答題使用Gemini評分
            prompt = f"""
你是一位嚴格的專業考試評分老師。請客觀理性地評價學生答案，絕對不能有任何同情心或寬容態度。

題目：{question_text}

標準答案：{correct_answer}

學生答案：{user_answer}

## 重要原則：
1. **部分嚴格**：錯誤就是錯誤，不完整就是不完整，絕不寬容，如果說對可以給予部分分數
2. **客觀評分**：只看答案本身的正確性，不考慮任何主觀因素
3. **零分條件**：
   - 完全答錯 → 0分
   - 答非所問 → 0分
   - 概念錯誤 → 嚴重扣分
   - 關鍵要素缺失 → 按比例扣分
4.有講到關鍵詞可以給予部分分數

## 評分標準：
1. **正確率百分比** (0-100%)：
   - 100%：內容完全正確，無任何錯誤
   - 80-99%：主要內容正確，有極少數小錯誤
   - 60-79%：大部分正確，但有明顯錯誤
   - 40-59%：部分正確，但錯誤較多
   - 20-39%：少部分正確，錯誤很多
   - 0-19%：幾乎全錯或完全錯誤

2. **關鍵要素覆蓋度** (0-100%)：
   - 分析標準答案包含的所有關鍵要素
   - 嚴格檢查學生答案涵蓋了多少要素
   - 每遺漏一個要素都要按比例扣分
   - 部分正確的要素只能得到部分分數

**最終分數計算：**
最終分數 = (正確率 × 0.6) + (關鍵要素覆蓋度 × 0.4)

## 注意：評分必須嚴格客觀，寧可嚴格也不要寬鬆！

請以JSON格式回復：
{{
    "accuracy_percentage": 正確率百分比(0-100),
    "key_elements_coverage": 關鍵要素覆蓋度(0-100),
    "score": 最終分數(0-100),
    "is_correct": true/false (分數>=70為true),
    "feedback": "詳細的嚴格評分說明",
    "key_elements_in_standard": ["標準答案的關鍵要素"],
    "key_elements_covered": ["學生答案涵蓋的關鍵要素"],
    "missing_key_elements": ["學生答案遺漏的關鍵要素"],
    "accuracy_issues": ["內容正確性的問題點"]
}}

確保回復是有效的JSON格式。
"""
            
            # 使用超時和重試機制
            max_retries = 3
            response = None
            
            for attempt in range(max_retries):
                try:
                    print(f"嘗試API調用 (第{attempt + 1}次)")
                    
                    # 創建生成配置
                    generation_config = {
                        'temperature': 0.1,  # 降低temperature使結果更穩定
                        'max_output_tokens': 1500,  # 增加輸出長度
                        'candidate_count': 1
                    }
                    
                    # 創建一個事件來控制超時
                    import threading
                    import time
                    
                    result_container = {'response': None, 'error': None, 'completed': False}
                    
                    def api_call():
                        try:
                            result_container['response'] = model.generate_content(
                                prompt,
                                generation_config=generation_config
                            )
                            result_container['completed'] = True
                        except Exception as e:
                            result_container['error'] = e
                            result_container['completed'] = True
                    
                    # 在新線程中執行API調用
                    api_thread = threading.Thread(target=api_call)
                    api_thread.daemon = True
                    api_thread.start()
                    
                    # 等待最多45秒
                    api_thread.join(timeout=45)
                    
                    if not result_container['completed']:
                        # 超時了
                        raise TimeoutError("API調用超時")
                    elif result_container['error']:
                        # 有錯誤
                        raise result_container['error']
                    else:
                        # 成功
                        response = result_container['response']
                    
                    if response and hasattr(response, 'text') and response.text:
                        print(f"API調用成功")
                        break
                    else:
                        print(f"API回應為空 (嘗試{attempt + 1})")
                        if attempt == max_retries - 1:
                            response = None
                            
                except TimeoutError:
                    print(f"API調用超時 (嘗試{attempt + 1})")
                    if attempt == max_retries - 1:
                        response = None
                        break
                    time.sleep(2)  # 等待2秒後重試
                     
                except Exception as api_error:
                    print(f"API調用錯誤 (嘗試{attempt + 1}): {str(api_error)}")
                    if attempt == max_retries - 1:
                        response = None
                        break
                    time.sleep(2)  # 等待2秒後重試
            
            if response and hasattr(response, 'text') and response.text:
                try:
                    # 清理回應文字，移除可能的markdown標記
                    clean_text = response.text.strip()
                    if clean_text.startswith('```json'):
                        clean_text = clean_text[7:]
                    if clean_text.endswith('```'):
                        clean_text = clean_text[:-3]
                    clean_text = clean_text.strip()
                    
                    import json
                    result = json.loads(clean_text)
                    
                    # 確保包含所有必要字段
                    processed_result = {
                        'score': result.get('score', 50),
                        'is_correct': result.get('is_correct', False),
                        'feedback': result.get('feedback', '評分完成'),
                        'grading_type': 'ai_assisted',
                        'accuracy_percentage': result.get('accuracy_percentage', 50),
                        'key_elements_coverage': result.get('key_elements_coverage', 50),
                        'key_elements_in_standard': result.get('key_elements_in_standard', []),
                        'key_elements_covered': result.get('key_elements_covered', []),
                        'missing_key_elements': result.get('missing_key_elements', []),
                        'accuracy_issues': result.get('accuracy_issues', [])
                    }
                    
                    return processed_result
                except json.JSONDecodeError:
                    # 如果JSON解析失敗，使用基本評分
                    return {
                        'score': 50,
                        'is_correct': False,
                        'feedback': f"AI評分暫時無法使用，請人工檢查。學生答案：{user_answer}",
                        'grading_type': 'fallback',
                        'accuracy_percentage': 50,
                        'key_elements_coverage': 50,
                        'key_elements_in_standard': [],
                        'key_elements_covered': [],
                        'missing_key_elements': [],
                        'accuracy_issues': ['JSON解析失敗']
                    }
            else:
                return {
                    'score': 50,
                    'is_correct': False,
                    'feedback': "AI評分服務暫時無法使用",
                    'grading_type': 'fallback',
                    'accuracy_percentage': 50,
                    'key_elements_coverage': 50,
                    'key_elements_in_standard': [],
                    'key_elements_covered': [],
                    'missing_key_elements': [],
                    'accuracy_issues': ['AI服務無回應']
                }
                
    except Exception as e:
        print(f"Gemini評分錯誤: {e}")
        return {
            'score': 50,
            'is_correct': False,
            'feedback': f"評分過程中發生錯誤：{str(e)}",
            'grading_type': 'error',
            'accuracy_percentage': 50,
            'key_elements_coverage': 50,
            'key_elements_in_standard': [],
            'key_elements_covered': [],
            'missing_key_elements': [],
            'accuracy_issues': [f'系統錯誤: {str(e)}']
        }

def process_single_answer(args):
    """處理單個答案的包裝函數，用於並行處理"""
    answer, api_key_index, total_count = args
    api_key = API_KEYS[api_key_index % len(API_KEYS)]
    
    try:
        # 為這個worker創建專用的Gemini模型
        model = create_gemini_model(api_key)
        if not model:
            return create_error_result(answer, "API模型初始化失敗")
        
        # 透過共同字段查找正確答案
        query = {
            'school': answer.get('school'),
            'year': answer.get('year'),
            'question_number': answer.get('question_number')
        }
        
        exam_question = mongo.db.exam.find_one(query)
        
        if not exam_question:
            return create_not_found_result(answer)
        
        # 使用Gemini評分
        grading_result = grade_answer_with_gemini(
            model,
            answer.get('answer', ''),
            exam_question.get('answer', ''),
            exam_question.get('question_text', ''),
            exam_question.get('type', '')
        )
        
        # 整合答案和評分結果
        graded_answer = {
            **answer,
            'correct_answer': exam_question.get('answer', ''),
            'score': grading_result['score'],
            'is_correct': grading_result['is_correct'],
            'feedback': grading_result['feedback'],
            'grading_type': grading_result['grading_type'],
            'question_found': True
        }
        
        # 如果是AI輔助評分，添加詳細分析
        if grading_result['grading_type'] == 'ai_assisted':
            graded_answer.update({
                'accuracy_percentage': grading_result.get('accuracy_percentage', 50),
                'key_elements_coverage': grading_result.get('key_elements_coverage', 50),
                'key_elements_in_standard': grading_result.get('key_elements_in_standard', []),
                'key_elements_covered': grading_result.get('key_elements_covered', []),
                'missing_key_elements': grading_result.get('missing_key_elements', []),
                'accuracy_issues': grading_result.get('accuracy_issues', [])
            })
        
        return graded_answer
        
    except Exception as e:
        return create_error_result(answer, f"處理過程發生錯誤: {str(e)}")

def create_error_result(answer, error_msg):
    """創建錯誤結果"""
    # 注意：空答案已經被過濾掉，這裡只處理有內容但出錯的答案
    return {
        **answer,
        'score': 0,
        'is_correct': False,
        'feedback': error_msg,
        'grading_type': 'error',
        'question_found': False
    }

def create_not_found_result(answer):
    """創建未找到題目的結果"""
    # 注意：空答案已經被過濾掉，這裡只處理有內容但找不到題目的答案
    return {
        **answer,
        'score': 0,
        'is_correct': False,
        'feedback': '無法找到對應的題目進行評分',
        'grading_type': 'not_found',
        'question_found': False
    }

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
    
    try:
        user_name = get_user_info(token, 'name')
        return jsonify({'name': user_name}), 200
    except ValueError as e:
        error_msg = str(e)
        if "expired" in error_msg.lower():
            return jsonify({'message': 'Token已過期，請重新登錄', 'code': 'TOKEN_EXPIRED'}), 401
        elif "invalid" in error_msg.lower():
            return jsonify({'message': '無效的token', 'code': 'TOKEN_INVALID'}), 401
        else:
            return jsonify({'message': '認證失敗', 'code': 'AUTH_FAILED'}), 401
    except Exception as e:
        print(f"獲取用戶名稱時發生錯誤: {str(e)}")
        return jsonify({'message': '服務器內部錯誤', 'code': 'SERVER_ERROR'}), 500

# 注意：get-exam和get-exam-to-object函數已移動到quiz.py

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

    # 過濾掉空答案，只處理有內容的答案
    original_count = len(answers)
    filtered_answers = []
    skipped_count = 0
    
    for answer in answers:
        user_answer = answer.get('answer', '')
        if user_answer and user_answer.strip():
            # 有內容的答案，保留處理
            filtered_answers.append(answer)
        else:
            # 空答案，完全跳過
            skipped_count += 1
            print(f"跳過空答案題目: {answer.get('question_number', '未知')}")
    
    print(f"原始題目數: {original_count}, 有作答: {len(filtered_answers)}, 跳過空答案: {skipped_count}")
    
    if len(filtered_answers) == 0:
        return jsonify({
            'message': '所有題目都是空答案，無需處理',
            'total_questions': original_count,
            'answered_questions': 0,
            'skipped_questions': skipped_count
        }), 200

    # 使用過濾後的答案進行後續處理
    answers = filtered_answers
  
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    submission_id = str(uuid.uuid4())
    
    school = answers[0].get('school', '') if answers else ''
    year = answers[0].get('year', '') if answers else ''
    subject = answers[0].get('subject', '') if answers else ''
    department = answers[0].get('department', '') if answers else ''
    
    # 批改答案 - 使用並行處理
    print(f"🚀 開始並行批改 {len(answers)} 道題目...")
    
    # 準備並行處理的參數
    max_workers = min(len(API_KEYS), len(answers), 8)  # 最多8個並行worker
    task_args = [(answer, i, len(answers)) for i, answer in enumerate(answers)]
    
    graded_answers = []
    
    # 使用線程池並行處理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任務
        future_to_index = {executor.submit(process_single_answer, args): i 
                          for i, args in enumerate(task_args)}
        
        # 收集結果
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_index):
            completed_count += 1
            try:
                graded_answer = future.result()
                graded_answers.append((future_to_index[future], graded_answer))
                
                print(f"✅ 完成 {completed_count}/{len(answers)} 題")
                
            except Exception as e:
                print(f"❌ 處理失敗: {e}")
                error_answer = create_error_result(
                    answers[future_to_index[future]], 
                    f"並行處理失敗: {str(e)}"
                )
                graded_answers.append((future_to_index[future], error_answer))
    
    # 按原順序排序結果
    graded_answers.sort(key=lambda x: x[0])
    graded_answers = [answer for _, answer in graded_answers]
    
    print(f"🎉 所有題目批改完成！")
    
    # 計算整體成績 - 現在只包含有作答的題目
    # 統計各種評分結果
    successful_questions = [answer for answer in graded_answers 
                          if answer.get('grading_type') in ['automatic', 'ai_assisted']]
    invalid_answer_questions = [answer for answer in graded_answers 
                              if answer.get('grading_type') == 'invalid_answer']
    error_questions = [answer for answer in graded_answers 
                     if answer.get('grading_type') in ['error', 'not_found', 'fallback']]
    
    # 計算分數（包含所有實際作答的題目，包括回答"不知道"的）
    total_score = 0
    correct_count = 0
    
    # 所有實際作答的題目都參與統計（包括invalid_answer）
    for answer in graded_answers:
        if answer.get('score') is not None:
            total_score += answer['score']
        if answer.get('is_correct'):
            correct_count += 1
    
    # 統計基於實際處理的題目數量
    processed_count = len(graded_answers)
    average_score = total_score / processed_count if processed_count > 0 else 0
    accuracy_rate = (correct_count / processed_count) * 100 if processed_count > 0 else 0
    
    answer_stats = {}
    grading_stats = {}
    for answer in graded_answers:
        answer_type = answer.get('type', 'unknown')
        if answer_type not in answer_stats:
            answer_stats[answer_type] = 0
        answer_stats[answer_type] += 1
        
        grading_type = answer.get('grading_type', 'unknown')
        if grading_type not in grading_stats:
            grading_stats[grading_type] = 0
        grading_stats[grading_type] += 1
    
    # 整合的答案文件結構（包含評分结果）
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
            'original_questions': original_count,  # 原始題目總數
            'processed_questions': len(answers),   # 實際處理的題目數
            'skipped_questions': skipped_count,    # 跳過的空答案題目數
            'answer_stats': answer_stats,
            'grading_stats': grading_stats
        },
        'grading_results': {
            'total_score': total_score,
            'average_score': round(average_score, 2),
            'correct_count': correct_count,
            'accuracy_rate': round(accuracy_rate, 2),
            'processed_count': processed_count,  # 實際評分的題目數
            'skipped_count': skipped_count,      # 跳過的題目數
            'error_count': len(error_questions),  # 錯誤題目數
            'graded_at': current_time,
            'grading_method': 'gemini_ai'
        },
        'answers': graded_answers,  # 只包含實際處理的答案
        'status': 'graded'
    }
    
    try:
        result = mongo.db.user_answer.insert_one(integrated_submission)
        print(f"成功提交並評分答案，submission_id: {submission_id}")
        print(f"評分結果: 平均分數 {average_score:.2f}, 正確率 {accuracy_rate:.2f}%")
        print(f"統計: 原始題目 {original_count}, 實際處理 {processed_count}, 跳過空答案 {skipped_count}, 錯誤 {len(error_questions)}")
        
        return jsonify({
            'message': '答案提交並評分成功',
            'submission_id': submission_id,
            'original_questions': original_count,
            'processed_questions': processed_count,
            'skipped_questions': skipped_count,
            'grading_results': {
                'total_score': total_score,
                'average_score': round(average_score, 2),
                'correct_count': correct_count,
                'accuracy_rate': round(accuracy_rate, 2),
                'note': f'統計基於實際處理的 {processed_count} 道題目（已跳過 {skipped_count} 道空答案）'
            }
        }), 200
        
    except Exception as e:
        print(f"提交答案時發生錯誤: {str(e)}")
        return jsonify({'message': '答案提交失敗'}), 500

@dashboard_bp.route('/getUserSubmissions', methods=['POST', 'OPTIONS'])
def getUserSubmissions():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': '未提供授權標頭'}), 401
            
        token = auth_header.split(" ")[1]
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        user_email = decoded_token['user']
        
        # 獲取用戶資訊
        try:
            user_name = get_user_info(token, 'name')
        except Exception as e:
            print(f"獲取用戶資訊錯誤: {str(e)}")
            user_name = user_email  # 使用 email 作為備用
        
        # 獲取請求參數
        data = request.json or {}
        target_email = data.get('target_email', user_email)  # 如果沒有指定，查看自己的
        submission_id = data.get('submission_id', None)  # 可選：查看特定提交
        
        # 建立查詢條件
        query = {"user_email": target_email}
        if submission_id:
            query["submission_id"] = submission_id
        
        # 查詢提交記錄
        submissions = list(mongo.db.user_answer.find(query).sort("submit_time", -1))
        
        if not submissions:
            return jsonify({
                'message': '未找到提交記錄',
                'submissions': [],
                'count': 0
            }), 200
        
        # 格式化返回資料
        formatted_submissions = []
        for submission in submissions:
            # 轉換ObjectId為字串
            submission['_id'] = str(submission['_id'])
            
            # 加工答案資料，提供更清晰的分析
            answers = submission.get('answers', [])
            
            # 分析答案類型分佈
            answer_analysis = {
                'total_questions': len(answers),
                'by_type': {},
                'by_grading_result': {},
                'by_score_range': {
                    'excellent': 0,    # 90-100分
                    'good': 0,         # 70-89分
                    'average': 0,      # 50-69分
                    'poor': 0,         # 30-49分
                    'failed': 0        # 0-29分
                }
            }
            
            for answer in answers:
                # 按題目類型統計
                q_type = answer.get('type', 'unknown')
                if q_type not in answer_analysis['by_type']:
                    answer_analysis['by_type'][q_type] = {
                        'count': 0, 'correct': 0, 'avg_score': 0, 'total_score': 0
                    }
                answer_analysis['by_type'][q_type]['count'] += 1
                if answer.get('is_correct'):
                    answer_analysis['by_type'][q_type]['correct'] += 1
                score = answer.get('score', 0)
                answer_analysis['by_type'][q_type]['total_score'] += score
                
                # 按評分結果統計
                grading_type = answer.get('grading_type', 'unknown')
                if grading_type not in answer_analysis['by_grading_result']:
                    answer_analysis['by_grading_result'][grading_type] = 0
                answer_analysis['by_grading_result'][grading_type] += 1
                
                # 按分數範圍統計
                if score >= 90:
                    answer_analysis['by_score_range']['excellent'] += 1
                elif score >= 70:
                    answer_analysis['by_score_range']['good'] += 1
                elif score >= 50:
                    answer_analysis['by_score_range']['average'] += 1
                elif score >= 30:
                    answer_analysis['by_score_range']['poor'] += 1
                else:
                    answer_analysis['by_score_range']['failed'] += 1
            
            # 計算每種題型的平均分
            for type_info in answer_analysis['by_type'].values():
                if type_info['count'] > 0:
                    type_info['avg_score'] = round(type_info['total_score'] / type_info['count'], 2)
            
            # 優化答案顯示格式
            detailed_answers = []
            for i, answer in enumerate(answers, 1):
                detailed_answer = {
                    'question_number': answer.get('question_number', str(i)),
                    'type': answer.get('type', 'unknown'),
                    'question_text': answer.get('question_text', ''),
                    'student_answer': answer.get('answer', ''),
                    'correct_answer': answer.get('correct_answer', ''),
                    'score': answer.get('score', 0),
                    'is_correct': answer.get('is_correct', False),
                    'feedback': answer.get('feedback', ''),
                    'grading_type': answer.get('grading_type', 'unknown'),
                    'options': answer.get('options', [])
                }
                
                # 如果是AI評分，添加詳細分析
                if answer.get('grading_type') == 'ai_assisted':
                    detailed_answer.update({
                        'ai_analysis': {
                            'accuracy_percentage': answer.get('accuracy_percentage', 0),
                            'key_elements_coverage': answer.get('key_elements_coverage', 0),
                            'key_elements_in_standard': answer.get('key_elements_in_standard', []),
                            'key_elements_covered': answer.get('key_elements_covered', []),
                            'missing_key_elements': answer.get('missing_key_elements', []),
                            'accuracy_issues': answer.get('accuracy_issues', [])
                        }
                    })
                
                detailed_answers.append(detailed_answer)
            
            formatted_submission = {
                '_id': submission['_id'],
                'submission_id': submission.get('submission_id', ''),
                'user_name': submission.get('user_name', ''),
                'user_email': submission.get('user_email', ''),
                'submit_time': submission.get('submit_time', ''),
                'basic_info': {
                    'school': submission.get('school', ''),
                    'department': submission.get('department', ''),
                    'year': submission.get('year', ''),
                    'subject': submission.get('subject', '')
                },
                'grading_results': submission.get('grading_results', {}),
                'answer_summary': submission.get('answer_summary', {}),
                'answer_analysis': answer_analysis,
                'answers': detailed_answers,
                'status': submission.get('status', 'unknown')
            }
            
            formatted_submissions.append(formatted_submission)
        
        return jsonify({
            'message': '查詢成功',
            'submissions': formatted_submissions,
            'count': len(formatted_submissions),
            'query_info': {
                'target_email': target_email,
                'submission_id': submission_id,
                'queried_by': user_email
            }
        }), 200
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"獲取用戶提交記錄時發生錯誤: {str(e)}")
        return jsonify({'message': f'查詢失敗: {str(e)}'}), 500

# 新增：根據submission_id查詢特定提交的詳細資料
@dashboard_bp.route('/getSubmissionDetail', methods=['POST', 'OPTIONS'])
def getSubmissionDetail():
    if request.method == 'OPTIONS':
        return '', 204
    
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1]
    
    try:
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        user_email = decoded_token['user']
        
        data = request.json or {}
        submission_id = data.get('submission_id')
        
        if not submission_id:
            return jsonify({'message': '請提供submission_id'}), 400
        
        # 查詢特定提交
        submission = mongo.db.user_answer.find_one({"submission_id": submission_id})
        
        if not submission:
            return jsonify({'message': '未找到該提交記錄'}), 404
        
        # 轉換ObjectId為字串
        submission['_id'] = str(submission['_id'])
        
        # 詳細的題目分析
        answers = submission.get('answers', [])
        question_details = []
        
        for answer in answers:
            question_detail = {
                'question_number': answer.get('question_number', ''),
                'type': answer.get('type', ''),
                'question_text': answer.get('question_text', ''),
                'options': answer.get('options', []),
                'student_answer': answer.get('answer', ''),
                'correct_answer': answer.get('correct_answer', ''),
                'score': answer.get('score', 0),
                'is_correct': answer.get('is_correct', False),
                'feedback': answer.get('feedback', ''),
                'grading_type': answer.get('grading_type', 'unknown'),
                'question_found': answer.get('question_found', True)
            }
            
            # 根據題目類型提供不同的分析
            if answer.get('type') in ['single-choice', 'multiple-choice', 'true-false']:
                question_detail['comparison'] = {
                    'student_chose': answer.get('answer', ''),
                    'correct_option': answer.get('correct_answer', ''),
                    'match_result': answer.get('is_correct', False)
                }
            elif answer.get('grading_type') == 'ai_assisted':
                question_detail['ai_analysis'] = {
                    'accuracy_percentage': answer.get('accuracy_percentage', 0),
                    'key_elements_coverage': answer.get('key_elements_coverage', 0),
                    'key_elements_in_standard': answer.get('key_elements_in_standard', []),
                    'key_elements_covered': answer.get('key_elements_covered', []),
                    'missing_key_elements': answer.get('missing_key_elements', []),
                    'accuracy_issues': answer.get('accuracy_issues', [])
                }
            
            question_details.append(question_detail)
        
        return jsonify({
            'message': '查詢成功',
            'submission': {
                '_id': submission['_id'],
                'submission_id': submission.get('submission_id', ''),
                'user_info': {
                    'name': submission.get('user_name', ''),
                    'email': submission.get('user_email', ''),
                    'school': submission.get('school', ''),
                    'department': submission.get('department', ''),
                    'year': submission.get('year', ''),
                    'subject': submission.get('subject', '')
                },
                'submit_time': submission.get('submit_time', ''),
                'grading_results': submission.get('grading_results', {}),
                'answer_summary': submission.get('answer_summary', {}),
                'question_details': question_details,
                'status': submission.get('status', 'unknown')
            }
        }), 200
        
    except jwt.InvalidTokenError:
        return jsonify({'message': '無效的token'}), 401
    except Exception as e:
        print(f"獲取提交詳情時發生錯誤: {str(e)}")
        return jsonify({'message': f'查詢失敗: {str(e)}'}), 500