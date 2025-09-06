from flask import request,url_for, Blueprint, jsonify, current_app, send_from_directory, abort
import jwt
from accessories import mongo
from datetime import datetime, timedelta
from functools import wraps
import os
import time

def verify_token(token):
    """验证JWT token并返回用户信息"""
    try:
        decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        # 檢查token是否過期 - 現在使用Unix時間戳
        exp = decoded_token.get('exp')
        if exp and time.time() < exp:
            # 檢查 token 類型，只接受 access token
            token_type = decoded_token.get('type', 'access')  # 預設為 access 以向後兼容
            if token_type == 'access':
                # 返回用户邮箱
                user_email = decoded_token.get('user')
                if user_email:
                    return user_email
                else:
                    return None
            else:
                print(f"❌ 無效的 token 類型: {token_type}")
                return None
        return None
    except jwt.ExpiredSignatureError:
        print("❌ Token已過期")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ Token無效: {e}")
        return None

def get_user_info(token, key):

    decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])

    # 檢查 token 類型，只接受 access token
    token_type = decoded_token.get('type', 'access')  # 預設為 access 以向後兼容
    if token_type != 'access':
        print(f"❌ 無效的 token 類型: {token_type}")
        raise ValueError("Invalid token type")
    
    user = mongo.db.students.find_one({"email": decoded_token['user']})
    if not user:
        print(f"❌ 找不到用戶: {decoded_token['user']}")
        raise ValueError("User not found")

    return user[key]

