from flask import Blueprint, request, jsonify
from app.models import User, AuditLog
from app import db
from .auth import roles_required, token_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@roles_required('Admin')
def get_users(current_user):
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@admin_bp.route('/users', methods=['POST'])
@roles_required('Admin')
def create_user(current_user):
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email') or not data.get('role'):
        return jsonify({'message': 'Missing required fields!'}), 400
        
    if User.query.filter((User.username == data['username']) | (User.email == data['email'])).first():
        return jsonify({'message': 'Username or email already exists!'}), 400
        
    user = User(
        username=data['username'],
        email=data['email'],
        role=data['role'],
        password=data['password'],
        status='Active'
    )
    db.session.add(user)
    db.session.commit()
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action=f"Provisioned user {user.username}",
        target_table="users",
        target_id=user.id,
        new_value=str(user.to_dict())
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify(user.to_dict()), 201

@admin_bp.route('/users/<int:user_id>', methods=['PATCH'])
@roles_required('Admin')
def update_user(current_user, user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    old_value = str(user.to_dict())
    
    if 'status' in data:
        user.status = data['status']
    if 'role' in data:
        user.role = data['role']
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'password' in data and data['password']:
        user.password = data['password']
        
    db.session.commit()
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id, 
        action=f"Updated User {user.username}", 
        target_table="users", 
        target_id=user.id,
        old_value=old_value,
        new_value=str(user.to_dict())
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify(user.to_dict())
