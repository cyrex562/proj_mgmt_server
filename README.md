# Project Management Server

A comprehensive project management application built with Flask, SQLAlchemy, and modern web technologies.

## Features

- **User Management**: Users, groups, and role-based permissions
- **Project Management**: Create and manage projects with team members
- **Task Management**: Tasks, sub-tasks, milestones, epics, stories, and bugs
- **File Attachments**: Local and S3-compatible file storage
- **Multiple Views**: Kanban board and spreadsheet views for tasks
- **REST API**: Full API for frontend integration
- **Authentication**: Built-in auth with future OIDC support
- **Git Integration**: Future integration with GitLab, GitHub, and Forgejo

## Technology Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL/SQLite
- **Frontend**: TypeScript, HTMX (planned)
- **File Storage**: Local filesystem + S3-compatible services
- **Deployment**: Docker Compose
- **Authentication**: Flask-Login + future OIDC

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (optional, SQLite works for development)
- Node.js (for frontend development)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd proj_mgmt_server
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
flask init-db
```

6. Run the application:
```bash
python run.py
```

The application will be available at `http://localhost:5000`.

## Development

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

### API Documentation

The API endpoints are available under `/api/`:

- `GET /api/projects` - List user's projects
- `POST /api/projects` - Create a new project
- `GET /api/projects/{id}/tasks` - Get project tasks
- `POST /api/projects/{id}/tasks` - Create a new task
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `POST /api/tasks/{id}/files` - Upload file to task

### Project Structure

```
proj_mgmt_server/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models/              # Database models
│   │   ├── user.py         # User, Group, Permission models
│   │   ├── project.py      # Project and ProjectMember models
│   │   ├── task.py         # Task, Epic, Story, Bug, Milestone models
│   │   └── file.py         # FileAttachment model
│   ├── auth/               # Authentication blueprints
│   ├── api/                # REST API blueprints
│   └── main/               # Main application blueprints
├── migrations/             # Database migrations
├── requirements.txt        # Python dependencies
├── run.py                 # Application entry point
└── README.md
```

## Deployment

### Docker Compose

```bash
docker-compose up -d
```

### Environment Variables

Key environment variables:

- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: Database connection string
- `UPLOAD_FOLDER`: Local file upload directory
- `S3_BUCKET`: S3 bucket name (optional)
- `S3_ACCESS_KEY`: S3 access key (optional)
- `S3_SECRET_KEY`: S3 secret key (optional)

## Roadmap

- [ ] Frontend with TypeScript and HTMX
- [ ] Kanban board implementation
- [ ] Spreadsheet view for tasks
- [ ] Git server integration (GitLab/GitHub/Forgejo)
- [ ] OIDC authentication
- [ ] Advanced reporting and analytics
- [ ] Mobile app support
- [ ] Real-time notifications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.