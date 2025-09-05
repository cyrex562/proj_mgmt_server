from flask import request, jsonify
from flask_login import login_required, current_user
from app import db
from app.api import bp
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.api.schemas import ProjectSchema, ProjectMemberSchema

project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)
member_schema = ProjectMemberSchema()
members_schema = ProjectMemberSchema(many=True)

@bp.route('/projects', methods=['GET'])
@login_required
def get_projects():
    """Get all projects user has access to"""
    projects = Project.query.join(ProjectMember).filter(
        ProjectMember.user_id == current_user.id
    ).all()
    return jsonify(projects_schema.dump(projects))

@bp.route('/projects', methods=['POST'])
@login_required
def create_project():
    """Create a new project"""
    data = request.get_json()
    
    # Generate unique project key
    project_key = Project.generate_project_key(data['name'])
    
    project = Project(
        name=data['name'],
        key=project_key,
        description=data.get('description', ''),
        status=data.get('status', 'active'),
        priority=data.get('priority', 'medium'),
        creator_id=current_user.id
    )
    
    db.session.add(project)
    db.session.flush()  # Get the project ID
    
    # Add creator as project owner
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role='owner'
    )
    db.session.add(member)
    db.session.commit()
    
    return jsonify(project_schema.dump(project)), 201

@bp.route('/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """Get a specific project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(project_schema.dump(project))

@bp.route('/projects/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    """Update a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.status = data.get('status', project.status)
    project.priority = data.get('priority', project.priority)
    project.start_date = data.get('start_date')
    project.end_date = data.get('end_date')
    
    db.session.commit()
    return jsonify(project_schema.dump(project))

@bp.route('/projects/<int:project_id>/members', methods=['GET'])
@login_required
def get_project_members(project_id):
    """Get project members"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    members = project.members.all()
    return jsonify(members_schema.dump(members))

@bp.route('/projects/<int:project_id>/members', methods=['POST'])
@login_required
def add_project_member(project_id):
    """Add a member to project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    user = User.query.get_or_404(data['user_id'])
    
    # Check if user is already a member
    existing_member = project.members.filter_by(user_id=user.id).first()
    if existing_member:
        return jsonify({'error': 'User is already a member'}), 400
    
    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=data.get('role', 'member')
    )
    
    db.session.add(member)
    db.session.commit()
    
    return jsonify(member_schema.dump(member)), 201

@bp.route('/projects/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
def remove_project_member(project_id, user_id):
    """Remove a member from project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    member = project.members.filter_by(user_id=user_id).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    # Prevent removing the last owner
    if member.role == 'owner' and project.members.filter_by(role='owner').count() == 1:
        return jsonify({'error': 'Cannot remove the last owner'}), 400
    
    db.session.delete(member)
    db.session.commit()
    
    return jsonify({'message': 'Member removed successfully'})