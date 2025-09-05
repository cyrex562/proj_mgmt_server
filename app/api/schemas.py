from marshmallow import Schema, fields, validate
from app.models.user import User, Group
from app.models.project import Project, ProjectMember
from app.models.task import Task, Milestone
from app.models.file import FileAttachment

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=4, max=20))
    email = fields.Email(required=True)
    first_name = fields.Str(validate=validate.Length(max=64))
    last_name = fields.Str(validate=validate.Length(max=64))
    full_name = fields.Str(dump_only=True)
    avatar_url = fields.Str(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    is_admin = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)

class GroupSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(max=64))
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)

class ProjectMemberSchema(Schema):
    id = fields.Int(dump_only=True)
    role = fields.Str(validate=validate.OneOf(['owner', 'admin', 'member', 'viewer']))
    joined_at = fields.DateTime(dump_only=True)
    user = fields.Nested(UserSchema, dump_only=True)

class ProjectSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(max=128))
    key = fields.Str(dump_only=True)
    description = fields.Str()
    status = fields.Str(validate=validate.OneOf(['active', 'completed', 'archived', 'on_hold']))
    priority = fields.Str(validate=validate.OneOf(['low', 'medium', 'high', 'critical']))
    start_date = fields.Date()
    end_date = fields.Date()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    creator = fields.Nested(UserSchema, dump_only=True)
    members = fields.Nested(ProjectMemberSchema, many=True, dump_only=True)

class TaskSchema(Schema):
    id = fields.Int(dump_only=True)
    task_number = fields.Int(dump_only=True)
    task_key = fields.Str(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(max=255))
    description = fields.Str()
    status = fields.Str(validate=validate.OneOf(['backlog', 'todo', 'doing', 'done', 'cancelled']))
    priority = fields.Str(validate=validate.OneOf(['low', 'medium', 'high', 'critical']))
    task_type = fields.Str(validate=validate.OneOf(['task', 'story', 'bug', 'epic', 'milestone']))
    due_date = fields.Date()
    estimated_hours = fields.Float()
    actual_hours = fields.Float()
    progress_percentage = fields.Int(validate=validate.Range(min=0, max=100))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    completed_at = fields.DateTime(dump_only=True)
    is_completed = fields.Bool(dump_only=True)
    is_overdue = fields.Bool(dump_only=True)
    assignee = fields.Nested(UserSchema, dump_only=True)
    project_id = fields.Int(required=True)
    epic_id = fields.Int()
    milestone_id = fields.Int()
    milestone = fields.Nested('MilestoneSchema', dump_only=True)

class MilestoneSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(max=128))
    description = fields.Str()
    status = fields.Str(validate=validate.OneOf(['planned', 'in_progress', 'completed', 'cancelled']))
    target_date = fields.Date()
    completed_date = fields.Date(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    is_completed = fields.Bool(dump_only=True)
    is_overdue = fields.Bool(dump_only=True)
    project_id = fields.Int(required=True)
    task_count = fields.Int(dump_only=True)
    completed_task_count = fields.Int(dump_only=True)

class FileAttachmentSchema(Schema):
    id = fields.Int(dump_only=True)
    filename = fields.Str(dump_only=True)
    original_filename = fields.Str(dump_only=True)
    file_size = fields.Int(dump_only=True)
    human_readable_size = fields.Str(dump_only=True)
    mime_type = fields.Str(dump_only=True)
    file_extension = fields.Str(dump_only=True)
    is_image = fields.Bool(dump_only=True)
    is_document = fields.Bool(dump_only=True)
    is_archive = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    uploaded_by = fields.Nested(UserSchema, dump_only=True)
    task_id = fields.Int()
    project_id = fields.Int()