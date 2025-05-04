from flask import Blueprint

# Khởi tạo blueprint cho monitoring well
analysis_bp = Blueprint('analysis_api', __name__)

from . import routes