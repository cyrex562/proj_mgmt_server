#!/usr/bin/env python3
"""
Migration script to convert existing Task/Epic/Story/Bug models to unified WorkItem model.
This script preserves existing data while transitioning to the new structure.
"""

import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import create_app, db
from app.models.user import User
from app.models.project import Project as OldProject, ProjectMember as OldProjectMember
from app.models.task import Task as OldTask, Epic as OldEpic, Story as OldStory, Bug as OldBug, Milestone as OldMilestone
from app.models.work_item import (
    WorkItem, WorkItemType, WorkItemStatus, WorkItemPriority, StoryKind,
    WorkItemMembership, WorkItemDependency, Label, WorkItemLabel,
    Release, WorkItemRelease, Milestone, WorkItemMilestone
)
from app.models.project_new import Project as NewProject, ProjectCounter, ProjectMember as NewProjectMember

def migrate_projects():
    """Migrate projects to new structure with UUIDs"""
    print("Migrating projects...")
    
    old_projects = OldProject.query.all()
    project_mapping = {}
    
    for old_project in old_projects:
        # Create new project with UUID
        new_project = NewProject(
            key=old_project.key,
            name=old_project.name,
            description=old_project.description,
            status=old_project.status,
            priority=old_project.priority,
            start_date=old_project.start_date,
            end_date=old_project.end_date,
            created_at=old_project.created_at,
            updated_at=old_project.updated_at,
            creator_id=old_project.creator_id
        )
        
        db.session.add(new_project)
        db.session.flush()  # Get the UUID
        
        # Create project counter
        counter = ProjectCounter(project_id=new_project.id, next=1)
        db.session.add(counter)
        
        # Store mapping for later use
        project_mapping[old_project.id] = new_project.id
        
        print(f"  Migrated project: {old_project.name} -> {new_project.id}")
    
    db.session.commit()
    return project_mapping

def migrate_project_members(project_mapping):
    """Migrate project members"""
    print("Migrating project members...")
    
    old_members = OldProjectMember.query.all()
    
    for old_member in old_members:
        new_project_id = project_mapping.get(old_member.project_id)
        if not new_project_id:
            print(f"  Warning: Project {old_member.project_id} not found in mapping")
            continue
        
        new_member = NewProjectMember(
            project_id=new_project_id,
            user_id=old_member.user_id,
            role=old_member.role,
            joined_at=old_member.joined_at
        )
        
        db.session.add(new_member)
        print(f"  Migrated member: {old_member.user_id} -> {new_project_id}")
    
    db.session.commit()

def migrate_work_items(project_mapping):
    """Migrate tasks, epics, stories, and bugs to unified work items"""
    print("Migrating work items...")
    
    work_item_mapping = {}
    
    # Migrate tasks
    print("  Migrating tasks...")
    old_tasks = OldTask.query.all()
    for old_task in old_tasks:
        new_project_id = project_mapping.get(old_task.project_id)
        if not new_project_id:
            print(f"    Warning: Project {old_task.project_id} not found for task {old_task.id}")
            continue
        
        # Get project to generate key
        new_project = NewProject.query.get(new_project_id)
        key_id = new_project.generate_work_item_key()
        
        new_work_item = WorkItem(
            project_id=new_project_id,
            key_id=key_id,
            type=WorkItemType.TASK,
            title=old_task.title,
            description=old_task.description,
            status=map_status(old_task.status),
            priority=map_priority(old_task.priority),
            parent_id=None,  # Will handle parent relationships separately
            created_at=old_task.created_at,
            updated_at=old_task.updated_at,
            started_at=None,  # Not available in old model
            due_at=old_task.due_date,
            completed_at=old_task.completed_at,
            story_kind=None,
            repo_url=None,
            branch=None,
            commit_hash=None,
            progress_pct=old_task.progress_percentage,
            rollup_mode=False
        )
        
        db.session.add(new_work_item)
        db.session.flush()
        
        work_item_mapping[('task', old_task.id)] = new_work_item.id
        print(f"    Migrated task: {old_task.title} -> {new_work_item.key_id}")
    
    # Migrate epics
    print("  Migrating epics...")
    old_epics = OldEpic.query.all()
    for old_epic in old_epics:
        new_project_id = project_mapping.get(old_epic.project_id)
        if not new_project_id:
            print(f"    Warning: Project {old_epic.project_id} not found for epic {old_epic.id}")
            continue
        
        new_project = NewProject.query.get(new_project_id)
        key_id = new_project.generate_work_item_key()
        
        new_work_item = WorkItem(
            project_id=new_project_id,
            key_id=key_id,
            type=WorkItemType.EPIC,
            title=old_epic.title,
            description=old_epic.description,
            status=map_status(old_epic.status),
            priority=map_priority(old_epic.priority),
            parent_id=None,
            created_at=old_epic.created_at,
            updated_at=old_epic.updated_at,
            started_at=None,
            due_at=old_epic.due_date,
            completed_at=old_epic.completed_at,
            story_kind=None,
            repo_url=None,
            branch=None,
            commit_hash=None,
            progress_pct=old_epic.progress_percentage,
            rollup_mode=True  # Epics typically roll up from members
        )
        
        db.session.add(new_work_item)
        db.session.flush()
        
        work_item_mapping[('epic', old_epic.id)] = new_work_item.id
        print(f"    Migrated epic: {old_epic.title} -> {new_work_item.key_id}")
    
    # Migrate stories
    print("  Migrating stories...")
    old_stories = OldStory.query.all()
    for old_story in old_stories:
        new_project_id = project_mapping.get(old_story.project_id)
        if not new_project_id:
            print(f"    Warning: Project {old_story.project_id} not found for story {old_story.id}")
            continue
        
        new_project = NewProject.query.get(new_project_id)
        key_id = new_project.generate_work_item_key()
        
        new_work_item = WorkItem(
            project_id=new_project_id,
            key_id=key_id,
            type=WorkItemType.STORY,
            title=old_story.title,
            description=old_story.description,
            status=map_status(old_story.status),
            priority=map_priority(old_story.priority),
            parent_id=None,
            created_at=old_story.created_at,
            updated_at=old_story.updated_at,
            started_at=None,
            due_at=old_story.due_date,
            completed_at=old_story.completed_at,
            story_kind=StoryKind.USER,  # Default to user story
            repo_url=None,
            branch=None,
            commit_hash=None,
            progress_pct=old_story.progress_percentage,
            rollup_mode=False
        )
        
        db.session.add(new_work_item)
        db.session.flush()
        
        work_item_mapping[('story', old_story.id)] = new_work_item.id
        print(f"    Migrated story: {old_story.title} -> {new_work_item.key_id}")
    
    # Migrate bugs
    print("  Migrating bugs...")
    old_bugs = OldBug.query.all()
    for old_bug in old_bugs:
        new_project_id = project_mapping.get(old_bug.project_id)
        if not new_project_id:
            print(f"    Warning: Project {old_bug.project_id} not found for bug {old_bug.id}")
            continue
        
        new_project = NewProject.query.get(new_project_id)
        key_id = new_project.generate_work_item_key()
        
        new_work_item = WorkItem(
            project_id=new_project_id,
            key_id=key_id,
            type=WorkItemType.BUG,
            title=old_bug.title,
            description=old_bug.description,
            status=map_status(old_bug.status),
            priority=map_priority(old_bug.priority),
            parent_id=None,
            created_at=old_bug.created_at,
            updated_at=old_bug.updated_at,
            started_at=None,
            due_at=old_bug.due_date,
            completed_at=old_bug.completed_at,
            story_kind=None,
            repo_url=None,
            branch=None,
            commit_hash=None,
            progress_pct=old_bug.progress_percentage,
            rollup_mode=False
        )
        
        db.session.add(new_work_item)
        db.session.flush()
        
        work_item_mapping[('bug', old_bug.id)] = new_work_item.id
        print(f"    Migrated bug: {old_bug.title} -> {new_work_item.key_id}")
    
    db.session.commit()
    return work_item_mapping

def migrate_milestones(project_mapping):
    """Migrate milestones"""
    print("Migrating milestones...")
    
    milestone_mapping = {}
    old_milestones = OldMilestone.query.all()
    
    for old_milestone in old_milestones:
        new_project_id = project_mapping.get(old_milestone.project_id)
        if not new_project_id:
            print(f"  Warning: Project {old_milestone.project_id} not found for milestone {old_milestone.id}")
            continue
        
        new_milestone = Milestone(
            project_id=new_project_id,
            name=old_milestone.name,
            status=map_milestone_status(old_milestone.status),
            start_at=None,  # Not available in old model
            due_at=old_milestone.target_date,
            completed_at=old_milestone.completed_date,
            description=old_milestone.description
        )
        
        db.session.add(new_milestone)
        db.session.flush()
        
        milestone_mapping[old_milestone.id] = new_milestone.id
        print(f"  Migrated milestone: {old_milestone.name} -> {new_milestone.id}")
    
    db.session.commit()
    return milestone_mapping

def migrate_relationships(work_item_mapping, milestone_mapping):
    """Migrate relationships between work items"""
    print("Migrating relationships...")
    
    # Migrate epic-task relationships
    print("  Migrating epic-task relationships...")
    old_epics = OldEpic.query.all()
    for old_epic in old_epics:
        epic_work_item_id = work_item_mapping.get(('epic', old_epic.id))
        if not epic_work_item_id:
            continue
        
        # Find tasks assigned to this epic
        old_tasks = OldTask.query.filter_by(epic_id=old_epic.id).all()
        for old_task in old_tasks:
            task_work_item_id = work_item_mapping.get(('task', old_task.id))
            if task_work_item_id:
                membership = WorkItemMembership(
                    container_id=epic_work_item_id,
                    member_id=task_work_item_id,
                    relation=WorkItemType.EPIC
                )
                db.session.add(membership)
                print(f"    Created epic-task relationship: {epic_work_item_id} -> {task_work_item_id}")
    
    # Migrate milestone-task relationships
    print("  Migrating milestone-task relationships...")
    old_milestones = OldMilestone.query.all()
    for old_milestone in old_milestones:
        new_milestone_id = milestone_mapping.get(old_milestone.id)
        if not new_milestone_id:
            continue
        
        # Find tasks assigned to this milestone
        old_tasks = OldTask.query.filter_by(milestone_id=old_milestone.id).all()
        for old_task in old_tasks:
            task_work_item_id = work_item_mapping.get(('task', old_task.id))
            if task_work_item_id:
                milestone_relationship = WorkItemMilestone(
                    work_item_id=task_work_item_id,
                    milestone_id=new_milestone_id
                )
                db.session.add(milestone_relationship)
                print(f"    Created milestone-task relationship: {new_milestone_id} -> {task_work_item_id}")
    
    db.session.commit()

def map_status(old_status):
    """Map old status to new status enum"""
    status_mapping = {
        'backlog': WorkItemStatus.NOT_STARTED,
        'todo': WorkItemStatus.READY,
        'doing': WorkItemStatus.IN_PROGRESS,
        'done': WorkItemStatus.DONE,
        'cancelled': WorkItemStatus.CANCELLED
    }
    return status_mapping.get(old_status, WorkItemStatus.NOT_STARTED)

def map_priority(old_priority):
    """Map old priority to new priority enum"""
    priority_mapping = {
        'low': WorkItemPriority.LOW,
        'medium': WorkItemPriority.MEDIUM,
        'high': WorkItemPriority.HIGH,
        'critical': WorkItemPriority.URGENT
    }
    return priority_mapping.get(old_priority, WorkItemPriority.MEDIUM)

def map_milestone_status(old_status):
    """Map old milestone status to new status"""
    status_mapping = {
        'planned': 'not_started',
        'in_progress': 'in_progress',
        'completed': 'done',
        'cancelled': 'slipped'
    }
    return status_mapping.get(old_status, 'not_started')

def main():
    """Main migration function"""
    app = create_app()
    
    with app.app_context():
        print("Starting migration to unified WorkItem model...")
        print("=" * 50)
        
        try:
            # Create new tables
            print("Creating new tables...")
            db.create_all()
            
            # Migrate data
            project_mapping = migrate_projects()
            migrate_project_members(project_mapping)
            work_item_mapping = migrate_work_items(project_mapping)
            milestone_mapping = migrate_milestones(project_mapping)
            migrate_relationships(work_item_mapping, milestone_mapping)
            
            print("=" * 50)
            print("Migration completed successfully!")
            print(f"Migrated {len(project_mapping)} projects")
            print(f"Migrated {len(work_item_mapping)} work items")
            print(f"Migrated {len(milestone_mapping)} milestones")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    main()