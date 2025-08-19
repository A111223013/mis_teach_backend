"""
AI 教學系統 API 端點
整合 RAG 系統，提供完整的智能教學 API 服務
"""

import logging
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

# ==================== 全局變數 ====================

# 用戶會話數據
user_sessions = {}

# ==================== 工具函數 ====================

def get_user_id() -> str:
        """獲取用戶 ID"""
        if 'user_id' not in session:
            session['user_id'] = f"user_{uuid.uuid4().hex[:8]}"
        return session['user_id']
    
def get_user_session_data(user_id: str) -> Dict[str, Any]:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
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
    return user_sessions[user_id]
    
def chat_with_ai(question: str, conversation_type: str = "general", session_id: str = None) -> dict:
    """AI 對話處理"""
    try:
        # 檢查 AI 服務是否可用
        if not RAG_AVAILABLE:
            return {
                'success': False,
                'error': 'AI 服務不可用',
                'response': '抱歉，AI 教學服務暫時不可用。'
            }

        # 根據對話類型處理
        if conversation_type == "tutoring" and session_id:
            # 使用 RAG 系統的教學對話
            try:
                response = handle_tutoring_conversation(session_id, question, user_id or "default")
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
            # 一般對話
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
    """獲取測驗結果數據 - 供內部調用"""
    try:
        # 解析 result_id 格式：result_<quiz_history_id>
        if not result_id.startswith('result_'):
            return None
        
        try:
            quiz_history_id = int(result_id.split('_')[1])
        except (ValueError, IndexError):
            return None
        
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
                return None
            
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
            
            # 從MongoDB獲取題目詳情
            from accessories import mongo
            exam_collection = mongo.db.exam
            
            errors = []
            questions = []  # 新增 questions 陣列
            
            # 處理錯題
            for i, error in enumerate(error_result):
                try:
                    mongodb_question_id = error[0]
                    user_answer = error[1]
                    score = error[2]
                    time_taken = error[3]
                    
                    # 從MongoDB獲取題目詳情
                    question_detail = exam_collection.find_one({"_id": mongodb_question_id})
                    
                    if question_detail:
                        error_data = {
                            'question_id': f'q{i+1}',
                            'question_text': question_detail.get('question_text', f'題目 {i+1}'),
                            'user_answer': user_answer or '未作答',
                            'correct_answer': question_detail.get('answer', '無參考答案'),
                            'is_correct': False,
                            'is_marked': False,
                            'score': score,
                            'time_taken': time_taken,
                            'topic': question_detail.get('topic', '計算機概論'),
                            'difficulty': question_detail.get('difficulty', 2),
                            'options': question_detail.get('options', []),
                            'image_file': question_detail.get('image_file', ''),
                            'question_type': question_detail.get('question_type', 'short-answer'),
                            'feedback': {'explanation': '此題答錯'}
                        }
                        errors.append(error_data)
                        questions.append(error_data)  # 同時加入 questions
                except Exception as e:
                    print(f"❌ 處理錯題 {i+1} 時發生錯誤: {e}")
                    continue
            
            # 如果有題目ID列表，構建完整的題目陣列
            if question_ids:
                print(f"🔍 開始構建完整題目陣列，共 {len(question_ids)} 道題目")
                
                # 創建錯題字典，方便查詢用戶答案
                error_dict = {}
                for error in error_result:
                    mongodb_question_id = error[0]
                    user_answer = error[1]
                    error_dict[mongodb_question_id] = {
                        'user_answer': user_answer,
                        'score': error[2],
                        'time_taken': error[3]
                    }
                
                print(f"📊 錯題字典: {list(error_dict.keys())}")
                
                # 計算統計數據
                total_questions = len(question_ids)
                error_count = len(error_dict)
                correct_count = history_result[6]  # 從資料庫獲取正確數
                answered_count = history_result[5]  # 從資料庫獲取已答題數
                unanswered_count = total_questions - answered_count
                
                print(f"📊 統計數據:")
                print(f"  - 總題數: {total_questions}")
                print(f"  - 已答題數: {answered_count}")
                print(f"  - 正確數: {correct_count}")
                print(f"  - 錯誤數: {error_count}")
                print(f"  - 未答題數: {unanswered_count}")
                
                # 根據已答題數，判斷前N題為已作答，後面的為未作答
                # 這是基於題目順序的假設，可能需要根據實際資料庫結構調整
                answered_question_ids = set(question_ids[:answered_count])
                unanswered_question_ids = set(question_ids[answered_count:])
                
                print(f"📊 題目分類:")
                print(f"  - 已作答題目數量: {len(answered_question_ids)}")
                print(f"  - 未作答題目數量: {len(unanswered_question_ids)}")
                print(f"  - 已作答題目ID範例: {list(answered_question_ids)[:3] if answered_question_ids else '無'}")
                print(f"  - 未作答題目ID範例: {list(unanswered_question_ids)[:3] if unanswered_question_ids else '無'}")
                
                for i, question_id in enumerate(question_ids):
                    try:
                        print(f"🔍 處理題目 {i+1}: {question_id}")
                        
                        # 檢查題目狀態
                        is_error = question_id in error_dict
                        is_answered = question_id in answered_question_ids
                        
                        print(f"  - 是否為錯題: {is_error}")
                        print(f"  - 是否為已作答: {is_answered}")
                        
                        # 從MongoDB獲取題目詳情
                        from bson import ObjectId
                        
                        try:
                            # 嘗試轉換為 ObjectId
                            if isinstance(question_id, str) and len(question_id) == 24:
                                object_id = ObjectId(question_id)
                                print(f"  - 轉換為 ObjectId: {object_id}")
                            else:
                                print(f"  - 題目ID格式不正確: {question_id}")
                                continue
                        except Exception as oid_error:
                            print(f"  - ObjectId 轉換失敗: {oid_error}")
                            continue
                        
                        question_detail = exam_collection.find_one({"_id": object_id})
                        
                        if question_detail:
                            # 構建題目資料
                            if is_error:
                                # 錯題：使用錯誤記錄中的用戶答案
                                error_info = error_dict[question_id]
                                user_answer = error_info['user_answer']
                                
                                # 解析用戶答案 JSON
                                try:
                                    answer_data = json.loads(user_answer)
                                    actual_user_answer = answer_data.get('answer', '')
                                    print(f"  - 用戶答案: {actual_user_answer}")
                                except:
                                    actual_user_answer = user_answer
                                    print(f"  - 用戶答案解析失敗: {user_answer}")
                                
                                question_data = {
                                    'question_id': f'q{i+1}',
                                    'question_text': question_detail.get('question_text', f'題目 {i+1}'),
                                    'user_answer': actual_user_answer,
                                    'correct_answer': question_detail.get('answer', '無參考答案'),
                                    'is_correct': False,  # 錯題
                                    'is_marked': False,
                                    'score': float(error_info['score']) if error_info['score'] else 0,
                                    'time_taken': error_info['time_taken'] if error_info['time_taken'] else 0,
                                    'topic': question_detail.get('topic', '計算機概論'),
                                    'difficulty': question_detail.get('difficulty', 2),
                                    'options': question_detail.get('options', []),
                                    'image_file': question_detail.get('image_file', ''),
                                    'question_type': question_detail.get('question_type', 'short-answer')
                                }
                                print(f"  - 題目狀態: 錯題")
                            elif is_answered and not is_error:
                                # 已作答且正確的題目
                                question_data = {
                                    'question_id': f'q{i+1}',
                                    'question_text': question_detail.get('question_text', f'題目 {i+1}'),
                                    'user_answer': '正確作答',  # 標記為正確作答
                                    'correct_answer': question_detail.get('answer', '無參考答案'),
                                    'is_correct': True,  # 正確作答
                                    'is_marked': False,
                                    'score': 1.0,
                                    'time_taken': 0,
                                    'topic': question_detail.get('topic', '計算機概論'),
                                    'difficulty': question_detail.get('difficulty', 2),
                                    'options': question_detail.get('options', []),
                                    'image_file': question_detail.get('image_file', ''),
                                    'question_type': question_detail.get('question_type', 'short-answer')
                                }
                                print(f"  - 題目狀態: 正確作答")
                            else:
                                # 未作答的題目
                                question_data = {
                                    'question_id': f'q{i+1}',
                                    'question_text': question_detail.get('question_text', f'題目 {i+1}'),
                                    'user_answer': '',  # 未作答
                                    'correct_answer': question_detail.get('answer', '無參考答案'),
                                    'is_correct': False,  # 未作答不算正確
                                    'is_marked': False,
                                    'score': 0.0,
                                    'time_taken': 0,
                                    'topic': question_detail.get('topic', '計算機概論'),
                                    'difficulty': question_detail.get('difficulty', 2),
                                    'options': question_detail.get('options', []),
                                    'image_file': question_detail.get('image_file', ''),
                                    'question_type': question_detail.get('question_type', 'short-answer')
                                }
                                print(f"  - 題目狀態: 未作答")
                            
                            questions.append(question_data)
                            print(f"✅ 新增題目 {i+1}: {question_data['question_text'][:50]}...")
                        else:
                            print(f"⚠️ 找不到題目 {i+1}: {question_id}")
                    except Exception as e:
                        print(f"❌ 處理題目 {i+1} 時發生錯誤: {e}")
                        continue
            else:
                print(f"⚠️ 沒有題目ID列表，無法構建完整題目陣列")
            
            print(f"📊 最終統計:")
            print(f"  - 總題數: {history_result[4]}")
            print(f"  - 錯題數: {len(errors)}")
            print(f"  - 題目陣列長度: {len(questions)}")
            print(f"  - 資料庫統計: 正確 {history_result[6]}，錯誤 {history_result[7]}，已答 {history_result[5]}")
            
            # 驗證統計數據
            actual_error_count = len([q for q in questions if not q['is_correct'] and q['user_answer'] and q['user_answer'] != '正確作答'])
            actual_correct_count = len([q for q in questions if q['is_correct'] and q['user_answer'] == '正確作答'])
            actual_unanswered_count = len([q for q in questions if not q['user_answer']])
            
            print(f"📊 驗證統計:")
            print(f"  - 實際錯題數: {actual_error_count}")
            print(f"  - 實際正確數: {actual_correct_count}")
            print(f"  - 實際未答數: {actual_unanswered_count}")
            
            # 構建結果數據
            result_data = {
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
                'questions': questions,  # 新增 questions 陣列
                'errors': errors
            }
            
            print(f"✅ 成功獲取測驗結果")
            return result_data
            
    except Exception as e:
        print(f"❌ 獲取測驗結果時發生錯誤: {str(e)}")
        return None

# ==================== API路由 ====================

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

        result = chat_with_ai(
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

@ai_teacher_bp.route('/ai-tutoring', methods=['POST', 'OPTIONS'])
def ai_tutoring():
    """AI 教學對話端點 - 使用 RAG 系統"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400
        
        user_input = data.get('user_input', '').strip()
        session_id = data.get('session_id')
        conversation_type = data.get('conversation_type', 'tutoring')

        if not session_id:
            return jsonify({'success': False, 'error': '會話ID不能為空'}), 400

        # 獲取用戶ID（從token或session）
        user_id = get_user_id() or "default"
        
        print(f"🎓 AI教學對話請求:")
        print(f"  - 用戶輸入: {user_input}")
        print(f"  - 會話ID: {session_id}")
        print(f"  - 對話類型: {conversation_type}")
        print(f"  - 用戶ID: {user_id}")

        # 使用 RAG 系統的教學對話
        try:
            response = handle_tutoring_conversation(session_id, user_input, user_id)
            print(f"✅ RAG教學回應: {response[:100]}...")
            
            return jsonify({
                'success': True,
                'response': response,
                'conversation_type': 'tutoring',
                'session_id': session_id
            })
            
        except Exception as rag_error:
            print(f"❌ RAG教學對話失敗: {rag_error}")
            # 如果RAG失敗，回退到一般AI對話
            fallback_result = chat_with_ai(
                question=user_input or "初始化會話",
                conversation_type=conversation_type,
                session_id=session_id
            )
            return jsonify(fallback_result)
        
    except Exception as e:
        logger.error(f"❌ AI教學對話端點錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '處理教學對話時發生錯誤'
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
        
        # 處理測驗數據
        processed_result = {
            'user_id': get_user_id(),
            'quiz_id': data.get('quiz_id', ''),
            'answers': data.get('answers', []),
            'submit_time': data.get('submit_time', datetime.now().isoformat()),
            'total_time': data.get('total_time', 0),
            'score': data.get('score', 0),
            'total_questions': len(data.get('answers', [])),
            'correct_count': sum(1 for answer in data.get('answers', []) if answer.get('is_correct', False)),
            'wrong_count': sum(1 for answer in data.get('answers', []) if not answer.get('is_correct', False)),
            'marked_count': sum(1 for answer in data.get('answers', []) if answer.get('is_marked', False)),
            'unanswered_count': 0 # 假設所有題目都已回答
        }
        
        # 保存到用戶會話
        user_id = get_user_id()
        session_data = get_user_session_data(user_id)
        session_data['quiz_results'].append(processed_result)
        
        # 生成結果 ID
        result_id = f"result_{processed_result['user_id']}_{processed_result['quiz_id']}_{processed_result['submit_time']}"
            
        return jsonify({
            'success': True,
            'result_id': result_id,
            'message': '測驗結果提交成功'
        })
            
    except Exception as e:
        logger.error(f"❌ 提交測驗結果失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

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
        user_email = get_user_info(token, 'email')
        if not user_email:
            return jsonify({'success': False, 'error': '無法獲取用戶資訊'}), 401
        
        # 創建學習會話ID
        session_id = f"learning_{user_email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 保存會話 ID 到用戶數據（用於追蹤）
        user_id = get_user_id()
        session_data = get_user_session_data(user_id)
        session_data['learning_sessions'].append({
            'session_id': session_id,
            'result_id': result_id,
            'start_time': datetime.now().isoformat(),
            'source': 'mongodb', # 暫時固定為 mongodb，後續可改為 redis 或直接從 quiz_errors 讀取
            'error_count': 0 # 後續從 quiz_errors 讀取
        })
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'開始錯題學習，會話ID: {session_id}'
        })
        
    except Exception as e:
        logger.error(f"❌ 開始錯題學習失敗: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@ai_teacher_bp.route('/get-quiz-result/<result_id>', methods=['GET', 'OPTIONS'])
def get_quiz_result(result_id):
    """獲取測驗結果"""
    if request.method == 'OPTIONS':
        return jsonify({'message': 'CORS preflight'}), 200
    
    try:
        # 獲取測驗結果數據
        result_data = get_quiz_result_data(result_id)
        
        if not result_data:
            return jsonify({'success': False, 'error': '測驗結果不存在'}), 404
        
        return jsonify({
            'success': True,
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f"❌ 獲取測驗結果失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取測驗結果失敗：{str(e)}'
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
        user_id = get_user_id()
        session_data = get_user_session_data(user_id)

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
            user_id = get_user_id()
            session_data = get_user_session_data(user_id)
            
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
        user_id = get_user_id()
        session_data = get_user_session_data(user_id)
        
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

# ==================== 初始化檢查 ====================

def check_system_ready():
    """檢查系統是否準備就緒"""
    try:
        if RAG_AVAILABLE:
            logger.info("✅ AI教學系統初始化完成")
        else:
            logger.warning("⚠️ AI教學系統部分功能不可用")
        return True
    except Exception as e:
        logger.error(f"❌ AI教學系統初始化失敗: {e}")
        return False

# 系統啟動時檢查
if __name__ == "__main__":
    check_system_ready()
