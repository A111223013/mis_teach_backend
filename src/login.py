from flask import request, jsonify, Blueprint, current_app
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import jwt
from accessories import mongo, get_user_info
from flask_login import logout_user
login_bp = Blueprint('login', __name__)

@login_bp.route('/login_user', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 204
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user_data = mongo.db.students.find_one({"email": email})
    if user_data and check_password_hash(user_data['password'], password):
        token = jwt.encode({'user': user_data['email'], 'exp': datetime.strftime(datetime.now() + timedelta(hours=3), format="%Y%m%d%H%M%S")}, current_app.config['SECRET_KEY'])
        return jsonify({'token': token}), 200
    else:
        return jsonify({'message': '用戶名或密碼不正確'}), 401



@login_bp.route('/logout',  methods=['OPTIONS','POST'])
def logout():
    logout_user()
    return jsonify({'message': 'success logged out'}), 200


