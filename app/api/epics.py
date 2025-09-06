from flask import request, jsonify
from flask_login import login_required, current_user
from app import db
from app.api import bp
from app.models.task import Epic
from app.models.project_new import Project
from app.api.schemas import EpicSchema

epic_schema = EpicSchema()
epics_schema = EpicSchema(many=True)

@bp.route('/projects/<int:project_id>/epics', methods=['GET'])
@login_required
def get_project_epics(project_id):
    """Get all epics for a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    epics = Epic.query.filter_by(project_id=project_id).all()
    return jsonify(epics_schema.dump(epics))

@bp.route('/projects/<int:project_id>/epics', methods=['POST'])
@login_required
def create_epic(project_id):
    """Create a new epic"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    epic = Epic(
        title=data['title'],
        description=data.get('description', ''),
        status=data.get('status', 'backlog'),
        priority=data.get('priority', 'medium'),
        project_id=project.id,
        assignee_id=data.get('assignee_id') if data.get('assignee_id') else None,
        due_date=data.get('due_date') if data.get('due_date') else None,
        estimated_hours=data.get('estimated_hours') if data.get('estimated_hours') else None
    )
    
    db.session.add(epic)
    db.session.flush()  # Get the epic ID
    
    # Generate epic key
    epic.epic_key = epic.generate_epic_key()
    
    db.session.commit()
    
    return jsonify(epic_schema.dump(epic)), 201

@bp.route('/epics/<int:epic_id>', methods=['GET'])
@login_required
def get_epic(epic_id):
    """Get a specific epic"""
    epic = Epic.query.get_or_404(epic_id)
    
    if not epic.project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(epic_schema.dump(epic))

@bp.route('/epics/<int:epic_id>', methods=['PUT'])
@login_required
def update_epic(epic_id):
    """Update an epic"""
    epic = Epic.query.get_or_404(epic_id)
    
    if not epic.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    epic.title = data.get('title', epic.title)
    epic.description = data.get('description', epic.description)
    epic.status = data.get('status', epic.status)
    epic.priority = data.get('priority', epic.priority)
    
    # Handle empty values for optional fields
    assignee_id = data.get('assignee_id', epic.assignee_id)
    epic.assignee_id = assignee_id if assignee_id else None
    
    due_date = data.get('due_date', epic.due_date)
    epic.due_date = due_date if due_date else None
    
    estimated_hours = data.get('estimated_hours', epic.estimated_hours)
    epic.estimated_hours = estimated_hours if estimated_hours else None
    
    actual_hours = data.get('actual_hours', epic.actual_hours)
    epic.actual_hours = actual_hours if actual_hours else None
    
    # Handle progress percentage - only update if explicitly provided
    if 'progress_percentage' in data:
        progress_percentage = data.get('progress_percentage')
        epic.progress_percentage = progress_percentage if progress_percentage is not None else 0
    else:
        # Auto-update progress from tasks if not manually set
        epic.update_progress_from_tasks()
    
    # Update completion date if status changed to done
    if epic.status == 'done' and not epic.completed_at:
        from datetime import datetime
        epic.completed_at = datetime.utcnow()
    elif epic.status != 'done':
        epic.completed_at = None
    
    db.session.commit()
    
    return jsonify(epic_schema.dump(epic))

@bp.route('/epics/<int:epic_id>', methods=['DELETE'])
@login_required
def delete_epic(epic_id):
    """Delete an epic"""
    epic = Epic.query.get_or_404(epic_id)
    
    if not epic.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    # Unassign all tasks from this epic
    for task in epic.tasks:
        task.epic_id = None
    
    db.session.delete(epic)
    db.session.commit()
    
    return jsonify({'message': 'Epic deleted successfully'})

@bp.route('/epics/<int:epic_id>/tasks', methods=['GET'])
@login_required
def get_epic_tasks(epic_id):
    """Get all tasks assigned to an epic"""
    epic = Epic.query.get_or_404(epic_id)
    
    if not epic.project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    tasks = epic.tasks.all()
    from app.api.schemas import TaskSchema
    task_schema = TaskSchema(many=True)
    return jsonify(task_schema.dump(tasks))

@bp.route('/epics/<int:epic_id>/tasks/<int:task_id>', methods=['POST'])
@login_required
def assign_task_to_epic(epic_id, task_id):
    """Assign a task to an epic"""
    epic = Epic.query.get_or_404(epic_id)
    from app.models.task import Task
    task = Task.query.get_or_404(task_id)
    
    # Check if both epic and task belong to the same project
    if epic.project_id != task.project_id:
        return jsonify({'error': 'Epic and task must belong to the same project'}), 400
    
    if not epic.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    task.epic_id = epic.id
    db.session.commit()
    
    # Update epic progress
    epic.update_progress_from_tasks()
    db.session.commit()
    
    return jsonify({'message': 'Task assigned to epic successfully'})

@bp.route('/epics/<int:epic_id>/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def unassign_task_from_epic(epic_id, task_id):
    """Unassign a task from an epic"""
    epic = Epic.query.get_or_404(epic_id)
    from app.models.task import Task
    task = Task.query.get_or_404(task_id)
    
    if not epic.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    if task.epic_id != epic.id:
        return jsonify({'error': 'Task is not assigned to this epic'}), 400
    
    task.epic_id = None
    db.session.commit()
    
    # Update epic progress
    epic.update_progress_from_tasks()
    db.session.commit()
    
    return jsonify({'message': 'Task unassigned from epic successfully'})

@bp.route('/epics/<int:epic_id>/progress', methods=['POST'])
@login_required
def update_epic_progress(epic_id):
    """Manually update epic progress from assigned tasks"""
    epic = Epic.query.get_or_404(epic_id)
    
    if not epic.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    epic.update_progress_from_tasks()
    db.session.commit()
    
    return jsonify(epic_schema.dump(epic))