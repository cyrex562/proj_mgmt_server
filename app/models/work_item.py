import uuid
from datetime import datetime, date
from enum import Enum
from sqlalchemy import text, Index
from sqlalchemy.dialects.postgresql import UUID, ENUM
from app import db

class WorkItemType(Enum):
    TASK = 'task'
    EPIC = 'epic'
    FEATURE = 'feature'
    STORY = 'story'
    BUG = 'bug'

class WorkItemStatus(Enum):
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    BLOCKED = 'blocked'
    READY = 'ready'
    DONE = 'done'
    CANCELLED = 'cancelled'

class WorkItemPriority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'

class StoryKind(Enum):
    USER = 'user'
    ENGINEERING = 'engineering'
    TESTING = 'testing'

class WorkItem(db.Model):
    """Unified work item model for tasks, epics, features, stories, and bugs"""
    __tablename__ = 'work_items'
    
    # Primary key
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Project relationship
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False, index=True)
    
    # Key generation
    key_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Type and basic info
    type = db.Column(ENUM(WorkItemType), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Status and priority
    status = db.Column(ENUM(WorkItemStatus), default=WorkItemStatus.NOT_STARTED, index=True)
    priority = db.Column(ENUM(WorkItemPriority), default=WorkItemPriority.MEDIUM)
    
    # Parent-child relationship (only for tasks)
    parent_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=True, index=True)
    
    # User assignments
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    due_at = db.Column(db.Date, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Story-specific fields
    story_kind = db.Column(ENUM(StoryKind), nullable=True)
    
    # Git integration
    repo_url = db.Column(db.String(500), nullable=True)
    branch = db.Column(db.String(255), nullable=True)
    commit_hash = db.Column(db.String(40), nullable=True)
    
    # Progress
    progress_pct = db.Column(db.Float, nullable=True, default=0.0)
    rollup_mode = db.Column(db.Boolean, default=False, nullable=False)
    
    # Full-text search (for future use)
    tsv = db.Column(db.Text, nullable=True)
    
    # Relationships
    project = db.relationship('Project', backref='work_items')
    parent = db.relationship('WorkItem', remote_side=[id], backref='children')
    assignee = db.relationship('User', foreign_keys=[assignee_id], backref='assigned_work_items')
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='reported_work_items')
    
    # Container memberships (epic, feature, story, bug)
    container_memberships = db.relationship('WorkItemMembership', 
                                          foreign_keys='WorkItemMembership.member_id',
                                          backref='member_work_item',
                                          cascade='all, delete-orphan')
    
    # Container relationships (when this work item is a container)
    member_containers = db.relationship('WorkItemMembership',
                                      foreign_keys='WorkItemMembership.container_id',
                                      backref='container_work_item',
                                      cascade='all, delete-orphan')
    
    # Dependencies
    predecessors = db.relationship('WorkItemDependency',
                                 foreign_keys='WorkItemDependency.successor_id',
                                 backref='successor_work_item',
                                 cascade='all, delete-orphan')
    
    successors = db.relationship('WorkItemDependency',
                               foreign_keys='WorkItemDependency.predecessor_id',
                               backref='predecessor_work_item',
                               cascade='all, delete-orphan')
    
    # Labels
    labels = db.relationship('WorkItemLabel', backref='work_item', cascade='all, delete-orphan')
    
    # Releases
    releases = db.relationship('WorkItemRelease', backref='work_item', cascade='all, delete-orphan')
    
    # Milestones
    milestones = db.relationship('WorkItemMilestone', backref='work_item', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('ix_work_items_project_type_status', 'project_id', 'type', 'status'),
    )
    
    def __repr__(self):
        return f'<WorkItem {self.key_id}: {self.title}>'
    
    @property
    def is_completed(self):
        """Check if work item is completed"""
        return self.status == WorkItemStatus.DONE
    
    @property
    def is_overdue(self):
        """Check if work item is overdue"""
        return (self.due_at and 
                self.due_at < date.today() and 
                not self.is_completed)
    
    @property
    def is_blocked(self):
        """Check if work item is blocked by dependencies"""
        if self.status == WorkItemStatus.BLOCKED:
            return True
        
        # Check if any predecessor is not done
        for dep in self.predecessors:
            if dep.predecessor_work_item.status != WorkItemStatus.DONE:
                return True
        return False
    
    def get_containers(self, relation_type=None):
        """Get containers that contain this work item"""
        query = db.session.query(WorkItem).join(WorkItemMembership, 
                                               WorkItem.id == WorkItemMembership.container_id)
        query = query.filter(WorkItemMembership.member_id == self.id)
        
        if relation_type:
            query = query.filter(WorkItemMembership.relation == relation_type)
        
        return query.all()
    
    def get_members(self, relation_type=None):
        """Get members contained by this work item"""
        query = db.session.query(WorkItem).join(WorkItemMembership,
                                              WorkItem.id == WorkItemMembership.member_id)
        query = query.filter(WorkItemMembership.container_id == self.id)
        
        if relation_type:
            query = query.filter(WorkItemMembership.relation == relation_type)
        
        return query.all()
    
    def calculate_rollup_status(self):
        """Calculate status based on members"""
        members = self.get_members()
        if not members:
            return self.status
        
        # Check for blocked members
        if any(member.status == WorkItemStatus.BLOCKED for member in members):
            return WorkItemStatus.BLOCKED
        
        # Check for in-progress members
        if any(member.status == WorkItemStatus.IN_PROGRESS for member in members):
            return WorkItemStatus.IN_PROGRESS
        
        # Check if all members are done
        if all(member.status == WorkItemStatus.DONE for member in members):
            return WorkItemStatus.DONE
        
        # Check for ready members
        if any(member.status == WorkItemStatus.READY for member in members):
            return WorkItemStatus.READY
        
        return WorkItemStatus.NOT_STARTED
    
    def calculate_rollup_progress(self):
        """Calculate progress percentage based on members"""
        members = self.get_members()
        if not members:
            return self.progress_pct or 0.0
        
        # Simple average for now (can be enhanced with points later)
        total_progress = sum(member.progress_pct or 0.0 for member in members)
        return round(total_progress / len(members), 1)
    
    def update_rollup_fields(self):
        """Update status and progress based on members if rollup_mode is enabled"""
        if not self.rollup_mode:
            return
        
        # Update status
        new_status = self.calculate_rollup_status()
        if new_status != self.status:
            self.status = new_status
        
        # Update progress
        new_progress = self.calculate_rollup_progress()
        if new_progress != self.progress_pct:
            self.progress_pct = new_progress
        
        # Update completion date
        if self.status == WorkItemStatus.DONE and not self.completed_at:
            self.completed_at = datetime.utcnow()
        elif self.status != WorkItemStatus.DONE:
            self.completed_at = None
    
    def validate_parent_child_relationship(self):
        """Validate parent-child relationship constraints"""
        if self.parent_id:
            parent = WorkItem.query.get(self.parent_id)
            if not parent:
                raise ValueError("Parent work item not found")
            
            # Both parent and child must be tasks
            if self.type != WorkItemType.TASK or parent.type != WorkItemType.TASK:
                raise ValueError("Parent-child relationships are only allowed between tasks")
            
            # Prevent self-parenting
            if self.id == parent.id:
                raise ValueError("Work item cannot be its own parent")
            
            # Prevent circular references
            if self._would_create_cycle(parent):
                raise ValueError("Parent-child relationship would create a cycle")
    
    def _would_create_cycle(self, potential_parent):
        """Check if setting potential_parent as parent would create a cycle"""
        current = potential_parent
        visited = set()
        
        while current and current.parent_id:
            if current.parent_id in visited:
                return True
            visited.add(current.parent_id)
            current = WorkItem.query.get(current.parent_id)
        
        return False
    
    def validate_story_kind(self):
        """Validate story_kind field based on type"""
        if self.type == WorkItemType.STORY and not self.story_kind:
            raise ValueError("Story kind is required for story work items")
        elif self.type != WorkItemType.STORY and self.story_kind:
            raise ValueError("Story kind can only be set for story work items")
    
    def validate_membership_constraints(self):
        """Validate membership relationship constraints"""
        # This will be called when memberships are created/updated
        # Implementation will be in the membership model
        pass


class WorkItemMembership(db.Model):
    """Many-to-many relationship for work item containers and members"""
    __tablename__ = 'work_item_memberships'
    
    container_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=False)
    member_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=False)
    relation = db.Column(ENUM(WorkItemType), nullable=False)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('container_id', 'member_id', 'relation'),
        Index('ix_work_item_memberships_container', 'container_id'),
        Index('ix_work_item_memberships_member', 'member_id'),
    )
    
    def validate_membership_rules(self):
        """Validate membership relationship rules"""
        container = WorkItem.query.get(self.container_id)
        member = WorkItem.query.get(self.member_id)
        
        if not container or not member:
            raise ValueError("Container or member work item not found")
        
        # Prevent self-membership
        if container.id == member.id:
            raise ValueError("Work item cannot be a member of itself")
        
        # Validate relationship rules
        valid_relationships = {
            WorkItemType.EPIC: [WorkItemType.TASK, WorkItemType.STORY, WorkItemType.BUG],
            WorkItemType.FEATURE: [WorkItemType.EPIC, WorkItemType.STORY, WorkItemType.TASK, WorkItemType.BUG],
            WorkItemType.STORY: [WorkItemType.TASK],
            WorkItemType.BUG: [WorkItemType.TASK],
        }
        
        if container.type not in valid_relationships:
            raise ValueError(f"{container.type.value} cannot be a container")
        
        if member.type not in valid_relationships[container.type]:
            raise ValueError(f"{container.type.value} cannot contain {member.type.value}")


class WorkItemDependency(db.Model):
    """Dependency relationships between work items (DAG)"""
    __tablename__ = 'work_item_deps'
    
    predecessor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=False)
    successor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=False)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('predecessor_id', 'successor_id'),
        Index('ix_work_item_deps_predecessor', 'predecessor_id'),
        Index('ix_work_item_deps_successor', 'successor_id'),
    )
    
    def validate_dependency_rules(self):
        """Validate dependency relationship rules"""
        predecessor = WorkItem.query.get(self.predecessor_id)
        successor = WorkItem.query.get(self.successor_id)
        
        if not predecessor or not successor:
            raise ValueError("Predecessor or successor work item not found")
        
        # Prevent self-dependency
        if predecessor.id == successor.id:
            raise ValueError("Work item cannot depend on itself")
        
        # Check for cycles
        if self._would_create_cycle(predecessor, successor):
            raise ValueError("Dependency would create a cycle")
    
    def _would_create_cycle(self, predecessor, successor):
        """Check if adding this dependency would create a cycle"""
        # Use DFS to check for path from successor to predecessor
        visited = set()
        stack = [successor]
        
        while stack:
            current = stack.pop()
            if current.id == predecessor.id:
                return True
            
            if current.id in visited:
                continue
            visited.add(current.id)
            
            # Add all successors to stack
            for dep in current.successors:
                stack.append(dep.successor_work_item)
        
        return False


class Label(db.Model):
    """Labels for work items"""
    __tablename__ = 'labels'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    color = db.Column(db.String(7), nullable=True)  # Hex color code
    description = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Label {self.name}>'


class WorkItemLabel(db.Model):
    """Many-to-many relationship between work items and labels"""
    __tablename__ = 'work_item_labels'
    
    work_item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=False)
    label_id = db.Column(UUID(as_uuid=True), db.ForeignKey('labels.id'), nullable=False)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('work_item_id', 'label_id'),
        Index('ix_work_item_labels_work_item', 'work_item_id'),
        Index('ix_work_item_labels_label', 'label_id'),
    )


class Release(db.Model):
    """Release model"""
    __tablename__ = 'releases'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    version = db.Column(db.String(50), nullable=True)
    tag = db.Column(db.String(100), nullable=True)
    status = db.Column(ENUM('not_started', 'in_progress', 'ready', 'released'), 
                      default='not_started', nullable=False, index=True)
    released_at = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    repo_url = db.Column(db.String(500), nullable=True)
    
    # Relationships
    project = db.relationship('Project', backref='releases')
    work_items = db.relationship('WorkItemRelease', backref='release', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Release {self.name}>'


class WorkItemRelease(db.Model):
    """Many-to-many relationship between work items and releases"""
    __tablename__ = 'work_item_releases'
    
    work_item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=False)
    release_id = db.Column(UUID(as_uuid=True), db.ForeignKey('releases.id'), nullable=False)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('work_item_id', 'release_id'),
        Index('ix_work_item_releases_work_item', 'work_item_id'),
        Index('ix_work_item_releases_release', 'release_id'),
    )


class ProjectMilestone(db.Model):
    """Project milestone model"""
    __tablename__ = 'project_milestones'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    status = db.Column(ENUM('not_started', 'in_progress', 'done', 'slipped'),
                      default='not_started', nullable=False, index=True)
    start_at = db.Column(db.Date, nullable=True)
    due_at = db.Column(db.Date, nullable=True)
    completed_at = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    project = db.relationship('Project', backref='milestones')
    work_items = db.relationship('WorkItemMilestone', backref='milestone', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Milestone {self.name}>'


class WorkItemMilestone(db.Model):
    """Many-to-many relationship between work items and milestones"""
    __tablename__ = 'work_item_milestones'
    
    work_item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('work_items.id'), nullable=False)
    milestone_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project_milestones.id'), nullable=False)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('work_item_id', 'milestone_id'),
        Index('ix_work_item_milestones_work_item', 'work_item_id'),
        Index('ix_work_item_milestones_milestone', 'milestone_id'),
    )