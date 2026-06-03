from flask import Blueprint, request, jsonify
from app.models import User, AuditLog
from app import db
import jwt
import datetime
from functools import wraps
from flask import current_app

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) > 1:
                token = parts[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['id'])
            if not current_user:
                return jsonify({'message': 'Token is invalid (User not found)!'}), 401
            if current_user.status != 'Active':
                return jsonify({'message': 'Account is deactivated!'}), 403
        except Exception as e:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(current_user, *args, **kwargs):
            user_role = current_user.role
            allowed_roles = list(roles)
            if 'Procurement Officer' in allowed_roles and 'Procurement Staff' not in allowed_roles:
                allowed_roles.append('Procurement Staff')
            if 'Procurement Staff' in allowed_roles and 'Procurement Officer' not in allowed_roles:
                allowed_roles.append('Procurement Officer')
                
            if user_role not in allowed_roles and user_role != 'Admin':
                return jsonify({'message': 'Insufficient permissions!'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password!'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.verify_password(data['password']):
        return jsonify({'message': 'Invalid credentials!'}), 401
    
    if user.status != 'Active':
        return jsonify({'message': 'Account is deactivated. Contact administrator.'}), 403
    
    token = jwt.encode({
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")
    
    # Update activity and Audit Log
    user.last_login = datetime.datetime.utcnow()
    log = AuditLog(user_id=user.id, action="Logged in", target_table="users", target_id=user.id)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    })

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify(current_user.to_dict())
