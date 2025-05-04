from flask import Blueprint

# Khởi tạo blueprint cho monitoring well
analysis_bp = Blueprint('analysis', __name__)

from . import routes