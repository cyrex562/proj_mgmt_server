from flask import request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.api import bp
from app.models.file import FileAttachment
from app.models.task import Task
from app.models.project import Project
from app.api.schemas import FileAttachmentSchema
import os
import uuid
from datetime import datetime

file_schema = FileAttachmentSchema()
files_schema = FileAttachmentSchema(many=True)

ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx',
    'ppt', 'pptx', 'zip', 'rar', '7z', 'tar', 'gz', 'mp4', 'avi', 'mov',
    'mp3', 'wav', 'flac', 'svg', 'webp', 'bmp', 'tiff', 'rtf', 'odt'
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/tasks/<int:task_id>/files', methods=['GET'])
@login_required
def get_task_files(task_id):
    """Get all files attached to a task"""
    task = Task.query.get_or_404(task_id)
    
    if not task.project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    files = task.attachments.all()
    return jsonify(files_schema.dump(files))

@bp.route('/tasks/<int:task_id>/files', methods=['POST'])
@login_required
def upload_task_file(task_id):
    """Upload a file to a task"""
    task = Task.query.get_or_404(task_id)
    
    if not task.project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    file_extension = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Save file locally
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Get file info
    file_size = os.path.getsize(file_path)
    mime_type = file.content_type or 'application/octet-stream'
    
    # Create database record
    attachment = FileAttachment(
        filename=unique_filename,
        original_filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        storage_type='local',
        task_id=task.id,
        uploaded_by_id=current_user.id
    )
    
    db.session.add(attachment)
    db.session.commit()
    
    return jsonify(file_schema.dump(attachment)), 201

@bp.route('/files/<int:file_id>', methods=['GET'])
@login_required
def download_file(file_id):
    """Download a file"""
    attachment = FileAttachment.query.get_or_404(file_id)
    
    # Check access permissions
    if attachment.task:
        if not attachment.task.project.can_user_access(current_user):
            return jsonify({'error': 'Access denied'}), 403
    elif attachment.project:
        if not attachment.project.can_user_access(current_user):
            return jsonify({'error': 'Access denied'}), 403
    else:
        return jsonify({'error': 'File not found'}), 404
    
    if attachment.storage_type == 'local':
        if os.path.exists(attachment.file_path):
            return send_file(
                attachment.file_path,
                as_attachment=True,
                download_name=attachment.original_filename,
                mimetype=attachment.mime_type
            )
        else:
            return jsonify({'error': 'File not found on disk'}), 404
    else:
        # Handle S3 or other cloud storage
        return jsonify({'error': 'Cloud storage not implemented yet'}), 501

@bp.route('/files/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    """Delete a file"""
    attachment = FileAttachment.query.get_or_404(file_id)
    
    # Check access permissions
    if attachment.task:
        if not attachment.task.project.can_user_access(current_user, 'admin'):
            return jsonify({'error': 'Access denied'}), 403
    elif attachment.project:
        if not attachment.project.can_user_access(current_user, 'admin'):
            return jsonify({'error': 'Access denied'}), 403
    else:
        return jsonify({'error': 'File not found'}), 404
    
    # Delete file from disk
    if attachment.storage_type == 'local' and os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)
    
    # Delete database record
    db.session.delete(attachment)
    db.session.commit()
    
    return jsonify({'message': 'File deleted successfully'})

@bp.route('/projects/<int:project_id>/files', methods=['GET'])
@login_required
def get_project_files(project_id):
    """Get all files attached to a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user):
        return jsonify({'error': 'Access denied'}), 403
    
    files = FileAttachment.query.filter_by(project_id=project.id).all()
    return jsonify(files_schema.dump(files))

@bp.route('/projects/<int:project_id>/files', methods=['POST'])
@login_required
def upload_project_file(project_id):
    """Upload a file to a project"""
    project = Project.query.get_or_404(project_id)
    
    if not project.can_user_access(current_user, 'member'):
        return jsonify({'error': 'Access denied'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    file_extension = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Save file locally
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Get file info
    file_size = os.path.getsize(file_path)
    mime_type = file.content_type or 'application/octet-stream'
    
    # Create database record
    attachment = FileAttachment(
        filename=unique_filename,
        original_filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        storage_type='local',
        project_id=project.id,
        uploaded_by_id=current_user.id
    )
    
    db.session.add(attachment)
    db.session.commit()
    
    return jsonify(file_schema.dump(attachment)), 201