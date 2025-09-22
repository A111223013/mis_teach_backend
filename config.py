import os

class Config:
    # 基本配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 3600,
        'pool_size': 5,
        'max_overflow': 10
    }
    
    # 安全配置
    def _get_security_key(self):
        """獲取安全密鑰，自動處理路徑問題"""
        import os
        # 獲取當前文件所在目錄
        current_dir = os.path.dirname(os.path.abspath(__file__))
        security_key_path = os.path.join(current_dir, 'security_key')
        
        with open(security_key_path, 'r') as f:
            return f.read().strip()
    
    @property
    def SECRET_KEY(self):
        return self._get_security_key()
    
    @property 
    def SECURITY_PASSWORD_SALT(self):
        return self._get_security_key()
    
    # 郵件配置
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'misteacher011@gmail.com'
    MAIL_PASSWORD = 'fumk aeyn fwsf odto'
    MAIL_DEFAULT_SENDER = 'misteacher011@gmail.com'
    
    # 資料庫配置
    # MongoDB
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/MIS_Teach')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'MIS_Teach')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Neo4j
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '123456789')
    
    # JWT 配置
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1小時
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30天
    
    ROUTE_ROLE_MAPPING = {
       
    }

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/mis_teach'
    SQLALCHEMY_BINDS = {}
    
    API_BASE_URL = 'http://localhost:5000'
    DOMAIN_NAME = 'http://localhost:4200'
    DEBUG = True

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/mis_teach'
    SQLALCHEMY_BINDS = {}
    
    API_BASE_URL = 'http://localhost:5000'
    DOMAIN_NAME = 'http://localhost:4200'
    DEBUG = True
    
