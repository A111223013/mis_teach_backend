class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_recycle': 3600,
            'pool_size': 5,
            'max_overflow': 10
        }
    MONGO_URI = "mongodb://localhost:27017/MIS_Teach"
    SECRET_KEY = open('./security_key','r').read()
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
    
