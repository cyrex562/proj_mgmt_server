from flask import request, jsonify
from flask_login import login_required, current_user
from app import db
from app.api import bp
from app.models.work_item import (
    WorkItem, WorkItemType, WorkItemStatus, WorkItemPriority, StoryKind,
    WorkItemMembership, WorkItemDependency, Label, WorkItemLabel,
    Release, WorkItemRelease, ProjectMilestone, WorkItemMilestone
)
from app.models.project_new import Project, ProjectCounter
from app.api.schemas_new import WorkItemSchema, WorkItemMembershipSchema, LabelSchema, ReleaseSchema, ProjectMilestoneSchema

work_item_schema = WorkItemSchema()
work_items_schema = WorkItemSchema(many=True)
label_schema = LabelSchema()
labels_schema = LabelSchema(many=True)
release_schema = ReleaseSchema()
releases_schema = ReleaseSchema(many=True)
milestone_schema = ProjectMilestoneSchema()
milestones_schema = ProjectMilestoneSchema(many=True)

@bp.route('/projects/<uuid:project_id>/work-items', methods=['GET'])
@login_required
def get_project_work_items(project_id):
    """Get all work items for a project with optional filtering"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    # Get query parameters for filtering
    work_item_type = request.args.get('type')
    status = request.args.get('status')
    priority = request.args.get('priority')
    parent_id = request.args.get('parent_id')
    container_id = request.args.get('container_id')
    container_type = request.args.get('container_type')
    
    # Build query
    query = WorkItem.query.filter_by(project_id=project_id)
    
    if work_item_type:
        try:
            query = query.filter(WorkItem.type == WorkItemType(work_item_type))
        except ValueError:
            return jsonify({'error': 'Invalid work item type'}), 400
    
    if status:
        try:
            query = query.filter(WorkItem.status == WorkItemStatus(status))
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if priority:
        try:
            query = query.filter(WorkItem.priority == WorkItemPriority(priority))
        except ValueError:
            return jsonify({'error': 'Invalid priority'}), 400
    
    if parent_id:
        query = query.filter(WorkItem.parent_id == parent_id)
    
    if container_id:
        # Get work items that are members of the specified container
        query = query.join(WorkItemMembership, WorkItem.id == WorkItemMembership.member_id)
        query = query.filter(WorkItemMembership.container_id == container_id)
        
        if container_type:
            try:
                query = query.filter(WorkItemMembership.relation == WorkItemType(container_type))
            except ValueError:
                return jsonify({'error': 'Invalid container type'}), 400
    
    work_items = query.all()
    return jsonify(work_items_schema.dump(work_items))

@bp.route('/projects/<uuid:project_id>/work-items', methods=['POST'])
@login_required
def create_work_item(project_id):
    """Create a new work item"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    
    if not data.get('type'):
        return jsonify({'error': 'Type is required'}), 400
    
    try:
        work_item_type = WorkItemType(data['type'])
    except ValueError:
        return jsonify({'error': 'Invalid work item type'}), 400
    
    # Generate key
    key_id = project.generate_work_item_key()
    
    # Create work item
    work_item = WorkItem(
        project_id=project_id,
        key_id=key_id,
        type=work_item_type,
        title=data['title'],
        description=data.get('description', ''),
        status=WorkItemStatus(data.get('status', 'not_started')),
        priority=WorkItemPriority(data.get('priority', 'medium')),
        parent_id=data.get('parent_id'),
        due_at=data.get('due_at'),
        story_kind=StoryKind(data['story_kind']) if data.get('story_kind') else None,
        repo_url=data.get('repo_url'),
        branch=data.get('branch'),
        commit_hash=data.get('commit_hash'),
        progress_pct=data.get('progress_pct', 0.0),
        rollup_mode=data.get('rollup_mode', False)
    )
    
    # Validate constraints
    try:
        work_item.validate_parent_child_relationship()
        work_item.validate_story_kind()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    db.session.add(work_item)
    db.session.commit()
    
    return jsonify(work_item_schema.dump(work_item)), 201

@bp.route('/work-items/<uuid:work_item_id>', methods=['GET'])
@login_required
def get_work_item(work_item_id):
    """Get a specific work item"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(work_item_schema.dump(work_item))

@bp.route('/work-items/<uuid:work_item_id>', methods=['PUT'])
@login_required
def update_work_item(work_item_id):
    """Update a work item"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    # Update fields
    if 'title' in data:
        work_item.title = data['title']
    
    if 'description' in data:
        work_item.description = data['description']
    
    if 'status' in data:
        try:
            work_item.status = WorkItemStatus(data['status'])
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if 'priority' in data:
        try:
            work_item.priority = WorkItemPriority(data['priority'])
        except ValueError:
            return jsonify({'error': 'Invalid priority'}), 400
    
    if 'parent_id' in data:
        work_item.parent_id = data['parent_id']
    
    if 'due_at' in data:
        work_item.due_at = data['due_at']
    
    if 'story_kind' in data:
        work_item.story_kind = StoryKind(data['story_kind']) if data['story_kind'] else None
    
    if 'repo_url' in data:
        work_item.repo_url = data['repo_url']
    
    if 'branch' in data:
        work_item.branch = data['branch']
    
    if 'commit_hash' in data:
        work_item.commit_hash = data['commit_hash']
    
    if 'progress_pct' in data:
        work_item.progress_pct = data['progress_pct']
    
    if 'rollup_mode' in data:
        work_item.rollup_mode = data['rollup_mode']
    
    # Validate constraints
    try:
        work_item.validate_parent_child_relationship()
        work_item.validate_story_kind()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Update rollup fields if needed
    work_item.update_rollup_fields()
    
    # Update completion date
    if work_item.status == WorkItemStatus.DONE and not work_item.completed_at:
        from datetime import datetime
        work_item.completed_at = datetime.utcnow()
    elif work_item.status != WorkItemStatus.DONE:
        work_item.completed_at = None
    
    db.session.commit()
    
    return jsonify(work_item_schema.dump(work_item))

@bp.route('/work-items/<uuid:work_item_id>', methods=['DELETE'])
@login_required
def delete_work_item(work_item_id):
    """Delete a work item"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    # Delete related records (cascade will handle most)
    db.session.delete(work_item)
    db.session.commit()
    
    return jsonify({'message': 'Work item deleted successfully'})

@bp.route('/work-items/<uuid:work_item_id>/members', methods=['POST'])
@login_required
def add_work_item_member(work_item_id):
    """Add a member to a work item container"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    member_id = data.get('member_id')
    relation_type = data.get('relation_type', work_item.type.value)
    
    if not member_id:
        return jsonify({'error': 'Member ID is required'}), 400
    
    member = WorkItem.query.get_or_404(member_id)
    
    # Create membership
    membership = WorkItemMembership(
        container_id=work_item_id,
        member_id=member_id,
        relation=WorkItemType(relation_type)
    )
    
    try:
        membership.validate_membership_rules()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    db.session.add(membership)
    
    # Update rollup fields
    work_item.update_rollup_fields()
    
    db.session.commit()
    
    return jsonify({'message': 'Member added successfully'})

@bp.route('/work-items/<uuid:work_item_id>/members/<uuid:member_id>', methods=['DELETE'])
@login_required
def remove_work_item_member(work_item_id, member_id):
    """Remove a member from a work item container"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    membership = WorkItemMembership.query.filter_by(
        container_id=work_item_id,
        member_id=member_id
    ).first()
    
    if not membership:
        return jsonify({'error': 'Membership not found'}), 404
    
    db.session.delete(membership)
    
    # Update rollup fields
    work_item.update_rollup_fields()
    
    db.session.commit()
    
    return jsonify({'message': 'Member removed successfully'})

@bp.route('/work-items/<uuid:work_item_id>/dependencies', methods=['POST'])
@login_required
def add_work_item_dependency(work_item_id):
    """Add a dependency to a work item"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    predecessor_id = data.get('predecessor_id')
    
    if not predecessor_id:
        return jsonify({'error': 'Predecessor ID is required'}), 400
    
    predecessor = WorkItem.query.get_or_404(predecessor_id)
    
    # Create dependency
    dependency = WorkItemDependency(
        predecessor_id=predecessor_id,
        successor_id=work_item_id
    )
    
    try:
        dependency.validate_dependency_rules()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    db.session.add(dependency)
    db.session.commit()
    
    return jsonify({'message': 'Dependency added successfully'})

@bp.route('/work-items/<uuid:work_item_id>/dependencies/<uuid:predecessor_id>', methods=['DELETE'])
@login_required
def remove_work_item_dependency(work_item_id, predecessor_id):
    """Remove a dependency from a work item"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    dependency = WorkItemDependency.query.filter_by(
        predecessor_id=predecessor_id,
        successor_id=work_item_id
    ).first()
    
    if not dependency:
        return jsonify({'error': 'Dependency not found'}), 404
    
    db.session.delete(dependency)
    db.session.commit()
    
    return jsonify({'message': 'Dependency removed successfully'})

@bp.route('/work-items/<uuid:work_item_id>/rollup', methods=['POST'])
@login_required
def update_work_item_rollup(work_item_id):
    """Manually update rollup fields for a work item"""
    work_item = WorkItem.query.get_or_404(work_item_id)
    
    if not work_item.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    work_item.update_rollup_fields()
    db.session.commit()
    
    return jsonify(work_item_schema.dump(work_item))

# Labels endpoints
@bp.route('/labels', methods=['GET'])
@login_required
def get_labels():
    """Get all labels"""
    labels = Label.query.all()
    return jsonify(labels_schema.dump(labels))

@bp.route('/labels', methods=['POST'])
@login_required
def create_label():
    """Create a new label"""
    data = request.get_json()
    
    label = Label(
        name=data['name'],
        color=data.get('color'),
        description=data.get('description')
    )
    
    db.session.add(label)
    db.session.commit()
    
    return jsonify(label_schema.dump(label)), 201

# Releases endpoints
@bp.route('/projects/<uuid:project_id>/releases', methods=['GET'])
@login_required
def get_project_releases(project_id):
    """Get all releases for a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    releases = Release.query.filter_by(project_id=project_id).all()
    return jsonify(releases_schema.dump(releases))

@bp.route('/projects/<uuid:project_id>/releases', methods=['POST'])
@login_required
def create_release(project_id):
    """Create a new release"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    release = Release(
        project_id=project_id,
        name=data['name'],
        version=data.get('version'),
        tag=data.get('tag'),
        status=data.get('status', 'not_started'),
        description=data.get('description'),
        repo_url=data.get('repo_url')
    )
    
    db.session.add(release)
    db.session.commit()
    
    return jsonify(release_schema.dump(release)), 201

# Milestones endpoints
@bp.route('/projects/<uuid:project_id>/milestones', methods=['GET'])
@login_required
def get_project_milestones(project_id):
    """Get all milestones for a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    milestones = ProjectMilestone.query.filter_by(project_id=project_id).all()
    return jsonify(milestones_schema.dump(milestones))

@bp.route('/projects/<uuid:project_id>/milestones', methods=['POST'])
@login_required
def create_milestone(project_id):
    """Create a new milestone"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    milestone = ProjectMilestone(
        project_id=project_id,
        name=data['name'],
        status=data.get('status', 'not_started'),
        start_at=data.get('start_at'),
        due_at=data.get('due_at'),
        description=data.get('description')
    )
    
    db.session.add(milestone)
    db.session.commit()
    
    return jsonify(milestone_schema.dump(milestone)), 201


# Backward compatibility endpoints for old task API
@bp.route('/projects/<uuid:project_id>/tasks', methods=['GET'])
@login_required
def get_project_tasks_compat(project_id):
    """Backward compatibility: Get tasks for a project (redirects to work items)"""
    return get_project_work_items(project_id)

@bp.route('/projects/<uuid:project_id>/tasks', methods=['POST'])
@login_required
def create_project_task_compat(project_id):
    """Backward compatibility: Create a task (redirects to work items)"""
    return create_work_item(project_id)

@bp.route('/tasks/<uuid:task_id>', methods=['GET'])
@login_required
def get_task_compat(task_id):
    """Backward compatibility: Get a task (redirects to work item)"""
    return get_work_item(task_id)

@bp.route('/tasks/<uuid:task_id>', methods=['PUT'])
@login_required
def update_task_compat(task_id):
    """Backward compatibility: Update a task (redirects to work item)"""
    return update_work_item(task_id)

@bp.route('/tasks/<uuid:task_id>', methods=['DELETE'])
@login_required
def delete_task_compat(task_id):
    """Backward compatibility: Delete a task (redirects to work item)"""
    return delete_work_item(task_id)