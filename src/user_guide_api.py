from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from datetime import datetime
import logging
from src.config import get_db_connection

# 創建藍圖
user_guide_bp = Blueprint('user_guide', __name__)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@user_guide_bp.route('/api/user-guide/status', methods=['GET'])
@cross_origin()
def get_user_guide_status():
    """
    獲取用戶導覽狀態
    """
    try:
        # 從 session 獲取用戶 ID，如果沒有則使用預設值
        user_id = session.get('user_id', 'anonymous_user')
        
        # 連接 MongoDB
        db = get_db_connection()
        users_collection = db.users
        
        # 查找用戶記錄
        user_record = users_collection.find_one({'user_id': user_id})
        
        if user_record:
            # 用戶存在，返回實際狀態
            status = {
                'user_id': user_id,
                'new_user': user_record.get('new_user', True),
                'guide_completed': user_record.get('guide_completed', False),
                'last_login': user_record.get('last_login', datetime.now().isoformat()),
                'guide_completion_date': user_record.get('guide_completion_date')
            }
        else:
            # 用戶不存在，創建新用戶記錄
            new_user_record = {
                'user_id': user_id,
                'new_user': True,
                'guide_completed': False,
                'last_login': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            users_collection.insert_one(new_user_record)
            
            status = {
                'user_id': user_id,
                'new_user': True,
                'guide_completed': False,
                'last_login': new_user_record['last_login']
            }
        
        logger.info(f"用戶 {user_id} 導覽狀態: {status}")
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"獲取用戶導覽狀態失敗: {str(e)}")
        return jsonify({
            'error': '獲取用戶狀態失敗',
            'message': str(e)
        }), 500

@user_guide_bp.route('/api/user-guide/mark-guided', methods=['POST'])
@cross_origin()
def mark_user_as_guided():
    """
    標記用戶已完成導覽
    """
    try:
        # 從 session 獲取用戶 ID
        user_id = session.get('user_id', 'anonymous_user')
        
        # 連接 MongoDB
        db = get_db_connection()
        users_collection = db.users
        
        # 更新用戶記錄
        update_result = users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'new_user': False,
                    'guide_completed': True,
                    'guide_completion_date': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
            },
            upsert=True  # 如果用戶不存在則創建
        )
        
        if update_result.modified_count > 0 or update_result.upserted_id:
            logger.info(f"用戶 {user_id} 已完成導覽")
            return jsonify({
                'success': True,
                'message': '導覽狀態已更新',
                'user_id': user_id,
                'completion_date': datetime.now().isoformat()
            }), 200
        else:
            logger.warning(f"用戶 {user_id} 導覽狀態更新失敗")
            return jsonify({
                'success': False,
                'message': '導覽狀態更新失敗'
            }), 400
            
    except Exception as e:
        logger.error(f"標記用戶導覽完成失敗: {str(e)}")
        return jsonify({
            'error': '標記導覽完成失敗',
            'message': str(e)
        }), 500

@user_guide_bp.route('/api/user-guide/reset', methods=['POST'])
@cross_origin()
def reset_user_guide_status():
    """
    重置用戶導覽狀態（用於測試）
    """
    try:
        # 從 session 獲取用戶 ID
        user_id = session.get('user_id', 'anonymous_user')
        
        # 連接 MongoDB
        db = get_db_connection()
        users_collection = db.users
        
        # 重置用戶記錄
        update_result = users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'new_user': True,
                    'guide_completed': False,
                    'guide_completion_date': None,
                    'last_updated': datetime.now().isoformat(),
                    'reset_at': datetime.now().isoformat()
                }
            },
            upsert=True
        )
        
        if update_result.modified_count > 0 or update_result.upserted_id:
            logger.info(f"用戶 {user_id} 導覽狀態已重置")
            return jsonify({
                'success': True,
                'message': '導覽狀態已重置為新用戶',
                'user_id': user_id,
                'reset_date': datetime.now().isoformat()
            }), 200
        else:
            logger.warning(f"用戶 {user_id} 導覽狀態重置失敗")
            return jsonify({
                'success': False,
                'message': '導覽狀態重置失敗'
            }), 400
            
    except Exception as e:
        logger.error(f"重置用戶導覽狀態失敗: {str(e)}")
        return jsonify({
            'error': '重置導覽狀態失敗',
            'message': str(e)
        }), 500

@user_guide_bp.route('/api/user-guide/stats', methods=['GET'])
@cross_origin()
def get_guide_statistics():
    """
    獲取導覽統計數據
    """
    try:
        # 連接 MongoDB
        db = get_db_connection()
        users_collection = db.users
        
        # 統計數據
        total_users = users_collection.count_documents({})
        new_users = users_collection.count_documents({'new_user': True})
        guided_users = users_collection.count_documents({'guide_completed': True})
        
        stats = {
            'total_users': total_users,
            'new_users': new_users,
            'guided_users': guided_users,
            'completion_rate': round((guided_users / total_users * 100), 2) if total_users > 0 else 0,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"導覽統計數據: {stats}")
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"獲取導覽統計失敗: {str(e)}")
        return jsonify({
            'error': '獲取統計數據失敗',
            'message': str(e)
        }), 500

# 測試端點
@user_guide_bp.route('/api/user-guide/test', methods=['GET'])
@cross_origin()
def test_user_guide_api():
    """
    測試 API 連接
    """
    try:
        user_id = session.get('user_id', 'test_user')
        return jsonify({
            'success': True,
            'message': '用戶導覽 API 正常運作',
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'error': 'API 測試失敗',
            'message': str(e)
        }), 500
