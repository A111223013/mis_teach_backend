"""
AI 教學系統 API 端點
整合 RAG 系統，提供完整的智能教學 API 服務
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from typing import Dict, Any, List, Optional
import uuid
from src.api import get_user_info, verify_token
from werkzeug.security import generate_password_hash
from flask_mail import Message
from flask import jsonify, request, redirect, url_for, Blueprint, current_app
import uuid
from accessories import mail, redis_client, mongo, save_json_to_mongo
from src.api import get_user_info, verify_token
from bson.objectid import ObjectId
import jwt
from datetime import datetime

# 導入 RAG 系統模組
RAG_AVAILABLE = False
Config = None
MultiAITutor = None
AIResponder = None

try:
    from .rag_sys.config import Config
    from .rag_sys.rag_ai_role import MultiAITutor, AIResponder
    RAG_AVAILABLE = True
    logger = logging.getLogger(__name__)
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ RAG 系統模組導入失敗: {e}")

# 創建 Blueprint
ai_teacher_bp = Blueprint('ai_teacher', __name__)

class AITeacherService:
    """AI 教學服務"""
    
    def __init__(self):
        """初始化服務"""
        self.config = None
        self.tutor = None
        self.responder = None
        self.user_sessions = {}  # 用戶會話數據

        if RAG_AVAILABLE:
            try:
                self.config = Config()
                # 使用整合後的 MultiAITutor 和 AIResponder
                self.tutor = MultiAITutor()
                self.responder = AIResponder()
            except Exception as e:
                logger.error(f"❌ AI 教學服務初始化失敗: {e}")
                # 不修改全局變數，只記錄錯誤
    
    def get_user_id(self) -> str:
        """獲取用戶 ID"""
        if 'user_id' not in session:
            session['user_id'] = f"user_{uuid.uuid4().hex[:8]}"
        return session['user_id']
    
    def get_user_session_data(self, user_id: str) -> Dict[str, Any]:
        """獲取用戶會話數據"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'current_ai_model': 'gemini',
                'in_conversation': False,
                'conversation_count': 0,
                'last_activity': datetime.now().isoformat(),
                'user_profile': {
                    'learning_style': 'unknown',
                    'weak_topics': [],
                    'strong_topics': [],
                    'total_questions': 0,
                    'correct_answers': 0
                },
                'quiz_results': [],
                'learning_sessions': []
            }
        return self.user_sessions[user_id]
    
    def chat_with_ai(
        self,
        question: str,
        conversation_type: str = "general",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """與 AI 進行對話 - 純 API 串接"""
        try:
            if not RAG_AVAILABLE or not self.tutor:
                return {
                    'success': False,
                    'error': 'AI 服務不可用',
                    'response': '抱歉，AI 教學服務暫時不可用。'
                }

            if not user_id:
                user_id = self.get_user_id()

            # 根據對話類型調用不同的 AI 處理器
            if conversation_type == "tutoring" and session_id:
                # 教學對話：調用 MultiAITutor 的教學會話處理
                response = self.tutor.handle_tutoring_conversation(session_id, question, user_id)
            elif conversation_type == "tutoring":
                # 新的教學會話：調用 MultiAITutor 的新問題處理
                response = self.tutor.start_new_question(question)
            else:
                # 一般問題：調用 AIResponder
                if self.responder:
                    result = self.responder.answer_question(question)
                    response = result.get('詳細回答', '抱歉，無法回答您的問題。')
                else:
                    response = "AI 回應器不可用。"

            # 更新用戶會話數據
            session_data = self.get_user_session_data(user_id)
            session_data['conversation_count'] += 1
            session_data['last_activity'] = datetime.now().isoformat()
            session_data['in_conversation'] = True

            return {
                'success': True,
                'response': response,
                'conversation_type': conversation_type,
                'ai_model': 'gemini',
                'conversation_count': session_data['conversation_count'],
                'knowledge_used': True
            }

        except Exception as e:
            logger.error(f"❌ AI 對話失敗: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': '抱歉，處理您的問題時發生錯誤。'
            }
    
    def submit_quiz_results(self, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """提交測驗結果"""
        try:
            user_id = self.get_user_id()
            session_data = self.get_user_session_data(user_id)
            
            # 處理測驗數據
            processed_result = self._process_quiz_data(quiz_data, user_id)
            
            # 保存到用戶會話
            session_data['quiz_results'].append(processed_result)
            
            # 生成結果 ID
            result_id = f"result_{processed_result['user_id']}_{processed_result['quiz_id']}_{processed_result['submit_time']}"
            
            return {
                'success': True,
                'result_id': result_id,
                'message': '測驗結果提交成功'
            }
            
        except Exception as e:
            logger.error(f"❌ 提交測驗結果失敗: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_quiz_data(self, quiz_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """處理測驗數據"""
        answers = quiz_data.get('answers', [])
        
        # 計算統計數據
        total_questions = len(answers)
        correct_count = sum(1 for answer in answers if answer.get('is_correct', False))
        wrong_count = total_questions - correct_count
        marked_count = sum(1 for answer in answers if answer.get('is_marked', False))
        unanswered_count = 0  # 假設所有題目都已回答
        
        return {
            'user_id': user_id,
            'quiz_id': quiz_data.get('quiz_id', ''),
            'answers': answers,
            'submit_time': quiz_data.get('submit_time', datetime.now().isoformat()),
            'total_time': quiz_data.get('total_time', 0),
            'score': quiz_data.get('score', correct_count),
            'total_questions': total_questions,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'marked_count': marked_count,
            'unanswered_count': unanswered_count
        }
    
    def start_error_learning(self, result_id: str) -> Dict[str, Any]:
        """開始錯題學習"""
        try:
            user_id = self.get_user_id()
            session_data = self.get_user_session_data(user_id)

            # 首先嘗試從 Redis 獲取用戶的所有錯題數據
            import json
            
            # 從 session 或 token 獲取用戶 email
            user_email = None
            try:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(" ")[1]
                    user_email = get_user_info(token, 'email')
            except:
                pass
            
            if user_email:
                # 創建 Redis 連接
                r = redis_client
                user_error_key = f"user_errors:{user_email}"
                error_data = r.get(user_error_key)
                
                if error_data:
                    logger.info(f"從 Redis 獲取用戶 {user_email} 的錯題數據")
                    # 處理bytes到string的轉換
                    if isinstance(error_data, bytes):
                        error_data = error_data.decode('utf-8')
                    error_list = json.loads(error_data)
                    
                    if error_list:
                        logger.info(f"成功從 Redis 獲取 {len(error_list)} 道錯題")
                        
                        # 創建學習會話ID
                        session_id = f"learning_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        # 保存會話 ID 到用戶數據（用於追蹤）
                        if 'learning_sessions' not in session_data:
                            session_data['learning_sessions'] = []
                        session_data['learning_sessions'].append({
                            'session_id': session_id,
                            'result_id': result_id,
                            'start_time': datetime.now().isoformat(),
                            'source': 'redis',
                            'error_count': len(error_list)
                        })

                        return {
                            'success': True,
                            'session_id': session_id,
                            'total_wrong_questions': len(error_list),
                            'message': f'開始學習 {len(error_list)} 道錯題',
                            'source': 'redis'
                        }

            # 如果 Redis 中沒有數據，再從 MongoDB 獲取
            from accessories import mongo
            submission = mongo.db.submissions.find_one({'submission_id': result_id})
            
            if submission:
                logger.info(f"從 MongoDB 獲取測驗結果 {result_id} 的錯題數據")
                
                # 提取錯題數據
                wrong_questions = submission.get('wrong_questions', [])
                
                if not wrong_questions:
                    return {
                        'success': True,
                        'message': '恭喜！您沒有錯題需要學習',
                        'wrong_questions': []
                    }
                
                logger.info(f"成功從 MongoDB 獲取 {len(wrong_questions)} 道錯題")
                
                # 創建學習會話ID
                session_id = f"learning_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # 保存會話 ID 到用戶數據（用於追蹤）
                if 'learning_sessions' not in session_data:
                    session_data['learning_sessions'] = []
                session_data['learning_sessions'].append({
                    'session_id': session_id,
                    'result_id': result_id,
                    'start_time': datetime.now().isoformat(),
                    'source': 'mongodb',
                    'error_count': len(wrong_questions)
                })

                return {
                    'success': True,
                    'session_id': session_id,
                    'total_wrong_questions': len(wrong_questions),
                    'message': f'開始學習 {len(wrong_questions)} 道錯題',
                    'source': 'mongodb'
                }
            
            # 如果都找不到數據，返回錯誤
            logger.warning(f"未找到用戶錯題數據")
            return {
                'success': False,
                'error': '未找到錯題數據，請先完成測驗'
            }
            
        except Exception as e:
            logger.error(f"❌ 開始錯題學習失敗: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# 創建服務實例
ai_teacher_service = AITeacherService()

# API 端點定義
@ai_teacher_bp.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """健康檢查"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    return jsonify({
        'success': True,
        'status': 'healthy',
        'rag_available': RAG_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@ai_teacher_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """AI 聊天端點"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400

        question = data.get('question', '').strip()
        conversation_type = data.get('type', 'general')
        session_id = data.get('session_id')  # 教學會話 ID

        if not question:
            return jsonify({'success': False, 'error': '問題不能為空'}), 400

        result = ai_teacher_service.chat_with_ai(
            question=question,
            conversation_type=conversation_type,
            session_id=session_id
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 聊天端點錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '處理請求時發生錯誤'
        }), 500

@ai_teacher_bp.route('/submit-quiz-results', methods=['POST', 'OPTIONS'])
def submit_quiz_results():
    """提交測驗結果"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400
        
        result = ai_teacher_service.submit_quiz_results(data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 提交測驗結果錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '提交測驗結果時發生錯誤'
        }), 500

@ai_teacher_bp.route('/get-quiz-result/<result_id>', methods=['GET', 'OPTIONS'])
def get_quiz_result(result_id):
    """獲取測驗結果"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 驗證 token 並獲取用戶 email
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'success': False, 'error': '未提供授權標頭'}), 401
        
        token = auth_header.split(" ")[1]
        user_email = get_user_info(token, 'email')
        if not user_email:
            return jsonify({'success': False, 'error': '無法獲取用戶資訊'}), 401
        
        # 解析 result_id 格式：result_<quiz_history_id>
        if not result_id.startswith('result_'):
            return jsonify({'success': False, 'error': '無效的結果ID格式'}), 400
        
        try:
            quiz_history_id = int(result_id.split('_')[1])
        except (ValueError, IndexError):
            return jsonify({'success': False, 'error': '無效的結果ID格式'}), 400
        
        print(f"📝 正在查詢測驗結果，quiz_history_id: {quiz_history_id}")
        
        # 從 SQL 數據庫查詢測驗結果
        from accessories import sqldb
        from sqlalchemy import text
        import json
        
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
                print(f"⚠️ 未找到測驗歷史記錄，quiz_history_id: {quiz_history_id}")
                return jsonify({'success': False, 'error': '測驗結果不存在'}), 404
            
            # 查詢錯題詳情
            error_result = conn.execute(text("""
                SELECT mongodb_question_id, user_answer, score, time_taken, created_at
                FROM quiz_errors 
                WHERE quiz_history_id = :quiz_history_id
                ORDER BY created_at
            """), {
                'quiz_history_id': quiz_history_id
            }).fetchall()
            
            # 從MongoDB獲取題目詳情
            from accessories import mongo
            exam_collection = mongo.db.exam
            
            errors = []
            for i, error in enumerate(error_result):
                # 從MongoDB獲取題目詳情
                question_detail = None
                if error[0]:  # mongodb_question_id
                    try:
                        question_detail = exam_collection.find_one({'_id': ObjectId(error[0])})
                    except Exception as e:
                        print(f"⚠️ 無法從MongoDB獲取題目 {error[0]}: {e}")
                
                errors.append({
                    'question_id': error[0],
                    'question_index': i,  # 使用循環索引
                    'user_answer': json.loads(error[1]) if error[1] else '',
                    'is_correct': False,  # 在 quiz_errors 表中的都是錯題
                    'score': float(error[2]) if error[2] else 0,
                    'time_taken': error[3],
                    'created_at': error[4].isoformat() if error[4] else None,
                    'question_detail': question_detail  # 添加題目詳情
                })
            
            total_questions = history_result[4]
            answered_questions = history_result[5]
            correct_count = history_result[6]
            wrong_count = history_result[7]
            unanswered_count = total_questions - answered_questions
            
            # 構建前端期望的數據結構
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
                'marked_count': 0,  # 添加前端期望的字段
                'accuracy_rate': float(history_result[8]) if history_result[8] else 0,
                'average_score': float(history_result[9]) if history_result[9] else 0,
                'total_time_taken': history_result[10],
                'total_time': history_result[10],  # 添加前端期望的字段
                'submit_time': history_result[11].isoformat() if history_result[11] else None,
                'status': history_result[12],
                'created_at': history_result[13].isoformat() if history_result[13] else None,
                'errors': errors,
                'answers': []  # 初始化為空數組
            }
            
            # 如果有錯誤，從 errors 轉換
            if errors:
                print(f"🔍 處理 {len(errors)} 道錯題")
                result_data['answers'] = []
                for error in errors:
                    print(f"🔍 處理錯題 {error['question_id']}: question_detail = {error['question_detail']}")
                    if error['question_detail']:
                        print(f"🔍 MongoDB 題目詳情: question = {error['question_detail'].get('question', 'None')}")
                        print(f"🔍 MongoDB 題目詳情: answer = {error['question_detail'].get('answer', 'None')}")
                    
                    answer_obj = {
                        'question_id': error['question_id'],
                        'question_text': (
                            error['question_detail'].get('question_text', f'題目 {error["question_index"] + 1}') 
                            if error['question_detail'] else f'題目 {error["question_index"] + 1}'
                        ),
                        'user_answer': error['user_answer'],
                        'correct_answer': (
                            error['question_detail'].get('answer', '無參考答案') 
                            if error['question_detail'] else '無參考答案'
                        ),
                        'is_correct': error['is_correct'],
                        'is_marked': False,  # 默認未標記
                        'score': error['score'],
                        'time_taken': error['time_taken'],
                        'feedback': error['user_answer'].get('feedback', {}).get('explanation', 'AI 評分結果') if isinstance(error['user_answer'], dict) else 'AI 評分結果'
                    }
                    print(f"🔍 構建的答案對象: question_text = {answer_obj['question_text']}")
                    result_data['answers'].append(answer_obj)
            # 如果沒有錯誤記錄，需要從MongoDB獲取所有題目詳情
            elif total_questions > 0:
                print(f"📝 沒有錯誤記錄，從MongoDB獲取 {total_questions} 道題目詳情")
                try:
                    # 從 quiz_templates 獲取題目ID列表
                    question_ids = history_result[14]  # qt.question_ids
                    if question_ids:
                        question_ids_list = json.loads(question_ids) if isinstance(question_ids, str) else question_ids
                        
                        # 從MongoDB獲取所有題目詳情
                        all_questions = []
                        print(f"🔍 開始從MongoDB獲取 {len(question_ids_list)} 道題目詳情")
                        for i, q_id in enumerate(question_ids_list):
                            print(f"🔍 處理題目 {i+1}: q_id = {q_id}")
                            try:
                                question_detail = exam_collection.find_one({'_id': ObjectId(q_id)})
                                print(f"🔍 MongoDB 查詢結果: question_detail = {question_detail}")
                                
                                if question_detail:
                                    print(f"🔍 題目內容: {question_detail.get('question_text', 'None')}")
                                    print(f"🔍 正確答案: {question_detail.get('answer', 'None')}")
                                
                                question_obj = {
                                    'question_id': q_id,
                                    'question_text': (
                                        question_detail.get('question_text', f'題目 {i+1}') 
                                        if question_detail else f'題目 {i+1}'
                                    ),
                                    'user_answer': '未作答',
                                    'correct_answer': (
                                        question_detail.get('answer', '無參考答案') 
                                        if question_detail else '無參考答案'
                                    ),
                                    'is_correct': False,
                                    'is_marked': False,
                                    'score': 0,
                                    'time_taken': 0,
                                    'feedback': {'explanation': '此題未作答'}
                                }
                                print(f"🔍 構建的題目對象: question_text = {question_obj['question_text']}")
                                all_questions.append(question_obj)
                            except Exception as e:
                                print(f"⚠️ 無法獲取題目 {q_id}: {e}")
                                # 如果無法獲取，使用默認值
                                fallback_obj = {
                                    'question_id': q_id,
                                    'question_text': f'題目 {i+1}',
                                    'user_answer': '未作答',
                                    'correct_answer': '無參考答案',
                                    'is_correct': False,
                                    'is_marked': False,
                                    'score': 0,
                                    'time_taken': 0,
                                    'feedback': {'explanation': '此題未作答'}
                                }
                                print(f"🔍 使用默認題目對象: question_text = {fallback_obj['question_text']}")
                                all_questions.append(fallback_obj)
                        
                        result_data['answers'] = all_questions
                        print(f"✅ 成功獲取 {len(all_questions)} 道題目詳情")
                    else:
                        print("⚠️ 題目模板中沒有題目ID列表")
                        # 生成默認題目數據
                        result_data['answers'] = [
                            {
                                'question_id': f'q{i+1}',
                                'question_text': f'題目 {i+1}',
                                'user_answer': '未作答',
                                'correct_answer': '無參考答案',
                                'is_correct': False,
                                'is_marked': False,
                                'score': 0,
                                'time_taken': 0,
                                'feedback': {'explanation': '此題未作答'}
                            }
                            for i in range(total_questions)
                        ]
                except Exception as e:
                    print(f"❌ 獲取所有題目詳情失敗: {e}")
                    # 如果失敗，生成默認題目數據
                    result_data['answers'] = [
                        {
                            'question_id': f'q{i+1}',
                            'question_text': f'題目 {i+1}',
                            'user_answer': '未作答',
                            'correct_answer': '無參考答案',
                            'is_correct': False,
                            'is_marked': False,
                            'score': 0,
                            'time_taken': 0,
                            'feedback': {'explanation': '此題未作答'}
                        }
                        for i in range(total_questions)
                    ]
            
            print(f"✅ 成功獲取測驗結果")
            print(f"📊 返回數據結構: {result_data}")
            
            return jsonify({
                'success': True,
                'message': '獲取測驗結果成功',
                'data': result_data
            }), 200
            
    except Exception as e:
        print(f"❌ 獲取測驗結果時發生錯誤: {str(e)}")
        return jsonify({'success': False, 'error': f'獲取測驗結果失敗: {str(e)}'}), 500

@ai_teacher_bp.route('/start-error-learning', methods=['POST', 'OPTIONS'])
def start_error_learning():
    """開始錯題學習"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400
        
        result_id = data.get('result_id')
        if not result_id:
            return jsonify({'success': False, 'error': '缺少測驗結果ID'}), 400
        
        # 驗證 token 並獲取用戶 email
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'success': False, 'error': '未提供授權標頭'}), 401
        
        token = auth_header.split(" ")[1]
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'success': False, 'error': '無法獲取用戶資訊'}), 401
        
        # 創建學習會話ID
        session_id = f"learning_{user_email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'開始錯題學習，會話ID: {session_id}'
        })
        
    except Exception as e:
        print(f"❌ 開始錯題學習錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '開始錯題學習時發生錯誤'
        }), 500

@ai_teacher_bp.route('/system-guide', methods=['POST', 'OPTIONS'])
def system_guide():
    """系統使用指南"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        data = request.get_json() or {}
        user_type = data.get('user_type', 'new')
        
        if user_type == 'new':
            guide = """
            🎓 **歡迎使用 AI 智能教學系統！**
            
            我是您的專屬 MIS 教學助理，可以幫助您：
            
            📚 **學習輔導**：
            • 回答 MIS 相關問題
            • 解釋複雜概念
            • 提供學習建議
            
            🎯 **錯題學習**：
            • 分析錯誤原因
            • 提供針對性輔導
            • 確保概念理解
            
            💡 **使用技巧**：
            • 直接提問任何 MIS 相關問題
            • 描述您的困惑和疑問
            • 我會根據您的程度調整解釋方式
            
            現在就開始提問吧！我很樂意幫助您學習。
            """
        else:
            guide = """
            👋 **歡迎回來！**
            
            我記得您之前的學習進度，讓我們繼續您的 MIS 學習之旅。
            
            您可以：
            • 繼續之前的話題
            • 提出新的問題
            • 複習之前討論的內容
            
            有什麼我可以幫助您的嗎？
            """
        
        return jsonify({
            'success': True,
            'guide': guide,
            'user_type': user_type
        })
        
    except Exception as e:
        logger.error(f"❌ 系統指南錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取系統指南時發生錯誤'
        }), 500

@ai_teacher_bp.route('/learning-analysis', methods=['GET', 'OPTIONS'])
def get_learning_analysis():
    """獲取學習分析報告"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        user_id = ai_teacher_service.get_user_id()
        session_data = ai_teacher_service.get_user_session_data(user_id)

        # 生成簡單的學習分析
        analysis = {
            'total_conversations': session_data.get('conversation_count', 0),
            'quiz_results_count': len(session_data.get('quiz_results', [])),
            'learning_sessions_count': len(session_data.get('learning_sessions', [])),
            'last_activity': session_data.get('last_activity'),
            'recommendations': [
                '建議多練習錯題',
                '可以嘗試更多 AI 對話學習',
                '定期複習已學概念'
            ]
        }

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        logger.error(f"❌ 獲取學習分析錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取學習分析時發生錯誤'
        }), 500

@ai_teacher_bp.route('/exam-guidance', methods=['POST', 'OPTIONS'])
def get_exam_guidance():
    """獲取考試指導"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400

        wrong_answers = data.get('wrong_answers', [])
        exam_results = data.get('exam_results', {})

        # 生成考試指導
        guidance = f"""
        📊 **考試結果分析**

        根據您的測驗結果，我發現了 {len(wrong_answers)} 個需要加強的地方：

        🎯 **重點改進方向**：
        • 加強基礎概念理解
        • 多做相關練習題
        • 重點複習錯誤題目

        💡 **學習建議**：
        建議您針對錯題進行深入學習，我可以為您提供個性化的教學指導。
        """

        return jsonify({
            'success': True,
            'guidance': guidance,
            'wrong_count': len(wrong_answers)
        })

    except Exception as e:
        logger.error(f"❌ 獲取考試指導錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取考試指導時發生錯誤'
        }), 500

@ai_teacher_bp.route('/get_user_answer_object', methods=['GET', 'OPTIONS'])
def get_user_answer_object():
    """獲取學生作答資料"""
    try:
        # 檢查請求方法
        if request.method == 'OPTIONS':
            return '', 204
            
        # 檢查授權標頭
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'success': False,
                    'error': '未提供授權標頭'
                }), 401
        except Exception as e:
            logger.error(f"❌ 檢查授權標頭錯誤: {e}")
            return jsonify({
                'success': False,
                'error': '檢查授權標頭時發生錯誤'
            }), 500

        # 解析 token 並獲取用戶資訊
        try:
            token = auth_header.split(" ")[1]
            user = get_user_info(token, 'name')
            if not user:
                return jsonify({
                    'success': False,
                    'error': '無法獲取用戶資訊'
                }), 401
        except Exception as e:
            logger.error(f"❌ 解析用戶資訊錯誤: {e}")
            return jsonify({
                'success': False,
                'error': '解析用戶資訊時發生錯誤'
            }), 500

        # 從資料庫獲取用戶答案
        try:
            user_answer_collection = mongo.db.user_answer
            user_answer_data = user_answer_collection.find_one(
                {"user_name": user}
            )
            if not user_answer_data:
                return jsonify({
                    'success': False,
                    'error': '找不到用戶答案資料'
                }), 404
        except Exception as e:
            logger.error(f"❌ 獲取用戶答案資料錯誤: {e}")
            return jsonify({
                'success': False,
                'error': '獲取用戶答案資料時發生錯誤'
            }), 500

        # 處理並返回資料
        try:
            session_data = user_answer_data
            return jsonify({
                'success': True,    
                'user_answer_object': session_data
            })
        except Exception as e:
            logger.error(f"❌ 處理返回資料錯誤: {e}")
            return jsonify({
                'success': False,
                'error': '處理返回資料時發生錯誤'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ 獲取學生作答資料錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取學生作答資料時發生錯誤'
        }), 500

@ai_teacher_bp.route('/learning-progress/<session_id>', methods=['GET', 'OPTIONS'])
def get_learning_progress(session_id):
    """獲取學習進度"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        # 驗證 token
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'success': False,
                    'error': '未提供授權標頭'
                }), 401
            
            token = auth_header.split(" ")[1]
            user_email = get_user_info(token, 'email')
            if not user_email:
                return jsonify({
                    'success': False,
                    'error': '無法獲取用戶資訊'
                }), 401
        except Exception as e:
            logger.error(f"❌ 驗證用戶錯誤: {e}")
            return jsonify({
                'success': False,
                'error': '驗證用戶時發生錯誤'
            }), 500

        # 獲取學習進度數據
        try:
            user_id = ai_teacher_service.get_user_id()
            session_data = ai_teacher_service.get_user_session_data(user_id)
            
            # 查找對應的學習會話
            learning_session = None
            for session in session_data.get('learning_sessions', []):
                if session.get('session_id') == session_id:
                    learning_session = session
                    break
            
            if not learning_session:
                return jsonify({
                    'success': False,
                    'error': f'未找到學習會話 {session_id}'
                }), 404
            
            # 構建學習進度數據
            progress_data = {
                'session_id': session_id,
                'user_id': user_id,
                'start_time': learning_session.get('start_time'),
                'current_status': 'active',
                'total_questions': 0,  # 將從實際數據中獲取
                'completed_questions': 0,
                'understanding_level': 'medium',
                'learning_time': 0,
                'last_activity': session_data.get('last_activity'),
                'conversation_count': session_data.get('conversation_count', 0)
            }
            
            return jsonify({
                'success': True,
                'progress': progress_data
            })
            
        except Exception as e:
            logger.error(f"❌ 獲取學習進度錯誤: {e}")
            return jsonify({
                'success': False,
                'error': '獲取學習進度時發生錯誤'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ 學習進度端點錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '處理學習進度請求時發生錯誤'
        }), 500

@ai_teacher_bp.route('/ai-tutoring', methods=['POST', 'OPTIONS'])
def ai_tutoring():
    """AI 智能教學"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400

        session_id = data.get('session_id')
        question_data = data.get('question_data')
        user_input = data.get('user_input')
        action = data.get('action')

        if not session_id or not user_input:
            return jsonify({'success': False, 'error': '缺少必要參數'}), 400

        # 調用 AI 教學服務
        result = ai_teacher_service.chat_with_ai(
            question=user_input,
            conversation_type='tutoring',
            session_id=session_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ AI 教學錯誤: {e}")
        return jsonify({
            'success': False,
            'error': 'AI 教學處理時發生錯誤'
        }), 500

@ai_teacher_bp.route('/complete-question-learning', methods=['POST', 'OPTIONS'])
def complete_question_learning():
    """完成題目學習"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400

        session_id = data.get('session_id')
        question_id = data.get('question_id')
        understanding_level = data.get('understanding_level')

        if not session_id or not question_id:
            return jsonify({'success': False, 'error': '缺少必要參數'}), 400

        # 這裡可以添加完成學習的邏輯
        # 目前返回成功響應
        return jsonify({
            'success': True,
            'message': '題目學習完成',
            'session_id': session_id,
            'question_id': question_id,
            'understanding_level': understanding_level
        })
        
    except Exception as e:
        logger.error(f"❌ 完成題目學習錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '完成題目學習時發生錯誤'
        }), 500

@ai_teacher_bp.route('/conversation-history', methods=['GET', 'OPTIONS'])
def get_conversation_history():
    """獲取對話歷史"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        limit = request.args.get('limit', 20, type=int)
        
        # 獲取用戶對話歷史
        user_id = ai_teacher_service.get_user_id()
        session_data = ai_teacher_service.get_user_session_data(user_id)
        
        # 構建對話歷史數據
        conversation_history = {
            'total_conversations': session_data.get('conversation_count', 0),
            'recent_conversations': [],
            'last_activity': session_data.get('last_activity')
        }
        
        return jsonify({
            'success': True,
            'history': conversation_history
        })
        
    except Exception as e:
        logger.error(f"❌ 獲取對話歷史錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取對話歷史時發生錯誤'
        }), 500

@ai_teacher_bp.route('/knowledge-questions', methods=['GET', 'OPTIONS'])
def get_knowledge_questions():
    """獲取知識點測驗題目"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        topic = request.args.get('topic', '')
        difficulty = request.args.get('difficulty', 'medium')
        count = request.args.get('count', 5, type=int)
        
        # 這裡可以從資料庫獲取對應的題目
        # 目前返回模擬數據
        questions = []
        for i in range(min(count, 5)):
            questions.append({
                'id': f'knowledge_{i+1}',
                'question_text': f'{topic} 相關題目 {i+1}',
                'options': ['選項A', '選項B', '選項C', '選項D'],
                'correct_answer': '選項A',
                'difficulty': difficulty,
                'topic': topic
            })
        
        return jsonify({
            'success': True,
            'questions': questions,
            'total': len(questions)
        })
        
    except Exception as e:
        logger.error(f"❌ 獲取知識點題目錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取知識點題目時發生錯誤'
        }), 500

@ai_teacher_bp.route('/past-exam-questions', methods=['GET', 'OPTIONS'])
def get_past_exam_questions():
    """獲取考古題測驗題目"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        school = request.args.get('school', '')
        year = request.args.get('year', '')
        department = request.args.get('department', '')
        
        # 這裡可以從資料庫獲取對應的考古題
        # 目前返回模擬數據
        questions = []
        for i in range(5):
            questions.append({
                'id': f'past_exam_{i+1}',
                'question_text': f'{school} {year}年 {department} 考古題 {i+1}',
                'options': ['選項A', '選項B', '選項C', '選項D'],
                'correct_answer': '選項A',
                'school': school,
                'year': year,
                'department': department
            })
        
        return jsonify({
            'success': True,
            'questions': questions,
            'total': len(questions)
        })
        
    except Exception as e:
        logger.error(f"❌ 獲取考古題錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取考古題時發生錯誤'
        }), 500

@ai_teacher_bp.route('/submit-quiz-answers', methods=['POST', 'OPTIONS'])
def submit_quiz_answers():
    """提交測驗答案"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400

        # 處理測驗答案提交
        quiz_id = data.get('quiz_id')
        answers = data.get('answers', {})
        
        # 計算分數
        total_questions = len(answers)
        correct_count = 0
        
        for question_id, answer in answers.items():
            # 這裡可以添加答案驗證邏輯
            if answer.get('is_correct', False):
                correct_count += 1
        
        score = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        return jsonify({
            'success': True,
            'quiz_id': quiz_id,
            'score': score,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'wrong_count': total_questions - correct_count
        })
        
    except Exception as e:
        logger.error(f"❌ 提交測驗答案錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '提交測驗答案時發生錯誤'
        }), 500

@ai_teacher_bp.route('/get-quiz-result/<result_id>', methods=['GET', 'OPTIONS'])
def get_quiz_result_proxy(result_id):
    """測驗結果代理路由 - 轉發到 quiz.py 的 get_quiz_result 函數"""
    try:
        # 處理 CORS 預檢請求
        if request.method == 'OPTIONS':
            return jsonify({'message': 'CORS preflight'}), 200
        
        # 導入 quiz 模組中的 get_quiz_result 函數
        from .quiz import get_quiz_result
        
        # 調用 quiz.py 中的 get_quiz_result 函數
        return get_quiz_result(result_id)
        
    except Exception as e:
        logger.error(f"❌ 測驗結果代理路由錯誤: {e}")
        return jsonify({
            'success': False,
            'message': f'獲取測驗結果失敗: {str(e)}'
        }), 500
