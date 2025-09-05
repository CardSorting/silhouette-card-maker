from flask import Blueprint

bp = Blueprint('offset', __name__)

from app.offset import routes