from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.main import bp
from app.models.project import Project
from app.models.task import Task

@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        return render_template('main/dashboard.html', title='Dashboard')
    return render_template('main/index.html', title='Project Management')

@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with project overview"""
    # Get user's projects
    projects = Project.query.join(Project.members).filter(
        Project.members.any(user_id=current_user.id)
    ).all()
    
    # Get recent tasks assigned to user
    recent_tasks = Task.query.join(Project).join(Project.members).filter(
        Project.members.any(user_id=current_user.id),
        Task.assignee_id == current_user.id
    ).order_by(Task.updated_at.desc()).limit(10).all()
    
    # Get overdue tasks
    from datetime import date
    overdue_tasks = Task.query.join(Project).join(Project.members).filter(
        Project.members.any(user_id=current_user.id),
        Task.due_date < date.today(),
        Task.status != 'done'
    ).all()
    
    return render_template('main/dashboard.html', 
                         title='Dashboard',
                         projects=projects,
                         recent_tasks=recent_tasks,
                         overdue_tasks=overdue_tasks)

@bp.route('/projects')
@login_required
def projects():
    """Projects listing page"""
    return render_template('main/projects.html', title='Projects')

@bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    """Project detail page"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return render_template('errors/403.html'), 403
    
    return render_template('main/project_detail.html', 
                         title=f'{project.name} - Project',
                         project=project)

@bp.route('/projects/<int:project_id>/board')
@login_required
def project_board(project_id):
    """Kanban board view for project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return render_template('errors/403.html'), 403
    
    return render_template('main/project_board.html', 
                         title=f'{project.name} - Board',
                         project=project)

@bp.route('/projects/<int:project_id>/spreadsheet')
@login_required
def project_spreadsheet(project_id):
    """Spreadsheet view for project tasks"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return render_template('errors/403.html'), 403
    
    return render_template('main/project_spreadsheet.html', 
                         title=f'{project.name} - Spreadsheet',
                         project=project)

@bp.route('/projects/<int:project_id>/milestones')
@login_required
def project_milestones(project_id):
    """Milestone management view for a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return render_template('errors/403.html'), 403
    
    return render_template('main/milestones.html', 
                         title=f'{project.name} - Milestones',
                         project=project)

@bp.route('/tasks')
@login_required
def tasks():
    """All tasks view"""
    return render_template('main/tasks.html', title='All Tasks')

@bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('main/profile.html', title='Profile')