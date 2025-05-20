from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
from accessories import sqldb, mail, redis_client, token_store, mongo, login_manager
from config import Config, ProductionConfig, DevelopmentConfig
from src.login import login_bp
from src.register import register_bp
from src.dashboard import dashboard_bp
import os

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.schema.document import Document
from src.ai_agent import ai_agent_bp, init_embeddings_from_txt


app = Flask(__name__)

cfg = Config()
productionCfg = ProductionConfig()
developmentCfg = DevelopmentConfig()
app.config.from_object(cfg)
app.config.from_object(developmentCfg)

os.environ["GOOGLE_API_KEY"] = "AIzaSyAIXgxvFlTQe3lq4tuLx2fUiF4oaigBBYE"
init_embeddings_from_txt("ba.txt")  # 初始化 retriever

domain_name_config = app.config.get('DOMAIN_NAME')

CORS(
    app,
    supports_credentials=True,
    origins=domain_name_config,
    methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"]
)

#sqldb.init_app(app)
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
app.register_blueprint(ai_agent_bp, url_prefix='/ai_agent')

#with app.app_context():
#    sqldb.create_all()

if __name__ == '__main__':
    app.run(debug=True)
