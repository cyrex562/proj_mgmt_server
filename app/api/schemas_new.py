from marshmallow import Schema, fields, validate, post_load
from app.models.work_item import WorkItemType, WorkItemStatus, WorkItemPriority, StoryKind

class WorkItemSchema(Schema):
    id = fields.UUID(dump_only=True)
    key_id = fields.Str(dump_only=True)
    type = fields.Str(validate=validate.OneOf([t.value for t in WorkItemType]))
    title = fields.Str(required=True, validate=validate.Length(max=255))
    description = fields.Str()
    status = fields.Str(validate=validate.OneOf([s.value for s in WorkItemStatus]))
    priority = fields.Str(validate=validate.OneOf([p.value for p in WorkItemPriority]))
    parent_id = fields.UUID(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    started_at = fields.DateTime(allow_none=True)
    due_at = fields.Date(allow_none=True)
    completed_at = fields.DateTime(dump_only=True)
    story_kind = fields.Str(validate=validate.OneOf([k.value for k in StoryKind]), allow_none=True)
    repo_url = fields.Str(validate=validate.Length(max=500), allow_none=True)
    branch = fields.Str(validate=validate.Length(max=255), allow_none=True)
    commit_hash = fields.Str(validate=validate.Length(max=40), allow_none=True)
    progress_pct = fields.Float(validate=validate.Range(min=0, max=100), allow_none=True)
    rollup_mode = fields.Bool()
    
    # Computed fields
    is_completed = fields.Bool(dump_only=True)
    is_overdue = fields.Bool(dump_only=True)
    is_blocked = fields.Bool(dump_only=True)
    
    # Relationships
    project_id = fields.UUID(required=True)
    parent = fields.Nested('self', dump_only=True)
    children = fields.Nested('self', many=True, dump_only=True)
    containers = fields.Nested('self', many=True, dump_only=True)
    members = fields.Nested('self', many=True, dump_only=True)
    predecessors = fields.Nested('self', many=True, dump_only=True)
    successors = fields.Nested('self', many=True, dump_only=True)
    labels = fields.Nested('LabelSchema', many=True, dump_only=True)
    releases = fields.Nested('ReleaseSchema', many=True, dump_only=True)
    milestones = fields.Nested('ProjectMilestoneSchema', many=True, dump_only=True)

class WorkItemMembershipSchema(Schema):
    container_id = fields.UUID(required=True)
    member_id = fields.UUID(required=True)
    relation = fields.Str(validate=validate.OneOf([t.value for t in WorkItemType]))

class WorkItemDependencySchema(Schema):
    predecessor_id = fields.UUID(required=True)
    successor_id = fields.UUID(required=True)

class LabelSchema(Schema):
    id = fields.UUID(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(max=100))
    color = fields.Str(validate=validate.Length(max=7), allow_none=True)
    description = fields.Str(allow_none=True)

class WorkItemLabelSchema(Schema):
    work_item_id = fields.UUID(required=True)
    label_id = fields.UUID(required=True)

class ReleaseSchema(Schema):
    id = fields.UUID(dump_only=True)
    project_id = fields.UUID(required=True)
    name = fields.Str(required=True, validate=validate.Length(max=255))
    version = fields.Str(validate=validate.Length(max=50), allow_none=True)
    tag = fields.Str(validate=validate.Length(max=100), allow_none=True)
    status = fields.Str(validate=validate.OneOf(['not_started', 'in_progress', 'ready', 'released']))
    released_at = fields.DateTime(allow_none=True)
    description = fields.Str(allow_none=True)
    repo_url = fields.Str(validate=validate.Length(max=500), allow_none=True)

class WorkItemReleaseSchema(Schema):
    work_item_id = fields.UUID(required=True)
    release_id = fields.UUID(required=True)

class ProjectMilestoneSchema(Schema):
    id = fields.UUID(dump_only=True)
    project_id = fields.UUID(required=True)
    name = fields.Str(required=True, validate=validate.Length(max=255))
    status = fields.Str(validate=validate.OneOf(['not_started', 'in_progress', 'done', 'slipped']))
    start_at = fields.Date(allow_none=True)
    due_at = fields.Date(allow_none=True)
    completed_at = fields.Date(allow_none=True)
    description = fields.Str(allow_none=True)

class WorkItemMilestoneSchema(Schema):
    work_item_id = fields.UUID(required=True)
    milestone_id = fields.UUID(required=True)

class ProjectSchema(Schema):
    id = fields.UUID(dump_only=True)
    key = fields.Str(required=True, validate=validate.Length(min=2, max=10))
    name = fields.Str(required=True, validate=validate.Length(max=255))
    description = fields.Str(allow_none=True)
    status = fields.Str(validate=validate.OneOf(['active', 'completed', 'archived', 'on_hold']))
    priority = fields.Str(validate=validate.OneOf(['low', 'medium', 'high', 'critical']))
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    creator_id = fields.Int(required=True)
    
    # Relationships
    members = fields.Nested('ProjectMemberSchema', many=True, dump_only=True)
    work_items = fields.Nested(WorkItemSchema, many=True, dump_only=True)
    releases = fields.Nested(ReleaseSchema, many=True, dump_only=True)
    milestones = fields.Nested(ProjectMilestoneSchema, many=True, dump_only=True)

class ProjectMemberSchema(Schema):
    id = fields.Int(dump_only=True)
    project_id = fields.UUID(required=True)
    user_id = fields.Int(required=True)
    role = fields.Str(validate=validate.OneOf(['viewer', 'member', 'admin', 'owner']))
    joined_at = fields.DateTime(dump_only=True)
    
    # Relationships
    user = fields.Nested('UserSchema', dump_only=True)

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)
    email = fields.Str(dump_only=True)
    full_name = fields.Str(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


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
    work_item_id = fields.Str()
    project_id = fields.Str()