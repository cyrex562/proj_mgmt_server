from datetime import datetime, date
from app import db

class Task(db.Model):
    """Base task model for all project items"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_number = db.Column(db.Integer, nullable=False)  # Sequential number within project (e.g., 1, 2, 3...)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='backlog', index=True)  # backlog, todo, doing, done, cancelled
    priority = db.Column(db.String(16), default='medium')  # low, medium, high, critical
    task_type = db.Column(db.String(32), default='task')  # task, story, bug, epic, milestone
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    
    # Estimates and progress
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0.0)
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))  # For sub-tasks
    epic_id = db.Column(db.Integer, db.ForeignKey('epics.id'))
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'))
    
    # Relationships
    attachments = db.relationship('FileAttachment', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Task {self.title}>'
    
    @property
    def task_key(self):
        """Generate full task key (e.g., PROJ-001-001)"""
        if self.project and self.project.key and self.task_number:
            return f"{self.project.key}-{self.task_number:03d}"
        return f"TASK-{self.id}"
    
    @property
    def is_completed(self):
        """Check if task is completed"""
        return self.status == 'done'
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        return self.due_date and self.due_date < date.today() and not self.is_completed
    
    def update_progress(self):
        """Update progress based on status"""
        status_progress = {
            'backlog': 0,
            'todo': 25,
            'doing': 50,
            'done': 100,
            'cancelled': 0
        }
        self.progress_percentage = status_progress.get(self.status, 0)

class SubTask(db.Model):
    """Sub-task model"""
    __tablename__ = 'subtasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='backlog', index=True)
    priority = db.Column(db.String(16), default='medium')
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    
    # Estimates and progress
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0.0)
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Foreign keys
    parent_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    parent_task = db.relationship('Task', backref=db.backref('subtasks', lazy='dynamic'), foreign_keys=[parent_task_id])
    assignee = db.relationship('User', backref=db.backref('assigned_subtasks', lazy='dynamic'))
    
    def __repr__(self):
        return f'<SubTask {self.title}>'
    
    @property
    def is_completed(self):
        """Check if sub-task is completed"""
        return self.status == 'done'
    
    @property
    def is_overdue(self):
        """Check if sub-task is overdue"""
        return self.due_date and self.due_date < date.today() and not self.is_completed

class Epic(db.Model):
    """Epic model for grouping related stories and tasks"""
    __tablename__ = 'epics'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='backlog', index=True)
    priority = db.Column(db.String(16), default='medium')
    epic_key = db.Column(db.String(32), unique=True, index=True)  # e.g., "EPIC-001"
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    
    # Estimates and progress
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0.0)
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    assignee = db.relationship('User', backref=db.backref('assigned_epics', lazy='dynamic'))
    stories = db.relationship('Story', lazy='dynamic')
    tasks = db.relationship('Task', lazy='dynamic')
    
    def __repr__(self):
        return f'<Epic {self.epic_key}: {self.title}>'
    
    @property
    def is_completed(self):
        """Check if epic is completed"""
        return self.status == 'done'
    
    @property
    def is_overdue(self):
        """Check if epic is overdue"""
        return self.due_date and self.due_date < date.today() and not self.is_completed

class Story(db.Model):
    """User story model"""
    __tablename__ = 'stories'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='backlog', index=True)
    priority = db.Column(db.String(16), default='medium')
    story_key = db.Column(db.String(32), unique=True, index=True)  # e.g., "STORY-001"
    acceptance_criteria = db.Column(db.Text)
    story_points = db.Column(db.Integer)  # Agile story points estimation
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    
    # Estimates and progress
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0.0)
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    epic_id = db.Column(db.Integer, db.ForeignKey('epics.id'))
    
    # Relationships
    assignee = db.relationship('User', backref=db.backref('assigned_stories', lazy='dynamic'))
    epic = db.relationship('Epic', overlaps="stories")
    
    def __repr__(self):
        return f'<Story {self.story_key}: {self.title}>'
    
    @property
    def is_completed(self):
        """Check if story is completed"""
        return self.status == 'done'
    
    @property
    def is_overdue(self):
        """Check if story is overdue"""
        return self.due_date and self.due_date < date.today() and not self.is_completed

class Bug(db.Model):
    """Bug/issue model"""
    __tablename__ = 'bugs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='backlog', index=True)
    priority = db.Column(db.String(16), default='medium')
    bug_key = db.Column(db.String(32), unique=True, index=True)  # e.g., "BUG-001"
    severity = db.Column(db.String(16), default='medium')  # low, medium, high, critical
    environment = db.Column(db.String(64))  # e.g., "production", "staging", "development"
    steps_to_reproduce = db.Column(db.Text)
    expected_behavior = db.Column(db.Text)
    actual_behavior = db.Column(db.Text)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    
    # Estimates and progress
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0.0)
    progress_percentage = db.Column(db.Integer, default=0)
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    assignee = db.relationship('User', backref=db.backref('assigned_bugs', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Bug {self.bug_key}: {self.title}>'
    
    @property
    def is_completed(self):
        """Check if bug is completed"""
        return self.status == 'done'
    
    @property
    def is_overdue(self):
        """Check if bug is overdue"""
        return self.due_date and self.due_date < date.today() and not self.is_completed

class Milestone(db.Model):
    """Milestone model for project phases"""
    __tablename__ = 'milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='planned')  # planned, in_progress, completed, cancelled
    target_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # Relationships
    tasks = db.relationship('Task', backref='milestone', lazy='dynamic')
    
    def __repr__(self):
        return f'<Milestone {self.name}>'
    
    @property
    def is_completed(self):
        """Check if milestone is completed"""
        return self.status == 'completed'
    
    @property
    def is_overdue(self):
        """Check if milestone is overdue"""
        return self.target_date and self.target_date < date.today() and not self.is_completed
    
    @property
    def task_count(self):
        """Get total number of tasks assigned to this milestone"""
        return self.tasks.count()
    
    @property
    def completed_task_count(self):
        """Get number of completed tasks assigned to this milestone"""
        return self.tasks.filter_by(status='done').count()
    
    def update_status(self):
        """Update milestone status based on associated tasks"""
        if self.tasks.count() == 0:
            return
        
        completed_tasks = self.tasks.filter_by(status='done').count()
        total_tasks = self.tasks.count()
        
        if completed_tasks == total_tasks:
            self.status = 'completed'
            self.completed_date = date.today()
        elif completed_tasks > 0:
            self.status = 'in_progress'
        else:
            self.status = 'planned'