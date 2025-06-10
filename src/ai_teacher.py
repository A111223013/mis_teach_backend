"""
AI 教學系統 API 端點
整合 RAG 系統，提供完整的智能教學 API 服務
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from typing import Dict, Any, List, Optional
import uuid

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

            # 查找測驗結果
            target_result = None
            for result in session_data.get('quiz_results', []):
                if f"result_{result['user_id']}_{result['quiz_id']}_{result['submit_time']}" == result_id:
                    target_result = result
                    break

            # 如果找不到真實結果，使用 demo 數據
            if not target_result:
                logger.info(f"未找到測驗結果 {result_id}，使用 demo 數據進行錯題學習")
                target_result = self._generate_demo_quiz_result(result_id)
            
            # 提取錯題
            wrong_questions = [
                answer for answer in target_result['answers'] 
                if not answer.get('is_correct', True)
            ]
            
            if not wrong_questions:
                return {
                    'success': True,
                    'message': '恭喜！您沒有錯題需要學習',
                    'wrong_questions': []
                }
            
            # 調用 MultiAITutor 創建學習會話
            result = self.tutor.create_learning_session(user_id, wrong_questions)

            # 保存會話 ID 到用戶數據（用於追蹤）
            if 'learning_sessions' not in session_data:
                session_data['learning_sessions'] = []
            session_data['learning_sessions'].append({
                'session_id': result['session_id'],
                'result_id': result_id,
                'start_time': datetime.now().isoformat()
            })

            return result
            
        except Exception as e:
            logger.error(f"❌ 開始錯題學習失敗: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # 移除所有 AI 邏輯，這些已經移到 rag_ai_role.py 中

    def _generate_demo_quiz_result(self, result_id: str) -> Dict[str, Any]:
        """生成 demo 測驗結果用於測試"""
        demo_answers = [
            {
                'question_id': 'q1',
                'question_text': '什麼是作業系統中的死鎖（Deadlock）？',
                'user_answer': '程式停止運行',
                'correct_answer': '兩個或多個程序互相等待對方釋放資源而無法繼續執行的狀態',
                'is_correct': False,
                'is_marked': True,
                'topic': '作業系統',
                'difficulty': 3,
                'answer_time': 45
            },
            {
                'question_id': 'q2',
                'question_text': 'FIFO 排程演算法的特點是什麼？',
                'user_answer': '先進先出，按照程序到達的順序執行',
                'correct_answer': '先進先出，按照程序到達的順序執行',
                'is_correct': True,
                'is_marked': False,
                'topic': '作業系統',
                'difficulty': 2,
                'answer_time': 30
            },
            {
                'question_id': 'q3',
                'question_text': '資料庫中的 ACID 特性包括哪些？',
                'user_answer': '原子性、一致性',
                'correct_answer': '原子性（Atomicity）、一致性（Consistency）、隔離性（Isolation）、持久性（Durability）',
                'is_correct': False,
                'is_marked': True,
                'topic': '資料庫',
                'difficulty': 4,
                'answer_time': 60
            },
            {
                'question_id': 'q4',
                'question_text': 'TCP 和 UDP 的主要差異是什麼？',
                'user_answer': 'TCP 可靠，UDP 不可靠',
                'correct_answer': 'TCP 是面向連接的可靠傳輸協議，UDP 是無連接的不可靠傳輸協議',
                'is_correct': True,
                'is_marked': True,  # 標記但正確的題目
                'topic': '網路',
                'difficulty': 3,
                'answer_time': 40
            },
            {
                'question_id': 'q5',
                'question_text': '什麼是資料結構中的堆疊（Stack）？',
                'user_answer': '一種資料結構',
                'correct_answer': '後進先出（LIFO）的線性資料結構',
                'is_correct': False,
                'is_marked': False,
                'topic': '資料結構',
                'difficulty': 2,
                'answer_time': 25
            }
        ]

        correct_count = sum(1 for answer in demo_answers if answer['is_correct'])
        total_questions = len(demo_answers)

        return {
            'user_id': 'demo_user',
            'quiz_id': 'demo_quiz',
            'answers': demo_answers,
            'submit_time': datetime.now().isoformat(),
            'total_time': 300,
            'score': correct_count,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'wrong_count': total_questions - correct_count,
            'marked_count': sum(1 for answer in demo_answers if answer['is_marked']),
            'unanswered_count': 0
        }

# 創建服務實例
ai_teacher_service = AITeacherService()

# API 端點定義
@ai_teacher_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'rag_available': RAG_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@ai_teacher_bp.route('/chat', methods=['POST'])
def chat():
    """AI 聊天端點"""
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

@ai_teacher_bp.route('/submit-quiz-results', methods=['POST'])
def submit_quiz_results():
    """提交測驗結果"""
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

@ai_teacher_bp.route('/get-quiz-result/<result_id>', methods=['GET'])
def get_quiz_result(result_id):
    """獲取測驗結果"""
    try:
        user_id = ai_teacher_service.get_user_id()
        session_data = ai_teacher_service.get_user_session_data(user_id)

        # 查找測驗結果
        for result in session_data.get('quiz_results', []):
            if f"result_{result['user_id']}_{result['quiz_id']}_{result['submit_time']}" == result_id:
                return jsonify({
                    'success': True,
                    'result': result
                })

        # 如果找不到結果，返回 demo 數據用於測試
        logger.info(f"未找到測驗結果 {result_id}，返回 demo 數據")
        demo_result = ai_teacher_service._generate_demo_quiz_result(result_id)

        return jsonify({
            'success': True,
            'result': demo_result,
            'is_demo': True
        })
        
    except Exception as e:
        logger.error(f"❌ 獲取測驗結果錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '獲取測驗結果時發生錯誤'
        }), 500

@ai_teacher_bp.route('/start-error-learning', methods=['POST'])
def start_error_learning():
    """開始錯題學習"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '無效的請求數據'}), 400
        
        result_id = data.get('result_id')
        if not result_id:
            return jsonify({'success': False, 'error': '缺少測驗結果ID'}), 400
        
        result = ai_teacher_service.start_error_learning(result_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 開始錯題學習錯誤: {e}")
        return jsonify({
            'success': False,
            'error': '開始錯題學習時發生錯誤'
        }), 500

@ai_teacher_bp.route('/system-guide', methods=['POST'])
def system_guide():
    """系統使用指南"""
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

@ai_teacher_bp.route('/learning-analysis', methods=['GET'])
def get_learning_analysis():
    """獲取學習分析報告"""
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

@ai_teacher_bp.route('/exam-guidance', methods=['POST'])
def get_exam_guidance():
    """獲取考試指導"""
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
