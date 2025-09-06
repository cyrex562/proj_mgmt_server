from datetime import datetime
from app import db
import os

class FileAttachment(db.Model):
    """File attachment model for tasks and projects"""
    __tablename__ = 'file_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100))
    storage_type = db.Column(db.String(32), default='local')  # local, s3, etc.
    storage_url = db.Column(db.String(500))  # For S3 or other cloud storage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    work_item_id = db.Column(db.String(36), db.ForeignKey('work_items.id'))
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    uploaded_by = db.relationship('User', backref='uploaded_files')
    work_item = db.relationship('WorkItem', backref='attachments')
    
    def __repr__(self):
        return f'<FileAttachment {self.original_filename}>'
    
    @property
    def file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.original_filename)[1].lower()
    
    @property
    def is_image(self):
        """Check if file is an image"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
        return self.file_extension in image_extensions
    
    @property
    def is_document(self):
        """Check if file is a document"""
        doc_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}
        return self.file_extension in doc_extensions
    
    @property
    def is_archive(self):
        """Check if file is an archive"""
        archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz'}
        return self.file_extension in archive_extensions
    
    @property
    def human_readable_size(self):
        """Get human readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"