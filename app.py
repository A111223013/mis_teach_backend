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
import os
import redis, json ,time
from datetime import datetime
from flask_mail import Mail, Message
from accessories import mail, redis_client, send_calendar_notification
import threading
import schedule

# Temporarily removed langchain imports until dependencies are installed
# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
# from langchain_community.vectorstores import FAISS
# from langchain.text_splitter import CharacterTextSplitter
# from langchain.chains import RetrievalQA
# from langchain.schema.document import Document

from src.ai_teacher import ai_teacher_bp
from src.user_guide_api import user_guide_bp
from src.web_ai_assistant import web_ai_bp
from src.linebot import linebot_bp  # 新增 LINE Bot Blueprint
from src.learning_analytics import analytics_bp  # 從統一模組導入學習分析 API Blueprint
from src.unified_learning_analytics import learning_analytics_bp  # 統一學習分析 API Blueprint
from tool.insert_mongodb import initialize_mis_teach_db # 引入教材資料庫


# 定義 BASE_DIR 為 backend 資料夾的絕對路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Flask app
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "data", "courses_picture"),
    static_url_path="/static"
)

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

# Enable CORS
CORS(app, resources={r"/*": {"origins": app.config['DOMAIN_NAME']}},
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"], supports_credentials=True)

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
app.register_blueprint(user_guide_bp, url_prefix='/user-guide')
app.register_blueprint(web_ai_bp, url_prefix='/web-ai')
app.register_blueprint(linebot_bp, url_prefix='/linebot') # 註冊 LINE Bot Blueprint
app.register_blueprint(materials_bp, url_prefix="/materials")
app.register_blueprint(analytics_bp, url_prefix="/analytics")  # 註冊學習分析 API Blueprint
app.register_blueprint(learning_analytics_bp, url_prefix="/personalized_learning")  # 註冊統一學習分析 API Blueprint

# 創建靜態文件服務路由 (用於圖片)
@app.route('/static/images/<path:filename>')
def serve_static_image(filename):
    """提供靜態圖片文件服務"""
    try:
        import os
        from flask import send_from_directory
        
        # 圖片文件位於 backend/src/picture 目錄
        image_dir = os.path.join(os.path.dirname(__file__), 'src', 'picture')
        
        if os.path.exists(os.path.join(image_dir, filename)):
            return send_from_directory(image_dir, filename)
        else:
            return jsonify({'error': 'Image not found'}), 404
            
    except Exception as e:
        print(f"靜態圖片服務錯誤: {e}")
        return jsonify({'error': 'Image service error'}), 500

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
                event_title = notification.get('title')
                event_content = notification.get('content', '')
                event_date = notification.get('event_date', '')
                
                if student_email and event_title:
                    # 在應用程式上下文中發送郵件
                    with app.app_context():
                        success = send_calendar_notification(
                            student_email=student_email,
                            event_title=event_title,
                            event_content=event_content,
                            event_date=event_date
                        )
                    
                    if success:
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

def run_scheduler():
    """運行背景排程器"""
    # 每分鐘檢查一次通知
    schedule.every(1).minutes.do(check_calendar_notifications)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次

# 初始化數據庫表格
with app.app_context():
    sqldb.create_all()
    # 移除自動初始化，改為按需初始化
    init_quiz_tables()  # 初始化測驗相關表格
    from src.dashboard import init_calendar_tables
    init_calendar_tables()  # 初始化行事曆表格

    # 啟動背景排程器
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✅ 行事曆通知排程器已啟動")
init_mongo_data()
initialize_mis_teach_db()

if __name__ == '__main__':
    app.run(debug=True)
