from flask import request, jsonify
from flask_login import login_required, current_user
from app import db
from app.api import bp
from app.models.task import Task, SubTask, Epic, Story, Bug, Milestone
from app.models.project import Project
from app.api.schemas import TaskSchema, MilestoneSchema

task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)
milestone_schema = MilestoneSchema()
milestones_schema = MilestoneSchema(many=True)

@bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
@login_required
def get_project_tasks(project_id):
    """Get all tasks for a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    # Get query parameters for filtering
    status = request.args.get('status')
    task_type = request.args.get('type')
    assignee_id = request.args.get('assignee_id')
    
    query = project.tasks
    
    if status:
        query = query.filter(Task.status == status)
    if task_type:
        query = query.filter(Task.task_type == task_type)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    
    tasks = query.all()
    return jsonify(tasks_schema.dump(tasks))

@bp.route('/projects/<int:project_id>/tasks', methods=['POST'])
@login_required
def create_task(project_id):
    """Create a new task"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    # Get next task number for this project
    task_number = project.get_next_task_number()
    
    task = Task(
        task_number=task_number,
        title=data['title'],
        description=data.get('description', ''),
        status=data.get('status', 'backlog'),
        priority=data.get('priority', 'medium'),
        task_type=data.get('task_type', 'task'),
        project_id=project.id,
        assignee_id=data.get('assignee_id') if data.get('assignee_id') else None,
        epic_id=data.get('epic_id') if data.get('epic_id') else None,
        milestone_id=data.get('milestone_id') if data.get('milestone_id') else None,
        due_date=data.get('due_date') if data.get('due_date') else None,
        estimated_hours=data.get('estimated_hours') if data.get('estimated_hours') else None
    )
    
    db.session.add(task)
    db.session.commit()
    
    return jsonify(task_schema.dump(task)), 201

@bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    """Get a specific task"""
    task = Task.query.get_or_404(task_id)
    
    if not task.project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(task_schema.dump(task))

@bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """Update a task"""
    task = Task.query.get_or_404(task_id)
    
    if not task.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.status = data.get('status', task.status)
    task.priority = data.get('priority', task.priority)
    # Handle empty values for optional fields
    assignee_id = data.get('assignee_id', task.assignee_id)
    task.assignee_id = assignee_id if assignee_id else None
    
    due_date = data.get('due_date', task.due_date)
    task.due_date = due_date if due_date else None
    
    estimated_hours = data.get('estimated_hours', task.estimated_hours)
    task.estimated_hours = estimated_hours if estimated_hours else None
    
    actual_hours = data.get('actual_hours', task.actual_hours)
    task.actual_hours = actual_hours if actual_hours else None
    
    # Handle progress percentage - only update if explicitly provided
    if 'progress_percentage' in data:
        progress_percentage = data.get('progress_percentage')
        task.progress_percentage = progress_percentage if progress_percentage is not None else 0
    else:
        # Only auto-update progress if not manually set
        task.update_progress()
    
    # Update completion date if status changed to done
    if task.status == 'done' and not task.completed_at:
        from datetime import datetime
        task.completed_at = datetime.utcnow()
    elif task.status != 'done':
        task.completed_at = None
    
    db.session.commit()
    
    return jsonify(task_schema.dump(task))

@bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete a task"""
    task = Task.query.get_or_404(task_id)
    
    if not task.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    # Update milestone status if task was assigned to one
    if task.milestone:
        task.milestone.update_status()
    
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted successfully'})

@bp.route('/projects/<int:project_id>/milestones', methods=['GET'])
@login_required
def get_project_milestones(project_id):
    """Get all milestones for a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    milestones = project.milestones.all()
    return jsonify(milestones_schema.dump(milestones))

@bp.route('/projects/<int:project_id>/milestones', methods=['POST'])
@login_required
def create_milestone(project_id):
    """Create a new milestone"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    # Handle empty date strings
    target_date = data.get('target_date')
    if target_date == '' or target_date is None:
        target_date = None
    
    milestone = Milestone(
        name=data['name'],
        description=data.get('description', ''),
        target_date=target_date,
        project_id=project.id
    )
    
    db.session.add(milestone)
    db.session.commit()
    
    return jsonify(milestone_schema.dump(milestone)), 201

@bp.route('/milestones/<int:milestone_id>', methods=['PUT'])
@login_required
def update_milestone(milestone_id):
    """Update a milestone"""
    milestone = Milestone.query.get_or_404(milestone_id)
    
    if not milestone.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    milestone.name = data.get('name', milestone.name)
    milestone.description = data.get('description', milestone.description)
    
    # Handle empty date strings
    target_date = data.get('target_date', milestone.target_date)
    if target_date == '' or target_date is None:
        target_date = None
    milestone.target_date = target_date
    
    milestone.status = data.get('status', milestone.status)
    
    milestone.update_status()
    db.session.commit()
    
    return jsonify(milestone_schema.dump(milestone))

@bp.route('/milestones/<int:milestone_id>', methods=['DELETE'])
@login_required
def delete_milestone(milestone_id):
    """Delete a milestone"""
    milestone = Milestone.query.get_or_404(milestone_id)
    
    if not milestone.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    # Unassign all tasks from this milestone
    for task in milestone.tasks:
        task.milestone_id = None
    
    db.session.delete(milestone)
    db.session.commit()
    
    return jsonify({'message': 'Milestone deleted successfully'})

@bp.route('/milestones/<int:milestone_id>/tasks', methods=['GET'])
@login_required
def get_milestone_tasks(milestone_id):
    """Get all tasks assigned to a milestone"""
    milestone = Milestone.query.get_or_404(milestone_id)
    
    if not milestone.project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    tasks = milestone.tasks.all()
    return jsonify(tasks_schema.dump(tasks))

@bp.route('/milestones/<int:milestone_id>/tasks/<int:task_id>', methods=['POST'])
@login_required
def assign_task_to_milestone(milestone_id, task_id):
    """Assign a task to a milestone"""
    milestone = Milestone.query.get_or_404(milestone_id)
    task = Task.query.get_or_404(task_id)
    
    # Check if both milestone and task belong to the same project
    if milestone.project_id != task.project_id:
        return jsonify({'error': 'Task and milestone must belong to the same project'}), 400
    
    if not milestone.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    task.milestone_id = milestone_id
    milestone.update_status()
    db.session.commit()
    
    return jsonify({'message': 'Task assigned to milestone successfully'})

@bp.route('/milestones/<int:milestone_id>/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def unassign_task_from_milestone(milestone_id, task_id):
    """Unassign a task from a milestone"""
    milestone = Milestone.query.get_or_404(milestone_id)
    task = Task.query.get_or_404(task_id)
    
    if not milestone.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    if task.milestone_id != milestone_id:
        return jsonify({'error': 'Task is not assigned to this milestone'}), 400
    
    task.milestone_id = None
    milestone.update_status()
    db.session.commit()
    
    return jsonify({'message': 'Task unassigned from milestone successfully'})

@bp.route('/tasks/<int:task_id>/milestone', methods=['PUT'])
@login_required
def update_task_milestone(task_id):
    """Update milestone assignment for a task"""
    task = Task.query.get_or_404(task_id)
    
    if not task.project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    milestone_id = data.get('milestone_id')
    
    if milestone_id:
        milestone = Milestone.query.get_or_404(milestone_id)
        if milestone.project_id != task.project_id:
            return jsonify({'error': 'Milestone must belong to the same project'}), 400
        task.milestone_id = milestone_id
    else:
        task.milestone_id = None
    
    # Update milestone status if task was assigned to one
    if task.milestone:
        task.milestone.update_status()
    
    db.session.commit()
    
    return jsonify({'message': 'Task milestone updated successfully'})