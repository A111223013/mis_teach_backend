from flask import request,url_for, Blueprint, jsonify, current_app, send_from_directory, abort
import jwt
from accessories import mongo
from datetime import datetime, timedelta
from functools import wraps
import os
import time

def verify_token(token):
    try:
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        # 檢查token是否過期 - 現在使用Unix時間戳
        exp = decoded_token.get('exp')
        if exp and time.time() < exp:
            return True
        return False
    except jwt.ExpiredSignatureError:
        print("❌ Token已過期")
        return False
    except jwt.InvalidTokenError as e:
        print(f"❌ Token無效: {e}")
        return False

def get_user_info(token, key):
    # 檢查token是否為空或None
    if not token or token == 'null' or token.strip() == '':
        raise ValueError("Token is empty or null")
    
    try:
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        user = mongo.db.students.find_one({"email": decoded_token['user']})
        if not user:
            raise ValueError("User not found")
        return user[key]
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

