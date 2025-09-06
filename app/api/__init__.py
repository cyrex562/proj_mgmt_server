from flask import Blueprint

bp = Blueprint('api', __name__)

from app.api import projects, files, users, work_items