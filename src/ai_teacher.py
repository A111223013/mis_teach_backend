"""
AI 教學系統 API 端點
整合 RAG 系統，提供完整的智能教學 API 服務
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from typing import Dict, Any, List, Optional
import uuid
from accessories import mongo
from bson.objectid import ObjectId

# 導入 RAG 系統模組
RAG_AVAILABLE = False

try:
    from .rag_sys.rag_ai_role import handle_tutoring_conversation
    RAG_AVAILABLE = True
    logger = logging.getLogger(__name__)
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ RAG 系統模組導入失敗: {e}")

# 創建 Blueprint
ai_teacher_bp = Blueprint('ai_teacher', __name__)

# ==================== 工具函數 ====================

def get_user_id() -> str:
        """獲取用戶 ID"""
        if 'user_id' not in session:
            session['user_id'] = f"user_{uuid.uuid4().hex[:8]}"
        return session['user_id']
    
def _extract_user_answer(user_answer_raw: str) -> str:
    """提取用戶答案的實際內容"""
    if not user_answer_raw:
        return '未作答'
    
    # 如果是 JSON 格式，提取用戶答案
    if user_answer_raw.startswith('{'):
        try:
            answer_data = json.loads(user_answer_raw)
            
            # 優先從 answer 欄位獲取
            answer = answer_data.get('answer', '')
            if answer:
                return answer
            
            # 如果 answer 為空，從 feedback.explanation 中提取用戶答案
            feedback = answer_data.get('feedback', {})
            explanation = feedback.get('explanation', '')
            
            # 從 explanation 中提取用戶答案的關鍵詞
            if '您的答案' in explanation:
                # 提取「您的答案 X 是」或類似格式
                import re
                patterns = [
                    r'您的答案\s*([^\s是]+)',
                    r'學生答案\s*[『「]([^』」]+)[』」]',
                    r'學生答案為\s*[『「]([^』」]+)[』」]',
                    r'答案\s*[『「]([^』」]+)[』」]'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, explanation)
                    if match:
                        return match.group(1).strip()
            
            # 如果都沒有，返回 '未作答'
            return '未作答'
            
        except json.JSONDecodeError:
            return user_answer_raw
    
    return user_answer_raw
    
def chat_with_ai(question: str, conversation_type: str = "general", session_id: str = None) -> dict:
    """AI 對話處理"""
    try:
        if not RAG_AVAILABLE:
            return {
                'success': False,
                'error': 'AI 服務不可用',
                'response': '抱歉，AI 教學服務暫時不可用。'
            }

        if conversation_type == "tutoring" and session_id:
            try:
                response = handle_tutoring_conversation(session_id, question, get_user_id())
                return {
                    'success': True,
                    'response': response,
                    'conversation_type': 'tutoring',
                    'session_id': session_id
                }
            except Exception as e:
                logger.error(f"❌ 教學對話失敗: {e}")
            return {
                'success': False,
                    'error': f'教學對話失敗：{str(e)}',
                    'response': '抱歉，教學對話處理失敗，請重試。'
            }
        else:
            return {
                'success': True,
                'response': f'您好！我是AI教學助手。關於「{question}」，我很樂意為您解答。請使用AI導師功能獲得更專業的指導。',
                'conversation_type': 'general'
            }
        
    except Exception as e:
        logger.error(f"❌ AI對話失敗: {e}")
        return {
            'success': False,
            'error': f'AI對話失敗：{str(e)}',
            'response': '抱歉，AI對話處理失敗，請重試。'
        }

def get_quiz_result_data(result_id: str) -> dict:
    """獲取測驗結果數據"""
    try:
        if not result_id.startswith('result_'):
            return None
        
        try:
            quiz_history_id = int(result_id.split('_')[1])
        except (ValueError, IndexError):
            return None
        
        from accessories import sqldb
        from sqlalchemy import text
        
        with sqldb.engine.connect() as conn:
            # 查詢 quiz_history 和 quiz_templates
            history_result = conn.execute(text("""
                SELECT qh.id, qh.quiz_template_id, qh.user_email, qh.quiz_type, 
                       qh.total_questions, qh.answered_questions, qh.correct_count, qh.wrong_count,
                       qh.accuracy_rate, qh.average_score, qh.total_time_taken, 
                       qh.submit_time, qh.status, qh.created_at,
                       qt.question_ids
                FROM quiz_history qh
                LEFT JOIN quiz_templates qt ON qh.quiz_template_id = qt.id
                WHERE qh.id = :quiz_history_id
            """), {
                'quiz_history_id': quiz_history_id
            }).fetchone()
            
            if not history_result:
                return None
            
            # 獲取所有題目的用戶答案
            answers_result = conn.execute(text("""
                SELECT mongodb_question_id, user_answer, is_correct, score, created_at
                FROM quiz_answers 
                WHERE quiz_history_id = :quiz_history_id
                ORDER BY created_at
            """), {
                'quiz_history_id': quiz_history_id
            }).fetchall()
            
            # 構建答案字典，用於快速查找
            answers_dict = {}
            for answer in answers_result:
                question_id = str(answer[0])  # 確保ID為字符串格式
                user_answer = answer[1]
                is_correct = bool(answer[2])  # 確保為 boolean 類型
                score = float(answer[3]) if answer[3] else 0
                created_at = answer[4]
                
                # 調試：打印答案資訊
                print(f"🔍 構建答案字典 {question_id}: is_correct={is_correct}, user_answer='{user_answer}'")
                
                answers_dict[question_id] = {
                    'user_answer': user_answer,
                    'is_correct': is_correct,
                    'score': score,
                    'created_at': created_at
                }
            
            # 解析題目ID列表
            question_ids_str = history_result[14]
            if question_ids_str:
                try:
                    question_ids = json.loads(question_ids_str)
                    print(f"🔍 解析題目ID列表成功: {len(question_ids)} 題")
                except json.JSONDecodeError:
                    question_ids = []
                    print(f"❌ 解析題目ID列表失敗")
            else:
                question_ids = []
                print(f"⚠️ 題目ID列表為空")
            
            # 調試：打印answers_dict的keys
            print(f"🔍 answers_dict keys: {list(answers_dict.keys())}")
            print(f"🔍 question_ids: {question_ids}")
            
            # 構建題目陣列
            questions = []
            for question_id in question_ids:
                question_obj = mongo.db.exam.find_one({'_id': ObjectId(question_id)})
                if not question_obj:
                    continue
                
                # 從 answers_dict 獲取題目資訊 - 確保ID格式一致
                question_id_str = str(question_id)
                answer_info = answers_dict.get(question_id_str, {})
                is_correct = answer_info.get('is_correct', False)  # 預設為錯誤，確保能撈取到錯題
                user_answer_raw = answer_info.get('user_answer', '')
                
                # 解析用戶答案
                actual_user_answer = _extract_user_answer(user_answer_raw)
                
                # 調試：檢查題目狀態
                print(f"🔍 題目 {question_id_str}: 在answers_dict中找到={question_id_str in answers_dict}, is_correct={is_correct}, user_answer_raw='{user_answer_raw}', actual_user_answer='{actual_user_answer}'")
                
                question_data = {
                    'question_id': str(question_obj['_id']),
                    'question_text': question_obj.get('question_text', ''),
                    'correct_answer': question_obj.get('answer', ''),
                    'user_answer': actual_user_answer,
                    'is_correct': is_correct,
                    'is_marked': False,
                    'topic': question_obj.get('topic', '計算機概論'),
                    'difficulty': question_obj.get('difficulty', 2),
                    'options': question_obj.get('options', []),
                    'image_file': question_obj.get('image_file', ''),
                    'key_points': question_obj.get('key_points', '')
                }
                
                questions.append(question_data)
            
            # 構建返回結果
            result = {
                'quiz_history_id': history_result[0],
                'quiz_template_id': history_result[1],
                'user_email': history_result[2],
                'quiz_type': history_result[3],
                'total_questions': history_result[4],
                'answered_questions': history_result[5],
                'correct_count': history_result[6],
                'wrong_count': history_result[7],
                'accuracy_rate': history_result[8],
                'average_score': history_result[9],
                'total_time_taken': history_result[10],
                'submit_time': history_result[11].isoformat() if history_result[11] else None,
                'status': history_result[12],
                'created_at': history_result[13].isoformat() if history_result[13] else None,
                'questions': questions,
                'errors': [q for q in questions if not q['is_correct']]
            }
            
            return result
            
    except Exception as e:
        return None

# ==================== API 路由 ====================

@ai_teacher_bp.route('/ai-tutoring', methods=['POST', 'OPTIONS'])
def ai_tutoring():
    """AI 教學對話端點"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True})
        
        data = request.get_json()
        user_input = data.get('user_input', '')
        session_id = data.get('session_id', '')
        conversation_type = data.get('conversation_type', 'tutoring')
        
        
        # 調用 AI 對話處理
        result = chat_with_ai(user_input or "初始化會話", conversation_type, session_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ AI教學對話端點錯誤: {e}")
        return jsonify({
            'success': False,
            'error': f'AI教學對話失敗：{str(e)}',
            'response': '抱歉，AI教學對話處理失敗，請重試。'
        })

@ai_teacher_bp.route('/get-quiz-result/<result_id>', methods=['GET', 'OPTIONS'])
def get_quiz_result(result_id):
    """獲取測驗結果"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True})
        
        # 獲取測驗結果數據
        result_data = get_quiz_result_data(result_id)
        
        if result_data:
            return jsonify({
                'success': True,
                'data': result_data
            })
        else:
            return jsonify({
                'success': False,
                'error': '未找到測驗結果'
            }), 404
        
    except Exception as e:
        logger.error(f"❌ 獲取測驗結果失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取測驗結果失敗：{str(e)}'
        }), 500

@ai_teacher_bp.route('/start-error-learning', methods=['POST', 'OPTIONS'])
def start_error_learning():
    """開始錯題學習"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True})
        
        data = request.get_json()
        result_id = data.get('result_id', '')
        
        # 獲取測驗結果數據
        result_data = get_quiz_result_data(result_id)
        
        if not result_data:
            return jsonify({
                'success': False,
                'error': '未找到測驗結果'
            }), 404
        
        # 檢查是否有錯題
        wrong_questions = [q for q in result_data.get('questions', []) if not q['is_correct']]
        
        if not wrong_questions:
            return jsonify({
                'success': False,
                'error': '沒有錯題需要學習'
                }), 400
        
        # 創建學習會話
        session_id = f"learning_{get_user_id()}_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{result_id}"
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'wrong_questions_count': len(wrong_questions),
            'message': f'發現 {len(wrong_questions)} 道錯題，開始學習！'
        })
        
    except Exception as e:
        logger.error(f"❌ 開始錯題學習失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'開始錯題學習失敗：{str(e)}'
        }), 500
