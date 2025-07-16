class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_recycle': 3600,
            'pool_size': 5,
            'max_overflow': 10
        }
    MONGO_URI = "mongodb://localhost:27017/MIS_Teach"
    # 添加錯誤處理以防security_key文件不存在
    try:
        with open('./security_key', 'r') as f:
            SECRET_KEY = f.read().strip()
    except FileNotFoundError:
        # 如果security_key文件不存在，使用默認密鑰
        print("⚠️ security_key文件不存在，使用默認密鑰")
        SECRET_KEY = 'default-secret-key-for-development-only'
    except Exception as e:
        print(f"⚠️ 讀取security_key失敗: {e}")
        SECRET_KEY = 'default-secret-key-for-development-only'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'misteacher011@gmail.com'
    MAIL_PASSWORD = 'fumk aeyn fwsf odto'
    REDIS_URL = 'redis://localhost:6379/0'
    MAIL_DEFAULT_SENDER = 'misteacher011@gmail.com'
    SECURITY_PASSWORD_SALT = open('./security_key','r').read()
    
    
    ROUTE_ROLE_MAPPING = {
       
    }

  
 
class DevelopmentConfig(Config):
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/MIS_Teach'
    #SQLALCHEMY_BINDS = {}
    
    
    API_BASE_URL = 'http://localhost:5000'
    DOMAIN_NAME = 'http://localhost:4200'
    DEBUG = True
    

class ProductionConfig(Config):
    API_BASE_URL = 'http://localhost:5000'
    DOMAIN_NAME = 'http://localhost:4200'
    DEBUG = True
    
