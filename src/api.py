from flask import request,url_for, Blueprint, jsonify, current_app, send_from_directory, abort
import jwt
from accessories import mongo
from datetime import datetime, timedelta
from functools import wraps
import os



def verify_token(token):
    decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
    exp = decoded_token['exp']
    exp = datetime.strptime(exp, "%Y%m%d%H%M%S")
    if datetime.now()<exp:
        return True
    return False

def get_user_info(token, key):
    decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
    user = mongo.db.students.find_one({"email": decoded_token['user']})
    return user[key]
