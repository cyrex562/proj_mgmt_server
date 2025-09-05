from app import create_app, db
from app.models.user import User, Group, Permission
from app.models.project import Project
from app.models.task import Task
from app.models.file import FileAttachment

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Group': Group,
        'Permission': Permission,
        'Project': Project,
        'Task': Task,
        'FileAttachment': FileAttachment
    }

@app.cli.command()
def init_db():
    """Initialize the database with default data"""
    db.create_all()
    
    # Create default permissions
    permissions = [
        ('create_project', 'Create new projects'),
        ('edit_project', 'Edit project details'),
        ('delete_project', 'Delete projects'),
        ('manage_members', 'Manage project members'),
        ('create_task', 'Create tasks'),
        ('edit_task', 'Edit tasks'),
        ('delete_task', 'Delete tasks'),
        ('assign_task', 'Assign tasks to users'),
        ('view_all_projects', 'View all projects'),
        ('admin_users', 'Manage users and groups')
    ]
    
    for perm_name, perm_desc in permissions:
        if not Permission.query.filter_by(name=perm_name).first():
            permission = Permission(name=perm_name, description=perm_desc)
            db.session.add(permission)
    
    # Create default groups
    groups = [
        ('users', 'Regular users', ['create_project', 'create_task', 'edit_task']),
        ('project_managers', 'Project managers', [
            'create_project', 'edit_project', 'manage_members', 
            'create_task', 'edit_task', 'delete_task', 'assign_task'
        ]),
        ('admins', 'System administrators', [
            'create_project', 'edit_project', 'delete_project', 'manage_members',
            'create_task', 'edit_task', 'delete_task', 'assign_task',
            'view_all_projects', 'admin_users'
        ])
    ]
    
    for group_name, group_desc, group_perms in groups:
        if not Group.query.filter_by(name=group_name).first():
            group = Group(name=group_name, description=group_desc)
            db.session.add(group)
            db.session.flush()  # Get the group ID
            
            # Add permissions to group
            for perm_name in group_perms:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    group.permissions.append(permission)
    
    db.session.commit()
    print("Database initialized with default data")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)