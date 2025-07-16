from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
from accessories import sqldb, mail, redis_client, token_store, mongo, login_manager, init_mongo_data
from config import Config, ProductionConfig, DevelopmentConfig
from src.login import login_bp
from src.register import register_bp
from src.dashboard import dashboard_bp
from src.quiz import quiz_bp, init_quiz_tables
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

app = Flask(__name__)

cfg = Config()
productionCfg = ProductionConfig()
developmentCfg = DevelopmentConfig()
app.config.from_object(cfg)
app.config.from_object(developmentCfg)

# Set Google API key if needed
os.environ["GOOGLE_API_KEY"] = "AIzaSyAIXgxvFlTQe3lq4tuLx2fUiF4oaigBBYE"

domain_name_config = app.config.get('DOMAIN_NAME')

# 修復CORS配置，允許多個域名
CORS(
    app,
    supports_credentials=True,
    origins=[
        domain_name_config,
        "http://localhost:4200", 
        "http://127.0.0.1:4200",
        "http://127.0.0.1:5000",
        "http://localhost:5000"
    ],
    methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"]
)

# 初始化數據庫
# sqldb.init_app(app)  # 暫時註釋掉SQL數據庫
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
app.register_blueprint(ai_teacher_bp, url_prefix='/ai_teacher')
app.register_blueprint(user_guide_bp, url_prefix='/user-guide')
app.register_blueprint(web_ai_bp, url_prefix='/web-ai')

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
# with app.app_context():
#     sqldb.create_all()
#     init_quiz_tables()  # 初始化測驗相關表格

if __name__ == '__main__':
    print("🚀 Starting Flask application...")
    print("✅ JWT token format fixed")
    print("⚠️  Langchain dependencies temporarily disabled")
    print("⚠️  SQL database temporarily disabled") 
    print("📸 Static image service enabled at /static/images/")
    app.run(debug=True)
