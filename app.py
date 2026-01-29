from flask import Flask, jsonify, request, Blueprint, send_from_directory
from flask_cors import CORS
import sys
from accessories import sqldb, mail, redis_client, token_store, mongo, login_manager, init_mongo_data
from sqlalchemy import text
from config import Config, ProductionConfig, DevelopmentConfig
from src.login import login_bp
from src.register import register_bp
from src.dashboard import dashboard_bp
from src.quiz import quiz_bp, init_quiz_tables
from src.ai_quiz import ai_quiz_bp
from src.materials_api import materials_bp
from src.note import note_bp
import os
import redis, json ,time
from datetime import datetime
from flask_mail import Mail, Message
from accessories import mail, redis_client, send_calendar_notification
import threading
import schedule
from src.dashboard import init_calendar_tables
from neo4j.exceptions import ServiceUnavailable


from src.ai_teacher import ai_teacher_bp
# user_guide_api 已整合到 website_guide
from src.web_ai_assistant import web_ai_bp
from src.website_guide import guide_bp
from src.linebot import linebot_bp  # 新增 LINE Bot Blueprint
from src.learning_analytics import analytics_bp
from tool.insert_mongodb import initialize_mis_teach_db # 引入教材資料庫
from tool.init_neo4j_knowledge_graph import init_neo4j_knowledge_graph  # 引入Neo4j知識圖譜初始化
from accessories import init_neo4j  # 引入Neo4j驅動初始化
from tool.insert_test_school import check_and_insert_test_school  # 引入測試學校自動檢查
from src.news_api import news_api_bp  # 引入新聞 API Blueprint
from tool.init_news_table import init_news_table, migrate_news_data  # 引入新聞表初始化與資料遷移
from tool.rename_materials import rename_materials

# 定義 BASE_DIR 為 backend 資料夾的絕對路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Flask app
# 明確禁用 Flask 的默認 static 文件處理，使用自定義路由
app = Flask(__name__, static_folder=None, static_url_path=None)

# Load configuration based on environment
cfg = Config()
productionCfg = ProductionConfig()
developmentCfg = DevelopmentConfig()
app.config.from_object(cfg)
if len(sys.argv) > 1:
    if sys.argv[-1] == 'production':
        app.config.from_object(productionCfg)
    else:
        app.config.from_object(developmentCfg)
else:
    app.config.from_object(developmentCfg)


domain_name_config = app.config.get('DOMAIN_NAME')

# 定義允許的來源（包含所有 ngrok instant endpoints、Cloudflare Tunnel 和 localhost）
def is_allowed_origin(origin):
    """檢查來源是否為允許的域名"""
    if not origin:
        return False
    # 允許 localhost（開發環境）
    if origin.startswith('http://localhost:') or origin.startswith('https://localhost:'):
        return True
    # 允許所有 .ngrok-free.app 和 .ngrok.io 域名（Docker Desktop instant endpoints）
    if origin.endswith('.ngrok-free.app') or origin.endswith('.ngrok.io'):
        return True
    # 允許所有 .trycloudflare.com 域名（Cloudflare Tunnel）
    if origin.endswith('.trycloudflare.com'):
        return True
    # 也允許配置的特定域名
    if origin == app.config.get('DOMAIN_NAME'):
        return True
    return False

# Enable CORS - 手動處理，避免 Flask-CORS 函數參數的兼容性問題
# 使用 after_request 鉤子完全控制 CORS 頭的設置
@app.after_request
def handle_cors(response):
    """手動處理 CORS 頭，只允許通過檢查的來源"""
    origin = request.headers.get('Origin', '')
    
    # 只對通過檢查的來源設置 CORS 頭
    if is_allowed_origin(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE, PATCH'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
    
    # 處理 OPTIONS 預檢請求
    if request.method == 'OPTIONS':
        response.status_code = 200
    
    return response

# 初始化數據庫
sqldb.init_app(app)  # 啟用SQL數據庫
mail.init_app(app)
redis_client.init_app(app)
token_store.init_app(app)
mongo.init_app(app)
login_manager.init_app(app)
login_manager.login_view = '/login'


# Register blueprints
app.register_blueprint(login_bp, url_prefix='/login')
app.register_blueprint(register_bp, url_prefix='/register')
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(quiz_bp, url_prefix='/quiz')
app.register_blueprint(ai_quiz_bp, url_prefix='/ai_quiz')
app.register_blueprint(ai_teacher_bp, url_prefix='/ai_teacher')
app.register_blueprint(web_ai_bp, url_prefix='/web-ai')
app.register_blueprint(guide_bp, url_prefix='/guide')  # 註冊導覽 Blueprint
app.register_blueprint(linebot_bp, url_prefix='/linebot') # 註冊 LINE Bot Blueprint
app.register_blueprint(materials_bp, url_prefix="/materials")
app.register_blueprint(note_bp, url_prefix="/note")  # 註冊筆記 API Blueprint
app.register_blueprint(analytics_bp, url_prefix='/api/learning-analytics')  # 註冊學習分析 API Blueprint
app.register_blueprint(news_api_bp) # 註冊新聞 API Blueprint

# 創建靜態文件服務路由 (用於題目圖片)
@app.route('/static/images/<path:filename>')
def serve_static_image(filename):
    """提供靜態圖片文件服務（題目圖片）"""
    try:
        import os
        import mimetypes
        from flask import send_from_directory
        
        # 圖片文件位於 backend/src/picture 目錄
        # 使用絕對路徑，確保路徑正確
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_dir = os.path.join(base_dir, 'src', 'picture')
        image_path = os.path.join(image_dir, filename)
        
        # 確定 MIME 類型
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            # 根據副檔名設定預設 MIME 類型
            ext = os.path.splitext(filename)[1].lower()
            mime_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml'
            }
            mime_type = mime_map.get(ext, 'image/jpeg')
        
        if os.path.exists(image_path):
            response = send_from_directory(image_dir, filename, mimetype=mime_type)
            # 設置 CORS 頭 - 動態允許 ngrok 域名
            origin = request.headers.get('Origin', '')
            if is_allowed_origin(origin):
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                response.headers['Access-Control-Allow-Origin'] = app.config.get('DOMAIN_NAME', '*')
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
            response.headers['Content-Type'] = mime_type
            return response
        else:
            return jsonify({'error': 'Image not found'}), 404
            
    except Exception as e:
        print(f"靜態圖片服務錯誤: {e}")
        return jsonify({'error': 'Image service error'}), 500

# 創建課程圖片服務路由
@app.route('/static/<path:filename>')
def serve_course_image(filename):
    """提供課程圖片文件服務"""
    try:
        import os
        import mimetypes
        from flask import send_from_directory, Response
        
        # 課程圖片文件位於 backend/data/courses_picture 目錄
        # 使用絕對路徑，確保路徑正確
        base_dir = os.path.dirname(os.path.abspath(__file__))
        course_image_dir = os.path.join(base_dir, 'data', 'courses_picture')
        image_path = os.path.join(course_image_dir, filename)
        
        # 確定 MIME 類型
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            # 根據副檔名設定預設 MIME 類型
            ext = os.path.splitext(filename)[1].lower()
            mime_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml'
            }
            mime_type = mime_map.get(ext, 'image/jpeg')
        
        if os.path.exists(image_path):
            response = send_from_directory(course_image_dir, filename, mimetype=mime_type)
            # 設置 CORS 頭 - 動態允許 ngrok 域名
            origin = request.headers.get('Origin', '')
            if is_allowed_origin(origin):
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                response.headers['Access-Control-Allow-Origin'] = app.config.get('DOMAIN_NAME', '*')
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
            response.headers['Content-Type'] = mime_type
            return response
        else:
            # 如果課程圖片不存在，嘗試從題目圖片目錄查找
            base_dir = os.path.dirname(os.path.abspath(__file__))
            question_image_dir = os.path.join(base_dir, 'src', 'picture')
            question_image_path = os.path.join(question_image_dir, filename)
            if os.path.exists(question_image_path):
                response = send_from_directory(question_image_dir, filename, mimetype=mime_type)
                origin = request.headers.get('Origin', '')
                if is_allowed_origin(origin):
                    response.headers['Access-Control-Allow-Origin'] = origin
                else:
                    response.headers['Access-Control-Allow-Origin'] = app.config.get('DOMAIN_NAME', '*')
                response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
                response.headers['Content-Type'] = mime_type
                return response
            return jsonify({'error': 'Image not found', 'filename': filename}), 404
            
    except Exception as e:
        print(f"❌ 課程圖片服務錯誤: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Image service error', 'message': str(e)}), 500

def check_calendar_notifications():
    """檢查 Redis 中的行事曆通知並發送郵件"""
    try:
        # 獲取當前時間
        current_time = datetime.now()
        current_time_str = current_time.strftime('%Y-%m-%d %H:%M')
        
        # 從 Redis List 獲取所有通知
        notifications = redis_client.lrange('event_notification', 0, -1)
        notifications_to_send = []
        
        for notification_data in notifications:
            try:
                notification = json.loads(notification_data)
                notify_time_str = notification.get('notify_time')
                
                if notify_time_str:
                    # 檢查是否到了通知時間（允許 5 分鐘誤差）
                    notify_time = datetime.strptime(notify_time_str, '%Y-%m-%d %H:%M')
                    time_diff = abs((notify_time - current_time).total_seconds())
                    
                    if time_diff <= 300:  # 5 分鐘內
                        notifications_to_send.append({
                            'notification_data': notification_data,
                            'event_id': notification.get('event_id'),
                            'notification': notification
                        })
            except Exception as e:
                print(f"處理通知時發生錯誤: {e}")
                continue
        
        # 發送通知
        for item in notifications_to_send:
            try:
                notification = item['notification']
                student_email = notification.get('student_email')
                user_id = notification.get('user_id')
                event_title = notification.get('event_title') or notification.get('title')
                event_content = notification.get('event_content') or notification.get('content', '')
                event_date = notification.get('event_date', '')
                
                if student_email and event_title:
                    # 發送郵件通知
                    mail_success = False
                    with app.app_context():
                        mail_success = send_calendar_notification(
                            student_email=student_email,
                            event_title=event_title,
                            event_content=event_content,
                            event_date=event_date
                        )
                    
                    # 發送 LINE Bot 通知
                    line_success = False
                    if user_id:
                        line_success = send_line_calendar_notification(
                            user_id=user_id,
                            event_title=event_title,
                            event_content=event_content,
                            event_date=event_date
                        )
                    
                    if mail_success or line_success:
                        # 發送成功後從 Redis List 移除
                        redis_client.lrem('event_notification', 1, item['notification_data'])
                        print(f"✅ 通知已發送並從 Redis List 移除: event_id {item['event_id']}")
                    else:
                        print(f"❌ 通知發送失敗: event_id {item['event_id']}")
                            
            except Exception as e:
                print(f"發送通知時發生錯誤: {e}")
                continue
                
    except Exception as e:
        print(f"檢查行事曆通知時發生錯誤: {e}")

def send_line_calendar_notification(user_id: str, event_title: str, event_content: str, event_date: str) -> bool:
    """發送 LINE Bot 行事曆通知"""
    try:
        from src.linebot import line_bot_api, PushMessageRequest, TextMessage
        
        # 格式化事件日期
        try:
            event_datetime = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            formatted_date = event_datetime.strftime('%Y年%m月%d日 %H:%M')
        except:
            formatted_date = event_date
        
        # 創建通知訊息
        notification_text = f"""🔔 行事曆提醒

📅 事件：{event_title}
⏰ 時間：{formatted_date}
{f'📝 內容：{event_content}' if event_content else ''}
"""
        
        # 發送 LINE 訊息
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=notification_text)]
            )
        )
        
        print(f"✅ LINE 行事曆通知已發送給用戶 {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ 發送 LINE 行事曆通知失敗: {e}")
        return False

def run_scheduler():
    """運行背景排程器"""
    schedule.every(1).minutes.do(check_calendar_notifications)
    while True:
        schedule.run_pending()
        time.sleep(60) 

# 初始化數據庫表格
with app.app_context():
    sqldb.create_all()
    init_quiz_tables() 
    init_calendar_tables()
    init_news_table()  # 初始化新聞表
    migrate_news_data()  # 自動遷移 ithome_news.json 到資料庫（若尚未導入）
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    # 初始化MongoDB數據
    init_mongo_data()
    initialize_mis_teach_db()
    rename_materials()
    # 自動檢查並插入測試學校資料
    check_and_insert_test_school()
    
    # 初始化Neo4j（如果服務未運行則跳過）
    try:
        init_neo4j()  # 初始化Neo4j驅動
        init_neo4j_knowledge_graph()
        print("✓ Neo4j 知識圖譜初始化成功")
    except ServiceUnavailable as e:
        print("⚠ 警告: Neo4j 服務未運行，跳過知識圖譜初始化")
        print(f"  詳細資訊: {str(e)}")
    except Exception as e:
        print(f"⚠ 警告: Neo4j 初始化時發生錯誤，跳過知識圖譜初始化")
        print(f"  詳細資訊: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
