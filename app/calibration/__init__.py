from flask import Blueprint

bp = Blueprint('calibration', __name__)

from app.calibration import routes