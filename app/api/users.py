from flask import request, jsonify
from flask_login import login_required, current_user
from app import db
from app.api import bp
from app.models.user import User
from app.api.schemas import UserSchema

user_schema = UserSchema()
users_schema = UserSchema(many=True)

@bp.route('/users', methods=['GET'])
@login_required
def get_users():
    """Get all users (for assignment dropdowns, etc.)"""
    users = User.query.all()
    return jsonify(users_schema.dump(users))

@bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Get a specific user"""
    user = User.query.get_or_404(user_id)
    return jsonify(user_schema.dump(user))

@bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update user profile (only own profile or admin)"""
    user = User.query.get_or_404(user_id)
    
    # Users can only update their own profile unless they're admin
    if user.id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    # Update allowed fields
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'email' in data:
        user.email = data['email']
    
    db.session.commit()
    
    return jsonify(user_schema.dump(user))