from flask import jsonify, request, Blueprint, current_app
from accessories import mongo
from src.api import verify_token

# 創建 AI 測驗藍圖
ai_quiz_bp = Blueprint('ai_quiz', __name__)

@ai_quiz_bp.route('/get-user-submissions-analysis', methods=['POST', 'OPTIONS'])
def get_user_submissions_analysis():
    """獲取用戶提交分析數據 - 用於錯題統整"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True})
        
        # 驗證用戶身份
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少授權token'}), 401
        
        user_email = verify_token(token.split(" ")[1])
        if not user_email:
            return jsonify({'error': '無效的token'}), 401
        
        # 從 MongoDB user_answer 集合獲取用戶的所有提交記錄
        submissions = list(mongo.db.user_answer.find(
            {'user_email': user_email},
            {'_id': 0}  # 排除 _id 字段
        ).sort('submit_time', -1))  # 按提交時間倒序排列
        
        print(f"找到 {len(submissions)} 條提交記錄")
        
        # 處理提交數據，確保每個題目都有完整的分析信息
        processed_submissions = []
        for submission in submissions:
            # 獲取評分結果統計
            print(submission)
            grading_results = submission.get('grading_results', {})
            answer_summary = submission.get('answer_summary', {})
            
            processed_submission = {
                'submission_id': submission.get('submission_id', ''),
                'quiz_type': submission.get('subject', 'unknown'),  # 使用 subject 作為測驗類型
                'submit_time': submission.get('submit_time', ''),
                'total_questions': submission.get('processed_count', 0) + submission.get('skipped_count', 0),
                'total_score': submission.get('total_score', 0),
                'average_score': submission.get('average_score', 0),
                'correct_count': submission.get('correct_count', 0),
                'accuracy_rate': submission.get('accuracy_rate', 0),
                'processed_count': submission.get('processed_count', 0),
                'skipped_count': submission.get('skipped_count', 0),
                'error_count': submission.get('error_count', 0),
                'grading_method': submission.get('grading_method', 'unknown'),
                'status': submission.get('status', 'unknown'),
                'answers': submission.get('answers', [])  # 直接使用原始的 answers 數組
            }
            
            processed_submissions.append(processed_submission)
        
        return jsonify({
            'success': True,
            'submissions': processed_submissions,
            'total_submissions': len(processed_submissions)
        })
        
    except Exception as e:
        print(f"❌ 獲取用戶提交分析失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取用戶提交分析失敗：{str(e)}'
        }), 500

@ai_quiz_bp.route('/get-user-errors-mongo', methods=['POST', 'OPTIONS'])
def get_user_errors_mongo():
    """從 MongoDB error_questions 集合獲取用戶錯題"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True})
        
        # 驗證用戶身份
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少授權token'}), 401
        
        user_email = verify_token(token.split(" ")[1])
        if not user_email:
            return jsonify({'error': '無效的token'}), 401
        
        # 從 MongoDB error_questions 集合獲取用戶錯題
        error_questions = list(mongo.db.error_questions.find(
            {'user_email': user_email},
            {'_id': 0}  # 排除 _id 字段
        ).sort('timestamp', -1))  # 按時間倒序排列
        
        return jsonify({
            'success': True,
            'error_questions': error_questions,
            'total_errors': len(error_questions)
        })
        
    except Exception as e:
        print(f"❌ 獲取用戶錯題失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'獲取用戶錯題失敗：{str(e)}'
        }), 500
