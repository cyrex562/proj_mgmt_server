import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from app import db

class Project(db.Model):
    """Project model for organizing work items and team collaboration"""
    __tablename__ = 'projects'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = db.Column(db.String(10), unique=True, nullable=False, index=True)  # 2-10 chars, UPPERCASE
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='active', index=True)  # active, completed, archived, on_hold
    priority = db.Column(db.String(16), default='medium')  # low, medium, high, critical
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Foreign keys
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    members = db.relationship('ProjectMember', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
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
    
    def get_next_key_id(self):
        """Get the next sequential key ID for this project"""
        # Use the project counter system
        counter = ProjectCounter.query.filter_by(project_id=self.id).first()
        if not counter:
            counter = ProjectCounter(project_id=self.id, next=1)
            db.session.add(counter)
            db.session.flush()
        
        # Get the next number and increment
        next_id = counter.next
        counter.next += 1
        db.session.commit()
        
        return next_id
    
    def generate_work_item_key(self):
        """Generate a work item key for this project"""
        key_id = self.get_next_key_id()
        return f"{self.key}-{key_id}"
    
    @staticmethod
    def generate_project_key(name):
        """Generate a unique project key from the project name"""
        # Extract first 3-4 characters from name and convert to uppercase
        base_key = ''.join(c.upper() for c in name if c.isalnum())[:4]
        
        # Ensure minimum length
        if len(base_key) < 2:
            base_key = 'PROJ'
        
        # Check for uniqueness and add number if needed
        counter = 1
        project_key = base_key
        while Project.query.filter_by(key=project_key).first():
            project_key = f"{base_key}{counter}"
            counter += 1
        
        return project_key


class ProjectCounter(db.Model):
    """Project counter for generating sequential key IDs"""
    __tablename__ = 'project_counters'
    
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), primary_key=True)
    next = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationships
    project = db.relationship('Project', backref='counter')
    
    def __repr__(self):
        return f'<ProjectCounter {self.project_id}: {self.next}>'


class ProjectMember(db.Model):
    """Project membership model"""
    __tablename__ = 'project_members'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(32), default='member')  # viewer, member, admin, owner
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='project_memberships')
    
    def __repr__(self):
        return f'<ProjectMember {self.user.username} in {self.project.name}>'