from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

class Permission(db.Model):
    """Permissions that can be assigned to groups"""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship with groups
    groups = db.relationship('Group', secondary='group_permissions', back_populates='permissions')
    
    def __repr__(self):
        return f'<Permission {self.name}>'

class Group(db.Model):
    """User groups for role-based access control"""
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Many-to-many relationships
    users = db.relationship('User', secondary='user_groups', back_populates='groups')
    permissions = db.relationship('Permission', secondary='group_permissions', back_populates='groups')
    
    def __repr__(self):
        return f'<Group {self.name}>'
    
    def has_permission(self, permission_name):
        """Check if group has a specific permission"""
        return any(perm.name == permission_name for perm in self.permissions)

class UserGroup(db.Model):
    """Association table for users and groups"""
    __tablename__ = 'user_groups'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupPermission(db.Model):
    """Association table for groups and permissions"""
    __tablename__ = 'group_permissions'
    
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    """User model with authentication and profile information"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    avatar_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    groups = db.relationship('Group', secondary='user_groups', back_populates='users')
    created_projects = db.relationship('Project', backref='creator', lazy='dynamic')
    # assigned_work_items relationship is defined in WorkItem model via backref
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission through their groups"""
        if self.is_admin:
            return True
        return any(group.has_permission(permission_name) for group in self.groups)
    
    def has_group(self, group_name):
        """Check if user belongs to a specific group"""
        return any(group.name == group_name for group in self.groups)
    
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))