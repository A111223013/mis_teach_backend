from flask import Flask, jsonify, request, Blueprint, send_from_directory
from flask_cors import CORS
import sys
from accessories import sqldb, mail, redis_client, token_store, mongo, login_manager, init_mongo_data
from config import Config, ProductionConfig, DevelopmentConfig
from src.login import login_bp
from src.register import register_bp
from src.dashboard import dashboard_bp
from src.quiz import quiz_bp, init_quiz_tables
from src.ai_quiz import ai_quiz_bp
from src.materials_api import materials_bp
import os

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

# Initialize Flask app
app = Flask(__name__)

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
init_mongo_data()

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

# 初始化數據庫表格
with app.app_context():
    sqldb.create_all()
    # 移除自動初始化，改為按需初始化
    init_quiz_tables()  # 初始化測驗相關表格

if __name__ == '__main__':
    app.run(debug=True)
