from datetime import datetime
from app import db

class Project(db.Model):
    """Project model for organizing tasks and team collaboration"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    key = db.Column(db.String(16), unique=True, nullable=False, index=True)  # e.g., "PROJ-001"
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='active', index=True)  # active, completed, archived, on_hold
    priority = db.Column(db.String(16), default='medium')  # low, medium, high, critical
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    members = db.relationship('ProjectMember', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    milestones = db.relationship('Milestone', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    epics = db.relationship('Epic', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    stories = db.relationship('Story', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    bugs = db.relationship('Bug', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def is_member(self, user):
        """Check if user is a member of this project"""
        return self.members.filter_by(user_id=user.id).first() is not None
    
    def get_member_role(self, user):
        """Get user's role in this project"""
        member = self.members.filter_by(user_id=user.id).first()
        return member.role if member else None
    
    def can_user_access(self, user, required_role=None):
        """Check if user can access this project with optional role requirement"""
        if not self.is_member(user):
            return False
        
        if required_role is None:
            return True
        
        user_role = self.get_member_role(user)
        role_hierarchy = {'viewer': 1, 'member': 2, 'admin': 3, 'owner': 4}
        
        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)
    
    def get_next_task_number(self):
        """Get the next sequential task number for this project"""
        from app.models.task import Task
        max_task_number = db.session.query(db.func.max(Task.task_number)).filter_by(project_id=self.id).scalar()
        return (max_task_number or 0) + 1
    
    @staticmethod
    def generate_project_key(name):
        """Generate a unique project key from the project name"""
        # Extract first 3-4 characters from name and convert to uppercase
        base_key = ''.join(c.upper() for c in name if c.isalnum())[:4]
        if len(base_key) < 3:
            base_key = base_key.ljust(3, 'X')
        
        # Find the next available number
        counter = 1
        while True:
            key = f"{base_key}-{counter:03d}"
            existing = Project.query.filter_by(key=key).first()
            if not existing:
                return key
            counter += 1

class ProjectMember(db.Model):
    """Association table for project members with roles"""
    __tablename__ = 'project_members'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='member')  # owner, admin, member, viewer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='project_memberships')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_project_member'),)
    
    def __repr__(self):
        return f'<ProjectMember {self.user.username} in {self.project.name} as {self.role}>'